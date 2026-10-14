"""
Eco-Campus — services/data_generator.py
Reproducible seed data generator for rooms, equipment, weekly timetables,
14-day 15-minute electricity meter readings with deliberate ghost load scenarios,
hourly water readings with suspected leak patterns, users, settings, and sim state.

Features
--------
- Seeded RNG (reproducible, seed=42)
- 12 rooms across Blocks A, B, C (classrooms, labs, seminar halls, reading room)
- Normalized equipment table with rated kW, counts, and in-class expected factors
- Mon–Sat weekly timetables (09:00–17:00) with realistic lunch and free gaps
- 14 days of 15-minute readings (1,344 intervals/room = 16,128 total readings):
    actual = idle_baseline + sum(rated_kw of ON equipment) + small noise
- 4 Deliberate electricity scenarios:
    1. A-102: AC on overnight (overnight ghost load)
    2. B-201: Lab equipment / workstations on after class (evening ghost load)
    3. C-301: Projector and lights on during lunch gap (midday ghost load)
    4. C-302: Legitimately above expected during big hackathon class (explainability)
- 6 Water locations with realistic circadian flow profiles (14 days × 24 h = 336/loc)
- 1 Water leak scenario at Block C Washrooms (1–4 AM high flow) + WaterAlert record
- Seed users (admin, student, student2) with bcrypt-hashed passwords
- Default settings (prices, emissions, equipment constants)
- Single-row sim_state with virtual_now initialized
- CSV and JSON dump written to backend/data/generated_sample_data/
- Idempotent execution (drops/creates tables or clears records before seeding)
"""
import csv
import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db import models
from app.db.database import create_all_tables, drop_all_tables

# Fixed reference timeline: 14 days ending at 2026-10-12 00:00:00 (Monday)
BASE_END_DATE = datetime(2026, 10, 12, 0, 0, 0)
BASE_START_DATE = BASE_END_DATE - timedelta(days=14)  # 2026-09-28 00:00:00 (Monday)


