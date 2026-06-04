# MindForge Archive Plan

Date: 2026-06-05
Status: Soft Archived — paused learning project

## 1. Archive Type

This is a **soft archive** (also called "paused" or "learning project preserved"). Specifically:

- **NOT** a GitHub hard archive (the repository is not archived on GitHub)
- **NOT** code deletion (all code remains in the repository)
- **NOT** directory restructuring (no files or directories are moved)
- **NOT** a git tag (no `archive/vX-final` or `paused/YYYY-MM-DD` tag is created in this commit)
- **NOT** a push to remote (changes are committed locally only)
- The code **can still run locally** — nothing is broken
- The project **can be restarted** from any direction in the future

**What soft archive means**: We stop actively investing in new features and product development. The repository is preserved as a learning artifact, postmortem reference, and potential starting point for future experiments.

## 2. Current State

| Item | Status |
|------|--------|
| Branch | `main` |
| HEAD | `e02c9fc` |
| Ahead of origin/main | 0 |
| Behind origin/main | 11 (will be updated after commit) |
| Dirty tracked changes | None |
| Untracked files | `pictures/`, `setup.png`, `tmp/`, `uv.lock`, `docs/specs/*_v2.md`, `docs/superpowers/brainstorms/*`, `docs/superpowers/reviews/*` |
| Strategic docs exist | Yes — `docs/specs/mindforge_strategic_repositioning.md`, brainstorm, review |
| Postmortem docs exist | Yes — `docs/postmortem/mindforge-postmortem.md`, `mindforge-lessons-for-vibe-coding.md`, `mindforge-archive-plan.md` |
| Validation protocol exists | Yes — `docs/product/validation-protocol.md` (never executed) |

### Directions No Longer Actively Pursued

- Independent Web knowledge-base product
- Knowledge Library UI polish
- Wiki / Topic Browser development
- Relationship Panel / Graph-like UI
- Knowledge Card v2 implementation
- Distill Prompt v2 implementation
- Obsidian export implementation
- Agent Memory Infrastructure implementation
- New feature development of any kind

## 3. Stop Investment List

The following areas will no longer receive investment. Code is **not deleted** — it remains in the repository for reference.

| Area | Reason |
|------|--------|
| **Independent Web knowledge-base product** | No validated user scenario; covered by existing tools |
| **Knowledge Library UI polish** | UI problems are surface-level; root cause is product direction |
| **Wiki / Topic Browser** | Feature without validated user need |
| **Relationship Panel / Graph-like UI** | Lab features with no value loop; same-tag is not knowledge graph |
| **Knowledge Card v2 implementation** | Schema change depends on product form, which is no longer pursued |
| **Distill Prompt v2 implementation** | Prompt optimization solves extraction quality, not product direction |
| **Obsidian export implementation** | Depends on Obsidian-first direction, which is not validated |
| **Agent Memory Infrastructure implementation** | Depends on agent memory direction, which is not validated |
| **New feature development** | All new features require validated product direction first |

## 4. Preserved Assets List

The following assets are preserved and may be reused in future projects:

| Asset | Location | Reusability |
|-------|----------|-------------|
| **Source pipeline** | `src/mindforge/ingestion_*.py`, `src/mindforge/import_cli.py` | High — file ingestion is reusable |
| **FakeProvider** | `src/mindforge/llm/fake.py` | High — demo/testing pattern |
| **approval-first design** | `src/mindforge/approval_*.py` | High — applies to any AI output workflow |
| **ai_draft / human_approved boundary** | `src/mindforge/cards.py`, `src/mindforge/approver.py` | High — engineering contract |
| **local-first constraint** | `src/mindforge/config.py`, `src/mindforge/secret_store.py` | High — privacy-first design |
| **tests** | `tests/` | Medium — reference for testing patterns |
| **docs** | `docs/` | High — documentation methodology |
| **specs** | `docs/specs/` | High — SPEC writing patterns |
| **postmortem** | `docs/postmortem/` | High — learning for future projects |
| **validation protocol** | `docs/product/validation-protocol.md` | High — kill criteria methodology |
| **engineering workflow** | CLAUDE.md, `.claude/` | High — SDD/TDD/review/audit workflow |
| **transferable experience** | This document + postmortem | High — avoid repeating mistakes |

## 5. README Status Update

The following README files have been updated with a project status banner at the top:

- `README.md` — Chinese
- `README.zh-CN.md` — Chinese
- `README.en.md` — English

### Chinese Banner

```
> **项目状态：Paused / Soft Archived**
> MindForge 当前作为一次 vibe coding 学习项目与复盘样本保留。独立 Web 知识库产品方向不再继续积极推进；代码仍保留用于学习、复盘和未来可能的实验。详细复盘见 [docs/postmortem/](docs/postmortem/)。
```

### English Banner

```
> **Project Status: Paused / Soft Archived**
> MindForge is currently preserved as a vibe-coding learning project and postmortem artifact. The standalone Web knowledge-base product direction is no longer actively pursued. The code remains available for reference, learning, and possible future experiments. See [docs/postmortem/](docs/postmortem/) for details.
```

These banners are placed after the title and before the original content. Original README content is preserved unchanged.

## 6. Tag Decision

**No tag is created in this commit.**

Rationale:
- Soft archive does not require a tag
- Tags imply a release milestone, which this is not
- If a tag is needed in the future, it can be added on demand:
  - `git tag archive/v0.7-final` — for a final release marker
  - `git tag paused/2026-06-05` — for a pause timestamp

## 7. GitHub Archive Decision

**GitHub hard archive is NOT recommended at this time.**

Rationale:
- The code may still be useful as a learning asset
- Future experiments may restart from this codebase
- GitHub archive makes the repository read-only and signals "abandoned"
- Soft archive (status banner + postmortem) is sufficient for current needs

**If permanent stop is decided in the future**, GitHub archive can be considered:
- GitHub Settings → Archive this repository
- This makes the repo read-only and adds an "Archived" badge

## 8. If Restarted in the Future

Before writing any code to restart MindForge, the following conditions must be met:

1. **Clear target user**: Who exactly will use this? Not "personal knowledge managers" — be specific.

2. **Clear real scenario**: What exact problem are they solving? Not "organizing knowledge" — be specific.

3. **3-5 real dogfood sessions**: Real usage by real users (or yourself for real tasks), not hypothetical scenarios.

4. **Knowledge extraction value validated**: Evidence that AI-distilled knowledge has more reuse value than good summaries.

5. **CLI / Markdown proven insufficient**: Evidence that a simpler form (script, CLI, Obsidian plugin) cannot solve the problem, justifying Web investment.

6. **Restart SPEC written**: A new SPEC document that defines the restart direction, scope, and acceptance criteria — **before** any implementation.

The restart should follow the vibe coding startup checklist (see `docs/postmortem/mindforge-lessons-for-vibe-coding.md`): one-sentence scenario → manual validation → CLI/script validation → real dogfood → then decide Web/backend/architecture.
