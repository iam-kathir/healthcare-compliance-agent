"""
Agent Routes — Watcher, Thinker, Fixer endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from api.database import get_db, Policy, Claim, Patient, AuditLog, Fix
from api.models import WatcherTextRequest, WatcherURLRequest, ThinkerScanRequest, FixerRequest
from agents.watcher import extract_policy_from_text, extract_policy_from_url, extract_policy_from_file
from agents.thinker import score_claim_risk, batch_score_claims_from_excel
from agents.fixer import generate_fix_plan, generate_email_template
from utils.cms_scraper import fetch_cms_news
from utils.smart_mapper import map_columns, generate_quality_report
from datetime import datetime
import pandas as pd
import io
import json
import uuid
import traceback

router = APIRouter()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  WATCHER ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _save_policy_to_db(db: Session, policy_data: dict, source_url: str = "", raw_text: str = "") -> dict:
    """Save extracted policy to database — always commits."""
    try:
        db_policy = Policy(
            title=policy_data.get("title", "Untitled Policy"),
            policy_type=policy_data.get("policy_type", policy_data.get("type", "General")),
            affected_codes=policy_data.get("affected_codes", ""),
            requirements=policy_data.get("requirements", ""),
            denial_triggers=policy_data.get("denial_triggers", ""),
            impact_level=policy_data.get("impact_level", "MEDIUM"),
            deadline_days=int(policy_data.get("deadline_days", 30)),
            summary=policy_data.get("summary", ""),
            source_url=source_url,
            raw_text=raw_text[:5000] if raw_text else "",
            created_at=datetime.utcnow(),
        )
        db.add(db_policy)
        db.commit()
        db.refresh(db_policy)

        # Audit
        audit = AuditLog(
            action="Watcher extracted policy",
            entity_type="Policy",
            entity_id=str(db_policy.id),
            details=f"Policy '{db_policy.title}' extracted and saved (impact: {db_policy.impact_level})",
            user="Watcher Agent",
        )
        db.add(audit)
        db.commit()

        return {
            "id": db_policy.id,
            "title": db_policy.title,
            "policy_type": db_policy.policy_type,
            "affected_codes": db_policy.affected_codes,
            "requirements": db_policy.requirements,
            "denial_triggers": db_policy.denial_triggers,
            "impact_level": db_policy.impact_level,
            "deadline_days": db_policy.deadline_days,
            "summary": db_policy.summary,
            "source_url": db_policy.source_url,
        }
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to save policy: {str(e)}")


@router.post("/watcher/scan-text")
def watcher_scan_text(request: WatcherTextRequest, db: Session = Depends(get_db)):
    """Extract policy from pasted text using Claude and save to DB."""
    try:
        if not request.text or len(request.text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Text too short to extract policy")

        policy_data = extract_policy_from_text(request.text)
        if not policy_data or not policy_data.get("title"):
            raise HTTPException(status_code=422, detail="Could not extract a valid policy from the text")

        saved = _save_policy_to_db(db, policy_data, source_url=request.source_url, raw_text=request.text)
        return {"status": "success", "policy": saved}

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Watcher scan-text error: {str(e)}")


@router.post("/watcher/scan-url")
def watcher_scan_url(request: WatcherURLRequest, db: Session = Depends(get_db)):
    """Fetch URL content, extract policy with Claude, save to DB."""
    try:
        if not request.url or not request.url.startswith("http"):
            raise HTTPException(status_code=400, detail="Invalid URL")

        policy_data, raw_text = extract_policy_from_url(request.url)
        if not policy_data or not policy_data.get("title"):
            raise HTTPException(status_code=422, detail="Could not extract a valid policy from the URL")

        saved = _save_policy_to_db(db, policy_data, source_url=request.url, raw_text=raw_text)
        return {"status": "success", "policy": saved}

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Watcher scan-url error: {str(e)}")


@router.post("/watcher/upload")
async def watcher_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Read uploaded PDF/TXT/Excel file, extract policy with Claude, save to DB."""
    try:
        contents = await file.read()
        filename = file.filename or "unknown.txt"

        policy_data, raw_text = extract_policy_from_file(contents, filename)
        if not policy_data or not policy_data.get("title"):
            raise HTTPException(status_code=422, detail="Could not extract a valid policy from the file")

        saved = _save_policy_to_db(db, policy_data, source_url=f"file://{filename}", raw_text=raw_text)
        return {"status": "success", "policy": saved, "filename": filename}

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Watcher upload error: {str(e)}")