# ---------------------------------------------------------------------------
# Room Definitions (12 rooms across 3 blocks)
# ---------------------------------------------------------------------------
ROOM_DEFINITIONS = [
    # Block A: Academic & Lecture Halls
    {
        "room_code": "A-101",
        "block": "A",
        "name": "Lecture Hall A-101",
        "room_type": "classroom",
        "capacity": 60,
        "idle_baseline_kw": 0.12,
        "equipment": [
            {"kind": "light", "rated_kw": 0.04, "count": 14, "expected_in_class": 1.0},
            {"kind": "fan", "rated_kw": 0.075, "count": 8, "expected_in_class": 1.0},
            {"kind": "ac", "rated_kw": 1.8, "count": 2, "expected_in_class": 1.0},
            {"kind": "projector", "rated_kw": 0.35, "count": 1, "expected_in_class": 0.8},
        ],
    },
    {
        "room_code": "A-102",
        "block": "A",
        "name": "Classroom A-102",
        "room_type": "classroom",
        "capacity": 45,
        "idle_baseline_kw": 0.10,
        "equipment": [
            {"kind": "light", "rated_kw": 0.04, "count": 10, "expected_in_class": 1.0},
            {"kind": "fan", "rated_kw": 0.075, "count": 6, "expected_in_class": 1.0},
            {"kind": "ac", "rated_kw": 1.8, "count": 2, "expected_in_class": 1.0},
            {"kind": "projector", "rated_kw": 0.35, "count": 1, "expected_in_class": 0.7},
        ],
    },
    {
        "room_code": "A-201",
        "block": "A",
        "name": "Seminar Hall A-201",
        "room_type": "seminar",
        "capacity": 120,
        "idle_baseline_kw": 0.25,
        "equipment": [
            {"kind": "light", "rated_kw": 0.05, "count": 24, "expected_in_class": 1.0},
            {"kind": "fan", "rated_kw": 0.075, "count": 12, "expected_in_class": 1.0},
            {"kind": "ac", "rated_kw": 2.2, "count": 4, "expected_in_class": 1.0},
            {"kind": "projector", "rated_kw": 0.50, "count": 2, "expected_in_class": 1.0},
        ],
    },
    {
        "room_code": "A-202",
        "block": "A",
        "name": "Central Reading Room",
        "room_type": "reading_room",
        "capacity": 55,
        "idle_baseline_kw": 0.15,
        "equipment": [
            {"kind": "light", "rated_kw": 0.03, "count": 20, "expected_in_class": 0.9},
            {"kind": "fan", "rated_kw": 0.075, "count": 8, "expected_in_class": 0.8},
            {"kind": "ac", "rated_kw": 2.0, "count": 2, "expected_in_class": 1.0},
            {"kind": "pc", "rated_kw": 0.12, "count": 6, "expected_in_class": 0.6},
        ],
    },

    # Block B: Science & Engineering Labs
    {
        "room_code": "B-101",
        "block": "B",
        "name": "Classroom B-101",
        "room_type": "classroom",
        "capacity": 50,
        "idle_baseline_kw": 0.10,
        "equipment": [
            {"kind": "light", "rated_kw": 0.04, "count": 12, "expected_in_class": 1.0},
            {"kind": "fan", "rated_kw": 0.075, "count": 6, "expected_in_class": 1.0},
            {"kind": "projector", "rated_kw": 0.35, "count": 1, "expected_in_class": 0.8},
        ],
    },
    {
        "room_code": "B-102",
        "block": "B",
        "name": "Classroom B-102",
        "room_type": "classroom",
        "capacity": 50,
        "idle_baseline_kw": 0.10,
        "equipment": [
            {"kind": "light", "rated_kw": 0.04, "count": 12, "expected_in_class": 1.0},
            {"kind": "fan", "rated_kw": 0.075, "count": 6, "expected_in_class": 1.0},
            {"kind": "ac", "rated_kw": 1.8, "count": 2, "expected_in_class": 1.0},
        ],
    },
    {
        "room_code": "B-201",
        "block": "B",
        "name": "Computer Systems Lab",
        "room_type": "lab",
        "capacity": 40,
        "idle_baseline_kw": 0.30,
        "equipment": [
            {"kind": "light", "rated_kw": 0.04, "count": 16, "expected_in_class": 1.0},
            {"kind": "ac", "rated_kw": 2.0, "count": 2, "expected_in_class": 1.0},
            {"kind": "pc", "rated_kw": 0.15, "count": 30, "expected_in_class": 0.9},
            {"kind": "projector", "rated_kw": 0.35, "count": 1, "expected_in_class": 0.8},
        ],
    },
    {
        "room_code": "B-202",
        "block": "B",
        "name": "IoT & Electronics Lab",
        "room_type": "lab",
        "capacity": 35,
        "idle_baseline_kw": 0.20,
        "equipment": [
            {"kind": "light", "rated_kw": 0.04, "count": 14, "expected_in_class": 1.0},
            {"kind": "fan", "rated_kw": 0.075, "count": 6, "expected_in_class": 1.0},
            {"kind": "pc", "rated_kw": 0.15, "count": 15, "expected_in_class": 0.8},
            {"kind": "lab_equipment", "rated_kw": 0.40, "count": 10, "expected_in_class": 0.7},
        ],
    },

    # Block C: Innovation & Research
    {
        "room_code": "C-101",
        "block": "C",
        "name": "Classroom C-101",
        "room_type": "classroom",
        "capacity": 45,
        "idle_baseline_kw": 0.10,
        "equipment": [
            {"kind": "light", "rated_kw": 0.04, "count": 10, "expected_in_class": 1.0},
            {"kind": "fan", "rated_kw": 0.075, "count": 6, "expected_in_class": 1.0},
            {"kind": "projector", "rated_kw": 0.35, "count": 1, "expected_in_class": 0.8},
        ],
    },
    {
        "room_code": "C-201",
        "block": "C",
        "name": "Auditorium C-201",
        "room_type": "seminar",
        "capacity": 150,
        "idle_baseline_kw": 0.35,
        "equipment": [
            {"kind": "light", "rated_kw": 0.05, "count": 30, "expected_in_class": 1.0},
            {"kind": "fan", "rated_kw": 0.075, "count": 16, "expected_in_class": 1.0},
            {"kind": "ac", "rated_kw": 2.5, "count": 4, "expected_in_class": 1.0},
            {"kind": "projector", "rated_kw": 0.60, "count": 2, "expected_in_class": 1.0},
        ],
    },
    {
        "room_code": "C-301",
        "block": "C",
        "name": "Smart Classroom C-301",
        "room_type": "classroom",
        "capacity": 55,
        "idle_baseline_kw": 0.12,
        "equipment": [
            {"kind": "light", "rated_kw": 0.04, "count": 12, "expected_in_class": 1.0},
            {"kind": "fan", "rated_kw": 0.075, "count": 6, "expected_in_class": 1.0},
            {"kind": "projector", "rated_kw": 0.35, "count": 1, "expected_in_class": 1.0},
            {"kind": "ac", "rated_kw": 1.8, "count": 2, "expected_in_class": 1.0},
        ],
    },
    {
        "room_code": "C-302",
        "block": "C",
        "name": "Data Science Studio C-302",
        "room_type": "lab",
        "capacity": 60,
        "idle_baseline_kw": 0.25,
        "equipment": [
            {"kind": "light", "rated_kw": 0.04, "count": 14, "expected_in_class": 1.0},
            {"kind": "fan", "rated_kw": 0.075, "count": 8, "expected_in_class": 1.0},
            {"kind": "ac", "rated_kw": 2.0, "count": 2, "expected_in_class": 1.0},
            {"kind": "pc", "rated_kw": 0.15, "count": 25, "expected_in_class": 0.8},
            {"kind": "projector", "rated_kw": 0.35, "count": 1, "expected_in_class": 1.0},
        ],
    },
]

