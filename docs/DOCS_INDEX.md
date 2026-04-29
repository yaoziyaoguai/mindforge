# MindForge Docs Index

This page is the navigation map for the active documentation set. Historical milestone notes live under `docs/archive/` and are not required for normal use.

## Cleanup Summary

The active docs have been consolidated into four layers:

- user path: `README.md`, `GETTING_STARTED.md`, `USER_GUIDE.md`;
- developer path: `ARCHITECTURE.md`, `SOURCE_ADAPTER_PROTOCOL.md`, `OBSIDIAN_BINDING.md`, `LLM_PROVIDER_CONFIG.md`, `SECURITY.md`, `TESTING.md`;
- planning/history path: `ROADMAP.md`, `ROADMAP_PROGRESS.md`, `CHANGELOG.md`;
- historical archive: `docs/archive/`.

Milestone reviews, superseded design notes, and narrow smoke/completion notes were moved to the archive. New users should not start there; archive files are retained only for historical decisions, old quality gates, and implementation context.

## First-Time Users

1. [README](../README.md) - project overview and quick start.
2. [Getting Started](./GETTING_STARTED.md) - install, initialize, scan, process, approve, recall.
3. [User Guide](./USER_GUIDE.md) - command map, artifacts, daily workflows.
4. [Demo Vault README](../examples/demo-vault/README.md) - safe fictional sample vault.

## Daily Users

1. [User Guide](./USER_GUIDE.md)
2. [LLM Provider Config](./LLM_PROVIDER_CONFIG.md), only when switching away from `fake`
3. [Testing](./TESTING.md), for smoke and troubleshooting

## Developers

1. [Architecture](./ARCHITECTURE.md)
2. [Security](./SECURITY.md)
3. [SourceAdapter Protocol](./SOURCE_ADAPTER_PROTOCOL.md)
4. [Obsidian Binding](./OBSIDIAN_BINDING.md)
5. [MindForge Protocol](./MINDFORGE_PROTOCOL.md)
6. [Testing](./TESTING.md)

## Planning And History

- [Roadmap](./ROADMAP.md) - future direction and deliberate non-goals.
- [Roadmap Progress](./ROADMAP_PROGRESS.md) - current completion snapshot.
- [M5 Backlog](./M5_BACKLOG.md) - future spike candidates.
- [Changelog](./CHANGELOG.md) - release history summary.
- [v0.5.1 Local Usability Review](./V0_5_1_LOCAL_USABILITY_REVIEW.md) - local product-loop smoke and acceptance report.
- [v0.5 Obsidian Binding Review](./V0_5_OBSIDIAN_BINDING_REVIEW.md) - latest binding release review.
- `docs/archive/` - detailed historical reviews and superseded design notes.

## Specialist Protocols

These documents remain active because source files, tests, or error messages reference them directly:

- [Human Approval Protocol](./M3_HUMAN_APPROVAL_PROTOCOL.md)
- [Recall / Review Protocol](./M4_RECALL_REVIEW_PROTOCOL.md)
- [PDF / Docx Adapter Protocol](./M5_1_PDF_DOCX_ADAPTER_PROTOCOL.md)
- [WebClip / ChatExport Adapter Protocol](./M5_2_WEBCLIP_CHATEXPORT_PROTOCOL.md)
- [Project Context Protocol](./M5_3_PROJECT_CONTEXT_PROTOCOL.md)
- [Lexical Recall Protocol](./M5_4_LEXICAL_RECALL_PROTOCOL.md)
- [Telemetry Protocol](./M5_7_TELEMETRY_PROTOCOL.md)
