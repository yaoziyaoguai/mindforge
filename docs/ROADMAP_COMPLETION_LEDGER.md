# Roadmap Completion Ledger

This compact guard ledger is intentionally the only retained roadmap-adjacent
document besides `ROADMAP.md`. Tests keep it because it protects future-gate
status buckets without requiring dozens of historical milestone files.

## Status Buckets

| Bucket | Meaning | Who can move it |
| --- | --- | --- |
| `available` | Safe local capability is usable now | Normal contribution flow |
| `real-opt-in` | Real provider path exists but requires explicit opt-in | Named human authorizer |
| `review-only` | Produces inspectable artifacts, not approved knowledge | Normal contribution flow |
| `pushed` | Implemented, committed, and validated in the local branch history | Normal contribution flow |
| `local-complete` | Finished locally but not pushed | Current maintainer |
| `future-gated` | Requires fresh design review and explicit human authorization | Named human authorizer |
| `release-gated` | Requires named release authorization before tag/release | Named human authorizer |
| `forbidden` | Conflicts with MindForge identity or safety model | Nobody |

## Current Guarded Gates

| Capability | Bucket | Boundary |
| --- | --- | --- |
| External account ingestion | `future-gated` | sample folder, item cap, dry-run-first, no-persist preview |
| Real Obsidian formal-note write | `future-gated` | diff preview, backup, rollback, per-write confirmation |
| Approval UX polish | `future-gated` | ergonomics only; no timer/model/similarity auto-approval |
| Custom executable strategy runtime | `future-gated` | not active; declarative custom strategies only |
| RAG / embedding / semantic merge | `future-gated` | not active; lexical recall remains current path |
| Public release / git tag | `release-gated` | no automation may create a tag |
| Auto-approve / generated `human_approved` | `forbidden` | only explicit human approval can promote a draft |

No tag and No release are part of the current local workflow closure. Public
tags or release artifacts require a separate named release authorization.

## Completion Claim

MindForge is clean enough for long-term local use on non-sensitive or
project-only data. The current safe path and product direction are documented in
`README.md`.

Opening a future gate requires updating `README.md`, this ledger, and the
boundary tests in the same change.