# ---------------------------------------------------------------------------
# Water Locations (6 monitoring points across campus)
# ---------------------------------------------------------------------------
WATER_LOCATION_DEFINITIONS = [
    {
        "name": "Admin Block Main Supply",
        "building": "Admin Block",
        "description": "Primary inlet meter for administration building and registrar offices",
        "low_flow_threshold_lph": 50.0,
    },
    {
        "name": "Block A Restrooms & Labs",
        "building": "Block A",
        "description": "Secondary distribution line for Block A washrooms and research facilities",
        "low_flow_threshold_lph": 40.0,
    },
    {
        "name": "Block B Science Labs & Faucets",
        "building": "Block B",
        "description": "Lab prep sinks and general plumbing line in Block B",
        "low_flow_threshold_lph": 45.0,
    },
    {
        "name": "Block C Washrooms & Cafeteria",
        "building": "Block C",
        "description": "Inlet line serving ground floor canteen and multi-floor washrooms",
        "low_flow_threshold_lph": 60.0,
    },
    {
        "name": "Hostel Block Main Storage Tank",
        "building": "Hostel Block",
        "description": "Overhead reservoir feed line for campus residential block",
        "low_flow_threshold_lph": 80.0,
    },
    {
        "name": "Sports Complex & Irrigation Line",
        "building": "Sports Complex",
        "description": "Outdoor sports facilities and surrounding grounds irrigation",
        "low_flow_threshold_lph": 50.0,
    },
]

# ---------------------------------------------------------------------------
# Default Settings
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS = [
    {
        "key": "electricity_price_per_kwh",
        "value": "8.50",
        "description": "Campus electricity commercial tariff in INR per kWh",
    },
    {
        "key": "emissions_factor_kg_per_kwh",
        "value": "0.71",
        "description": "Grid carbon emission factor in kg CO2 per kWh (Central Electricity Authority)",
    },
    {
        "key": "fan_watt_equivalent",
        "value": "75",
        "description": "Rated power consumption of standard ceiling fan in Watts for human-readable metric",
    },
    {
        "key": "bucket_litres",
        "value": "15",
        "description": "Standard bucket capacity in litres for water equivalence metric",
    },
    {
        "key": "water_night_threshold_lph",
        "value": "50.0",
        "description": "Flow rate threshold (L/h) above which 1–4 AM night water flow is flagged as suspected leak",
    },
    {
        "key": "water_low_flow_baseline_lph",
        "value": "15.0",
        "description": "Normal expected night baseline water flow rate (L/h) when buildings are unoccupied",
    },
]


# ---------------------------------------------------------------------------
# Timetable Generation Helper
# ---------------------------------------------------------------------------
def _build_timetable_for_room(room_code: str, room_type: str) -> List[dict]:
    """
    Generate weekly Monday–Saturday timetable entries between 09:00 and 17:00.
    Includes gaps:
    - 13:00 to 14:00 universal lunch break gap
    - Mid-morning or late-afternoon free period gaps
    """
    entries = []

    if room_type == "reading_room":
        # Reading room is open Mon-Sat 09:00-13:00 and 14:00-18:00 (13:00-14:00 lunch gap)
        for day in range(6):  # Mon (0) to Sat (5)
            entries.append({
                "day_of_week": day,
                "start_time": "09:00",
                "end_time": "13:00",
                "activity": "General Study & Library Reference",
                "expected_students": 45,
            })
            entries.append({
                "day_of_week": day,
                "start_time": "14:00",
                "end_time": "17:00",
                "activity": "Quiet Study & Research",
                "expected_students": 35,
            })
        return entries

    if room_type == "seminar":
        # Seminar halls have scheduled events 2-3 days a week
        for day in [1, 3, 5]:  # Tue, Thu, Sat
            entries.append({
                "day_of_week": day,
                "start_time": "09:30",
                "end_time": "12:30",
                "activity": "Department Guest Lecture & Seminar",
                "expected_students": 90,
            })
            entries.append({
                "day_of_week": day,
                "start_time": "14:30",
                "end_time": "16:30",
                "activity": "Technical Presentation / Project Review",
                "expected_students": 75,
            })
        return entries

    if room_type == "lab":
        # Labs have practical slots
        lab_activities = [
            "Data Structures & Algorithms Lab",
            "Advanced Operating Systems Lab",
            "IoT Sensor Systems Lab",
            "Database Engineering Practical",
        ]
        for day in range(6):
            activity_morning = lab_activities[(day * 2) % len(lab_activities)]
            activity_afternoon = lab_activities[(day * 2 + 1) % len(lab_activities)]

            # Morning practical: 09:00 - 12:00 (12:00 - 14:00 free + lunch gap)
            entries.append({
                "day_of_week": day,
                "start_time": "09:00",
                "end_time": "12:00",
                "activity": activity_morning,
                "expected_students": 30,
            })
            # Afternoon practical: 14:00 - 17:00
            # Special entry for C-302 on Wednesday (day 2): Hackathon
            if room_code == "C-302" and day == 2:
                entries.append({
                    "day_of_week": day,
                    "start_time": "10:00",
                    "end_time": "13:00",
                    "activity": "AI Hackathon & High-Performance Computing Workshop",
                    "expected_students": 60,
                })
            else:
                entries.append({
                    "day_of_week": day,
                    "start_time": "14:00",
                    "end_time": "17:00",
                    "activity": activity_afternoon,
                    "expected_students": 28,
                })
        return entries

    # Standard Classrooms
    subjects = [
        "Software Engineering",
        "Computer Networks",
        "Applied Mathematics",
        "Environmental Science",
        "Embedded Systems",
    ]
    for day in range(6):
        # Morning Period 1: 09:00 - 10:30
        entries.append({
            "day_of_week": day,
            "start_time": "09:00",
            "end_time": "10:30",
            "activity": subjects[day % len(subjects)],
            "expected_students": 35,
        })
        # Gap: 10:30 - 11:00 (Break)
        # Morning Period 2: 11:00 - 12:30
        entries.append({
            "day_of_week": day,
            "start_time": "11:00",
            "end_time": "12:30",
            "activity": subjects[(day + 1) % len(subjects)],
            "expected_students": 38,
        })
        # Universal Lunch Gap: 12:30 / 13:00 - 14:00
        # Afternoon Period 3: 14:00 - 15:30
        entries.append({
            "day_of_week": day,
            "start_time": "14:00",
            "end_time": "15:30",
            "activity": subjects[(day + 2) % len(subjects)],
            "expected_students": 32,
        })
        # Gap: 15:30 - 16:00
        # Late Afternoon Period 4: 16:00 - 17:00 (on Mon, Wed, Fri only)
        if day in [0, 2, 4]:
            entries.append({
                "day_of_week": day,
                "start_time": "16:00",
                "end_time": "17:00",
                "activity": f"{subjects[(day + 3) % len(subjects)]} Tutorial",
                "expected_students": 25,
            })

    return entries


