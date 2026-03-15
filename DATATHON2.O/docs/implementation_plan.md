# Smart Excel Import + Missing Data Flagging — Enhancement Plan

## Problem
Hospitals upload messy, unorganized Excel files with inconsistent column names (e.g. `Pt Name`, `patient_name`, [Patient](file:///D:/DATATHON2.O/api/database.py#48-62)). The current system requires exact column names and silently drops unrecognized columns. The Thinker also does not flag when critical claim fields are missing (e.g. no CPT code, no ICD-10, no prior auth info) — which directly impacts policy compliance.

## Proposed Changes

### New Utility: Smart Column Mapper

#### [NEW] [smart_mapper.py](file:///D:/DATATHON2.O/utils/smart_mapper.py)
A fuzzy column-mapping engine that:
1. Defines canonical DB columns with **aliases** (e.g. `patient_name` → `["pt name", "patient", "name", "pt_name", "patient name"]`)
2. Uses string similarity matching (difflib) to auto-map messy column headers to canonical fields
3. Returns a **mapping report** showing: original column → mapped field → confidence %
4. Flags unmapped columns so the user knows what data was ignored

---

### Enhanced Bulk Upload Endpoint

#### [MODIFY] [claims.py](file:///D:/DATATHON2.O/api/routes/claims.py)
Update `POST /claims/bulk` to:
1. Call `smart_mapper.py` to auto-map columns before processing
2. Return a **data quality report**: how many rows had missing critical fields
3. Auto-generate missing `claim_id` and `patient_id` when absent
4. Return the column mapping used so the user can verify it

---

### Missing Data Flagging in Thinker

#### [MODIFY] [agents.py](file:///D:/DATATHON2.O/api/routes/agents.py)
Add a new POST endpoint `POST /agents/thinker/analyze-data-quality`:
1. Accepts an uploaded Excel file
2. Runs smart column mapping
3. For each row, checks required fields against each matching policy's requirements:
   - Missing CPT code → 🚩 **CRITICAL** flag
   - Missing ICD-10 → 🚩 **CRITICAL** flag  
   - Missing prior auth when policy requires it → ⚠ **WARNING** flag
   - Missing documentation when policy requires it → ⚠ **WARNING** flag
   - Missing service date, billed amount, payer → ℹ **INFO** flag
4. Returns per-row flag list + aggregate summary

#### [MODIFY] [thinker.py](file:///D:/DATATHON2.O/agents/thinker.py)
Add `check_data_quality(claim_data, policies)` function that generates flags for a single claim by comparing its fields against policy requirements.

---

### Frontend: Smart Upload + Data Quality Dashboard

#### [MODIFY] [app.py](file:///D:/DATATHON2.O/app.py)
**Data Management → Excel Upload tab** — enhanced to show:
1. Column mapping preview table (original → mapped → confidence)
2. Manual override dropdowns for uncertain mappings
3. Data quality summary: ✅ Complete / ⚠ Warnings / 🚩 Critical Missing
4. Per-row flags expandable view

**Thinker → new "Data Quality Check" tab**:
1. Upload Excel → see flag summary: X critical, Y warnings, Z info
2. Table with color-coded rows (red = critical flags, amber = warnings)
3. "Fix suggestions" per flag (e.g. "Add CPT code", "Attach prior auth")
4. Download flagged report as Excel

---

## Workflow Ideas for Better Usage

> [!TIP]
> ### Suggested End-to-End Hospital Workflow
> 1. **Upload** → Hospital uploads raw Excel in Data Management
> 2. **Map** → Smart mapper shows column preview + auto-maps
> 3. **Quality Check** → Thinker auto-scans for missing fields + policy violations  
> 4. **Risk Score** → XGBoost scores each row for denial probability
> 5. **Fix** → Fixer generates corrective actions for flagged claims
> 6. **Export** → Download clean, scored, flagged report for billing team

> [!IMPORTANT]
> ### Additional Feature Ideas
> - **Batch Fix Mode**: Fixer generates fix plans for ALL high-risk claims at once, not one-by-one
> - **Policy Auto-Match**: When uploading Excel, auto-detect which CMS policies are relevant to the uploaded CPT codes and show them as context
> - **Compliance Score Card**: A per-provider "report card" showing their compliance trends over time
> - **Data Completeness Gauge**: A radial progress chart showing % of required fields filled (like 73% complete)

## Verification Plan

### Manual Testing
1. Create a messy Excel file with non-standard column headers and missing data
2. Upload it and verify column mapping preview appears correctly
3. Run data quality check and verify flags are raised for missing CPT/ICD-10 codes
4. Verify flagged rows are highlighted in red/amber in the UI
