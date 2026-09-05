"""
Clinova - Standalone Demo Seeder CLI
Seeds an evaluation clinician (doctor@clinova.health / clinova2026)
and a complete longitudinal patient profile: Eleanor Vance (CL-8F29K4)
with 2 reports, longitudinal lab deltas, cross-record conflicts, and pending verifications.
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.db_models import User
from app.api.demo import seed_demo_patient

def main():
    print("==================================================")
    print("CLINOVA - Synthetic Clinical Patient Seeder")
    print("Tagline: 'One patient. One record. Every insight traceable.'")
    print("==================================================")

    # Initialize tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Create or get demo doctor
        doc_email = "doctor@clinova.health"
        doctor = db.query(User).filter(User.email == doc_email).first()
        if not doctor:
            doctor = User(
                email=doc_email,
                hashed_password=get_password_hash("clinova2026"),
                full_name="Dr. Sarah Chen, MD",
                role="doctor"
            )
            db.add(doctor)
            db.commit()
            db.refresh(doctor)
            print(f"[+] Created Clinician Account: {doctor.email} (Password: clinova2026)")
        else:
            print(f"[*] Found Existing Clinician: {doctor.email}")

        # 2. Seed demo patient
        result = seed_demo_patient(db=db, current_user=doctor)
        print(f"[+] Seeded Patient: {result['name']} (ID: {result['patient_id']})")
        print(f"[+] Uploaded & Extracted: {result['reports_count']} medical reports")
        print(f"[+] Total Structured Labs: {result['labs_count']} results")
        print(f"[+] Longitudinal Diff: Baseline Hemoglobin 10.2 -> Followup 11.8 g/dL (+15.7%)")
        print(f"[+] Cross-Record Conflicts: Penicillin allergy contradiction flagged")
        print(f"[+] Verification Queue: Items populated with PENDING_VERIFICATION")
        print("==================================================")
        print("Seeding Complete. You can now launch Clinova and log in!")
        print("==================================================")

    finally:
        db.close()

if __name__ == "__main__":
    main()