# ---------------------------------------------------------------------------
# Core Generation Engine
# ---------------------------------------------------------------------------
def generate_all(
    db: Session,
    seed: int = 42,
    export_dir: str = None,
    reset: bool = True,
) -> dict:
    """
    Main entry point for generating all campus seed data.
    Ensures idempotency, reproducible RNG, and comprehensive output dumps.
    """
    py_rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    if reset:
        drop_all_tables()
        create_all_tables()

    # 1. Users
    users = [
        models.User(
            username="admin",
            email="admin@ghostwatt.demo",
            password_hash=hash_password("admin123"),
            role="admin",
            is_active=True,
            phone="9876500000",
            full_name="Demo Admin",
        ),
        models.User(
            username="student",
            email="student@ghostwatt.demo",
            password_hash=hash_password("student123"),
            role="student",
            is_active=True,
            phone="9876543210",
            full_name="Demo Student",
        ),
        models.User(
            username="student2",
            email="student2@ghostwatt.demo",
            password_hash=hash_password("student123"),
            role="student",
            is_active=True,
            phone="9876543211",
            full_name="Demo Student 2",
        ),
    ]
    db.add_all(users)
    db.flush()

    admin_user = users[0]
    student_user = users[1]

    # 2. Settings
    settings_records = [
        models.Setting(
            key=s["key"],
            value=s["value"],
            description=s["description"],
        )
        for s in DEFAULT_SETTINGS
    ]
    db.add_all(settings_records)
    db.flush()

    # 3. Sim State (id=1, virtual_now initialized to BASE_END_DATE)
    sim_state = models.SimState(
        id=1,
        virtual_now=BASE_END_DATE,
        speed=1.0,
        running=False,
    )
    db.add(sim_state)
    db.flush()

    # 4. Rooms and Equipment
    room_models = []
    equipment_models = []
    equipment_by_room_code: Dict[str, List[models.Equipment]] = {}

    for r_def in ROOM_DEFINITIONS:
        room = models.Room(
            room_code=r_def["room_code"],
            block=r_def["block"],
            name=r_def["name"],
            room_type=r_def["room_type"],
            capacity=r_def["capacity"],
            idle_baseline_kw=r_def["idle_baseline_kw"],
            is_active=True,
        )
        db.add(room)
        db.flush()
        room_models.append(room)

        room_eq_list = []
        for eq_def in r_def["equipment"]:
            eq = models.Equipment(
                room_id=room.id,
                kind=eq_def["kind"],
                rated_kw=eq_def["rated_kw"],
                count=eq_def["count"],
                state="OFF",
                expected_in_class=eq_def["expected_in_class"],
            )
            db.add(eq)
            room_eq_list.append(eq)
            equipment_models.append(eq)

        equipment_by_room_code[room.room_code] = room_eq_list

    db.flush()

    # 5. Timetables
    timetable_models = []
    timetable_lookup: Dict[int, List[dict]] = {}

    for room in room_models:
        t_entries = _build_timetable_for_room(room.room_code, room.room_type)
        timetable_lookup[room.id] = t_entries
        for t in t_entries:
            entry = models.TimetableEntry(
                room_id=room.id,
                day_of_week=t["day_of_week"],
                start_time=t["start_time"],
                end_time=t["end_time"],
                activity=t["activity"],
                expected_students=t["expected_students"],
                is_active=True,
            )
            db.add(entry)
            timetable_models.append(entry)

    db.flush()

    # 6. Meter Readings (14 days × 24 hours × 4 intervals = 1,344 per room)
    # Timeline: BASE_START_DATE to BASE_END_DATE
    total_intervals = 14 * 24 * 4  # 1,344
    interval_delta = timedelta(minutes=15)

    meter_readings_models = []
    ghost_stats = {
        "A-102_overnight_ac": 0,
        "B-201_evening_lab": 0,
        "C-301_lunch_projector": 0,
        "C-302_hackathon_high_load": 0,
    }

    # Pre-index equipment power by room
    eq_summary_by_room: Dict[str, dict] = {}
    for r_def in ROOM_DEFINITIONS:
        code = r_def["room_code"]
        eq_map = {}
        for eq in r_def["equipment"]:
            eq_map[eq["kind"]] = {
                "rated_kw": eq["rated_kw"],
                "count": eq["count"],
                "total_kw": eq["rated_kw"] * eq["count"],
                "expected_in_class": eq["expected_in_class"],
            }
        eq_summary_by_room[code] = eq_map

    for room in room_models:
        code = room.room_code
        idle_kw = room.idle_baseline_kw
        eq_summary = eq_summary_by_room[code]
        t_slots = timetable_lookup[room.id]

        for step in range(total_intervals):
            current_ts = BASE_START_DATE + step * interval_delta
            weekday = current_ts.weekday()  # 0=Mon, 6=Sun
            time_str = current_ts.strftime("%H:%M")
            hour = current_ts.hour
            day_index = (current_ts - BASE_START_DATE).days  # 0 to 13

            # Check if active class is scheduled
            active_class = None
            if weekday < 6:  # Mon to Sat
                for slot in t_slots:
                    if slot["day_of_week"] == weekday and slot["start_time"] <= time_str < slot["end_time"]:
                        active_class = slot
                        break

            # Calculate normal demand based on appliance model
            # actual = idle_baseline + sum(rated_kw of ON equipment) + small noise
            noise = float(np_rng.normal(0.0, 0.015))

            if active_class is not None:
                # Class in session: equipment operating according to expected_in_class
                on_kw = 0.0
                for kind, details in eq_summary.items():
                    on_kw += details["total_kw"] * details["expected_in_class"]
                actual_kw = idle_kw + on_kw + noise
            else:
                # Room empty: normal consumption is idle baseline
                actual_kw = idle_kw + noise

            # -----------------------------------------------------------------
            # Inject Deliberate Scenarios:
            # -----------------------------------------------------------------

            # Ghost Scenario 1: A-102 AC on overnight
            # Nights of Days 3, 4, 10, 11 (Thu/Fri nights) between 21:00 and 06:45
            is_a102_ghost = False
            if code == "A-102" and day_index in [3, 4, 10, 11] and (hour >= 21 or hour < 7):
                ac_power = eq_summary["ac"]["total_kw"]  # 2 * 1.8 = 3.6 kW
                actual_kw = idle_kw + ac_power + noise
                is_a102_ghost = True
                ghost_stats["A-102_overnight_ac"] += 1

            # Ghost Scenario 2: B-201 Computer Lab equipment on after class
            # Days 1, 3, 8, 10 (Tue/Thu evenings) from 17:00 to 22:30
            is_b201_ghost = False
            if code == "B-201" and day_index in [1, 3, 8, 10] and (17 <= hour < 22 or (hour == 22 and current_ts.minute <= 30)):
                pc_power = eq_summary["pc"]["total_kw"] * 0.95       # 30 * 0.15 = 4.5 kW
                light_power = eq_summary["light"]["total_kw"] * 0.8  # ~0.5 kW
                actual_kw = idle_kw + pc_power + light_power + noise
                is_b201_ghost = True
                ghost_stats["B-201_evening_lab"] += 1

            # Ghost Scenario 3: C-301 projector and lights on during lunch gap
            # Every weekday (Mon-Fri) between 13:00 and 14:00
            is_c301_ghost = False
            if code == "C-301" and weekday < 5 and 13 <= hour < 14:
                proj_power = eq_summary["projector"]["total_kw"]  # 0.35 kW
                light_power = eq_summary["light"]["total_kw"]     # 0.48 kW
                actual_kw = idle_kw + proj_power + light_power + noise
                is_c301_ghost = True
                ghost_stats["C-301_lunch_projector"] += 1

            # Explainability Scenario 4: C-302 legitimately above expected during big class
            # Day 9 (Wednesday Oct 7) from 10:00 to 13:00 (AI Hackathon session)
            if code == "C-302" and day_index == 9 and 10 <= hour < 13:
                # Extra server rigs, high GPU usage, and personal student laptops plugged in
                extra_legitimate_kw = 3.2 + float(np_rng.uniform(0.1, 0.4))
                actual_kw += extra_legitimate_kw
                ghost_stats["C-302_hackathon_high_load"] += 1

            actual_kw = max(round(actual_kw, 3), round(idle_kw * 0.8, 3))
            interval_kwh = round(actual_kw * 0.25, 4)

            reading = models.MeterReading(
                room_id=room.id,
                timestamp=current_ts,
                actual_demand_kw=actual_kw,
                interval_kwh=interval_kwh,
                source="simulated",
                is_simulated=True,
            )
            meter_readings_models.append(reading)

    db.bulk_save_objects(meter_readings_models)
    db.flush()

    # 7. Water Locations and Readings (14 days × 24 hours = 336 hourly readings)
    water_locations = []
    for loc_def in WATER_LOCATION_DEFINITIONS:
        w_loc = models.WaterLocation(
            name=loc_def["name"],
            building=loc_def["building"],
            description=loc_def["description"],
            low_flow_threshold_lph=loc_def["low_flow_threshold_lph"],
        )
        db.add(w_loc)
        db.flush()
        water_locations.append(w_loc)

    water_readings_models = []
    total_water_hours = 14 * 24
    hour_delta = timedelta(hours=1)

    # Find the target leak location: "Block C Washrooms & Cafeteria"
    leak_loc = next(l for l in water_locations if "Block C" in l.name)

    for loc in water_locations:
        threshold = loc.low_flow_threshold_lph
        baseline = 15.0 if loc.id != leak_loc.id else 20.0

        for h in range(total_water_hours):
            w_ts = BASE_START_DATE + h * hour_delta
            hour = w_ts.hour
            day_index = (w_ts - BASE_START_DATE).days

            # Realistic circadian diurnal flow curve
            if 0 <= hour < 5:
                # Quiet night baseline
                flow = baseline + float(np_rng.normal(0.0, 2.0))
            elif 5 <= hour < 8:
                # Early morning buildup
                flow = 60.0 + (hour - 5) * 35.0 + float(np_rng.normal(0.0, 6.0))
            elif 8 <= hour < 12:
                # Morning peak working hours
                flow = 160.0 + float(np_rng.normal(0.0, 15.0))
            elif 12 <= hour < 14:
                # Lunch break surge
                flow = 240.0 + (50.0 if "Cafeteria" in loc.name else 0.0) + float(np_rng.normal(0.0, 18.0))
            elif 14 <= hour < 18:
                # Afternoon sessions
                flow = 140.0 + float(np_rng.normal(0.0, 12.0))
            elif 18 <= hour < 21:
                # Evening taper
                flow = 80.0 + float(np_rng.normal(0.0, 8.0))
            else:
                # 21:00 - 24:00 night settling
                flow = 30.0 + float(np_rng.normal(0.0, 4.0))

            # Suspected leak anomaly: Block C Washrooms on Days 10, 11, 12 between 1 AM and 4 AM
            if loc.id == leak_loc.id and day_index in [10, 11, 12] and (1 <= hour < 4):
                # Massive continuous night flow (210 - 260 L/h vs 20 L/h baseline)
                flow = 230.0 + float(np_rng.normal(0.0, 10.0))

            flow = max(round(flow, 1), 2.0)
            litres = round(flow * 1.0, 1)

            reading = models.WaterReading(
                location_id=loc.id,
                timestamp=w_ts,
                flow_rate_lph=flow,
                interval_litres=litres,
                expected_baseline_lph=baseline,
                source="simulated",
                is_simulated=True,
            )
            water_readings_models.append(reading)

    db.bulk_save_objects(water_readings_models)
    db.flush()

    # 8. Water Alerts (suspected leak record for Block C Washrooms)
    leak_start = BASE_START_DATE + timedelta(days=11, hours=1)  # Day 11, 01:00 AM
    leak_end = BASE_START_DATE + timedelta(days=11, hours=4)    # Day 11, 04:00 AM
    water_alert = models.WaterAlert(
        location_id=leak_loc.id,
        detected_at=leak_end + timedelta(minutes=15),
        window_start=leak_start,
        window_end=leak_end,
        avg_flow_lph=234.8,
        baseline_lph=20.0,
        status="SUSPECTED",
        inspection_notes=(
            "Automated night-flow anomaly detected: sustained 234.8 L/h between 01:00 and 04:00 AM "
            "(baseline: 20.0 L/h, threshold: 60.0 L/h). Suspected broken flush valve or supply pipe "
            "fracture in Block C second-floor restroom."
        ),
        resolved_at=None,
    )
    db.add(water_alert)
    db.flush()

    # 9. Corrective Action and Verified Savings Record (Demonstration)
    room_a102 = next(r for r in room_models if r.room_code == "A-102")
    action_time = BASE_START_DATE + timedelta(days=11, hours=22, minutes=15)
    demo_action = models.Action(
        room_id=room_a102.id,
        user_id=student_user.id,
        action_type="switch_off",
        equipment="AC",
        timestamp=action_time,
        notes="Noticed A-102 split AC units running while room was locked for the night. Switched off via dashboard.",
        verification_status="verified",
    )
    db.add(demo_action)
    db.flush()

    demo_savings = models.SavingsRecord(
        action_id=demo_action.id,
        interval_start=action_time,
        pre_avg_kw=3.71,
        post_avg_kw=0.11,
        reduction_kw=3.60,
        credited_kwh=0.90,
        monetary_saving_inr=round(0.90 * 8.50, 2),
        emissions_kg=round(0.90 * 0.71, 3),
        verification_status="verified",
        is_simulated=True,
    )
    db.add(demo_savings)
    db.flush()

    # 10. Sample Student Water Complaint + Audit History
    demo_complaint = models.Complaint(
        complaint_code="WC-0001",
        student_id=student_user.id,
        building="Block C",
        location_detail="2nd Floor Washroom (West Wing)",
        category="leaking_tap",
        description="Urinal flush pipe continuously discharging high-pressure water onto the floor.",
        status="acknowledged",
        assigned_to=admin_user.id,
        resolution_notes="Facilities team notified. Work order #WO-481 raised.",
    )
    db.add(demo_complaint)
    db.flush()

    complaint_history = [
        models.ComplaintHistory(
            complaint_id=demo_complaint.id,
            changed_by=student_user.id,
            old_status=None,
            new_status="submitted",
            note="Complaint filed by student.",
            changed_at=action_time - timedelta(hours=2),
        ),
        models.ComplaintHistory(
            complaint_id=demo_complaint.id,
            changed_by=admin_user.id,
            old_status="submitted",
            new_status="acknowledged",
            note="Acknowledged by admin maintenance desk. Assigned to plumbing supervisor.",
            changed_at=action_time - timedelta(hours=1),
        ),
    ]
    db.add_all(complaint_history)
    db.commit()

    # 11. Dump CSV and JSON artifacts
    if export_dir is None:
        export_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "generated_sample_data")
        )
    os.makedirs(export_dir, exist_ok=True)

    _export_dumps(
        export_dir=export_dir,
        rooms=room_models,
        equipment=equipment_models,
        timetables=timetable_models,
        meter_readings=meter_readings_models,
        water_locations=water_locations,
        water_readings=water_readings_models,
        water_alert=water_alert,
        settings=settings_records,
        users=users,
        ghost_stats=ghost_stats,
    )

    summary = {
        "status": "success",
        "counts": {
            "users": len(users),
            "rooms": len(room_models),
            "equipment": len(equipment_models),
            "timetable_entries": len(timetable_models),
            "meter_readings": len(meter_readings_models),
            "water_locations": len(water_locations),
            "water_readings": len(water_readings_models),
            "water_alerts": 1,
            "actions": 1,
            "savings_records": 1,
            "complaints": 1,
            "complaint_history": len(complaint_history),
            "settings": len(settings_records),
            "sim_state": 1,
        },
        "ghost_scenarios_injected": {
            "A-102_overnight_ac_intervals": ghost_stats["A-102_overnight_ac"],
            "B-201_evening_lab_intervals": ghost_stats["B-201_evening_lab"],
            "C-301_lunch_projector_intervals": ghost_stats["C-301_lunch_projector"],
            "C-302_hackathon_high_load_intervals": ghost_stats["C-302_hackathon_high_load"],
            "Block_C_night_water_leak_hours": 9,  # 3 nights × 3 hours
        },
        "time_range": {
            "start": BASE_START_DATE.isoformat(),
            "end": BASE_END_DATE.isoformat(),
            "duration_days": 14,
        },
        "export_dir": export_dir,
    }

    return summary


