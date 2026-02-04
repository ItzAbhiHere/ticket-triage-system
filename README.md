# Ticket Triage System (Rules + LLM)

A lightweight **AI automation** project that triages incoming support tickets into structured, reliable outputs using a **hybrid approach**:
- **Rules** for deterministic overrides (high-risk keywords, category inference)
- **LLM** for summaries and initial classification
- **Confidence scoring** + **human-in-the-loop** escalation for safety

This system is designed to behave like a real internal tool: **auditable**, **debuggable**, and resilient to failures.

---

## What it does

Given raw ticket text, the system returns a **stable payload** with:

- `summary` (3–5 bullet points)
- `category` (Billing | Bug | Feature | General)
- `priority` (Low | Medium | High)
- `suggested_assignee` (team mapping)
- `confidence` (0.0–1.0)
- `needs_human_review` (True / False)
- `rules_applied` (audit trail)
- `explanation` (human-readable reason)
- `error` (optional debugging context)

The output shape is **guaranteed**, even when the LLM fails.

---

## Why Rules + AI

Pure AI outputs can be unreliable in edge cases. This project intentionally combines:

- **Rules** to guarantee predictable behavior where needed  
  (e.g. outages, billing keywords, login failures)
- **AI** for flexible summarization and initial classification
- **Confidence scoring + review gates** to avoid blind automation

This makes the system safer to integrate into real operational workflows.

---

## How it works (high level)

```mermaid
flowchart TD
  A[Ticket text] --> B[analyze_ticket LLM JSON and validation]
  B -->|valid| C[apply_rules rules confidence routing]
  B -->|error| D[Fallback payload]
  D --> C
  C --> E[Final payload category priority assignee confidence review gate]
