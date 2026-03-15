"""
Pydantic Schemas — Healthcare Compliance Agent
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Policy ──────────────────────────────────────────────────

class PolicyCreate(BaseModel):
    title: str
    policy_type: str = "General"
    affected_codes: str = ""
    requirements: str = ""
    denial_triggers: str = ""
    impact_level: str = "MEDIUM"
    deadline_days: int = 30
    summary: str = ""
    source_url: str = ""
    raw_text: str = ""


class PolicyOut(BaseModel):
    id: int
    title: str
    policy_type: str
    affected_codes: str
    requirements: str
    denial_triggers: str
    impact_level: str
    deadline_days: int
    summary: str
    source_url: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Patient ─────────────────────────────────────────────────

class PatientCreate(BaseModel):
    patient_id: str
    name: str
    dob: str = ""
    gender: str = ""
    provider_name: str = ""
    facility: str = ""
    payer: str = ""


class PatientOut(BaseModel):
    id: int
    patient_id: str
    name: str
    dob: str
    gender: str
    provider_name: str
    facility: str
    payer: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Claim ───────────────────────────────────────────────────

class ClaimCreate(BaseModel):
    claim_id: str
    patient_db_id: Optional[int] = None
    patient_name: str = ""
    cpt_code: str = ""
    icd10_code: str = ""
    billed_amount: float = 0.0
    claim_status: str = "Pending"
    denial_reason: str = ""
    service_date: str = ""
    prior_auth_required: bool = False
    documentation_required: bool = False
    policy_impact_level: str = "MEDIUM"
    provider_compliance_score: float = 0.85
    risk_score: float = 0.0
    risk_level: str = "LOW"


class ClaimOut(BaseModel):
    id: int
    claim_id: str
    patient_db_id: Optional[int] = None
    patient_name: str
    cpt_code: str
    icd10_code: str
    billed_amount: float
    claim_status: str
    denial_reason: str
    service_date: str
    prior_auth_required: bool
    documentation_required: bool
    policy_impact_level: str
    provider_compliance_score: float
    risk_score: float
    risk_level: str
    matched_policy: str
    recommended_action: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClaimStats(BaseModel):
    total_claims: int = 0
    pending_claims: int = 0
    approved_claims: int = 0
    denied_claims: int = 0
    high_risk: int = 0
    medium_risk: int = 0
    low_risk: int = 0
    total_billed: float = 0.0
    total_at_risk: float = 0.0


# ─── Audit Log ───────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    timestamp: Optional[datetime] = None
    action: str
    entity_type: str
    entity_id: str
    details: str
    user: str

    class Config:
        from_attributes = True


# ─── Fix ─────────────────────────────────────────────────────

class FixCreate(BaseModel):
    claim_id: str
    policy_id: Optional[int] = None
    policy_title: str = ""
    action_plan: str = ""
    status: str = "Pending"
    deadline: str = ""
    estimated_savings: float = 0.0
    email_template: str = ""


class FixOut(BaseModel):
    id: int
    claim_id: str
    policy_id: Optional[int] = None
    policy_title: str
    action_plan: str
    status: str
    deadline: str
    estimated_savings: float
    email_template: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Agent Request/Response Schemas ──────────────────────────

class WatcherTextRequest(BaseModel):
    text: str
    source_url: str = ""


class WatcherURLRequest(BaseModel):
    url: str


class ThinkerScanRequest(BaseModel):
    patient_name: str = ""
    patient_id: str = ""
    cpt_code: str = ""
    icd10_code: str = ""
    billed_amount: float = 0.0
    payer: str = ""
    provider_name: str = ""
    prior_auth_required: bool = False
    documentation_required: bool = False
    provider_compliance_score: float = 0.85
    service_date: str = ""
    claim_status: str = "Pending"


class FixerRequest(BaseModel):
    claim_id: str
    policy_id: Optional[int] = None