# ---------------------------------------------------------------------------
# Data Export Helpers
# ---------------------------------------------------------------------------
def _export_dumps(
    export_dir: str,
    rooms: List[models.Room],
    equipment: List[models.Equipment],
    timetables: List[models.TimetableEntry],
    meter_readings: List[models.MeterReading],
    water_locations: List[models.WaterLocation],
    water_readings: List[models.WaterReading],
    water_alert: models.WaterAlert,
    settings: List[models.Setting],
    users: List[models.User],
    ghost_stats: dict,
):
    """Write comprehensive CSV and JSON representations for documentation and offline verification."""

    # 1. Rooms JSON & CSV
    rooms_data = [
        {
            "id": r.id,
            "room_code": r.room_code,
            "block": r.block,
            "name": r.name,
            "room_type": r.room_type,
            "capacity": r.capacity,
            "idle_baseline_kw": r.idle_baseline_kw,
        }
        for r in rooms
    ]
    with open(os.path.join(export_dir, "rooms.json"), "w", encoding="utf-8") as f:
        json.dump(rooms_data, f, indent=2)

    with open(os.path.join(export_dir, "rooms.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rooms_data[0].keys())
        writer.writeheader()
        writer.writerows(rooms_data)

    # 2. Equipment JSON & CSV
    equipment_data = [
        {
            "id": eq.id,
            "room_id": eq.room_id,
            "kind": eq.kind,
            "rated_kw": eq.rated_kw,
            "count": eq.count,
            "state": eq.state,
            "expected_in_class": eq.expected_in_class,
        }
        for eq in equipment
    ]
    with open(os.path.join(export_dir, "equipment.json"), "w", encoding="utf-8") as f:
        json.dump(equipment_data, f, indent=2)

    with open(os.path.join(export_dir, "equipment.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=equipment_data[0].keys())
        writer.writeheader()
        writer.writerows(equipment_data)

    # 3. Timetable JSON & CSV
    timetable_data = [
        {
            "id": t.id,
            "room_id": t.room_id,
            "day_of_week": t.day_of_week,
            "start_time": t.start_time,
            "end_time": t.end_time,
            "activity": t.activity,
            "expected_students": t.expected_students,
        }
        for t in timetables
    ]
    with open(os.path.join(export_dir, "timetable.json"), "w", encoding="utf-8") as f:
        json.dump(timetable_data, f, indent=2)

    with open(os.path.join(export_dir, "timetable.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=timetable_data[0].keys())
        writer.writeheader()
        writer.writerows(timetable_data)

    # 4. Water Locations JSON & CSV
    water_locations_data = [
        {
            "id": wl.id,
            "name": wl.name,
            "building": wl.building,
            "description": wl.description,
            "low_flow_threshold_lph": wl.low_flow_threshold_lph,
        }
        for wl in water_locations
    ]
    with open(os.path.join(export_dir, "water_locations.json"), "w", encoding="utf-8") as f:
        json.dump(water_locations_data, f, indent=2)

    with open(os.path.join(export_dir, "water_locations.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=water_locations_data[0].keys())
        writer.writeheader()
        writer.writerows(water_locations_data)

    # 5. Water Alert JSON
    water_alert_data = {
        "id": water_alert.id,
        "location_id": water_alert.location_id,
        "detected_at": water_alert.detected_at.isoformat(),
        "window_start": water_alert.window_start.isoformat(),
        "window_end": water_alert.window_end.isoformat(),
        "avg_flow_lph": water_alert.avg_flow_lph,
        "baseline_lph": water_alert.baseline_lph,
        "status": water_alert.status,
        "inspection_notes": water_alert.inspection_notes,
    }
    with open(os.path.join(export_dir, "water_alerts.json"), "w", encoding="utf-8") as f:
        json.dump([water_alert_data], f, indent=2)

    # 6. Settings JSON
    settings_data = [
        {"key": s.key, "value": s.value, "description": s.description}
        for s in settings
    ]
    with open(os.path.join(export_dir, "settings.json"), "w", encoding="utf-8") as f:
        json.dump(settings_data, f, indent=2)

    # 7. Users JSON (sanitized demo credentials metadata)
    users_data = [
        {"id": u.id, "username": u.username, "email": u.email, "role": u.role, "is_active": u.is_active}
        for u in users
    ]
    with open(os.path.join(export_dir, "users.json"), "w", encoding="utf-8") as f:
        json.dump(users_data, f, indent=2)

    # 8. Meter Readings CSV
    with open(os.path.join(export_dir, "meter_readings.csv"), "w", newline="", encoding="utf-8") as f:
        fieldnames = ["room_id", "timestamp", "actual_demand_kw", "interval_kwh", "source", "is_simulated"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for mr in meter_readings:
            writer.writerow({
                "room_id": mr.room_id,
                "timestamp": mr.timestamp.isoformat(),
                "actual_demand_kw": mr.actual_demand_kw,
                "interval_kwh": mr.interval_kwh,
                "source": mr.source,
                "is_simulated": mr.is_simulated,
            })

    # 9. Water Readings CSV
    with open(os.path.join(export_dir, "water_readings.csv"), "w", newline="", encoding="utf-8") as f:
        fieldnames = ["location_id", "timestamp", "flow_rate_lph", "interval_litres", "expected_baseline_lph", "source", "is_simulated"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for wr in water_readings:
            writer.writerow({
                "location_id": wr.location_id,
                "timestamp": wr.timestamp.isoformat(),
                "flow_rate_lph": wr.flow_rate_lph,
                "interval_litres": wr.interval_litres,
                "expected_baseline_lph": wr.expected_baseline_lph,
                "source": wr.source,
                "is_simulated": wr.is_simulated,
            })

    # 10. Summary JSON
    summary_data = {
        "generated_at": datetime.now().isoformat(),
        "total_rooms": len(rooms),
        "total_equipment_records": len(equipment),
        "total_timetable_entries": len(timetables),
        "total_meter_readings": len(meter_readings),
        "total_water_locations": len(water_locations),
        "total_water_readings": len(water_readings),
        "ghost_scenarios_injected": ghost_stats,
    }
    with open(os.path.join(export_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
