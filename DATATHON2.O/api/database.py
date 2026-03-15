"""
SQLAlchemy Database Setup — Healthcare Compliance Agent
Tables: Policy, Patient, Claim, AuditLog, Fix
"""
import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, DateTime,
    Boolean, ForeignKey, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hca.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── ORM Models ───────────────────────────────────────────────

class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    policy_type = Column(String(100), default="General")
    affected_codes = Column(Text, default="")          # comma-separated CPT/ICD codes
    requirements = Column(Text, default="")
    denial_triggers = Column(Text, default="")
    impact_level = Column(String(20), default="MEDIUM") # HIGH / MEDIUM / LOW
    deadline_days = Column(Integer, default=30)
    summary = Column(Text, default="")
    source_url = Column(String(1000), default="")
    raw_text = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    dob = Column(String(20), default="")
    gender = Column(String(20), default="")
    provider_name = Column(String(200), default="")
    facility = Column(String(200), default="")
    payer = Column(String(200), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    claims = relationship("Claim", back_populates="patient")


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    claim_id = Column(String(50), unique=True, nullable=False)
    patient_db_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    patient_name = Column(String(200), default="")
    cpt_code = Column(String(20), default="")
    icd10_code = Column(String(20), default="")
    billed_amount = Column(Float, default=0.0)
    claim_status = Column(String(50), default="Pending")
    denial_reason = Column(String(500), default="")
    service_date = Column(String(20), default="")
    prior_auth_required = Column(Boolean, default=False)
    documentation_required = Column(Boolean, default=False)
    policy_impact_level = Column(String(20), default="MEDIUM")
    provider_compliance_score = Column(Float, default=0.85)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(20), default="LOW")
    matched_policy = Column(String(500), default="")
    recommended_action = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="claims")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String(200), nullable=False)
    entity_type = Column(String(100), default="")
    entity_id = Column(String(100), default="")
    details = Column(Text, default="")
    user = Column(String(100), default="System")


class Fix(Base):
    __tablename__ = "fixes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    claim_id = Column(String(50), nullable=False)
    policy_id = Column(Integer, nullable=True)
    policy_title = Column(String(500), default="")
    action_plan = Column(Text, default="")
    status = Column(String(50), default="Pending")       # Pending / In Progress / Fixed
    deadline = Column(String(50), default="")
    estimated_savings = Column(Float, default=0.0)
    email_template = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Create all tables ───────────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)
