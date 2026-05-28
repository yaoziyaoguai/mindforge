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
| [Architecture Overview](dev/architecture.md) | Code architecture |
| [Architecture Map](dev/architecture-map.md) | Module and subsystem map |
| [Contributing Guide](dev/contributing.md) | How to contribute |
| [Testing Guidelines](dev/testing.md) | Testing framework and conventions |
| [Workspace Data Layout](dev/workspace-data-layout.md) | Workspace directory and data organization |
| [Release Process](dev/release-process.md) | Version release workflow |
| [Copy Policy](dev/copy-policy.md) | UI copy standards |
| [Design System](dev/design-system.md) | Design system reference |

---

## Architecture Decision Records (ADR)

| Document | Description |
|----------|-------------|
| [ADR-001: Retrieval Backend](adr/2026-05-24-001-retrieval-backend.md) | Retrieval backend selection |
| [ADR-002: Kuzu Graph Backend](adr/2026-05-24-002-kuzu-graph-backend.md) | Graph database backend selection |
| [ADR-003: Retrieval Quality Baseline](adr/2026-05-25-003-retrieval-quality-baseline.md) | Retrieval quality baseline |
| [ADR-004: Graph Query Capability Gap](adr/2026-05-25-004-graph-query-capability-gap-analysis.md) | Graph query capability analysis |
| [ADR-005: Extension Plugin Boundary](adr/2026-05-25-005-extension-plugin-boundary.md) | Extension plugin boundary |
| [ADR-006: Graph Ontology v1](adr/2026-05-25-006-graph-ontology-v1.md) | Graph ontology v1 |
| [ADR-007: Graph Backend Decision](adr/2026-05-25-007-graph-backend-decision.md) | Graph backend decision |

---

## Design Documents

| Document | Description |
|----------|-------------|
| [Target Architecture Map](design/2026-05-26-100-target-architecture-map.md) | Target architecture map |
| [Web Design Direction](design/2026-05-26-102-mindforge-web-design-direction.md) | Web design direction |
| [Web Design Shotgun Comparison](design/2026-05-26-104-web-design-shotgun-comparison.md) | Web design comparison |
| [Final Web Design Decision](design/2026-05-26-105-final-web-design-decision.md) | Final web design decision |
| [Obsidian Binding Design](design/obsidian-binding-design.md) | Obsidian binding design |
| [Real Provider Opt-in Safety](design/real-provider-opt-in-safety.md) | Real model opt-in safety design |
| [RFC: Source Adapter V2](design/rfc/RFC_0001_SOURCE_ADAPTER_V2.md) | Source adapter RFC |
| [RFC: Wiki Presentation V2](design/rfc/RFC_0002_WIKI_PRESENTATION_V2.md) | Wiki presentation RFC |
| [RFC: Knowledge Quality & Navigation](design/rfc/RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md) | Knowledge quality & navigation RFC |
| [v2.0-v2.5 Changelog](design/v2.0-v2.5-changelog.md) | v2.0-v2.5 changelog |

---

## User Validation

| Document | Description |
|----------|-------------|
| [Validation Protocol](product/validation-protocol.md) | User validation protocol |
| [Test Script](product/test-script.md) | Test script |
| [Observer Checklist](product/observer-checklist.md) | Observer checklist |
| [Feedback Form](product/feedback-form.md) | Feedback form |
| [Sample Workspace Validation](product/sample-workspace-validation.md) | Sample workspace validation |

---

## Lab / Internal Features

The following features are lab/internal/experimental. They are **not** part of MindForge's main product path, are not exposed in the main navigation, and carry no API stability guarantees:

| Feature | Status | Notes |
|---------|--------|-------|
| Graph Page (standalone) | internal | `/graph` route preserved but not in main nav; Library GraphExplorer is the main entry |
| Sensemaking Workspace | lab | Experimental analysis via simple heuristics; hidden from main nav |
| Entity Resolution | lab | ConceptCandidate deterministic detection; no auto-upgrade |
| GraphRepository | internal | Repository Pattern wrapper over GraphPort; test-only |
| Extension Plugin | lab | ExtensionManifest/ExportAdapter architecture placeholder |
| Dogfood Scenarios | internal | Developer/maintainer tools; not user-facing |

Current main product path:
```
Source / Import → ai_draft → Review → explicit approval
    → human_approved → Library → Recall (BM25) / Wiki (LLM synthesis) → Export
```