@router.get("/watcher/news")
def watcher_fetch_news():
    """Fetch latest CMS healthcare news (with fallback to mock data)."""
    try:
        news = fetch_cms_news()
        return {"status": "success", "news": news, "count": len(news)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"News fetch error: {str(e)}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  THINKER ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/thinker/scan")
def thinker_scan(request: ThinkerScanRequest, db: Session = Depends(get_db)):
    """Score a single claim from user-input patient details. Saves result to DB."""
    try:
        # Get all policies from DB for matching
        policies = db.query(Policy).all()
        policy_list = [
            {
                "id": p.id,
                "title": p.title,
                "affected_codes": p.affected_codes,
                "requirements": p.requirements,
                "denial_triggers": p.denial_triggers,
                "impact_level": p.impact_level,
            }
            for p in policies
        ]

        claim_data = {
            "patient_name": request.patient_name,
            "patient_id": request.patient_id,
            "cpt_code": request.cpt_code,
            "icd10_code": request.icd10_code,
            "billed_amount": request.billed_amount,
            "payer": request.payer,
            "provider_name": request.provider_name,
            "prior_auth_required": request.prior_auth_required,
            "documentation_required": request.documentation_required,
            "provider_compliance_score": request.provider_compliance_score,
            "service_date": request.service_date,
            "claim_status": request.claim_status,
        }

        result = score_claim_risk(claim_data, policy_list)

        # Save claim with risk scores to DB
        claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        db_claim = Claim(
            claim_id=claim_id,
            patient_name=request.patient_name,
            cpt_code=request.cpt_code,
            icd10_code=request.icd10_code,
            billed_amount=request.billed_amount,
            claim_status=request.claim_status,
            service_date=request.service_date,
            prior_auth_required=request.prior_auth_required,
            documentation_required=request.documentation_required,
            provider_compliance_score=request.provider_compliance_score,
            policy_impact_level=result.get("policy_impact_level", "MEDIUM"),
            risk_score=result.get("risk_score", 0.0),
            risk_level=result.get("risk_level", "LOW"),
            matched_policy=result.get("matched_policy", ""),
            recommended_action=result.get("recommended_action", ""),
            created_at=datetime.utcnow(),
        )
        db.add(db_claim)
        db.commit()
        db.refresh(db_claim)

        # Audit
        audit = AuditLog(
            action="Thinker scanned claim",
            entity_type="Claim",
            entity_id=str(db_claim.id),
            details=f"Claim {claim_id} scored: risk={result.get('risk_score', 0)}, level={result.get('risk_level', 'LOW')}",
            user="Thinker Agent",
        )
        db.add(audit)
        db.commit()

        result["claim_id"] = claim_id
        result["db_id"] = db_claim.id
        return {"status": "success", "result": result}

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Thinker scan error: {str(e)}")


@router.post("/thinker/scan-existing")
def thinker_scan_existing(db: Session = Depends(get_db)):
    """Scan all existing claims in DB against policies and update risk scores."""
    try:
        claims = db.query(Claim).all()
        policies = db.query(Policy).all()

        if not claims:
            return {"status": "success", "message": "No claims to scan", "scanned": 0}

        policy_list = [
            {
                "id": p.id,
                "title": p.title,
                "affected_codes": p.affected_codes,
                "requirements": p.requirements,
                "denial_triggers": p.denial_triggers,
                "impact_level": p.impact_level,
            }
            for p in policies
        ]

        scanned = 0
        for claim in claims:
            claim_data = {
                "cpt_code": claim.cpt_code,
                "icd10_code": claim.icd10_code,
                "billed_amount": claim.billed_amount,
                "prior_auth_required": claim.prior_auth_required,
                "documentation_required": claim.documentation_required,
                "provider_compliance_score": claim.provider_compliance_score,
                "claim_status": claim.claim_status,
                "payer": "",
                "provider_name": "",
            }
            result = score_claim_risk(claim_data, policy_list)

            # Update claim in DB
            claim.risk_score = result.get("risk_score", 0.0)
            claim.risk_level = result.get("risk_level", "LOW")
            claim.matched_policy = result.get("matched_policy", "")
            claim.recommended_action = result.get("recommended_action", "")
            scanned += 1

        db.commit()

        audit = AuditLog(
            action="Thinker batch scan",
            entity_type="Claim",
            entity_id="batch",
            details=f"Scanned {scanned} existing claims against {len(policy_list)} policies",
            user="Thinker Agent",
        )
        db.add(audit)
        db.commit()

        return {"status": "success", "scanned": scanned, "message": f"Scanned {scanned} claims"}

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Thinker scan-existing error: {str(e)}")


