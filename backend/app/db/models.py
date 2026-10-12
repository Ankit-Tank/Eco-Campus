"""
GhostWatt — app/db/models.py
SQLAlchemy ORM models for all entities defined in SPEC §16 / ARCHITECTURE.

Tables
------
users, rooms, equipment, timetable, meter_readings, actions,
savings_records, water_locations, water_readings, water_alerts,
complaints, complaint_history, settings, sim_state
"""
import json
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Index, Integer, String, Text,
    Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class User(Base):
    """Campus users with role-based access (admin / student)."""

    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(100), unique=True, nullable=False, index=True)
    email         = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    role          = Column(
        SAEnum("admin", "student", name="user_role"),
        nullable=False,
        default="student",
    )
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=_now)

    # Relationships
    actions       = relationship("Action", back_populates="user")
    complaints    = relationship(
        "Complaint", back_populates="student", foreign_keys="Complaint.student_id"
    )


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------
class Room(Base):
    """Physical campus rooms across blocks A, B, and C."""

    __tablename__ = "rooms"

    id               = Column(Integer, primary_key=True, index=True)
    room_code        = Column(String(20), unique=True, nullable=False, index=True)  # e.g. "A-101"
    block            = Column(String(10), nullable=False)                           # "A", "B", "C"
    name             = Column(String(100), nullable=False)
    room_type        = Column(String(50), nullable=False)   # classroom / lab / seminar / reading_room
    capacity         = Column(Integer, default=40)
    idle_baseline_kw = Column(Float, default=0.1)           # expected kW when empty
    is_active        = Column(Boolean, default=True)

    # Relationships
    equipment        = relationship("Equipment", back_populates="room", cascade="all, delete-orphan")
    timetable        = relationship("TimetableEntry", back_populates="room", cascade="all, delete-orphan")
    meter_readings   = relationship("MeterReading", back_populates="room", cascade="all, delete-orphan")
    actions          = relationship("Action", back_populates="room")

    @property
    def equipment_config(self) -> str:
        """JSON-formatted equipment map for backward compatibility with expected_demand."""
        eq_map = {}
        for eq in self.equipment:
            eq_map[eq.kind] = eq.rated_kw * eq.count * (eq.expected_in_class if eq.expected_in_class is not None else 1.0)
        return json.dumps(eq_map)


# ---------------------------------------------------------------------------
# Equipment (normalized — one row per appliance kind per room)
# ---------------------------------------------------------------------------
class Equipment(Base):
    """
    Discrete equipment installed in a room.
    kind: light | fan | ac | projector | pc | lab_equipment
    rated_kw: kW rating per unit
    count: number of units installed
    state: ON | OFF (current simulated state)
    expected_in_class: fraction of units expected ON during class (0.0–1.0)
    """

    __tablename__ = "equipment"

    id                = Column(Integer, primary_key=True, index=True)
    room_id           = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)
    kind              = Column(
        SAEnum("light", "fan", "ac", "projector", "pc", "lab_equipment",
               name="equipment_kind"),
        nullable=False,
    )
    rated_kw          = Column(Float, nullable=False)         # kW per unit
    count             = Column(Integer, default=1)             # number of units
    state             = Column(
        SAEnum("ON", "OFF", name="equipment_state"),
        nullable=False,
        default="OFF",
    )
    expected_in_class = Column(Float, default=1.0)            # factor 0.0 - 1.0

    room = relationship("Room", back_populates="equipment")


# ---------------------------------------------------------------------------
# Timetable
# ---------------------------------------------------------------------------
class TimetableEntry(Base):
    """Weekly recurring timetable slots (Mon–Sat, 09:00–17:00 with gaps)."""

    __tablename__ = "timetable"

    id                = Column(Integer, primary_key=True, index=True)
    room_id           = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)
    day_of_week       = Column(Integer, nullable=False)    # 0=Mon … 5=Sat, 6=Sun
    start_time        = Column(String(5), nullable=False)  # "HH:MM"
    end_time          = Column(String(5), nullable=False)  # "HH:MM"
    activity          = Column(String(200), default="Class")
    expected_students = Column(Integer, default=30)
    is_active         = Column(Boolean, default=True)

    room = relationship("Room", back_populates="timetable")


# Alias for explicit naming
Timetable = TimetableEntry


