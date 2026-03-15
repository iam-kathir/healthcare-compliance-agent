"""
Database Seeder — Seed 10 CMS policies + sample patients & claims
Run: python seed_db.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.database import init_db, SessionLocal, Policy, Patient, Claim
from datetime import datetime, timedelta
import random


def seed_policies(db):
    """Seed 10 real CMS policies."""
    policies = [
        {
            "title": "Annual Wellness Visit (AWV) — Initial Visit Requirements",
            "policy_type": "Billing",
            "affected_codes": "G0438, G0439",
            "requirements": "Health Risk Assessment (HRA) questionnaire must be completed. Includes review of medical/family history, BMI, blood pressure, cognitive assessment, and personalized prevention plan. Cannot be billed with IPPE (G0402) on same date.",
            "denial_triggers": "Missing HRA documentation, billing G0438 and G0402 on same date, incomplete prevention plan, patient not eligible (within first 12 months of Part B)",
            "impact_level": "HIGH",
            "deadline_days": 14,
            "summary": "Annual Wellness Visits require a comprehensive Health Risk Assessment. G0438 is for initial AWV, G0439 for subsequent. Common denials stem from incomplete documentation or eligibility issues.",
        },
        {
            "title": "E/M Office Visit Documentation Standards — 99213/99214",
            "policy_type": "Documentation",
            "affected_codes": "99213, 99214, 99215",
            "requirements": "Based on Medical Decision Making (MDM) complexity OR total time. 99213: Low MDM (2 of 3: limited problems, limited data, low risk). 99214: Moderate MDM (2 of 3: multiple problems, moderate data, moderate risk). Must document all MDM elements.",
            "denial_triggers": "Insufficient MDM documentation, upcoding from 99213 to 99214 without supporting complexity, missing time documentation when billing based on time, lack of medical necessity",
            "impact_level": "HIGH",
            "deadline_days": 14,
            "summary": "E/M codes 99213-99215 require clear documentation of medical decision-making complexity. 2021 guidelines eliminated history/exam requirements for code selection, focusing on MDM or time.",
        },
        {
            "title": "Comprehensive Metabolic Panel — Prior Authorization",
            "policy_type": "Prior Authorization",
            "affected_codes": "80053",
            "requirements": "Prior authorization required for Medicare Advantage plans. Must demonstrate medical necessity with supporting diagnosis. Cannot be ordered as routine screening without qualifying ICD-10 code. Requires provider signature.",
            "denial_triggers": "Missing prior authorization, no qualifying diagnosis code, ordered as routine screening without medical indication, duplicate panel within 30 days",
            "impact_level": "MEDIUM",
            "deadline_days": 30,
            "summary": "CPT 80053 (Comprehensive Metabolic Panel) requires prior authorization for many Medicare Advantage plans. Common denials due to missing auth or lack of medical necessity documentation.",
        },
        {
            "title": "Critical Care Services Documentation — 99291",
            "policy_type": "Documentation",
            "affected_codes": "99291, 99292",
            "requirements": "Requires 30+ minutes of critical care time documented. Time must be spent at bedside or on the unit. Must document critical illness/injury requiring high-complexity decision making. Time documentation must be real-time, not retrospective.",
            "denial_triggers": "Total time less than 30 minutes, retrospective time documentation, no documentation of critical condition, billing concurrent critical care for multiple patients, overlap with other time-based codes",
            "impact_level": "HIGH",
            "deadline_days": 14,
            "summary": "Critical care code 99291 requires meticulous time documentation (30+ minutes). OIG audits show 34% of claims lack adequate time documentation. Real-time recording is mandatory.",
        },
        {
            "title": "Psychotherapy Services — 90837 Requirements",
            "policy_type": "Coverage",
            "affected_codes": "90837, 90834, 90832",
            "requirements": "90837 requires 53+ minutes face-to-face. Must document start/stop times. Treatment plan must be current (updated every 90 days). Diagnosis must support medical necessity. If billed with E/M, must use add-on code 90838.",
            "denial_triggers": "Session time under 53 minutes, outdated treatment plan, billing 90837 instead of 90834 (38-52 min), missing start/stop times, no documented treatment plan goals",
            "impact_level": "MEDIUM",
            "deadline_days": 30,
            "summary": "Psychotherapy code 90837 requires 53+ minutes of face-to-face time with documented start/stop times. Treatment plans must be updated quarterly with measurable goals.",
        },
        {
            "title": "Subsequent Hospital Care — 99232 Billing",
            "policy_type": "Billing",
            "affected_codes": "99232, 99231, 99233",
            "requirements": "Requires moderate MDM complexity with documentation of at least 2 of 3 elements: multiple chronic conditions, moderate data review, moderate treatment risk. Must document interval changes since last assessment.",
            "denial_triggers": "Insufficient documentation of MDM elements, billing 99232 when 99231 complexity level met, missing interval history, same-day duplicate billing",
            "impact_level": "MEDIUM",
            "deadline_days": 21,
            "summary": "Hospital care code 99232 requires moderate complexity MDM. Documentation must show clear interval changes and management updates since the previous encounter.",
        },
        {
            "title": "Chest X-Ray — 71046 Documentation",
            "policy_type": "Documentation",
            "affected_codes": "71046, 71045, 71047, 71048",
            "requirements": "Clinical indication must be documented in the order. Interpretation and report must include comparison with prior studies when available. PA and lateral views required for 71046. Separate interpretation required if ordering and interpreting provider differ.",
            "denial_triggers": "Missing clinical indication, no comparison with priors noted, billing 71046 when only PA view obtained, unsigned interpretation report",
            "impact_level": "LOW",
            "deadline_days": 45,
            "summary": "Chest X-ray code 71046 (2 views) requires documented clinical indication and proper interpretation report. Low denial risk when documentation standards are followed.",
        },
        {
            "title": "Physical Therapy — 97110 Therapeutic Exercise",
            "policy_type": "Coverage",
            "affected_codes": "97110, 97112, 97140, 97530",
            "requirements": "Requires skilled intervention (not routine exercise). Must document functional limitations and measurable goals. GP modifier required for PT services. Functional Limitation Reporting (FLR) codes required. Therapy cap applies ($2,330 combined PT/SLP; $2,330 OT).",
            "denial_triggers": "Missing GP modifier, exceeding therapy cap without KX modifier exception, maintenance therapy without skilled need, no documented functional progress, missing FLR codes",
            "impact_level": "MEDIUM",
            "deadline_days": 30,
            "summary": "PT code 97110 requires skilled intervention documentation with functional goals. GP modifier is mandatory. Claims exceeding the therapy cap need KX modifier with supporting documentation.",
        },
        {
            "title": "Venipuncture — 36415 Billing Requirements",
            "policy_type": "Billing",
            "affected_codes": "36415",
            "requirements": "Cannot be billed separately when performed as part of a bundled service. Only billable when venipuncture is the only service or when lab is sent to an outside reference lab. Must have qualifying order from authorized provider.",
            "denial_triggers": "Billing separately when bundled with other lab codes, no associated lab test ordered, duplicate billing, billing by non-credentialed staff",
            "impact_level": "LOW",
            "deadline_days": 45,
            "summary": "Venipuncture code 36415 has strict bundling rules. Cannot be billed separately when included in a comprehensive lab service. Low-risk when billing rules are followed correctly.",
        },
        {
            "title": "Preventive Visit — 99395 Established Patient",
            "policy_type": "Coverage",
            "affected_codes": "99395, 99396, 99391, 99392, 99393, 99394",
            "requirements": "Age-appropriate preventive services per USPSTF recommendations. Must document comprehensive review of systems, age-appropriate counseling, and anticipatory guidance. Cannot bill with same-day sick visit E/M without modifier 25.",
            "denial_triggers": "Billing with same-day E/M without modifier 25, wrong age category code, billing more than once per year, insufficient documentation of preventive components, missing counseling documentation",
            "impact_level": "LOW",
            "deadline_days": 30,
            "summary": "Preventive visit code 99395 (established patient, 18-39 years) requires age-appropriate screening and counseling documentation. Use modifier 25 if same-day E/M is also performed.",
        },
    ]

    count = 0
    for p in policies:
        existing = db.query(Policy).filter(Policy.title == p["title"]).first()
        if not existing:
            db.add(Policy(**p, created_at=datetime.utcnow()))
            count += 1

    db.commit()
    print(f"✓ Seeded {count} policies (skipped {len(policies) - count} duplicates)")


def seed_patients(db):
    """Seed sample patients."""
    patients = [
        {"patient_id": "P-10001", "name": "John Anderson", "dob": "1955-03-15", "gender": "Male", "provider_name": "Dr. Sarah Chen", "facility": "Metro Health Center", "payer": "Medicare"},
        {"patient_id": "P-10002", "name": "Maria Garcia", "dob": "1968-07-22", "gender": "Female", "provider_name": "Dr. James Wilson", "facility": "City Hospital", "payer": "Blue Cross"},
        {"patient_id": "P-10003", "name": "Robert Williams", "dob": "1972-11-08", "gender": "Male", "provider_name": "Dr. Emily Patel", "facility": "Regional Medical Center", "payer": "Aetna"},
        {"patient_id": "P-10004", "name": "Linda Johnson", "dob": "1949-05-30", "gender": "Female", "provider_name": "Dr. Michael Brown", "facility": "University Hospital", "payer": "Medicare"},
        {"patient_id": "P-10005", "name": "David Martinez", "dob": "1980-01-12", "gender": "Male", "provider_name": "Dr. Sarah Chen", "facility": "Metro Health Center", "payer": "United Health"},
    ]

    count = 0
    for p in patients:
        existing = db.query(Patient).filter(Patient.patient_id == p["patient_id"]).first()
        if not existing:
            db.add(Patient(**p, created_at=datetime.utcnow()))
            count += 1

    db.commit()
    print(f"✓ Seeded {count} patients")


def seed_claims(db):
    """Seed sample claims."""
    claims = [
        {"claim_id": "CLM-A0001", "patient_name": "John Anderson", "cpt_code": "99214", "icd10_code": "E11.9", "billed_amount": 250.00, "claim_status": "Pending", "service_date": "2025-12-15", "prior_auth_required": False, "documentation_required": True, "policy_impact_level": "HIGH", "provider_compliance_score": 0.78},
        {"claim_id": "CLM-A0002", "patient_name": "Maria Garcia", "cpt_code": "G0438", "icd10_code": "Z00.00", "billed_amount": 350.00, "claim_status": "Pending", "service_date": "2025-12-18", "prior_auth_required": False, "documentation_required": True, "policy_impact_level": "HIGH", "provider_compliance_score": 0.92},
        {"claim_id": "CLM-A0003", "patient_name": "Robert Williams", "cpt_code": "80053", "icd10_code": "R73.03", "billed_amount": 125.00, "claim_status": "Denied", "denial_reason": "Missing prior authorization", "service_date": "2025-12-10", "prior_auth_required": True, "documentation_required": False, "policy_impact_level": "MEDIUM", "provider_compliance_score": 0.65},
        {"claim_id": "CLM-A0004", "patient_name": "Linda Johnson", "cpt_code": "99291", "icd10_code": "J96.01", "billed_amount": 780.00, "claim_status": "Pending", "service_date": "2025-12-20", "prior_auth_required": False, "documentation_required": True, "policy_impact_level": "HIGH", "provider_compliance_score": 0.70},
        {"claim_id": "CLM-A0005", "patient_name": "David Martinez", "cpt_code": "97110", "icd10_code": "M54.5", "billed_amount": 95.00, "claim_status": "Approved", "service_date": "2025-11-28", "prior_auth_required": False, "documentation_required": True, "policy_impact_level": "MEDIUM", "provider_compliance_score": 0.88},
        {"claim_id": "CLM-A0006", "patient_name": "John Anderson", "cpt_code": "99213", "icd10_code": "J06.9", "billed_amount": 150.00, "claim_status": "Approved", "service_date": "2025-11-15", "prior_auth_required": False, "documentation_required": False, "policy_impact_level": "LOW", "provider_compliance_score": 0.95},
        {"claim_id": "CLM-A0007", "patient_name": "Maria Garcia", "cpt_code": "90837", "icd10_code": "F32.1", "billed_amount": 200.00, "claim_status": "Pending", "service_date": "2026-01-05", "prior_auth_required": True, "documentation_required": True, "policy_impact_level": "MEDIUM", "provider_compliance_score": 0.80},
        {"claim_id": "CLM-A0008", "patient_name": "Robert Williams", "cpt_code": "99215", "icd10_code": "E11.65", "billed_amount": 320.00, "claim_status": "Denied", "denial_reason": "Upcoding — documentation supports 99214", "service_date": "2025-12-05", "prior_auth_required": False, "documentation_required": True, "policy_impact_level": "HIGH", "provider_compliance_score": 0.55},
        {"claim_id": "CLM-A0009", "patient_name": "Linda Johnson", "cpt_code": "36415", "icd10_code": "Z13.1", "billed_amount": 15.00, "claim_status": "Approved", "service_date": "2025-12-22", "prior_auth_required": False, "documentation_required": False, "policy_impact_level": "LOW", "provider_compliance_score": 0.90},
        {"claim_id": "CLM-A0010", "patient_name": "David Martinez", "cpt_code": "99395", "icd10_code": "Z00.00", "billed_amount": 275.00, "claim_status": "Pending", "service_date": "2026-01-10", "prior_auth_required": False, "documentation_required": True, "policy_impact_level": "LOW", "provider_compliance_score": 0.85},
    ]

    count = 0
    for c in claims:
        existing = db.query(Claim).filter(Claim.claim_id == c["claim_id"]).first()
        if not existing:
            db.add(Claim(**c, created_at=datetime.utcnow()))
            count += 1

    db.commit()
    print(f"✓ Seeded {count} claims")


def main():
    print("=" * 50)
    print("  Healthcare Compliance Agent — Database Seeder")
    print("=" * 50)
    init_db()
    db = SessionLocal()
    try:
        seed_policies(db)
        seed_patients(db)
        seed_claims(db)
        print("\n✅ Database seeding complete!")
        print(f"   Policies: {db.query(Policy).count()}")
        print(f"   Patients: {db.query(Patient).count()}")
        print(f"   Claims:   {db.query(Claim).count()}")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
