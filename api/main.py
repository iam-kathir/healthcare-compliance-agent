"""
FastAPI Entry Point — Healthcare Compliance Agent
"""
import os
from dotenv import load_dotenv

# Load .env BEFORE anything else reads environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.database import init_db
from api.routes import policies, patients, claims, agents

app = FastAPI(
    title="Healthcare Compliance Agent API",
    description="Autonomous agent for healthcare policy monitoring, risk scoring, and compliance management",
    version="2.0.0",
)

# CORS — allow Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(policies.router, prefix="/policies", tags=["Policies"])
app.include_router(patients.router, prefix="/patients", tags=["Patients"])
app.include_router(claims.router, prefix="/claims", tags=["Claims"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {
        "app": "Healthcare Compliance Agent API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
