# Healthcare Compliance Agent 🏥🤖

An autonomous, AI-driven healthcare compliance management system built to ingest hospital billing data, analyze it against CMS (Centers for Medicare & Medicaid Services) policies, and proactively predict, explain, and prevent claim denials.

## 🌟 Key Features
*   **Intelligent Data Ingestion:** Upload messy, unstandardized hospital Excel files. Uses fuzzy string matching to auto-map arbitrary hospital columns to canonical database schemas.
*   **Hybrid Risk Engine (The Thinker):** 
    *   *Deterministic Layer:* Uses an **XGBoost Classifier** to evaluate 6 numerical features (CPT risk, normalized billed amount, compliance score, etc.) for a rigid probability risk score.
    *   *Generative Layer:* Integrates **Anthropic Claude 3.5 Sonnet** to provide human-readable reasoning explaining *why* the XGBoost model flagged a claim, cross-referencing specific CMS policy text.
*   **Corrective Action Plans (The Fixer):** Generates automated, pre-drafted emails to medical coding staff detailing exactly how to fix a flagged claim before submission.
*   **Policy Monitoring (The Watcher):** Scrapes and tracks CMS policy updates and converts complex legal jargon into structured JSON rulesets.
*   **Interactive Dashboard:** A modern, dark-themed Streamlit SPA with interactive Plotly visualizations tracking revenue-at-risk and compliance metrics.

## 🛠 Tech Stack
*   **Frontend / UI:** Streamlit, Plotly Express
*   **Backend API:** FastAPI, Uvicorn (ASGI)
*   **Database:** SQLite3 with SQLAlchemy ORM
*   **Machine Learning:** XGBoost, Scikit-Learn
*   **Generative AI:** Anthropic Claude API (`claude-sonnet-4-5`)
*   **Data Processing:** Pandas, Difflib
*   **Web Scraping / PDF Parse:** BeautifulSoup4, PyPDF2

## 🏗 Architecture
Follows a decoupled, microservice-inspired architecture:
*   **Backend (`localhost:8000`):** REST API handling all business logic, AI inference, and database transactions.
*   **Frontend (`localhost:8505`):** Stateless UI application communicating entirely via HTTP POST/GET requests to the FastAPI backend.

## 🚀 How to Run Locally

### 1. Prerequisites
Ensure you have Python 3.10+ installed.
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/healthcare-compliance-agent.git
cd healthcare-compliance-agent

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the root directory and add your Anthropic API key to enable the Generative AI features:
```env
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx
```

### 3. Start the Backend API (FastAPI)
```bash
python -m uvicorn api.main:app --reload --port 8000
```
*API documentation (Swagger UI) will be available at [`http://localhost:8000/docs`](http://localhost:8000/docs)*

### 4. Start the Frontend Application (Streamlit)
Open a new terminal window and run:
```bash
streamlit run app.py --server.port 8505
```
*The dashboard will be available at [`http://localhost:8505`](http://localhost:8505)*

### 5. (Optional) Seed the Database
To populate the database with 10 CMS policies, 50 patients, and 45 demo claims (including intentionally flawed claims that trigger the AI flags), run:
```bash
python scripts/seed_db.py
```

## 🔐 Security & Design Principles
*   **Idempotency & Transactions:** All bulk database operations are committed as single ORM transactions to prevent race conditions.
*   **Data Validation:** Pydantic models validate all incoming API payloads before database insertion.
*   **Audit Logging:** Every CRUD operation and AI inference request is strictly logged to an `AuditLog` table for HIPAA-compliant tracking.
*   **Graceful Degradation:** If the Claude API is unreachable or the XGBoost model file is missing, the system gracefully falls back to weighted heuristic scoring and generic reasoning strings without crashing.
