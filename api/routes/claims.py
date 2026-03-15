"""
Claims CRUD Routes + Stats + Bulk Upload
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from api.database import get_db, Claim, Patient, AuditLog
from api.models import ClaimCreate
from datetime import datetime
import pandas as pd
import io
import uuid

router = APIRouter()


@router.get("/")
def list_claims(db: Session = Depends(get_db)):
    try:
        claims = db.query(Claim).order_by(Claim.created_at.desc()).all()
        return [
            {
                "id": c.id,
                "claim_id": c.claim_id,
                "patient_db_id": c.patient_db_id,
                "patient_name": c.patient_name,
                "cpt_code": c.cpt_code,
                "icd10_code": c.icd10_code,
                "billed_amount": c.billed_amount,
                "claim_status": c.claim_status,
                "denial_reason": c.denial_reason,
                "service_date": c.service_date,
                "prior_auth_required": c.prior_auth_required,
                "documentation_required": c.documentation_required,
                "policy_impact_level": c.policy_impact_level,
                "provider_compliance_score": c.provider_compliance_score,
                "risk_score": c.risk_score,
                "risk_level": c.risk_level,
                "matched_policy": c.matched_policy or "",
                "recommended_action": c.recommended_action or "",
                "created_at": str(c.created_at) if c.created_at else "",
            }
            for c in claims
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
def create_claim(claim: ClaimCreate, db: Session = Depends(get_db)):
    try:
        db_claim = Claim(
            claim_id=claim.claim_id,
            patient_db_id=claim.patient_db_id,
            patient_name=claim.patient_name,
            cpt_code=claim.cpt_code,
            icd10_code=claim.icd10_code,
            billed_amount=claim.billed_amount,
            claim_status=claim.claim_status,
            denial_reason=claim.denial_reason,
            service_date=claim.service_date,
            prior_auth_required=claim.prior_auth_required,
            documentation_required=claim.documentation_required,
            policy_impact_level=claim.policy_impact_level,
            provider_compliance_score=claim.provider_compliance_score,
            risk_score=claim.risk_score,
            risk_level=claim.risk_level,
            created_at=datetime.utcnow(),
        )
        db.add(db_claim)
        db.commit()
        db.refresh(db_claim)

        audit = AuditLog(
            action="Created claim",
            entity_type="Claim",
            entity_id=str(db_claim.id),
            details=f"Claim '{db_claim.claim_id}' created (CPT: {db_claim.cpt_code}, Amount: ${db_claim.billed_amount})",
            user="System",
        )
        db.add(audit)
        db.commit()

        return {
            "id": db_claim.id,
            "claim_id": db_claim.claim_id,
            "message": "Claim created successfully",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def get_claim_stats(db: Session = Depends(get_db)):
    try:
        claims = db.query(Claim).all()
        total = len(claims)
        pending = sum(1 for c in claims if c.claim_status == "Pending")
        approved = sum(1 for c in claims if c.claim_status == "Approved")
        denied = sum(1 for c in claims if c.claim_status == "Denied")
        high_risk = sum(1 for c in claims if c.risk_level == "HIGH")
        medium_risk = sum(1 for c in claims if c.risk_level == "MEDIUM")
        low_risk = sum(1 for c in claims if c.risk_level == "LOW")
        total_billed = sum((c.billed_amount or 0) for c in claims)
        total_at_risk = sum((c.billed_amount or 0) for c in claims if c.risk_level in ("HIGH", "MEDIUM"))

        return {
            "total_claims": total,
            "pending_claims": pending,
            "approved_claims": approved,
            "denied_claims": denied,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "total_billed": round(total_billed, 2),
            "total_at_risk": round(total_at_risk, 2),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk")
async def bulk_upload_claims(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        from utils.smart_mapper import map_columns

        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        raw_columns = df.columns.tolist()

        # Smart column mapping
        map_result = map_columns(raw_columns)
        col_mapping = map_result["mapping"]       # {raw_col: canonical_field}
        col_confidence = map_result["confidence"]
        unmapped_cols = map_result["unmapped"]

        # Rename columns using the smart mapping
        rename_map = {raw: canon for raw, canon in col_mapping.items()}
        df = df.rename(columns=rename_map)

        # Drop duplicate columns that merged to the same canonical name
        df = df.loc[:, ~df.columns.duplicated(keep='first')]

        created_patients = 0
        created_claims = 0
        skipped = 0

        for _, row in df.iterrows():
            # Handle patient
            pid = str(row.get("patient_id", ""))
            if not pid or pid in ("", "nan", "None"):
                pid = f"P-{uuid.uuid4().hex[:6]}"
            
            # Use safe extraction string methods 
            def extract_scalar(val, default=""):
                if isinstance(val, (pd.Series, pd.DataFrame)):
                    return str(val.iloc[0]) if len(val) > 0 else default
                return str(val) if pd.notna(val) else default

            patient_name = extract_scalar(row.get("name", row.get("patient_name", "Unknown")), "Unknown")
            if patient_name in ("nan", "None", ""):
                patient_name = "Unknown"

            existing_patient = db.query(Patient).filter(Patient.patient_id == pid).first()

            if not existing_patient:
                new_patient = Patient(
                    patient_id=pid,
                    name=patient_name,
                    dob=str(row.get("dob", "")),
                    gender=str(row.get("gender", "")),
                    provider_name=str(row.get("provider_name", "")),
                    facility=str(row.get("facility", "")),
                    payer=str(row.get("payer", "")),
                    created_at=datetime.utcnow(),
                )
                db.add(new_patient)
                db.flush()
                created_patients += 1
                patient_db_id = new_patient.id
            else:
                patient_db_id = existing_patient.id

            # Handle claim
            cid = str(row.get("claim_id", ""))
            if not cid or cid in ("", "nan", "None"):
                cid = f"CLM-{uuid.uuid4().hex[:8].upper()}"

            existing_claim = db.query(Claim).filter(Claim.claim_id == cid).first()
            if existing_claim:
                skipped += 1
                continue

            # Safe float conversion
            def safe_float(val, default=0.0):
                try:
                    v = float(val)
                    return v if str(v) != "nan" else default
                except (ValueError, TypeError):
                    return default

            def safe_bool(val):
                if isinstance(val, bool):
                    return val
                s = str(val).strip().lower()
                return s in ("true", "1", "yes", "y", "t")

            new_claim = Claim(
                claim_id=cid,
                patient_db_id=patient_db_id,
                patient_name=patient_name,
                cpt_code=str(row.get("cpt_code", "")).replace("nan", ""),
                icd10_code=str(row.get("icd10_code", "")).replace("nan", ""),
                billed_amount=safe_float(row.get("billed_amount", 0)),
                claim_status=extract_scalar(row.get("claim_status", "Pending"), "Pending"),
                denial_reason=extract_scalar(row.get("denial_reason", "")),
                service_date=extract_scalar(row.get("service_date", "")),
                prior_auth_required=safe_bool(row.get("prior_auth_required", False)),
                documentation_required=safe_bool(row.get("documentation_required", False)),
                policy_impact_level=extract_scalar(row.get("policy_impact_level", "MEDIUM"), "MEDIUM"),
                provider_compliance_score=safe_float(row.get("provider_compliance_score", 0.85), 0.85),
                created_at=datetime.utcnow(),
            )
            db.add(new_claim)
            created_claims += 1

        db.commit()

        audit = AuditLog(
            action="Smart bulk upload",
            entity_type="Claim",
            entity_id="bulk",
            details=f"Uploaded {created_patients} patients, {created_claims} claims ({skipped} skipped duplicates). Mapped {len(col_mapping)}/{len(raw_columns)} columns.",
            user="System",
        )
        db.add(audit)
        db.commit()

        return {
            "message": f"Successfully uploaded {created_patients} patients and {created_claims} claims",
            "patients_created": created_patients,
            "claims_created": created_claims,
            "skipped_duplicates": skipped,
            "column_mapping": {raw: {"mapped_to": canon, "confidence": col_confidence.get(raw, 0)} for raw, canon in col_mapping.items()},
            "unmapped_columns": unmapped_cols,
            "total_raw_columns": len(raw_columns),
            "mapped_columns": len(col_mapping),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{claim_id}")
def get_claim(claim_id: int, db: Session = Depends(get_db)):
    try:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        return {
            "id": claim.id,
            "claim_id": claim.claim_id,
            "patient_db_id": claim.patient_db_id,
            "patient_name": claim.patient_name,
            "cpt_code": claim.cpt_code,
            "icd10_code": claim.icd10_code,
            "billed_amount": claim.billed_amount,
            "claim_status": claim.claim_status,
            "denial_reason": claim.denial_reason,
            "service_date": claim.service_date,
            "prior_auth_required": claim.prior_auth_required,
            "documentation_required": claim.documentation_required,
            "policy_impact_level": claim.policy_impact_level,
            "provider_compliance_score": claim.provider_compliance_score,
            "risk_score": claim.risk_score,
            "risk_level": claim.risk_level,
            "matched_policy": claim.matched_policy or "",
            "recommended_action": claim.recommended_action or "",
            "created_at": str(claim.created_at) if claim.created_at else "",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{claim_id}")
def delete_claim(claim_id: int, db: Session = Depends(get_db)):
    try:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        cid = claim.claim_id
        db.delete(claim)
        db.commit()

        audit = AuditLog(
            action="Deleted claim",
            entity_type="Claim",
            entity_id=str(claim_id),
            details=f"Claim '{cid}' deleted",
            user="System",
        )
        db.add(audit)
        db.commit()

        return {"message": f"Claim '{cid}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-all/confirm")
def delete_all_claims(db: Session = Depends(get_db)):
    """Delete ALL claims from the database."""
    try:
        count = db.query(Claim).count()
        db.query(Claim).delete()
        db.commit()

        audit = AuditLog(
            action="Deleted all claims",
            entity_type="Claim",
            entity_id="all",
            details=f"Bulk deleted {count} claims",
            user="System",
        )
        db.add(audit)
        db.commit()

        return {"message": f"Successfully deleted {count} claims", "deleted": count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
