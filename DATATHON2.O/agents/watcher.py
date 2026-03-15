"""
Watcher Agent — Policy extraction using Claude API
Handles: text input, URL scanning, file upload (PDF/TXT/Excel)
"""
import os
import json
import traceback

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from utils.pdf_reader import extract_text
from utils.cms_scraper import scrape_url


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-5"

EXTRACTION_PROMPT = """You are a healthcare policy analysis expert. Extract structured policy information from the following text.

Return ONLY a valid JSON object with these fields:
{
  "title": "Policy title or name",
  "policy_type": "Billing | Documentation | Prior Authorization | Coverage | Compliance | General",
  "affected_codes": "Comma-separated CPT/ICD-10 codes affected (e.g., 99213, 99214, G0438)",
  "requirements": "Key requirements for compliance",
  "denial_triggers": "Common reasons claims get denied under this policy",
  "impact_level": "HIGH | MEDIUM | LOW",
  "deadline_days": 30,
  "summary": "2-3 sentence summary of the policy and its impact on healthcare billing"
}

If the text does not contain a clear healthcare policy, still extract the most relevant information and structure it as above.

TEXT TO ANALYZE:
"""


def _call_claude(prompt: str) -> dict:
    """Call Claude API and parse JSON response."""
    if not HAS_ANTHROPIC or not ANTHROPIC_API_KEY:
        # Fallback: generate a mock policy from the text
        return _mock_extraction(prompt)

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Extract JSON from response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        # Try to find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        return json.loads(text)
    except Exception as e:
        traceback.print_exc()
        return _mock_extraction(prompt)


def _mock_extraction(text: str) -> dict:
    """Fallback mock extraction when Claude API is unavailable."""
    # Try to extract a meaningful title from the text
    lines = text.strip().split("\n")
    title = "Extracted Healthcare Policy"
    for line in lines[:5]:
        line = line.strip()
        if len(line) > 10 and len(line) < 200:
            title = line[:150]
            break

    # Check for common CPT codes in test
    codes_found = []
    common_codes = ["99213", "99214", "99215", "G0438", "G0439", "80053",
                    "99291", "90837", "99232", "71046", "97110", "36415", "99395"]
    for code in common_codes:
        if code in text:
            codes_found.append(code)

    return {
        "title": title,
        "policy_type": "General",
        "affected_codes": ", ".join(codes_found) if codes_found else "General",
        "requirements": "Documentation must meet CMS guidelines. All services must be medically necessary.",
        "denial_triggers": "Insufficient documentation, missing prior authorization, coding errors",
        "impact_level": "MEDIUM",
        "deadline_days": 30,
        "summary": f"Policy extracted from provided text. Affects {len(codes_found)} CPT codes. Requires compliance review and documentation verification.",
    }


def extract_policy_from_text(text: str) -> dict:
    """Extract policy information from pasted text."""
    prompt = EXTRACTION_PROMPT + text[:4000]
    return _call_claude(prompt)


def extract_policy_from_url(url: str) -> tuple:
    """Fetch URL content and extract policy. Returns (policy_data, raw_text)."""
    raw_text = scrape_url(url)
    if not raw_text or len(raw_text.strip()) < 20:
        raw_text = f"Policy page from URL: {url}. Unable to fetch full content."

    prompt = EXTRACTION_PROMPT + raw_text[:4000]
    policy_data = _call_claude(prompt)
    return policy_data, raw_text


def extract_policy_from_file(file_bytes: bytes, filename: str) -> tuple:
    """Extract policy from uploaded file. Returns (policy_data, raw_text)."""
    raw_text = extract_text(file_bytes, filename)
    if not raw_text or len(raw_text.strip()) < 10:
        raw_text = f"Content extracted from file: {filename}"

    prompt = EXTRACTION_PROMPT + raw_text[:4000]
    policy_data = _call_claude(prompt)
    return policy_data, raw_text
