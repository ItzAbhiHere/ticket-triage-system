from __future__ import annotations

import re
from typing import Any, Dict, List

ALLOWED_PRIORITY = {"Low", "Medium", "High"}
ALLOWED_CATEGORY = {"Billing", "Bug", "Feature", "General"}

ASSIGNEE_BY_CATEGORY = {
    "Billing": "Billing Team",
    "Bug": "Engineering - Bugs",
    "Feature": "Product - Feature Requests",
    "General": "Support L1",
}

# Simple keyword sets (MVP)
CATEGORY_KEYWORDS = {
    "Billing": ["refund", "invoice", "charged", "charge", "payment", "billing", "card", "subscription"],
    "Bug": ["error", "500", "crash", "crashing", "broken", "bug", "stack trace", "exception", "internal server error"],
    "Feature": ["feature request", "would like", "can you add", "enhancement", "request a feature", "add support for"],
}

HIGH_PRIORITY_KEYWORDS = [
    "production down", "prod down", "outage", "data loss", "security breach", "can't access",
    "cannot access", "can't login", "cannot login", "urgent", "immediately", "asap", "p0", "sev0", "sev1"
]


def _normalize_text(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def _keyword_hit(normalized_text: str, keywords: List[str]) -> bool:
    return any(k in normalized_text for k in keywords)


def _infer_category_from_text(normalized_text: str) -> str:
    # Billing has precedence if billing keywords present
    if _keyword_hit(normalized_text, CATEGORY_KEYWORDS["Billing"]):
        return "Billing"
    if _keyword_hit(normalized_text, CATEGORY_KEYWORDS["Bug"]):
        return "Bug"
    if _keyword_hit(normalized_text, CATEGORY_KEYWORDS["Feature"]):
        return "Feature"
    return "General"


def _infer_priority_from_text(normalized_text: str) -> str:
    if _keyword_hit(normalized_text, HIGH_PRIORITY_KEYWORDS):
        return "High"
    return ""  # empty means "no override"


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def apply_rules(ticket_text: str, llm_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 4: Rules engine + enrichment

    Inputs:
      - ticket_text: raw ticket text
      - llm_result: output from analyze_ticket(): {summary, priority, category}

    Output (final MVP-ish payload):
    {
      "summary": [...],
      "priority": "Low|Medium|High",
      "category": "Billing|Bug|Feature|General",
      "suggested_assignee": "...",
      "confidence": 0.0-1.0,
      "needs_human_review": bool,
      "rules_applied": [ ... ]
    }
    """
    rules_applied: List[str] = []

    normalized = _normalize_text(ticket_text)

    # --- Extract LLM values safely ---
    summary = llm_result.get("summary", [])
    llm_priority = llm_result.get("priority", "")
    llm_category = llm_result.get("category", "")

    # Defensive normalization
    if isinstance(llm_priority, str):
        llm_priority = llm_priority.strip().title()
    if isinstance(llm_category, str):
        llm_category = llm_category.strip().title()

    # If LLM outputs are invalid, treat as "unknown"
    if llm_priority not in ALLOWED_PRIORITY:
        rules_applied.append("llm_invalid_priority->needs_review")
        llm_priority = "Medium"  # safe default
    if llm_category not in ALLOWED_CATEGORY:
        rules_applied.append("llm_invalid_category->General")
        llm_category = "General"

    # --- Rule inference from ticket text ---
    rule_category = _infer_category_from_text(normalized)
    rule_priority_override = _infer_priority_from_text(normalized)  # "High" or ""

    # --- Apply category override if rules are confident ---
    final_category = llm_category
    override_applied = False
    if rule_category != llm_category:
        final_category = rule_category
        override_applied = True
        rules_applied.append(f"override_category:{llm_category}->{rule_category}")

    # --- Apply priority override if high-priority keywords present ---
    final_priority = llm_priority
    if rule_priority_override and rule_priority_override != llm_priority:
        final_priority = rule_priority_override
        override_applied = True
        rules_applied.append(f"override_priority:{llm_priority}->{rule_priority_override}")

    # --- Assignee mapping (team-level) ---
    suggested_assignee = ASSIGNEE_BY_CATEGORY.get(final_category, "Support L1")
    rules_applied.append(f"assignee_map:{final_category}->{suggested_assignee}")

    # --- Confidence (heuristic, defensible) ---
    confidence = 0.5

    # Agreement adds confidence
    if llm_category == rule_category:
        confidence += 0.2
        rules_applied.append("confidence:+0.2(category_agreement)")
    else:
        confidence -= 0.1
        rules_applied.append("confidence:-0.1(category_disagreement)")

    if not rule_priority_override:
        confidence += 0.05
        rules_applied.append("confidence:+0.05(no_priority_override_needed)")
    else:
        confidence += 0.1
        rules_applied.append("confidence:+0.1(high_priority_keywords)")

    # Override penalty (because human should verify)
    if override_applied:
        confidence -= 0.2
        rules_applied.append("confidence:-0.2(override_penalty)")

    # Short input penalty (avoid penalizing empty string; that’s handled upstream)
    if 0 < len(normalized) < 30:
        confidence -= 0.2
        rules_applied.append("confidence:-0.2(short_input)")

    confidence = _clamp(confidence)

    # --- needs_human_review ---
    needs_human_review = False
    if confidence < 0.6:
        needs_human_review = True
        rules_applied.append("review:confidence_below_0.6")
    if override_applied:
        needs_human_review = True
        rules_applied.append("review:override_applied")

    return {
        "summary": summary,
        "priority": final_priority,
        "category": final_category,
        "suggested_assignee": suggested_assignee,
        "confidence": round(confidence, 2),
        "needs_human_review": needs_human_review,
        "rules_applied": rules_applied,
    }
