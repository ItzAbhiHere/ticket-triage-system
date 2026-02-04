# Project Structure

- `analyze_ticket.py`
  Phase 3: LLM JSON extraction + strict validation
  Includes `triage_ticket()` as the v1 system entry point.

- `triage_rules.py`
  Phase 4: Rules engine + enrichment (assignee mapping, confidence scoring, review gates)

- `run_tests.py`
  Offline-safe test harness (uses fake client when API key is missing)

- `README.md`
  Project overview, how it works, how to run, and design rationale
