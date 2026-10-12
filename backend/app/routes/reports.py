"""
GhostWatt — routes/reports.py
Campus sustainability reports and CSV data export.

SPEC §12 & Prompt Requirements:
- GET /reports/summary?from&to:
  - Actual, expected, ghost kWh, Rs, CO2.
  - Top 3 rooms with explanations and recommended actions.
  - Rooms over limit.
  - Verified savings metrics.
  - Water totals and night-flow leak alerts.
  - Complaints status.
  - Tag every figure as simulated, calculated, or verified.
  - Students get a restricted version (internal staff details hidden).
- GET /reports/export.csv:
  - Downloadable CSV report with tagged figures and recommendations.
"""
import csv
from datetime import datetime, timedelta
import io
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.reports import (
    ApplianceLeftOnRequest,
    ApplianceLeftOnResponse,
    ComplaintsReport,
    ReportSummaryResponse,
    RoomOverLimitReport,
    TopGhostRoomReport,
    VerifiedSavingsReport,
    WaterReport,
)
from app.services.expected_demand import expected_kw
from app.services.savings_verification import get_settings_rates

router = APIRouter()

ROOM_RECOMMENDATIONS = {
    "A-101": (
        "Air conditioning operating during overnight unoccupied hours with zero scheduled classes.",
        "Install 2-hour auto shut-off timers and enforce post-21:00 manual shutdown checklist.",
    ),
    "A-102": (
        "Split AC units left running continuously while room was locked for the night.",
        "Connect AC circuits to a central BMS relay with automatic 20:00 curfew cutoff.",
    ),
    "B-201": (
        "Computer workstations and fluorescent fixtures left energized after laboratory sessions.",
        "Deploy automated OS power-management sleep profiles (15-min idle) and smart power strips.",
    ),
    "C-301": (
        "Audio-visual projector running in standby and room lights left on during lunch intermission.",
        "Set projector idle auto-sleep to 10 minutes and install PIR occupancy wall switches.",
    ),
}


