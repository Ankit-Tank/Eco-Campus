"""
Eco-Campus — scripts/seed.py
CLI script to seed the database with reproducible demo data.

Usage:
    cd backend
    python -m scripts.seed
    or
    python scripts/seed.py
"""
import os
import sys

# Ensure backend directory is in Python path for flexible invocation
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.database import SessionLocal, get_session
from app.services.data_generator import generate_all


def run_seed(seed: int = 42) -> dict:
    """Execute idempotent database reset and seeding."""
    print("=" * 70)
    print("  ECO-CAMPUS DATABASE SEEDING ENGINE")
    print("=" * 70)
    print(f"[*] Initializing database session (Seeded RNG: {seed})...")

    with get_session() as db:
        print("[*] Performing idempotent database reset & seeding...")
        result = generate_all(db, seed=seed, reset=True)

    counts = result["counts"]
    ghosts = result["ghost_scenarios_injected"]
    timeline = result["time_range"]

    print("\n" + "-" * 70)
    print("  SEED SUMMARY: DATABASE TABLE ROW COUNTS")
    print("-" * 70)
    for table, count in counts.items():
        print(f"    - {table:<25} : {count:>6} rows")

    print("\n" + "-" * 70)
    print("  DELIBERATE GHOST & EXPLAINABILITY SCENARIOS INJECTED")
    print("-" * 70)
    print(f"  1. [Ghost Load] Room A-102 AC Overnight:")
    print(f"     - 2x 1.8 kW split AC units left ON between 21:00 and 06:45")
    print(f"     - Total affected intervals: {ghosts.get('A-102_overnight_ac_intervals', 0)}")
    print()
    print(f"  2. [Ghost Load] Room B-201 Lab Equipment After Class:")
    print(f"     - 30x workstations + lab lighting running past 17:00 to 22:30")
    print(f"     - Total affected intervals: {ghosts.get('B-201_evening_lab_intervals', 0)}")
    print()
    print(f"  3. [Ghost Load] Room C-301 Lunch Break Gap:")
    print(f"     - Projector (0.35 kW) and lighting (0.48 kW) running 13:00 to 14:00")
    print(f"     - Total affected intervals: {ghosts.get('C-301_lunch_projector_intervals', 0)}")
    print()
    print(f"  4. [Explainability] Room C-302 Hackathon Workshop:")
    print(f"     - High power draw during scheduled full-capacity workshop (+3.4 kW)")
    print(f"     - Demonstrates explainable legitimate load vs unoccupied waste")
    print(f"     - Total high-load intervals: {ghosts.get('C-302_hackathon_high_load_intervals', 0)}")
    print()
    print(f"  5. [Water Anomaly] Block C Washrooms & Cafeteria:")
    print(f"     - High flow between 01:00 AM and 04:00 AM (234.8 L/h vs 20 L/h baseline)")
    print(f"     - Automated WaterAlert generated with status=SUSPECTED")
    print(f"     - Anomaly duration: {ghosts.get('Block_C_night_water_leak_hours', 9)} hours across 3 nights")

    print("\n" + "-" * 70)
    print("  DEMO USER ACCOUNTS")
    print("-" * 70)
    print("    - Admin:    admin@ghostwatt.demo    / admin123   (role: admin)")
    print("    - Student:  student@ghostwatt.demo  / student123 (role: student)")
    print("    - Student2: student2@ghostwatt.demo / student123 (role: student, permissions test)")

    print("\n" + "-" * 70)
    print("  CONFIGURED DEFAULT SETTINGS")
    print("-" * 70)
    print("    - Electricity Tariff   : Rs 8.50 / kWh")
    print("    - Carbon Emissions     : 0.71 kg CO2 / kWh")
    print("    - Ceiling Fan Equiv    : 75 W")
    print("    - Water Bucket Equiv   : 15 L")
    print("    - Water Night Threshold: 50.0 L/h")
    print("    - Water Night Baseline : 15.0 L/h")

    print("\n" + "-" * 70)
    print("  SIMULATION & EXPORT STATUS")
    print("-" * 70)
    print(f"    - Reading Interval     : 15 minutes (1,344 readings/room across 14 days)")
    print(f"    - Date Timeline Range  : {timeline['start']}  -->  {timeline['end']}")
    print(f"    - All data marked with : source='simulated', is_simulated=True")
    print(f"    - CSV/JSON dumps saved : {result['export_dir']}")
    print("=" * 70)
    print("  ECO-CAMPUS SEEDING COMPLETED SUCCESSFULLY")
    print("=" * 70)

    return result


if __name__ == "__main__":
    run_seed()