@router.post("/thinker/upload-excel")
async def thinker_upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload claims Excel, score each row, save to DB, return results."""
    try:
        contents = await file.read()
        policies = db.query(Policy).all()
        policy_list = [
            {
                "id": p.id,
                "title": p.title,
                "affected_codes": p.affected_codes,
                "requirements": p.requirements,
                "denial_triggers": p.denial_triggers,
                "impact_level": p.impact_level,
            }
            for p in policies
        ]

        results = batch_score_claims_from_excel(contents, policy_list)

        # Save scored claims to DB
        for r in results:
            claim_id = r.get("claim_id", f"CLM-{uuid.uuid4().hex[:8].upper()}")
            existing = db.query(Claim).filter(Claim.claim_id == claim_id).first()
            if existing:
                existing.risk_score = r.get("risk_score", 0.0)
                existing.risk_level = r.get("risk_level", "LOW")
                existing.matched_policy = r.get("matched_policy", "")
                existing.recommended_action = r.get("recommended_action", "")
            else:
                db_claim = Claim(
                    claim_id=claim_id,
                    patient_name=r.get("patient_name", ""),
                    cpt_code=r.get("cpt_code", ""),
                    icd10_code=r.get("icd10_code", ""),
                    billed_amount=float(r.get("billed_amount", 0)),
                    claim_status=r.get("claim_status", "Pending"),
                    service_date=r.get("service_date", ""),
                    prior_auth_required=bool(r.get("prior_auth_required", False)),
                    documentation_required=bool(r.get("documentation_required", False)),
                    provider_compliance_score=float(r.get("provider_compliance_score", 0.85)),
                    risk_score=r.get("risk_score", 0.0),
                    risk_level=r.get("risk_level", "LOW"),
                    matched_policy=r.get("matched_policy", ""),
                    recommended_action=r.get("recommended_action", ""),
                    created_at=datetime.utcnow(),
                )
                db.add(db_claim)

        db.commit()

        audit = AuditLog(
            action="Thinker Excel upload scan",
            entity_type="Claim",
            entity_id="excel",
            details=f"Scored {len(results)} claims from uploaded Excel",
            user="Thinker Agent",
        )
        db.add(audit)
        db.commit()

        return {"status": "success", "results": results, "count": len(results)}

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Thinker Excel upload error: {str(e)}")


@router.post("/thinker/analyze-data-quality")
async def thinker_analyze_data_quality(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload Excel, run smart column mapping, and flag missing/incomplete data against policies."""
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        raw_columns = df.columns.tolist()

        # Smart column mapping
        map_result = map_columns(raw_columns)
        col_mapping = map_result["mapping"]
        col_confidence = map_result["confidence"]

        # Rename columns
        rename_map = {raw: canon for raw, canon in col_mapping.items()}
        df = df.rename(columns=rename_map)

        # Get policies for comparison
        policies = db.query(Policy).all()
        policy_list = [
            {
                "id": p.id,
                "title": p.title,
                "affected_codes": p.affected_codes,
                "requirements": p.requirements,
                "denial_triggers": p.denial_triggers,
                "impact_level": p.impact_level,
            }
            for p in policies
        ]

        # Convert rows to dicts
        rows = []
        for _, row in df.iterrows():
            row_dict = {}
            for col in df.columns:
                val = row.get(col, None)
                row_dict[col] = str(val) if val is not None and str(val) != "nan" else ""
            rows.append(row_dict)

        # Generate quality report
        mapped_fields = set(col_mapping.values())
        report = generate_quality_report(rows, policy_list, mapped_fields)

        # Audit
        audit = AuditLog(
            action="Thinker data quality analysis",
            entity_type="Claim",
            entity_id="quality_check",
            details=f"Analyzed {len(rows)} rows: {report['critical_count']} critical, {report['warning_count']} warnings, {report['info_count']} info flags. Completeness: {report['completeness_pct']}%",
            user="Thinker Agent",
        )
        db.add(audit)
        db.commit()

        return {
            "status": "success",
            "column_mapping": {raw: {"mapped_to": canon, "confidence": col_confidence.get(raw, 0)} for raw, canon in col_mapping.items()},
            "unmapped_columns": map_result["unmapped"],
            "quality_report": report,
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Data quality analysis error: {str(e)}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FIXER ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/fixer/generate")
def fixer_generate(request: FixerRequest, db: Session = Depends(get_db)):
    """Generate a fix plan for a high-risk claim."""
    try:
        claim = db.query(Claim).filter(Claim.claim_id == request.claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail=f"Claim '{request.claim_id}' not found")

        policy = None
        if request.policy_id:
            policy = db.query(Policy).filter(Policy.id == request.policy_id).first()

        claim_data = {
            "claim_id": claim.claim_id,
            "cpt_code": claim.cpt_code,
            "icd10_code": claim.icd10_code,
            "billed_amount": claim.billed_amount,
            "claim_status": claim.claim_status,
            "denial_reason": claim.denial_reason,
            "risk_score": claim.risk_score,
            "risk_level": claim.risk_level,
            "matched_policy": claim.matched_policy,
        }

        policy_data = None
        if policy:
            policy_data = {
                "title": policy.title,
                "requirements": policy.requirements,
                "denial_triggers": policy.denial_triggers,
                "affected_codes": policy.affected_codes,
            }

        fix_result = generate_fix_plan(claim_data, policy_data)
        email = generate_email_template(fix_result)

        # Save fix to DB
        db_fix = Fix(
            claim_id=claim.claim_id,
            policy_id=request.policy_id,
            policy_title=policy.title if policy else claim.matched_policy or "General",
            action_plan=fix_result.get("action_plan", ""),
            status="Pending",
            deadline=fix_result.get("deadline", ""),
            estimated_savings=fix_result.get("estimated_savings", 0.0),
            email_template=email,
            created_at=datetime.utcnow(),
        )
        db.add(db_fix)
        db.commit()
        db.refresh(db_fix)

        audit = AuditLog(
            action="Fixer generated fix plan",
            entity_type="Fix",
            entity_id=str(db_fix.id),
            details=f"Fix plan for claim {claim.claim_id}; savings: ${fix_result.get('estimated_savings', 0)}",
            user="Fixer Agent",
        )
        db.add(audit)
        db.commit()

        return {
            "status": "success",
            "fix": {
                "id": db_fix.id,
                "claim_id": db_fix.claim_id,
                "policy_title": db_fix.policy_title,
                "action_plan": db_fix.action_plan,
                "deadline": db_fix.deadline,
                "estimated_savings": db_fix.estimated_savings,
                "email_template": db_fix.email_template,
                "status": db_fix.status,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Fixer generate error: {str(e)}")


@router.post("/fixer/mark-fixed/{fix_id}")
def fixer_mark_fixed(fix_id: int, db: Session = Depends(get_db)):
    """Mark a fix as completed."""
    try:
        fix = db.query(Fix).filter(Fix.id == fix_id).first()
        if not fix:
            raise HTTPException(status_code=404, detail="Fix not found")

        fix.status = "Fixed"
        db.commit()

        # Also update the claim status
        claim = db.query(Claim).filter(Claim.claim_id == fix.claim_id).first()
        if claim:
            claim.claim_status = "Fixed"
            claim.risk_level = "LOW"
            claim.risk_score = max(0, claim.risk_score - 50)
            db.commit()

        audit = AuditLog(
            action="Fixed claim",
            entity_type="Fix",
            entity_id=str(fix_id),
            details=f"Fix {fix_id} for claim {fix.claim_id} marked as Fixed",
            user="System",
        )
        db.add(audit)
        db.commit()

        return {"status": "success", "message": f"Fix {fix_id} marked as Fixed"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Mark fixed error: {str(e)}")


@router.get("/fixer/list")
def fixer_list(db: Session = Depends(get_db)):
    """Get all fix plans."""
    try:
        fixes = db.query(Fix).order_by(Fix.created_at.desc()).all()
        return [
            {
                "id": f.id,
                "claim_id": f.claim_id,
                "policy_id": f.policy_id,
                "policy_title": f.policy_title,
                "action_plan": f.action_plan,
                "status": f.status,
                "deadline": f.deadline,
                "estimated_savings": f.estimated_savings,
                "email_template": f.email_template,
                "created_at": str(f.created_at) if f.created_at else "",
            }
            for f in fixes
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AUDIT LOG ENDPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)):
    try:
        logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
        return [
            {
                "id": l.id,
                "timestamp": str(l.timestamp) if l.timestamp else "",
                "action": l.action,
                "entity_type": l.entity_type,
                "entity_id": l.entity_id,
                "details": l.details,
                "user": l.user,
            }
            for l in logs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
