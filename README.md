# Ticket Triage System (Rules + LLM)

A lightweight **AI automation** project that triages incoming support tickets into structured, reliable outputs using a **hybrid approach**:
- **Rules** for deterministic overrides (high-risk keywords, category inference)
- **LLM** for summaries and initial classification
- **Confidence scoring** + **human-in-the-loop** escalation for safety

This is designed to behave like a real internal tool: **auditable**, **debuggable**, and resilient to failures.

## What it does

Given raw ticket text, the system returns a stable payload with:
- `summary` (3–5 bullets)
- `category` (Billing | Bug | Feature | General)
- `priority` (Low | Medium | High)
- `suggested_assignee` (team mapping)
- `confidence` (0.0–1.0)
- `needs_human_review` (True/False)
- `rules_applied` (audit trail)
- `explanation` (human-readable reason)
- `error` (optional debugging context)

## Why Rules + AI

Pure AI outputs can be unreliable in edge cases. This project uses:
- **Rules** to guarantee predictable behavior where needed (e.g., outages, billing keywords)
- **AI** for flexible summarization and initial classification
- **Confidence + review gates** to avoid blind automation

## How it works (high level)

```mermaid
flowchart TD
  A[Ticket text] --> B[analyze_ticket: LLM JSON + validation]
  B -->|valid| C[apply_rules: rules + confidence + routing]
  B -->|error| D[Fallback payload]
  D --> C
  C --> E[Final payload: category, priority, assignee, confidence, review gate]

1. `analyze_ticket()` (Phase 3): Calls the LLM and strictly parses JSON output.
2. `apply_rules()` (Phase 4): Applies deterministic rules, assigns a team, computes confidence, flags human review.
3. `triage_ticket()` (V1 entry point): Orchestrates the full pipeline and ensures a **stable output even on failures**.

## Run locally (or in Colab)

Run the test harness:

```bash
python run_tests.py
