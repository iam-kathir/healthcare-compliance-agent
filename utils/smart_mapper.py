"""
Smart Column Mapper — Fuzzy matching for messy hospital Excel uploads
Maps arbitrary column names to canonical database fields using string similarity.
"""
import difflib
from typing import Dict, List, Tuple, Optional


# ─── Canonical DB columns with known aliases ─────────────────
COLUMN_ALIASES: Dict[str, List[str]] = {
    "patient_id": [
        "patient_id", "patientid", "pat_id", "pt_id", "pid", "patient id",
        "pat id", "mrn", "medical_record_number", "id_patient",
    ],
    "name": [
        "name", "patient_name", "patientname", "pt_name", "ptname",
        "patient name", "pt name", "full_name", "fullname", "full name",
        "patient_full_name",
    ],
    "dob": [
        "dob", "date_of_birth", "dateofbirth", "birth_date", "birthdate",
        "date of birth", "birth date", "birthday", "d.o.b", "d_o_b",
    ],
    "gender": [
        "gender", "sex", "patient_gender", "patient_sex", "pt_gender",
    ],
    "provider_name": [
        "provider_name", "provider", "doctor", "physician", "dr_name",
        "provider name", "attending", "attending_physician", "doc_name",
        "referring_provider", "rendering_provider",
    ],
    "facility": [
        "facility", "hospital", "clinic", "facility_name", "hospital_name",
        "clinic_name", "location", "site", "treatment_facility",
    ],
    "payer": [
        "payer", "insurance", "payer_name", "insurance_name", "insurer",
        "insurance_company", "plan", "health_plan", "payor", "coverage",
    ],
    "claim_id": [
        "claim_id", "claimid", "claim_number", "claim_no", "claim id",
        "clm_id", "claim#", "claim_num", "claim number",
    ],
    "cpt_code": [
        "cpt_code", "cpt", "cptcode", "procedure_code", "proc_code",
        "cpt code", "procedure code", "hcpcs", "hcpcs_code", "service_code",
    ],
    "icd10_code": [
        "icd10_code", "icd10", "icd_10", "icd", "diagnosis_code",
        "diag_code", "icd10 code", "icd-10", "dx_code", "diagnosis",
        "icd_code", "primary_diagnosis",
    ],
    "billed_amount": [
        "billed_amount", "amount", "billed", "charge", "total_charge",
        "billed amount", "charges", "total_amount", "bill_amount",
        "charge_amount", "total_charges", "cost", "price",
    ],
    "claim_status": [
        "claim_status", "status", "claim status", "claimstatus",
        "disposition", "adjudication_status", "result",
    ],
    "denial_reason": [
        "denial_reason", "denial reason", "deny_reason", "reason",
        "denial_code", "reject_reason", "rejection_reason", "remark_code",
    ],
    "service_date": [
        "service_date", "date_of_service", "dos", "service date",
        "date of service", "svc_date", "encounter_date", "visit_date",
        "treatment_date",
    ],
    "prior_auth_required": [
        "prior_auth_required", "prior_auth", "prior_authorization",
        "auth_required", "pre_auth", "preauth", "authorization",
        "prior authorization", "pa_required",
    ],
    "documentation_required": [
        "documentation_required", "doc_required", "documentation",
        "docs_needed", "documentation needed", "addl_docs",
    ],
    "policy_impact_level": [
        "policy_impact_level", "impact_level", "impact", "risk_category",
        "policy_impact", "severity",
    ],
    "provider_compliance_score": [
        "provider_compliance_score", "compliance_score", "compliance",
        "provider_score", "quality_score",
    ],
}

# Fields absolutely required for a valid claim record
CRITICAL_FIELDS = ["cpt_code", "icd10_code"]
WARNING_FIELDS = ["prior_auth_required", "documentation_required", "billed_amount"]
INFO_FIELDS = ["service_date", "payer", "provider_name", "patient_id", "name"]


def _normalize(col: str) -> str:
    """Lowercase, strip, replace special chars."""
    return col.strip().lower().replace("-", "_").replace(".", "_").replace(" ", "_").replace("#", "")


def map_columns(raw_columns: List[str], threshold: float = 0.55) -> Dict:
    """
    Map raw Excel column names to canonical DB fields.

    Returns dict with:
      - mapping: {raw_col: canonical_field}
      - confidence: {raw_col: float 0-1}
      - unmapped: [raw_cols that couldn't be mapped]
      - canonical_coverage: {canonical_field: raw_col or None}
    """
    mapping = {}
    confidence = {}
    unmapped = []

    # Build reverse lookup: alias → canonical
    alias_lookup = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_lookup[_normalize(alias)] = canonical

    used_canonicals = set()

    for raw_col in raw_columns:
        norm = _normalize(raw_col)

        # 1. Exact match
        if norm in alias_lookup:
            canon = alias_lookup[norm]
            if canon not in used_canonicals:
                mapping[raw_col] = canon
                confidence[raw_col] = 1.0
                used_canonicals.add(canon)
                continue

        # 2. Fuzzy match against all aliases
        best_match = None
        best_score = 0.0
        best_canon = None

        all_aliases = list(alias_lookup.keys())
        matches = difflib.get_close_matches(norm, all_aliases, n=3, cutoff=threshold)

        for match in matches:
            score = difflib.SequenceMatcher(None, norm, match).ratio()
            canon = alias_lookup[match]
            if canon not in used_canonicals and score > best_score:
                best_score = score
                best_match = match
                best_canon = canon

        if best_canon and best_score >= threshold:
            mapping[raw_col] = best_canon
            confidence[raw_col] = round(best_score, 3)
            used_canonicals.add(best_canon)
        else:
            unmapped.append(raw_col)

    # Build coverage report
    canonical_coverage = {}
    for canonical in COLUMN_ALIASES:
        matched_raw = None
        for raw_col, mapped_canon in mapping.items():
            if mapped_canon == canonical:
                matched_raw = raw_col
                break
        canonical_coverage[canonical] = matched_raw

    return {
        "mapping": mapping,
        "confidence": confidence,
        "unmapped": unmapped,
        "canonical_coverage": canonical_coverage,
    }


