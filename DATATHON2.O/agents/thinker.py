"""
Thinker Agent — XGBoost risk scoring + Claude reasoning
Scores claims for denial risk and provides AI-powered explanations.
"""
import os
import json
import traceback
import io
import numpy as np
import pandas as pd

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-5"
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "xgboost_model.json")

# CPT code risk categories
CPT_RISK_MAP = {
    "99213": 0.3, "99214": 0.5, "99215": 0.7, "G0438": 0.6, "G0439": 0.5,
    "80053": 0.4, "99291": 0.8, "90837": 0.5, "99232": 0.6, "71046": 0.3,
    "97110": 0.4, "36415": 0.2, "99395": 0.3, "99203": 0.4, "99204": 0.5,
    "99205": 0.7, "99281": 0.3, "99282": 0.4, "99283": 0.5, "99284": 0.6,
    "99285": 0.8, "99441": 0.4, "99442": 0.5, "99443": 0.6,
}


def _encode_features(claim_data: dict) -> np.ndarray:
    """Encode claim data into feature vector for XGBoost."""
    cpt = claim_data.get("cpt_code", "")
    cpt_risk = CPT_RISK_MAP.get(cpt, 0.5)

    billed = float(claim_data.get("billed_amount", 0))
    billed_norm = min(billed / 5000.0, 1.0)  # Normalize to 0-1

    prior_auth = 1.0 if claim_data.get("prior_auth_required", False) else 0.0
    doc_required = 1.0 if claim_data.get("documentation_required", False) else 0.0
    compliance = float(claim_data.get("provider_compliance_score", 0.85))

    # Impact level encoding
    impact_map = {"HIGH": 0.9, "MEDIUM": 0.5, "LOW": 0.2}
    impact = impact_map.get(claim_data.get("policy_impact_level", "MEDIUM"), 0.5)

    return np.array([[cpt_risk, billed_norm, prior_auth, doc_required, compliance, impact]])


def _predict_risk(features: np.ndarray) -> float:
    """Use XGBoost model to predict risk, or use heuristic fallback."""
    if HAS_XGB and os.path.exists(MODEL_PATH):
        try:
            model = xgb.XGBClassifier()
            model.load_model(MODEL_PATH)
            dmatrix = xgb.DMatrix(features)
            proba = model.predict_proba(features)
            return float(proba[0][1]) * 100  # Probability of denial
        except Exception:
            pass

    # Heuristic fallback
    cpt_risk = features[0][0]
    billed_norm = features[0][1]
    prior_auth = features[0][2]
    doc_required = features[0][3]
    compliance = features[0][4]
    impact = features[0][5]

    score = (
        cpt_risk * 25 +
        billed_norm * 20 +
        prior_auth * 15 +
        doc_required * 10 +
        (1 - compliance) * 20 +
        impact * 10
    )
    return min(max(score, 0), 100)


def _get_risk_level(score: float) -> str:
    if score >= 65:
        return "HIGH"
    elif score >= 35:
        return "MEDIUM"
    else:
        return "LOW"


def _match_policy(claim_data: dict, policies: list) -> dict:
    """Find the best matching policy for a claim's CPT code."""
    cpt = claim_data.get("cpt_code", "")
    best_match = None
    best_score = 0

    for policy in policies:
        codes = policy.get("affected_codes", "")
        if cpt and cpt in codes:
            impact_score = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(policy.get("impact_level", "LOW"), 1)
            if impact_score > best_score:
                best_score = impact_score
                best_match = policy

    return best_match or {}


def _get_claude_reasoning(claim_data: dict, policy: dict, risk_score: float, risk_level: str) -> str:
    """Get Claude's reasoning for the risk assessment."""
    if not HAS_ANTHROPIC or not ANTHROPIC_API_KEY:
        return _mock_reasoning(claim_data, risk_score, risk_level)

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = f"""You are a healthcare compliance expert. Analyze this claim and explain the risk assessment in 3-4 concise sentences.

Claim Details:
- CPT Code: {claim_data.get('cpt_code', 'N/A')}
- ICD-10: {claim_data.get('icd10_code', 'N/A')}
- Billed Amount: ${claim_data.get('billed_amount', 0)}
- Prior Auth Required: {claim_data.get('prior_auth_required', False)}
- Documentation Required: {claim_data.get('documentation_required', False)}
- Provider Compliance Score: {claim_data.get('provider_compliance_score', 0.85)}

Matched Policy: {policy.get('title', 'None')}
Policy Requirements: {policy.get('requirements', 'None')}
Denial Triggers: {policy.get('denial_triggers', 'None')}

Risk Score: {risk_score}/100 ({risk_level})

Explain WHY this claim has this risk level and what specific actions could reduce the risk."""

        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        return _mock_reasoning(claim_data, risk_score, risk_level)