# ---------------------------------------------------------------------------
# Meter Readings — composite index on (room_id, timestamp)
# ---------------------------------------------------------------------------
class MeterReading(Base):
    """15-minute electricity meter readings per room."""

    __tablename__ = "meter_readings"

    __table_args__ = (
        Index("ix_meter_readings_room_ts", "room_id", "timestamp"),
    )

    id               = Column(Integer, primary_key=True, index=True)
    room_id          = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    timestamp        = Column(DateTime, nullable=False, index=True)
    actual_demand_kw = Column(Float, nullable=False)
    interval_kwh     = Column(Float, nullable=False)    # actual_demand_kw × 0.25
    source           = Column(String(50), default="simulated")
    is_simulated     = Column(Boolean, default=True)

    room = relationship("Room", back_populates="meter_readings")


# ---------------------------------------------------------------------------
# Actions (corrective)
# ---------------------------------------------------------------------------
class Action(Base):
    """User-triggered corrective actions (e.g. switch off AC)."""

    __tablename__ = "actions"

    id                  = Column(Integer, primary_key=True, index=True)
    room_id             = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type         = Column(String(50), nullable=False)    # e.g. "switch_off"
    equipment           = Column(String(100), nullable=False)   # e.g. "AC"
    timestamp           = Column(DateTime, default=_now)
    notes               = Column(Text, default="")
    verification_status = Column(
        SAEnum("pending", "verified", "no_reduction", name="action_verify_status"),
        default="pending",
    )

    room           = relationship("Room", back_populates="actions")
    user           = relationship("User", back_populates="actions")
    savings_records = relationship("SavingsRecord", back_populates="action", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Savings Records — UNIQUE (action_id, interval_start)
# ---------------------------------------------------------------------------
class SavingsRecord(Base):
    """
    Pre/post action energy reduction per interval.
    UNIQUE constraint on (action_id, interval_start).
    """

    __tablename__ = "savings_records"

    __table_args__ = (
        UniqueConstraint("action_id", "interval_start", name="uq_savings_records_action_interval"),
    )

    id                  = Column(Integer, primary_key=True, index=True)
    action_id           = Column(Integer, ForeignKey("actions.id"), nullable=False, index=True)
    interval_start      = Column(DateTime, nullable=False)      # 15-min window start
    pre_avg_kw          = Column(Float, nullable=False)
    post_avg_kw         = Column(Float, nullable=False)
    reduction_kw        = Column(Float, nullable=False)         # max(0, pre − post)
    credited_kwh        = Column(Float, nullable=False)         # reduction_kw × 0.25
    monetary_saving_inr = Column(Float, nullable=False)
    emissions_kg        = Column(Float, nullable=False)
    verification_status = Column(
        SAEnum("verified", "no_reduction", name="savings_verify_status"),
        nullable=False,
    )
    is_simulated        = Column(Boolean, default=True)
    created_at          = Column(DateTime, default=_now)

    action = relationship("Action", back_populates="savings_records")


# ---------------------------------------------------------------------------
# Water Locations
# ---------------------------------------------------------------------------
class WaterLocation(Base):
    """Named water monitoring points (taps, overhead tanks, main lines)."""

    __tablename__ = "water_locations"

    id                     = Column(Integer, primary_key=True, index=True)
    name                   = Column(String(100), nullable=False)
    building               = Column(String(50), nullable=False)
    description            = Column(String(200), default="")
    low_flow_threshold_lph = Column(Float, default=50.0)   # night-flow alert threshold

    readings = relationship("WaterReading", back_populates="location", cascade="all, delete-orphan")
    alerts   = relationship("WaterAlert", back_populates="location", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Water Readings
# ---------------------------------------------------------------------------
class WaterReading(Base):
    """Hourly simulated water-flow readings per location."""

    __tablename__ = "water_readings"

    id                    = Column(Integer, primary_key=True, index=True)
    location_id           = Column(Integer, ForeignKey("water_locations.id"), nullable=False, index=True)
    timestamp             = Column(DateTime, nullable=False, index=True)
    flow_rate_lph         = Column(Float, nullable=False)
    interval_litres       = Column(Float, nullable=False)   # flow_rate_lph × 1.0 (hourly)
    expected_baseline_lph = Column(Float, default=50.0)
    source                = Column(String(50), default="simulated")
    is_simulated          = Column(Boolean, default=True)

    location = relationship("WaterLocation", back_populates="readings")


# ---------------------------------------------------------------------------
# Water Alerts
# ---------------------------------------------------------------------------
class WaterAlert(Base):
    """
    Automated or manual anomaly alerts for water monitoring.
    status: SUSPECTED | CONFIRMED | FALSE_ALARM
    inspection_notes: observations or findings from maintenance staff
    """

    __tablename__ = "water_alerts"

    id               = Column(Integer, primary_key=True, index=True)
    location_id      = Column(Integer, ForeignKey("water_locations.id"), nullable=False, index=True)
    detected_at      = Column(DateTime, nullable=False, default=_now)
    window_start     = Column(DateTime, nullable=False)    # start of anomalous period
    window_end       = Column(DateTime, nullable=False)    # end of anomalous period
    avg_flow_lph     = Column(Float, nullable=False)
    baseline_lph     = Column(Float, nullable=False)
    status           = Column(
        SAEnum("SUSPECTED", "CONFIRMED", "FALSE_ALARM", name="water_alert_status"),
        nullable=False,
        default="SUSPECTED",
    )
    inspection_notes = Column(Text, default="")
    resolved_at      = Column(DateTime, nullable=True)

    location = relationship("WaterLocation", back_populates="alerts")


# ---------------------------------------------------------------------------
# Complaints
# ---------------------------------------------------------------------------
class Complaint(Base):
    """Student-submitted water / facility complaints."""

    __tablename__ = "complaints"

    id               = Column(Integer, primary_key=True, index=True)
    complaint_code   = Column(String(20), unique=True, nullable=False)  # e.g. "WC-0001"
    student_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    building         = Column(String(50), nullable=False)
    location_detail  = Column(String(200), nullable=False)
    category         = Column(
        SAEnum(
            "leaking_tap", "broken_pipe", "overflowing_tank",
            "low_pressure", "general_wastage",
            name="complaint_category",
        ),
        nullable=False,
    )
    description      = Column(Text, nullable=False)
    attachment_path  = Column(String(300), nullable=True)
    assigned_to      = Column(Integer, ForeignKey("users.id"), nullable=True)
    status           = Column(
        SAEnum(
            "submitted", "acknowledged", "assigned",
            "in_progress", "resolved", "reopened",
            name="complaint_status",
        ),
        default="submitted",
    )
    created_at       = Column(DateTime, default=_now)
    updated_at       = Column(DateTime, default=_now, onupdate=_now)
    resolution_notes = Column(Text, default="")

    student = relationship("User", back_populates="complaints", foreign_keys=[student_id])
    history = relationship(
        "ComplaintHistory", back_populates="complaint", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Complaint History (audit trail)
# ---------------------------------------------------------------------------
class ComplaintHistory(Base):
    """Immutable audit trail of status transitions for complaints."""

    __tablename__ = "complaint_history"

    id           = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    changed_by   = Column(Integer, ForeignKey("users.id"), nullable=True)
    old_status   = Column(String(50), nullable=True)
    new_status   = Column(String(50), nullable=False)
    note         = Column(Text, default="")
    changed_at   = Column(DateTime, default=_now)

    complaint = relationship("Complaint", back_populates="history")


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
class Setting(Base):
    """Configurable system parameters (prices, emissions, thresholds)."""

    __tablename__ = "settings"

    id          = Column(Integer, primary_key=True, index=True)
    key         = Column(String(100), unique=True, nullable=False)
    value       = Column(String(500), nullable=False)
    description = Column(Text, default="")
    updated_at  = Column(DateTime, default=_now, onupdate=_now)


# ---------------------------------------------------------------------------
# Simulation State (single row: id=1)
# ---------------------------------------------------------------------------
class SimState(Base):
    """
    Simulation control table. Always maintains a single row (id=1).
    virtual_now : simulated current datetime
    speed       : simulation speed factor (e.g. 1.0 = 1x)
    running     : simulation running flag
    """

    __tablename__ = "sim_state"

    id          = Column(Integer, primary_key=True, default=1)
    virtual_now = Column(DateTime, nullable=False, default=_now)
    speed       = Column(Float, nullable=False, default=1.0)
    running     = Column(Boolean, nullable=False, default=False)
