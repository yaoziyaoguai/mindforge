# MindForge Product Boundaries & Safety Contracts

> **Developer & Agent Instruction**: This document defines the critical product boundaries, safety rules, and architectural invariants of MindForge. Any test that verifies "product positioning" or "safety constraints" should assert against this document rather than historical internal ledgers.

## 1. Core Workflow & State Transitions
- **ai_draft vs human_approved**: AI can only propose drafts (`ai_draft`). It cannot directly write to the permanent knowledge base (`human_approved`).
- **Explicit Approval Required**: A human MUST explicitly review and approve every `ai_draft` before it becomes `human_approved`. There is no "auto-approve" or "bulk-approve" bypassing this review.

## 2. Provider Safety
- **Fake Provider Default**: Out-of-the-box, the system uses a safe "fake" (dogfood/mock) provider. This ensures no network calls are made accidentally.
- **Real LLM Opt-in**: Connecting to a real LLM requires explicit opt-in (e.g., providing API keys in the local secret store) and user configuration.

## 3. Data Ingestion & Export
- **Source Adapter vs Provider**: 
  - `SourceAdapter` (e.g., Cubox, local files) is strictly for *reading* raw input.
  - `Provider` (e.g., LLM) is strictly for *processing* data.
- **Safe Export Copy, No Real Obsidian Write**: MindForge stages its export as a "safe copy" (e.g., to a `vault_template` or isolated staging folder). It does NOT write directly to the user's real, live Obsidian vault to prevent accidental data corruption.

## 4. Architectural Exclusions (Non-Goals for Main Path)
- **No RAG / Embedding / Vector DB**: The current main path relies on direct context passing, lexical search (BM25), or explicit references. RAG and Vector DBs are NOT part of the current main path.
- **Lab / Internal Features**: Features such as **Graph**, **Sensemaking**, **Entity** extraction, and **Community** sharing are considered experimental ("Lab" or internal). They are NOT the main path and should not clutter the core user journey.
