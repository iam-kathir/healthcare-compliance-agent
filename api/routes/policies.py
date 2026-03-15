"""
Policies CRUD Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api.database import get_db, Policy, AuditLog
from api.models import PolicyCreate
from datetime import datetime

router = APIRouter()


@router.get("/")
def list_policies(db: Session = Depends(get_db)):
    try:
        policies = db.query(Policy).order_by(Policy.created_at.desc()).all()
        return [
            {
                "id": p.id,
                "title": p.title,
                "policy_type": p.policy_type,
                "affected_codes": p.affected_codes,
                "requirements": p.requirements,
                "denial_triggers": p.denial_triggers,
                "impact_level": p.impact_level,
                "deadline_days": p.deadline_days,
                "summary": p.summary,
                "source_url": p.source_url,
                "created_at": str(p.created_at) if p.created_at else "",
            }
            for p in policies
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
def create_policy(policy: PolicyCreate, db: Session = Depends(get_db)):
    try:
        db_policy = Policy(
            title=policy.title,
            policy_type=policy.policy_type,
            affected_codes=policy.affected_codes,
            requirements=policy.requirements,
            denial_triggers=policy.denial_triggers,
            impact_level=policy.impact_level,
            deadline_days=policy.deadline_days,
            summary=policy.summary,
            source_url=policy.source_url,
            raw_text=policy.raw_text,
            created_at=datetime.utcnow(),
        )
        db.add(db_policy)
        db.commit()
        db.refresh(db_policy)

        # Audit log
        audit = AuditLog(
            action="Created policy",
            entity_type="Policy",
            entity_id=str(db_policy.id),
            details=f"Policy '{db_policy.title}' created",
            user="System",
        )
        db.add(audit)
        db.commit()

        return {
            "id": db_policy.id,
            "title": db_policy.title,
            "policy_type": db_policy.policy_type,
            "affected_codes": db_policy.affected_codes,
            "impact_level": db_policy.impact_level,
            "summary": db_policy.summary,
            "message": "Policy created successfully",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{policy_id}")
def get_policy(policy_id: int, db: Session = Depends(get_db)):
    try:
        policy = db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")
        return {
            "id": policy.id,
            "title": policy.title,
            "policy_type": policy.policy_type,
            "affected_codes": policy.affected_codes,
            "requirements": policy.requirements,
            "denial_triggers": policy.denial_triggers,
            "impact_level": policy.impact_level,
            "deadline_days": policy.deadline_days,
            "summary": policy.summary,
            "source_url": policy.source_url,
            "raw_text": policy.raw_text,
            "created_at": str(policy.created_at) if policy.created_at else "",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{policy_id}")
def delete_policy(policy_id: int, db: Session = Depends(get_db)):
    try:
        policy = db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")
        title = policy.title
        db.delete(policy)
        db.commit()

        audit = AuditLog(
            action="Deleted policy",
            entity_type="Policy",
            entity_id=str(policy_id),
            details=f"Policy '{title}' deleted",
            user="System",
        )
        db.add(audit)
        db.commit()

        return {"message": f"Policy '{title}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