def _compute_report_data(
    db: Session,
    current_user: models.User,
    date_from_str: Optional[str] = None,
    date_to_str: Optional[str] = None,
) -> Dict[str, Any]:
    """Compile campus metrics across electricity, savings, water, and complaints."""
    # 1. Resolve date range
    min_date = db.query(models.MeterReading.timestamp).order_by(models.MeterReading.timestamp.asc()).first()
    max_date = db.query(models.MeterReading.timestamp).order_by(models.MeterReading.timestamp.desc()).first()

    default_start = min_date[0] if min_date else (datetime.utcnow() - timedelta(days=14))
    default_end = max_date[0] if max_date else datetime.utcnow()

    start_dt = default_start
    if date_from_str:
        try:
            start_dt = datetime.fromisoformat(date_from_str)
        except ValueError:
            pass

    end_dt = default_end
    if date_to_str:
        try:
            end_dt = datetime.fromisoformat(date_to_str)
        except ValueError:
            pass

    price_kwh, emissions_factor = get_settings_rates(db)

    # 2. Electricity & Ghost Load Metrics
    readings = (
        db.query(models.MeterReading, models.Room)
        .join(models.Room, models.MeterReading.room_id == models.Room.id)
        .filter(
            models.MeterReading.timestamp >= start_dt,
            models.MeterReading.timestamp <= end_dt,
        )
        .all()
    )

    all_eq = db.query(models.Equipment).all()
    eq_by_room = {}
    for e in all_eq:
        eq_by_room.setdefault(e.room_id, []).append(e)

    all_tt = db.query(models.TimetableEntry).filter(models.TimetableEntry.is_active == True).all()
    tt_by_room = {}
    for t in all_tt:
        tt_by_room.setdefault(t.room_id, []).append(t)

    total_actual_kwh = 0.0
    total_expected_kwh = 0.0
    total_ghost_kwh = 0.0

    room_accumulators = {}

    for mr, room in readings:
        r_eq = eq_by_room.get(room.id, [])
        r_tt = tt_by_room.get(room.id, [])

        exp_demand, _ = expected_kw(room, r_eq, r_tt, mr.timestamp)
        actual_demand = mr.actual_demand_kw

        ghost_demand = max(0.0, actual_demand - exp_demand)
        int_kwh = mr.interval_kwh
        exp_int_kwh = round(exp_demand * 0.25, 4)
        ghost_int_kwh = round(ghost_demand * 0.25, 4)

        total_actual_kwh += int_kwh
        total_expected_kwh += exp_int_kwh
        total_ghost_kwh += ghost_int_kwh

        if room.id not in room_accumulators:
            room_accumulators[room.id] = {
                "room": room,
                "actual_kwh": 0.0,
                "expected_kwh": 0.0,
                "ghost_kwh": 0.0,
            }
        room_accumulators[room.id]["actual_kwh"] += int_kwh
        room_accumulators[room.id]["expected_kwh"] += exp_int_kwh
        room_accumulators[room.id]["ghost_kwh"] += ghost_int_kwh

    cost_inr = round(total_ghost_kwh * price_kwh, 2)
    co2_kg = round(total_ghost_kwh * emissions_factor, 4)

    # 3. Top 3 Rooms with Ghost Load
    sorted_rooms = sorted(
        room_accumulators.values(),
        key=lambda x: x["ghost_kwh"],
        reverse=True,
    )

    top_3_list: List[TopGhostRoomReport] = []
    for rank, rdata in enumerate(sorted_rooms[:3], start=1):
        rm: models.Room = rdata["room"]
        rm_ghost = round(rdata["ghost_kwh"], 2)
        rm_cost = round(rm_ghost * price_kwh, 2)
        rm_co2 = round(rm_ghost * emissions_factor, 3)

        expl, rec = ROOM_RECOMMENDATIONS.get(
            rm.room_code,
            (
                "Excess power consumption recorded outside scheduled instructional hours.",
                "Conduct maintenance walkthrough and install automated occupancy sensors.",
            ),
        )

        top_3_list.append(
            TopGhostRoomReport(
                rank=rank,
                room_id=rm.id,
                room_code=rm.room_code,
                name=rm.name,
                block=rm.block,
                ghost_kwh=rm_ghost,
                cost_inr=rm_cost,
                co2_kg=rm_co2,
                explanation=expl,
                recommended_action=rec,
                tag="calculated",
            )
        )

    # 4. Rooms Over Limit (>15% excess or >5 kWh ghost)
    rooms_over_limit: List[RoomOverLimitReport] = []
    for rdata in sorted_rooms:
        rm = rdata["room"]
        act_kwh = round(rdata["actual_kwh"], 2)
        exp_kwh = round(rdata["expected_kwh"], 2)
        gh_kwh = round(rdata["ghost_kwh"], 2)

        if gh_kwh > 5.0 or (exp_kwh > 0 and act_kwh > exp_kwh * 1.15):
            excess_pct = round(((act_kwh - exp_kwh) / max(0.1, exp_kwh)) * 100, 1)
            rooms_over_limit.append(
                RoomOverLimitReport(
                    room_code=rm.room_code,
                    name=rm.name,
                    actual_kwh=act_kwh,
                    expected_kwh=exp_kwh,
                    ghost_kwh=gh_kwh,
                    excess_percentage=excess_pct,
                    tag="calculated",
                )
            )

    # 5. Verified Savings
    savings_records = db.query(models.SavingsRecord).all()
    actions = db.query(models.Action).all()

    verified_kwh = round(sum(s.credited_kwh for s in savings_records), 4)
    savings_money = round(sum(s.monetary_saving_inr for s in savings_records), 2)
    savings_co2 = round(sum(s.emissions_kg for s in savings_records), 4)

    eq_map = {(e.room_id, e.kind.lower()): float(e.rated_kw * e.count) for e in all_eq}
    claimed_kwh = 0.0
    for act in actions:
        rating = eq_map.get((act.room_id, act.equipment.lower()), 0.0)
        claimed_kwh += rating * 0.25

    verified_actions_cnt = sum(
        1 for a in actions if str(a.verification_status).upper() == "VERIFIED"
    )

    verified_report = VerifiedSavingsReport(
        claimed_kwh=round(claimed_kwh, 4),
        verified_kwh=verified_kwh,
        monetary_saving_inr=savings_money,
        emissions_co2_kg=savings_co2,
        action_count=len(actions),
        verified_count=verified_actions_cnt,
        tag="verified",
    )

    # 6. Water Totals & Leak Alerts
    water_readings = (
        db.query(models.WaterReading)
        .filter(
            models.WaterReading.timestamp >= start_dt,
            models.WaterReading.timestamp <= end_dt,
        )
        .all()
    )
    total_litres = round(sum(w.interval_litres for w in water_readings), 1)

    # 1 AM - 4 AM excess litres
    night_excess = 0.0
    for w in water_readings:
        if w.timestamp.hour in (1, 2, 3) and w.flow_rate_lph > w.expected_baseline_lph:
            night_excess += (w.flow_rate_lph - w.expected_baseline_lph) * 1.0

    water_alerts = db.query(models.WaterAlert).all()
    active_alerts = sum(1 for a in water_alerts if a.status == "SUSPECTED")

    water_report = WaterReport(
        total_litres=total_litres,
        tag_total="simulated",
        night_excess_litres=round(night_excess, 1),
        tag_excess="calculated",
        leak_alerts_count=len(water_alerts),
        active_alerts_count=active_alerts,
        tag_alerts="calculated",
    )

    # 7. Complaints (Role-based restriction)
    is_student = (current_user.role == "student")
    all_complaints = db.query(models.Complaint).all()
    total_complaints = len(all_complaints)
    resolved_complaints = sum(1 for c in all_complaints if c.status == "resolved")
    open_complaints = total_complaints - resolved_complaints

    if is_student:
        student_own = sum(1 for c in all_complaints if c.student_id == current_user.id)
        complaints_report = ComplaintsReport(
            total_complaints=total_complaints,
            resolved_complaints=resolved_complaints,
            open_complaints=open_complaints,
            tag="calculated",
            is_restricted=True,
            own_complaints=student_own,
            category_breakdown=None,
            building_breakdown=None,
        )
    else:
        cat_counts = {}
        bld_counts = {}
        for c in all_complaints:
            cat_counts[c.category] = cat_counts.get(c.category, 0) + 1
            bld_counts[c.building] = bld_counts.get(c.building, 0) + 1

        complaints_report = ComplaintsReport(
            total_complaints=total_complaints,
            resolved_complaints=resolved_complaints,
            open_complaints=open_complaints,
            tag="calculated",
            is_restricted=False,
            own_complaints=None,
            category_breakdown=cat_counts,
            building_breakdown=bld_counts,
        )

    data_tags = {
        "actual_kwh": "simulated",
        "expected_kwh": "calculated",
        "ghost_kwh": "calculated",
        "cost_inr": "calculated",
        "co2_kg": "calculated",
        "top_ghost_rooms": "calculated",
        "rooms_over_limit": "calculated",
        "verified_savings": "verified",
        "total_water_litres": "simulated",
        "night_excess_litres": "calculated",
        "water_leak_alerts": "calculated",
        "complaints": "calculated",
    }

    # 8. Equivalents & Assumptions (SPEC §13)
    s_rows = db.query(models.Setting).all()
    cfg = {s.key: s.value for s in s_rows}
    fan_watts = float(cfg.get("fan_watt_equivalent", 75.0))
    bucket_litres = float(cfg.get("bucket_litres", 15.0))

    from app.services.carbon_calculator import fan_equivalents, bucket_equivalents
    # Estimate average ghost kW over duration
    duration_hours = max(1.0, (len(readings) / max(1, 12)) * 0.25)
    avg_ghost_kw = (total_ghost_kwh / duration_hours) if duration_hours > 0 else 0.0
    fan_res = fan_equivalents(avg_ghost_kw, fan_watts)
    bucket_res = bucket_equivalents(total_litres, bucket_litres)

    return {
        "date_from": start_dt.isoformat(),
        "date_to": end_dt.isoformat(),
        "actual_kwh": round(total_actual_kwh, 2),
        "expected_kwh": round(total_expected_kwh, 2),
        "ghost_kwh": round(total_ghost_kwh, 2),
        "cost_inr": cost_inr,
        "co2_kg": co2_kg,
        "fan_equivalents": fan_res["value"],
        "bucket_equivalents": bucket_res["value"],
        "fan_assumption": fan_res["assumption"],
        "bucket_assumption": bucket_res["assumption"],
        "assumptions": {
            "fan": fan_res["assumption"],
            "bucket": bucket_res["assumption"],
            "tariff": f"Commercial campus tariff of Rs {price_kwh:.2f} per kWh",
            "emissions": f"Regional grid emission factor of {emissions_factor:.2f} kg CO2/kWh",
        },
        "top_ghost_rooms": top_3_list,
        "rooms_over_limit": rooms_over_limit,
        "verified_savings": verified_report,
        "water": water_report,
        "complaints": complaints_report,
        "data_tags": data_tags,
        "is_restricted": is_student,
        "data_source": "simulated",
    }


