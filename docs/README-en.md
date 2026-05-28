# MindForge Documentation

This is the documentation entry point for MindForge, helping users and developers quickly find the right documents. | [中文版](README.md)

---

## User Documentation

### English

| Document | Description |
|----------|-------------|
| [Getting Started](en/getting-started.md) | Installation and first-run guide |
| [User Guide](en/user-guide.md) | Complete feature guide |
| [Model Setup](en/model-setup.md) | LLM provider configuration |
| [Sources](en/sources.md) | Managing knowledge sources |
| [Troubleshooting](en/troubleshooting.md) | Common issues and solutions |

### Chinese

| Document | Description |
|----------|-------------|
| [快速入门](zh-CN/getting-started.md) | Installation, initialization, and first-run guide |
| [用户指南](zh-CN/user-guide.md) | Complete feature guide |
| [模型配置](zh-CN/model-setup.md) | LLM provider configuration |
| [Source 管理](zh-CN/sources.md) | Knowledge source management |
| [审阅与审批](zh-CN/review-and-approval.md) | Review & approval workflow |
| [Library / Recall / Wiki](zh-CN/library-recall-wiki.md) | Browse, recall, wiki, health & graph |
| [Web Wiki](zh-CN/web-wiki.md) | Web Wiki page guide |
| [配置参考](zh-CN/configuration.md) | Complete configuration reference |
| [Troubleshooting](zh-CN/troubleshooting.md) | Common issues diagnosis |
| [FAQ](zh-CN/faq.md) | Frequently asked questions |

---

## Developer Documentation

| Document | Description |
|----------|-------------|
| [Architecture Overview](dev/architecture.md) | System architecture, layer rules, module inventory |
| [Contributing Guide](dev/contributing.md) | How to contribute |
| [Testing Guidelines](dev/testing.md) | Testing framework and conventions |
| [Design System](dev/design-system.md) | Design system reference & UI copy policy |
| [Workspace Data Layout](dev/workspace-data-layout.md) | Workspace directory and data organization |
| [Release Process](dev/release-process.md) | Version release workflow |

---

## Architecture Decision Records (ADR)

| Document | Description |
|----------|-------------|
| [ADR-001: Retrieval Backend](adr/2026-05-24-001-retrieval-backend.md) | Retrieval backend selection (BM25 vs FTS5) |
| [ADR-003: Retrieval Quality Baseline](adr/2026-05-25-003-retrieval-quality-baseline.md) | Retrieval quality baseline |
| [ADR-005: Extension Plugin Boundary](adr/2026-05-25-005-extension-plugin-boundary.md) | Extension plugin safety boundary |

Graph-related ADRs (ADR-002/004/006/007) have been moved to [archive](archive/). Current graph implementation is a deterministic local graph embedded in Library (card/source/tag/wiki_section node types only), not an independent product feature.

---

## Design Documents

| Document | Description |
|----------|-------------|
| [Target Architecture Map](design/2026-05-26-100-target-architecture-map.md) | Target architecture map |
| [Web Design Direction](design/2026-05-26-102-mindforge-web-design-direction.md) | Web design direction |
| [Final Web Design Decision](design/2026-05-26-105-final-web-design-decision.md) | Final web design decision |
| [Obsidian Binding Design](design/obsidian-binding-design.md) | Obsidian integration design (annotated as deferred) |
| [Real Provider Opt-in Safety](design/real-provider-opt-in-safety.md) | Real model opt-in safety design |
| [SDD Wiki Web Addendum](design/sdd/SDD_WIKI_WEB_PRESENTATION_ADDENDUM.md) | Wiki Web presentation UX/copy specification |

Completed RFC/SDD implementation documents and design comparison docs have been moved to [archive](archive/).

---

## User Validation

| Document | Description |
|----------|-------------|
| [Validation Protocol](product/validation-protocol.md) | User validation protocol (includes test script, observer checklist, feedback form, workspace validation checklist) |

---

## Other

| Document | Description |
|----------|-------------|
| [Release Notes](RELEASE_NOTES.md) | v0.1 initial release notes |

---

## Lab / Internal Features

The following features are lab/internal/experimental. They are **not** part of MindForge's main product path:

| Feature | Status | Notes |
|---------|--------|-------|
| Graph Page (standalone) | internal | `/graph` route preserved but not in main nav; Library GraphExplorer is the main entry |
| Sensemaking Workspace | lab | Experimental analysis via simple heuristics; hidden from main nav |
| Entity Resolution | lab | ConceptCandidate deterministic detection; no auto-upgrade |
| Extension Plugin | lab | Architecture placeholder |
| Dogfood Scenarios | internal | Developer/maintainer tools |

Current main product path:
```
Source / Import → ai_draft → Review → explicit approval
    → human_approved → Library → Recall (BM25) / Wiki (LLM synthesis) → Export
```

---

## Historical Documents

[archive/](archive/) contains historical design documents and archived ADRs. These **do not** represent current product capabilities or commitments, and are kept only as historical records of design discussions.
