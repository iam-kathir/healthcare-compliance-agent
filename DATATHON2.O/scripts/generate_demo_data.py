"""
Generate Demo Healthcare Excel Data
Creates a realistic Excel file with ~50 patient records and claims.
Mix of: approved, pending, denied, and intentionally flawed entries 
to demonstrate the compliance engine's flagging capabilities.

Run: python scripts/generate_demo_data.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import random
from datetime import datetime, timedelta

random.seed(42)

# ─── Realistic Patient Data ──────────────────────────────────
FIRST_NAMES_M = ["James","Robert","Michael","William","David","Richard","Joseph","Thomas","Charles","Daniel",
                 "Matthew","Anthony","Mark","Donald","Steven","Andrew","Paul","Joshua","Kenneth","Kevin"]
FIRST_NAMES_F = ["Mary","Patricia","Jennifer","Linda","Barbara","Elizabeth","Susan","Jessica","Sarah","Karen",
                 "Lisa","Nancy","Betty","Margaret","Sandra","Ashley","Dorothy","Kimberly","Emily","Donna"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
              "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
              "Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson"]

PROVIDERS = [
    ("Dr. Sarah Chen", "Metro Health Center"),
    ("Dr. James Wilson", "City Hospital"),
    ("Dr. Emily Patel", "Regional Medical Center"),
    ("Dr. Michael Brown", "University Hospital"),
    ("Dr. Priya Patel", "Regional Health Clinic"),
    ("Dr. Robert Chen", "Community Care Center"),
    ("Dr. Emily Davis", "Community Care Center"),
    ("Dr. Michael Lee", "University Hospital"),
    ("Dr. Sarah Johnson", "Metro Health Center"),
]

PAYERS = ["Medicare", "Medicaid", "Blue Cross Blue Shield", "Aetna", "United Health",
          "Cigna", "Humana", "Medicare Part A", "Medicare Part B", "Medicare Advantage"]

GENDERS = ["Male", "Female"]

# ─── CPT + ICD-10 combos (realistic pairings) ────────────────
# Format: (cpt, icd10, description, typical_amount, prior_auth, doc_required, impact)
VALID_COMBOS = [
    ("99213", "J06.9",  "Office visit - URI",                 150.00, False, False, "LOW"),
    ("99213", "E11.9",  "Office visit - Type 2 diabetes",     150.00, False, True,  "LOW"),
    ("99214", "E11.65", "Office visit - DM with complications",250.00, False, True,  "HIGH"),
    ("99214", "I10",    "Office visit - Hypertension",        250.00, False, True,  "HIGH"),
    ("99215", "E11.65", "Complex visit - DM complications",   350.00, False, True,  "HIGH"),
    ("G0438", "Z00.00", "Initial Annual Wellness Visit",      350.00, False, True,  "HIGH"),
    ("G0439", "Z00.00", "Subsequent Annual Wellness Visit",   280.00, False, True,  "HIGH"),
    ("80053", "R73.03", "Comprehensive Metabolic Panel",      125.00, True,  False, "MEDIUM"),
    ("80053", "E11.9",  "CMP - Diabetes monitoring",          125.00, True,  False, "MEDIUM"),
    ("99291", "J96.01", "Critical care - Respiratory failure", 780.00, False, True,  "HIGH"),
    ("99291", "I21.9",  "Critical care - MI",                 780.00, False, True,  "HIGH"),
    ("90837", "F32.1",  "Psychotherapy - Major depression",   200.00, True,  True,  "MEDIUM"),
    ("90837", "F41.1",  "Psychotherapy - GAD",                200.00, True,  True,  "MEDIUM"),
    ("99232", "J18.9",  "Hospital care - Pneumonia",          220.00, False, True,  "MEDIUM"),
    ("99232", "N17.9",  "Hospital care - Acute kidney injury",220.00, False, True,  "MEDIUM"),
    ("71046", "J18.1",  "Chest X-ray - Pneumonia",            85.00,  False, False, "LOW"),
    ("71046", "R05.9",  "Chest X-ray - Cough",                85.00,  False, False, "LOW"),
    ("97110", "M54.5",  "PT Therapeutic Exercise - Low back",  95.00,  False, True,  "MEDIUM"),
    ("97110", "M25.511","PT Therapeutic Exercise - Shoulder",   95.00,  False, True,  "MEDIUM"),
    ("36415", "Z13.1",  "Venipuncture - Screening",            15.00,  False, False, "LOW"),
    ("99395", "Z00.00", "Preventive visit 18-39",             275.00, False, True,  "LOW"),
    ("99203", "M54.5",  "New patient - Low back pain",        200.00, False, True,  "MEDIUM"),
    ("99204", "G43.909","New patient - Migraine",             300.00, False, True,  "MEDIUM"),
    ("99283", "S52.501A","ER visit - Fracture",               350.00, False, True,  "MEDIUM"),
    ("99284", "I21.9",  "ER visit - Chest pain / MI",         500.00, False, True,  "HIGH"),
    ("99285", "J96.01", "ER critical - Respiratory failure",   650.00, False, True,  "HIGH"),
]

# ─── Intentionally WRONG combos (will trigger compliance flags) ─
WRONG_COMBOS = [
    # Missing CPT code
    ("",      "E11.9",  "MISSING CPT - should flag critical",  250.00, False, True,  "HIGH"),
    # Missing ICD-10 code
    ("99214", "",       "MISSING ICD10 - should flag critical", 250.00, False, True,  "HIGH"),
    # Upcoded: documentation supports 99213 but billed 99215
    ("99215", "J06.9",  "Upcoded - simple URI billed as complex",350.00, False, True, "HIGH"),
    # Missing prior auth for 80053
    ("80053", "R73.03", "CMP WITHOUT prior auth",              125.00, False, False, "MEDIUM"),
    # Missing documentation for critical care
    ("99291", "J96.01", "Critical care - NO documentation",    780.00, False, False, "HIGH"),
    # Psychotherapy billed too high (90837 requires 53+ min)
    ("90837", "F32.1",  "Psychotherapy - missing auth",        200.00, False, True,  "MEDIUM"),
    # Duplicate venipuncture bundling issue
    ("36415", "Z13.1",  "Venipuncture - potential bundling",    15.00,  False, False, "LOW"),
    # Preventive + E/M same day without modifier
    ("99395", "Z00.00", "Preventive - same day issue",         275.00, False, False, "LOW"),
    # Extremely high billing amount (outlier)
    ("99214", "I10",    "Suspiciously HIGH billed amount",    4500.00, False, True,  "HIGH"),
    # Very low compliance provider
    ("99213", "E11.9",  "Low compliance provider",             150.00, False, True,  "LOW"),
]


def generate_patients(n=50):
    patients = []
    for i in range(1, n + 1):
        gender = random.choice(GENDERS)
        first = random.choice(FIRST_NAMES_M if gender == "Male" else FIRST_NAMES_F)
        last = random.choice(LAST_NAMES)
        provider, facility = random.choice(PROVIDERS)
        payer = random.choice(PAYERS)
        
        # Realistic DOB: ages 18-85
        age = random.randint(18, 85)
        dob = datetime(2026, 1, 1) - timedelta(days=age * 365 + random.randint(0, 364))
        
        patients.append({
            "patient_id": f"PAT{10000 + i}",
            "name": f"{first} {last}",
            "dob": dob.strftime("%Y-%m-%d"),
            "gender": gender,
            "provider_name": provider,
            "facility": facility,
            "payer": payer,
        })
    return patients


def generate_claims(patients, n_good=30, n_bad=15):
    claims = []
    claim_counter = 1
    
    # ─── Generate GOOD claims (Approved / Pending) ─────────────
    for _ in range(n_good):
        patient = random.choice(patients)
        combo = random.choice(VALID_COMBOS)
        cpt, icd10, desc, amount, prior_auth, doc_req, impact = combo
        
        # Add some realistic variance to billing
        amount_var = amount * random.uniform(0.9, 1.1)
        
        # Random service date in last 6 months
        days_ago = random.randint(1, 180)
        svc_date = (datetime(2026, 3, 15) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        # Mostly approved, some pending
        status = random.choice(["Approved"] * 7 + ["Pending"] * 3)
        
        claims.append({
            "claim_id": f"CLM-{claim_counter:05d}",
            "patient_id": patient["patient_id"],
            "patient_name": patient["name"],
            "cpt_code": cpt,
            "icd10_code": icd10,
            "billed_amount": round(amount_var, 2),
            "claim_status": status,
            "denial_reason": "",
            "service_date": svc_date,
            "prior_auth_required": prior_auth,
            "documentation_required": doc_req,
            "policy_impact_level": impact,
            "provider_compliance_score": round(random.uniform(0.75, 0.98), 2),
            "provider_name": patient["provider_name"],
            "facility": patient["facility"],
            "payer": patient["payer"],
        })
        claim_counter += 1
    
    # ─── Generate BAD claims (Denied / will trigger flags) ──────
    for _ in range(n_bad):
        patient = random.choice(patients)
        combo = random.choice(WRONG_COMBOS)
        cpt, icd10, desc, amount, prior_auth, doc_req, impact = combo
        
        amount_var = amount * random.uniform(0.95, 1.05)
        days_ago = random.randint(1, 180)
        svc_date = (datetime(2026, 3, 15) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        # Mix of denied, pending (awaiting review)
        if not cpt or not icd10:
            status = "Denied"
            denial = "Missing required code"
        elif amount > 3000:
            status = "Denied"
            denial = "Billed amount exceeds usual and customary"
        elif "Upcoded" in desc:
            status = "Denied"
            denial = "Upcoding — documentation supports lower code level"
        elif "WITHOUT prior auth" in desc:
            status = "Denied"
            denial = "Missing prior authorization"
        elif "Low compliance" in desc:
            status = "Pending"
            denial = ""
        else:
            status = random.choice(["Pending", "Denied"])
            denial = "Documentation insufficient" if status == "Denied" else ""
        
        compliance = round(random.uniform(0.40, 0.70), 2) if "Low compliance" in desc else round(random.uniform(0.50, 0.80), 2)
        
        claims.append({
            "claim_id": f"CLM-{claim_counter:05d}",
            "patient_id": patient["patient_id"],
            "patient_name": patient["name"],
            "cpt_code": cpt,
            "icd10_code": icd10,
            "billed_amount": round(amount_var, 2),
            "claim_status": status,
            "denial_reason": denial,
            "service_date": svc_date,
            "prior_auth_required": prior_auth,
            "documentation_required": doc_req,
            "policy_impact_level": impact,
            "provider_compliance_score": compliance,
            "provider_name": patient["provider_name"],
            "facility": patient["facility"],
            "payer": patient["payer"],
        })
        claim_counter += 1
    
    # Shuffle so good and bad are intermixed
    random.shuffle(claims)
    return claims


def main():
    print("=" * 55)
    print("  Healthcare Compliance Agent — Demo Data Generator")
    print("=" * 55)
    
    patients = generate_patients(50)
    claims = generate_claims(patients, n_good=30, n_bad=15)
    
    # ─── Create combined Excel with 2 sheets ──────────────────
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "demo_healthcare_data.xlsx")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df_patients = pd.DataFrame(patients)
    df_claims = pd.DataFrame(claims)
    
    # Also create a single-sheet "messy" version (like a real hospital upload)
    # Merge patient + claim info into one flat sheet
    df_flat = df_claims.copy()
    # Add some patient details
    patient_map = {p["patient_id"]: p for p in patients}
    df_flat["dob"] = df_flat["patient_id"].map(lambda pid: patient_map.get(pid, {}).get("dob", ""))
    df_flat["gender"] = df_flat["patient_id"].map(lambda pid: patient_map.get(pid, {}).get("gender", ""))
    
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_flat.to_excel(writer, sheet_name="Claims_Data", index=False)
        df_patients.to_excel(writer, sheet_name="Patient_List", index=False)
    
    print(f"\n✅ Generated {len(patients)} patients and {len(claims)} claims")
    print(f"   📁 Saved to: {output_path}")
    
    # Summary
    approved = sum(1 for c in claims if c["claim_status"] == "Approved")
    pending = sum(1 for c in claims if c["claim_status"] == "Pending")
    denied = sum(1 for c in claims if c["claim_status"] == "Denied")
    missing_cpt = sum(1 for c in claims if not c["cpt_code"])
    missing_icd = sum(1 for c in claims if not c["icd10_code"])
    
    print(f"\n   📊 Breakdown:")
    print(f"      ✓ Approved:    {approved}")
    print(f"      ⏳ Pending:     {pending}")
    print(f"      ✗ Denied:      {denied}")
    print(f"      ⚠ Missing CPT: {missing_cpt}")
    print(f"      ⚠ Missing ICD: {missing_icd}")
    print(f"\n   Upload this file via Data Management → Excel Upload")


if __name__ == "__main__":
    main()