@router.get(
    "/summary",
    response_model=ReportSummaryResponse,
    summary="Get campus sustainability executive report",
)
def get_report_summary(
    date_from: Optional[str] = Query(None, alias="from", description="Start timestamp (ISO)"),
    date_to: Optional[str] = Query(None, alias="to", description="End timestamp (ISO)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Generate comprehensive campus sustainability report:
    - Actual vs Expected vs Ghost Load electricity consumption.
    - Top 3 rooms with excess ghost load, root causes, and recommended actions.
    - Rooms operating over limit.
    - Verified savings meter audit totals.
    - Water consumption, night leaks, and student complaint statistics.
    - Every figure tagged as 'simulated', 'calculated', or 'verified'.
    - Students receive a privacy-restricted version.
    """
    report_dict = _compute_report_data(
        db=db,
        current_user=current_user,
        date_from_str=date_from,
        date_to_str=date_to,
    )
    return ReportSummaryResponse(**report_dict)


@router.get(
    "/export.csv",
    summary="Download sustainability report as CSV with data tags",
)
def export_report_csv(
    date_from: Optional[str] = Query(None, alias="from", description="Start timestamp (ISO)"),
    date_to: Optional[str] = Query(None, alias="to", description="End timestamp (ISO)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Generate downloadable CSV format campus sustainability report.
    Includes data tags ('simulated', 'calculated', 'verified') on every line.
    """
    data = _compute_report_data(
        db=db,
        current_user=current_user,
        date_from_str=date_from,
        date_to_str=date_to,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # CSV Header
    writer.writerow(["Section", "Metric", "Value", "Unit", "Data Tag", "Details / Notes"])

    # Executive Overview
    writer.writerow(["Executive Summary", "Reporting Period Start", data["date_from"], "ISO", "system", ""])
    writer.writerow(["Executive Summary", "Reporting Period End", data["date_to"], "ISO", "system", ""])
    writer.writerow(["Electricity", "Actual Electricity Consumption", data["actual_kwh"], "kWh", "simulated", "Total energy recorded by campus room meters"])
    writer.writerow(["Electricity", "Expected Baseline Consumption", data["expected_kwh"], "kWh", "calculated", "Timetable & equipment based expectation"])
    writer.writerow(["Electricity", "Ghost Load Electricity Waste", data["ghost_kwh"], "kWh", "calculated", "max(0, Actual - Expected) avoidable waste"])
    writer.writerow(["Financial & Carbon", "Ghost Load Monetary Loss", data["cost_inr"], "INR", "calculated", "Tariff based on configured electricity rate"])
    writer.writerow(["Financial & Carbon", "Ghost Load Carbon Emissions", data["co2_kg"], "kg CO2", "calculated", "Emissions factor based on grid intensity"])

    # Top 3 Ghost Load Rooms
    for r in data["top_ghost_rooms"]:
        writer.writerow([
            "Top Ghost Load Rooms",
            f"Rank #{r.rank} - {r.room_code} ({r.name})",
            r.ghost_kwh,
            "kWh",
            r.tag,
            f"Explanation: {r.explanation} | Recommendation: {r.recommended_action}",
        ])

    # Rooms Over Limit
    for rol in data["rooms_over_limit"]:
        writer.writerow([
            "Rooms Over Limit",
            f"{rol.room_code} ({rol.name})",
            f"+{rol.excess_percentage}%",
            "%",
            rol.tag,
            f"Actual: {rol.actual_kwh} kWh vs Expected: {rol.expected_kwh} kWh",
        ])

    # Verified Savings
    vs: VerifiedSavingsReport = data["verified_savings"]
    writer.writerow(["Verified Savings", "Claimed Savings Estimate", vs.claimed_kwh, "kWh", "calculated", "Theoretical appliance rating estimate"])
    writer.writerow(["Verified Savings", "Verified Energy Reductions", vs.verified_kwh, "kWh", vs.tag, "Confirmed reduction backed by meter readings"])
    writer.writerow(["Verified Savings", "Verified Cost Avoidance", vs.monetary_saving_inr, "INR", vs.tag, "Financial savings credited"])
    writer.writerow(["Verified Savings", "Verified Carbon Avoidance", vs.emissions_co2_kg, "kg CO2", vs.tag, "Carbon emissions avoided"])
    writer.writerow(["Verified Savings", "Corrective Actions Count", f"{vs.verified_count}/{vs.action_count}", "actions", vs.tag, "Verified actions out of total recorded"])

    # Water Conservation
    w: WaterReport = data["water"]
    writer.writerow(["Water Conservation", "Total Water Consumed", w.total_litres, "Litres", w.tag_total, "Campus water meter readings"])
    writer.writerow(["Water Conservation", "Night-flow Quiescent Excess", w.night_excess_litres, "Litres", w.tag_excess, "Unusual flow observed during 01:00-04:00"])
    writer.writerow(["Water Conservation", "Leak Alerts Total", w.leak_alerts_count, "alerts", w.tag_alerts, f"Active/Suspected leaks: {w.active_alerts_count}"])

    # Complaints
    c: ComplaintsReport = data["complaints"]
    writer.writerow(["Facility Complaints", "Total Complaints Submitted", c.total_complaints, "count", c.tag, ""])
    writer.writerow(["Facility Complaints", "Resolved Complaints", c.resolved_complaints, "count", c.tag, ""])
    writer.writerow(["Facility Complaints", "Open / In-Progress Complaints", c.open_complaints, "count", c.tag, ""])
    if c.is_restricted:
        writer.writerow(["Facility Complaints", "Student Own Complaints", c.own_complaints, "count", c.tag, "Restricted view for student account"])
    else:
        if c.category_breakdown:
            for cat, cnt in c.category_breakdown.items():
                writer.writerow(["Complaints Breakdown", f"Category: {cat}", cnt, "count", c.tag, "Admin campus breakdown"])

    csv_content = output.getvalue()
    filename = f"ghostwatt_sustainability_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/appliance-left-on",
    response_model=ApplianceLeftOnResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report an appliance left on in an unoccupied room (Students & Admins)",
)
def report_appliance_left_on(
    payload: ApplianceLeftOnRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Submits an observation that an electrical appliance was left running.
    Creates a signal and administrative notification visible to campus facility staff.
    """
    # 1. Resolve room
    room = None
    r_id_str = str(payload.room_id).strip()
    if r_id_str.isdigit():
        room = db.query(models.Room).filter(models.Room.id == int(r_id_str)).first()
    if not room:
        clean_code = r_id_str.replace("Room", "").strip().upper()
        room = db.query(models.Room).filter(models.Room.room_code == clean_code).first()
    if not room:
        room = db.query(models.Room).filter(models.Room.room_code.ilike(f"%{r_id_str}%")).first()

    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room '{payload.room_id}' not found.",
        )

    # 2. Determine appliance kind
    eq_kind = (payload.equipment_type or payload.appliance_kind or "appliance").lower()

    # 3. Generate unique complaint code
    count = db.query(models.Complaint).count()
    signal_code = f"AL-{count + 1:04d}"

    # 4. Create complaint record
    complaint = models.Complaint(
        student_id=current_user.id,
        complaint_code=signal_code,
        building=room.block,
        location_detail=f"Room {room.room_code} ({room.name})",
        category="appliance_left_on",
        description=f"Appliance Left On: {eq_kind.upper()}. {payload.notes or ''}".strip(),
        status="submitted",
        created_at=datetime.utcnow(),
    )
    db.add(complaint)
    db.flush()

    # 5. History and notification for facility staff
    history = models.ComplaintHistory(
        complaint_id=complaint.id,
        changed_by=current_user.id,
        old_status=None,
        new_status="submitted",
        note=f"Signal reported by {current_user.email}: {eq_kind} left on",
        changed_at=datetime.utcnow(),
    )
    db.add(history)

    notification = models.AdminNotification(
        title="Appliance Left On Signal",
        message=f"Appliance Left On reported in {room.room_code} ({eq_kind.upper()}) by {current_user.email}",
        notification_type="complaint",
        reference_id=complaint.complaint_code,
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.add(notification)

    db.commit()
    db.refresh(complaint)

    return ApplianceLeftOnResponse(
        status="signal_recorded",
        signal_id=complaint.complaint_code,
        complaint_id=complaint.id,
        complaint_code=complaint.complaint_code,
        category="appliance_left_on",
        room_code=room.room_code,
        block=room.block,
        equipment_type=eq_kind,
        reported_by=current_user.email,
        created_at=complaint.created_at.isoformat(),
        message=f"Signal recorded for {room.room_code}. Notification sent to administrators.",
        data_source="simulated",
    )