def _mock_reasoning(claim_data: dict, risk_score: float, risk_level: str) -> str:
    """Fallback reasoning when Claude is unavailable."""
    cpt = claim_data.get("cpt_code", "Unknown")
    amount = claim_data.get("billed_amount", 0)
    reasons = []

    if risk_level == "HIGH":
        reasons.append(f"CPT code {cpt} has been flagged for high denial rates in recent CMS audits.")
        if claim_data.get("prior_auth_required"):
            reasons.append("Prior authorization is required but may be missing or incomplete.")
        if amount > 1000:
            reasons.append(f"The billed amount of ${amount:.2f} exceeds typical reimbursement thresholds.")
        reasons.append("Recommend immediate documentation review and prior authorization verification.")
    elif risk_level == "MEDIUM":
        reasons.append(f"CPT code {cpt} carries moderate denial risk based on historical patterns.")
        if claim_data.get("documentation_required"):
            reasons.append("Additional documentation requirements must be verified before submission.")
        reasons.append("Review clinical notes for completeness before claim submission.")
    else:
        reasons.append(f"CPT code {cpt} has a low denial risk profile.")
        reasons.append("Standard documentation appears sufficient. Continue monitoring for policy changes.")

    return " ".join(reasons)


def score_claim_risk(claim_data: dict, policies: list) -> dict:
    """Score a single claim and return risk assessment."""
    # Match policy
    matched = _match_policy(claim_data, policies)
    if matched:
        claim_data["policy_impact_level"] = matched.get("impact_level", "MEDIUM")

    # Encode and predict
    features = _encode_features(claim_data)
    risk_score = round(_predict_risk(features), 1)
    risk_level = _get_risk_level(risk_score)

    # Get reasoning
    reasoning = _get_claude_reasoning(claim_data, matched, risk_score, risk_level)

    # Feature importance (simplified)
    feature_names = ["CPT Risk", "Billed Amount", "Prior Auth", "Documentation", "Compliance", "Policy Impact"]
    feature_values = features[0].tolist()

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "matched_policy": matched.get("title", "No specific policy match"),
        "policy_impact_level": matched.get("impact_level", "MEDIUM"),
        "reasoning": reasoning,
        "recommended_action": f"{'Immediate review required' if risk_level == 'HIGH' else 'Standard review' if risk_level == 'MEDIUM' else 'Continue monitoring'}",
        "feature_importance": dict(zip(feature_names, [round(v, 3) for v in feature_values])),
        "patient_name": claim_data.get("patient_name", ""),
        "cpt_code": claim_data.get("cpt_code", ""),
        "icd10_code": claim_data.get("icd10_code", ""),
        "billed_amount": claim_data.get("billed_amount", 0),
    }


def batch_score_claims_from_excel(file_bytes: bytes, policies: list) -> list:
    """Score claims from uploaded Excel file."""
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
        # Use smart mapper if available, otherwise basic normalization
        try:
            from utils.smart_mapper import map_columns
            map_result = map_columns(df.columns.tolist())
            rename_map = {raw: canon for raw, canon in map_result["mapping"].items()}
            df = df.rename(columns=rename_map)
            df = df.loc[:, ~df.columns.duplicated(keep='first')]
        except ImportError:
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    except Exception as e:
        return [{"error": f"Failed to read Excel: {str(e)}"}]

    def safe_float(val, default=0.0):
        try:
            v = float(val)
            return v if str(v) != "nan" else default
        except (ValueError, TypeError):
            return default

    def safe_str(val, default=""):
        if isinstance(val, (pd.Series, pd.DataFrame)):
            val = str(val.iloc[0]) if len(val) > 0 else default
        s = str(val)
        return default if s in ("nan", "None", "") else s

    results = []
    for _, row in df.iterrows():
        claim_data = {
            "claim_id": safe_str(row.get("claim_id", "")),
            "patient_name": safe_str(row.get("name", row.get("patient_name", "")), "Unknown"),
            "cpt_code": safe_str(row.get("cpt_code", "")),
            "icd10_code": safe_str(row.get("icd10_code", "")),
            "billed_amount": safe_float(row.get("billed_amount", 0)),
            "prior_auth_required": bool(row.get("prior_auth_required", False)),
            "documentation_required": bool(row.get("documentation_required", False)),
            "provider_compliance_score": safe_float(row.get("provider_compliance_score", 0.85), 0.85),
            "claim_status": safe_str(row.get("claim_status", "Pending"), "Pending"),
            "service_date": safe_str(row.get("service_date", "")),
            "payer": safe_str(row.get("payer", "")),
            "provider_name": safe_str(row.get("provider_name", "")),
        }
        result = score_claim_risk(claim_data, policies)
        result["claim_id"] = claim_data["claim_id"]
        result["service_date"] = claim_data["service_date"]
        result["claim_status"] = claim_data["claim_status"]
        results.append(result)

    return results
