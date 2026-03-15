# Healthcare Compliance Agent — Build Tasks

## Phase 1: Project Setup
- [x] Create project structure and directories
- [x] Create [requirements.txt](file:///D:/DATATHON2.O/requirements.txt)
- [ ] Set up virtual environment and install dependencies

## Phase 2: Backend — Database & Models
- [x] [api/database.py](file:///D:/DATATHON2.O/api/database.py) — SQLAlchemy ORM, tables: Policy, Patient, Claim, AuditLog, Fix
- [x] [api/models.py](file:///D:/DATATHON2.O/api/models.py) — Pydantic schemas

## Phase 3: Backend — API Routes
- [x] [api/main.py](file:///D:/DATATHON2.O/api/main.py) — FastAPI entry point with CORS
- [x] [api/routes/policies.py](file:///D:/DATATHON2.O/api/routes/policies.py) — /policies CRUD
- [x] [api/routes/patients.py](file:///D:/DATATHON2.O/api/routes/patients.py) — /patients CRUD
- [x] [api/routes/claims.py](file:///D:/DATATHON2.O/api/routes/claims.py) — /claims CRUD + stats + bulk
- [x] [api/routes/agents.py](file:///D:/DATATHON2.O/api/routes/agents.py) — /agents — Watcher, Thinker, Fixer endpoints

## Phase 4: AI Agents
- [x] [agents/watcher.py](file:///D:/DATATHON2.O/agents/watcher.py) — Claude API policy extraction (text, URL, PDF)
- [x] [agents/thinker.py](file:///D:/DATATHON2.O/agents/thinker.py) — XGBoost + Claude risk scoring
- [x] [agents/fixer.py](file:///D:/DATATHON2.O/agents/fixer.py) — Claude corrective action plans

## Phase 5: Utilities
- [x] [utils/pdf_reader.py](file:///D:/DATATHON2.O/utils/pdf_reader.py) — PDF/TXT extraction
- [x] [utils/cms_scraper.py](file:///D:/DATATHON2.O/utils/cms_scraper.py) — CMS RSS + web scraper with fallback

## Phase 6: Data & ML
- [x] [seed_db.py](file:///D:/DATATHON2.O/seed_db.py) — DB seeder with 10 CMS policies + sample data
- [x] [train_model.py](file:///D:/DATATHON2.O/train_model.py) — XGBoost model training
- [ ] `data/healthcare_compliance_cleaned.xlsx` — Sample dataset (optional)

## Phase 7: Frontend — Streamlit UI
- [/] `app.py` — Building complete UI:
- [ ] `app.py` — Full Streamlit UI with all pages:
  - [ ] Dashboard with charts (Plotly dark theme)
  - [ ] Data Management (Patients + Claims + Excel upload)
  - [ ] Watcher (Text, URL, PDF/Excel upload, Policy Library)
  - [ ] Thinker (Patient input, Excel upload, risk scoring)
  - [ ] Fixer (Fix plans, mark as fixed, deadline timers)
  - [ ] Audit Trail (filterable, exportable logs)
  - [ ] Professional CSS, animations, color scheme

## Phase 8: Verification
- [ ] Start backend and verify API docs at localhost:8000/docs
- [ ] Start frontend and verify all pages render
- [ ] Test Watcher → Thinker → Fixer pipeline flow
