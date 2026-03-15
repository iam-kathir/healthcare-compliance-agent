"""
Patients CRUD Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api.database import get_db, Patient, AuditLog
from api.models import PatientCreate
from datetime import datetime

router = APIRouter()


@router.get("/")
def list_patients(db: Session = Depends(get_db)):
    try:
        patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
        return [
            {
                "id": p.id,
                "patient_id": p.patient_id,
                "name": p.name,
                "dob": p.dob,
                "gender": p.gender,
                "provider_name": p.provider_name,
                "facility": p.facility,
                "payer": p.payer,
                "created_at": str(p.created_at) if p.created_at else "",
            }
            for p in patients
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    try:
        # Check for duplicate patient_id
        existing = db.query(Patient).filter(Patient.patient_id == patient.patient_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Patient ID '{patient.patient_id}' already exists")

        db_patient = Patient(
            patient_id=patient.patient_id,
            name=patient.name,
            dob=patient.dob,
            gender=patient.gender,
            provider_name=patient.provider_name,
            facility=patient.facility,
            payer=patient.payer,
            created_at=datetime.utcnow(),
        )
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)

        audit = AuditLog(
            action="Created patient",
            entity_type="Patient",
            entity_id=str(db_patient.id),
            details=f"Patient '{db_patient.name}' (ID: {db_patient.patient_id}) created",
            user="System",
        )
        db.add(audit)
        db.commit()

        return {
            "id": db_patient.id,
            "patient_id": db_patient.patient_id,
            "name": db_patient.name,
            "message": "Patient created successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return {
            "id": patient.id,
            "patient_id": patient.patient_id,
            "name": patient.name,
            "dob": patient.dob,
            "gender": patient.gender,
            "provider_name": patient.provider_name,
            "facility": patient.facility,
            "payer": patient.payer,
            "created_at": str(patient.created_at) if patient.created_at else "",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        name = patient.name
        db.delete(patient)
        db.commit()

        audit = AuditLog(
            action="Deleted patient",
            entity_type="Patient",
            entity_id=str(patient_id),
            details=f"Patient '{name}' deleted",
            user="System",
        )
        db.add(audit)
        db.commit()

        return {"message": f"Patient '{name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-all/confirm")
def delete_all_patients(db: Session = Depends(get_db)):
    """Delete ALL patients from the database."""
    try:
        count = db.query(Patient).count()
        db.query(Patient).delete()
        db.commit()

        audit = AuditLog(
            action="Deleted all patients",
            entity_type="Patient",
            entity_id="all",
            details=f"Bulk deleted {count} patients",
            user="System",
        )
        db.add(audit)
        db.commit()

        return {"message": f"Successfully deleted {count} patients", "deleted": count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
