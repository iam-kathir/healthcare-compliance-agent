"""
Fixer Agent — Corrective action plan generation using Claude API
Generates fix plans, email templates, and savings estimates.
"""
import os
import json
import traceback
from datetime import datetime, timedelta

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-5"


def generate_fix_plan(claim_data: dict, policy_data: dict = None) -> dict:
    """Generate a corrective action plan for a high-risk claim."""
    if HAS_ANTHROPIC and ANTHROPIC_API_KEY:
        return _claude_fix_plan(claim_data, policy_data)
    return _mock_fix_plan(claim_data, policy_data)


def _claude_fix_plan(claim_data: dict, policy_data: dict = None) -> dict:
    """Use Claude to generate fix plan."""
    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        policy_info = ""
        if policy_data:
            policy_info = f"""
Related Policy: {policy_data.get('title', 'N/A')}
Requirements: {policy_data.get('requirements', 'N/A')}
Denial Triggers: {policy_data.get('denial_triggers', 'N/A')}
Affected Codes: {policy_data.get('affected_codes', 'N/A')}"""

        prompt = f"""You are a healthcare billing compliance expert. Generate a corrective action plan for this claim.

Claim Details:
- Claim ID: {claim_data.get('claim_id', 'N/A')}
- CPT Code: {claim_data.get('cpt_code', 'N/A')}
- ICD-10: {claim_data.get('icd10_code', 'N/A')}
- Billed Amount: ${claim_data.get('billed_amount', 0)}
- Status: {claim_data.get('claim_status', 'N/A')}
- Denial Reason: {claim_data.get('denial_reason', 'N/A')}
- Risk Score: {claim_data.get('risk_score', 0)}/100
- Risk Level: {claim_data.get('risk_level', 'N/A')}
{policy_info}

Return ONLY a valid JSON object:
{{
  "action_plan": "Step-by-step corrective action plan (numbered steps, 4-6 steps)",
  "deadline": "YYYY-MM-DD (14 days from today for HIGH, 30 days for MEDIUM)",
  "estimated_savings": <float: estimated dollar amount saved if fix is implemented>,
  "priority": "URGENT | HIGH | MEDIUM | LOW",
  "department": "Billing | Coding | Clinical Documentation | Prior Auth"
}}"""

        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Parse JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        result = json.loads(text)
        result["estimated_savings"] = float(result.get("estimated_savings", claim_data.get("billed_amount", 0) * 0.7))
        return result

    except Exception as e:
        traceback.print_exc()
        return _mock_fix_plan(claim_data, policy_data)


def _mock_fix_plan(claim_data: dict, policy_data: dict = None) -> dict:
    """Fallback fix plan when Claude is unavailable."""
    risk_level = claim_data.get("risk_level", "MEDIUM")
    cpt = claim_data.get("cpt_code", "N/A")
    amount = float(claim_data.get("billed_amount", 0))

    if risk_level == "HIGH":
        deadline = (datetime.utcnow() + timedelta(days=14)).strftime("%Y-%m-%d")
        priority = "URGENT"
        savings = amount * 0.85
        plan = f"""1. IMMEDIATE: Review clinical documentation for CPT {cpt} to ensure all required elements are present.
2. Verify prior authorization status — obtain retroactive authorization if missing.
3. Cross-reference ICD-10 code ({claim_data.get('icd10_code', 'N/A')}) with CPT {cpt} for medical necessity alignment.
4. Contact payer to request pre-determination or reconsideration if claim was denied.
5. Update billing system with corrected codes and supplemental documentation.
6. Submit corrected claim with appeal letter referencing applicable CMS guidelines."""
    elif risk_level == "MEDIUM":
        deadline = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
        priority = "HIGH"
        savings = amount * 0.6
        plan = f"""1. Review documentation for CPT {cpt} completeness.
2. Verify all required modifiers are applied correctly.
3. Confirm ICD-10 code supports medical necessity for the billed service.
4. Ensure prior authorization documentation is on file if required.
5. Submit corrected claim if discrepancies are found."""
    else:
        deadline = (datetime.utcnow() + timedelta(days=45)).strftime("%Y-%m-%d")
        priority = "MEDIUM"
        savings = amount * 0.3
        plan = f"""1. Standard documentation review for CPT {cpt}.
2. Verify coding accuracy and compliance with current guidelines.
3. File claim with standard processing — monitor for any payer-specific requirements.
4. Schedule routine compliance check for this claim category."""

    return {
        "action_plan": plan,
        "deadline": deadline,
        "estimated_savings": round(savings, 2),
        "priority": priority,
        "department": "Billing",
    }


def generate_email_template(fix_plan: dict) -> str:
    """Generate an email template for the billing team."""
    priority = fix_plan.get("priority", "MEDIUM")
    deadline = fix_plan.get("deadline", "TBD")
    savings = fix_plan.get("estimated_savings", 0)
    action_plan = fix_plan.get("action_plan", "No action plan available")

    return f"""Subject: [ACTION REQUIRED - {priority}] Claim Compliance Fix — Deadline: {deadline}

Dear Billing Team,

A compliance review has identified an issue that requires immediate attention. Please review and action the following corrective plan.

PRIORITY: {priority}
DEADLINE: {deadline}
ESTIMATED REVENUE AT RISK: ${savings:,.2f}

ACTION PLAN:
{action_plan}

Please complete all steps by {deadline} to avoid potential claim rejection or revenue loss.

If you have questions or need additional clinical documentation, please contact the compliance team immediately.

Best regards,
Healthcare Compliance Agent
Automated Compliance Monitoring System

---
This is an automated message generated by the Healthcare Compliance Agent.
Do not reply to this email. For questions, contact your compliance officer.
"""