def check_data_quality(df_row: dict, policies: list, mapped_fields: set) -> List[dict]:
    """
    Check a single row for missing/incomplete data against policy requirements.

    Returns list of flag dicts:
      {level: CRITICAL|WARNING|INFO, field: str, message: str}
    """
    flags = []

    # ─── Critical: missing CPT / ICD-10 ───────────────────────
    cpt = str(df_row.get("cpt_code", "")).strip()
    icd = str(df_row.get("icd10_code", "")).strip()

    if not cpt or cpt in ("", "nan", "None"):
        flags.append({
            "level": "CRITICAL",
            "field": "cpt_code",
            "message": "Missing CPT/procedure code — claim cannot be processed without it",
        })

    if not icd or icd in ("", "nan", "None"):
        flags.append({
            "level": "CRITICAL",
            "field": "icd10_code",
            "message": "Missing ICD-10 diagnosis code — claim will be denied without a valid diagnosis",
        })

    # ─── Warning: policy-driven checks ────────────────────────
    for policy in policies:
        affected_codes = policy.get("affected_codes", "")
        if cpt and cpt in affected_codes:
            # Check prior auth
            pa = df_row.get("prior_auth_required", None)
            if "prior auth" in policy.get("requirements", "").lower() or "prior authorization" in policy.get("denial_triggers", "").lower():
                if pa is None or str(pa).strip() in ("", "nan", "None"):
                    flags.append({
                        "level": "WARNING",
                        "field": "prior_auth_required",
                        "message": f"Policy '{policy.get('title', '')}' requires prior authorization for {cpt} — field is missing",
                    })

            # Check documentation
            doc = df_row.get("documentation_required", None)
            if "documentation" in policy.get("requirements", "").lower():
                if doc is None or str(doc).strip() in ("", "nan", "None"):
                    flags.append({
                        "level": "WARNING",
                        "field": "documentation_required",
                        "message": f"Policy '{policy.get('title', '')}' has documentation requirements for {cpt} — field is missing",
                    })

            # Check for denial triggers
            denial_triggers = policy.get("denial_triggers", "")
            if "time" in denial_triggers.lower() and not df_row.get("service_date"):
                flags.append({
                    "level": "WARNING",
                    "field": "service_date",
                    "message": f"Policy '{policy.get('title', '')}' has time-based requirements — service date is missing",
                })

    # ─── Info: general missing fields ─────────────────────────
    billed = df_row.get("billed_amount", None)
    if billed is None or str(billed).strip() in ("", "nan", "None", "0", "0.0"):
        flags.append({
            "level": "WARNING",
            "field": "billed_amount",
            "message": "Billed amount is missing or zero — revenue tracking will be incomplete",
        })

    for field in ["service_date", "payer", "name", "patient_id"]:
        val = df_row.get(field, None)
        if val is None or str(val).strip() in ("", "nan", "None"):
            flags.append({
                "level": "INFO",
                "field": field,
                "message": f"Optional field '{field}' is missing — data will be incomplete",
            })

    return flags


def generate_quality_report(rows: list, policies: list, mapped_fields: set) -> dict:
    """
    Generate aggregate data quality report for all rows.

    Returns: {
        total_rows, critical_count, warning_count, info_count,
        rows_with_flags: [{row_index, flags: [...]}],
        field_summary: {field: {critical: N, warning: N, info: N}},
        completeness_pct: float (0-100)
    }
    """
    all_flags = []
    field_summary = {}
    total_fields_expected = 0
    total_fields_present = 0

    for i, row in enumerate(rows):
        flags = check_data_quality(row, policies, mapped_fields)
        if flags:
            all_flags.append({"row_index": i, "row_data": row, "flags": flags})

        # Count completeness
        for field in COLUMN_ALIASES:
            total_fields_expected += 1
            val = row.get(field, None)
            if val is not None and str(val).strip() not in ("", "nan", "None"):
                total_fields_present += 1

        # Aggregate field flags
        for f in flags:
            field = f["field"]
            if field not in field_summary:
                field_summary[field] = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
            field_summary[field][f["level"]] += 1

    critical_count = sum(1 for r in all_flags for f in r["flags"] if f["level"] == "CRITICAL")
    warning_count = sum(1 for r in all_flags for f in r["flags"] if f["level"] == "WARNING")
    info_count = sum(1 for r in all_flags for f in r["flags"] if f["level"] == "INFO")

    completeness = (total_fields_present / total_fields_expected * 100) if total_fields_expected > 0 else 0

    return {
        "total_rows": len(rows),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "info_count": info_count,
        "completeness_pct": round(completeness, 1),
        "rows_with_flags": all_flags[:100],  # Cap at 100 for performance
        "field_summary": field_summary,
    }
