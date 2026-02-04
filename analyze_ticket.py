import json
from typing import Any, Dict, Optional, Tuple

from triage_rules import apply_rules  # Phase 4 wiring

# MVP enums (must match Phase 1/2)
ALLOWED_PRIORITY = {"Low", "Medium", "High"}
ALLOWED_CATEGORY = {"Billing", "Bug", "Feature", "General"}

DEFAULT_LLM_FALLBACK = {
    "summary": [
        "Unable to confidently summarize ticket.",
        "Requires human review.",
        "Please review the original message."
    ],
    "priority": "Medium",
    "category": "General",
}


def _extract_response_text(response) -> str:
    """
    Helper to be robust across SDK response shapes.
    Tries common shapes:
      - response.choices[0].message.content
      - response.choices[0].text
    Falls back to str(response).
    """
    try:
        return response.choices[0].message.content.strip()
    except Exception:
        pass
    try:
        return response.choices[0].text.strip()
    except Exception:
        pass
    return str(response).strip()


def analyze_ticket(
    ticket_text: str,
    llm_client,
    model: str = "gpt-4"
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Phase 3: LLM Core
    Input: raw ticket text
    Output: (result_dict, error_str)
    """
    if not ticket_text or not ticket_text.strip():
        return None, "empty_ticket_text"

    prompt = f"""
Analyze the support ticket below and output ONLY valid JSON (no markdown, no extra text).

Ticket:
{ticket_text}

Return JSON with:
- summary: array of 3 to 5 concise bullet strings
- priority: one of "Low", "Medium", "High"
- category: one of "Billing", "Bug", "Feature", "General"

Rules:
- Do NOT invent details that are not in the ticket
- Keep it factual and concise
- If unsure of category, use "General"

Example:
{{"summary":["...","...","..."],"priority":"Medium","category":"Bug"}}
""".strip()

    # 1) Call LLM
    try:
        response = llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=350,
        )
        response_text = _extract_response_text(response)
    except Exception as e:
        return None, f"llm_call_failed: {e}"

    # 2) Parse JSON strictly
    try:
        data = json.loads(response_text)
    except Exception as e:
        return None, f"invalid_json: {e}"

    # 3) Validate shape + enums
    if not isinstance(data, dict):
        return None, "invalid_json_shape_not_object"

    summary = data.get("summary")
    priority = data.get("priority")
    category = data.get("category")

    if (
        not isinstance(summary, list)
        or not (3 <= len(summary) <= 5)
        or not all(isinstance(x, str) for x in summary)
    ):
        return None, "invalid_summary"

    if priority not in ALLOWED_PRIORITY:
        return None, "invalid_priority"

    if category not in ALLOWED_CATEGORY:
        return None, "invalid_category"

    return {
        "summary": summary,
        "priority": priority,
        "category": category,
    }, None


def triage_ticket(ticket_text: str, llm_client, model: str = "gpt-4") -> Dict[str, Any]:
    """
    V1 system entry point:
    Always returns a stable final payload (never None).

    Output keys (stable):
      summary, priority, category, suggested_assignee, confidence,
      needs_human_review, rules_applied, explanation, error
    """
    llm_result, err = analyze_ticket(ticket_text, llm_client, model=model)

    # Always have a safe baseline for Phase 4
    base_llm = llm_result if llm_result is not None else dict(DEFAULT_LLM_FALLBACK)

    final_payload = apply_rules(ticket_text, base_llm)

    # Build explanation + force safe behavior if LLM failed
    explanation_parts = []
    if err:
        explanation_parts.append(f"LLM issue: {err}")
        final_payload["needs_human_review"] = True
        final_payload["confidence"] = 0.0
        final_payload["rules_applied"].append("review:llm_failure_fallback")

    explanation_parts.append(
        f"Final: {final_payload['category']} / {final_payload['priority']} → {final_payload['suggested_assignee']}"
    )
    final_payload["explanation"] = " | ".join(explanation_parts)

    # Helpful for debugging (keep for v1)
    final_payload["error"] = err

    return final_payload
