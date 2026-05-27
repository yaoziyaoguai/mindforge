# Documentation Reset Batch 2 — Implementation Notes

Date: 2026-05-27
Baseline HEAD: `fb98003`
Task type: `docs_cleanup`
Source: `docs/dev/CURRENT_PROJECT_STATE.md` §6 AUTOPILOT-QUEUE + `docs/dev/documentation-debt-ledger.md`

---

## Summary

完成 Documentation Reset Batch 2 — 解决文档债台账中 DOC-01、DOC-02、DOC-03 三项。遵循 v4.6 确立的 index-first, no-moves 策略：

- DOC-01: 创建 `docs/README-en.md` 英文版文档入口页面
- DOC-02: 更新 ADR-006 frontmatter status 为 partial（反映 4/8 NodeType 实现现状）
- DOC-03: `docs/design/README.md` 新增 historical/reference 状态说明，`obsidian-binding-design.md` 标记为 deferred

---

## Changes

### DOC-01: English docs/README.md

**Files:**
- `docs/README-en.md` — 新建，完整英文翻译 docs/README.md
- `docs/README.md` — 添加 English version 链接

结构完全镜像中文版：推荐阅读顺序、用户文档、开发者文档、当前能力/限制/路线图/审计/实现笔记、Historical/Superseded 说明、Lab/Internal 功能通知、文档策略。

### DOC-02: ADR-006 Status Update

**Files:**
- `docs/adr/2026-05-25-006-graph-ontology-v1.md` — frontmatter `status: active` → `status: partial — ontology definition valid, but only 4/8 NodeType (card/source/tag/wiki_section) implemented as of v4.2; remaining 4 (community/topic/entity/concept_candidate) are lab/internal`

ADR-001 至 ADR-005 和 ADR-007 的状态描述准确，无需更新。仅 ADR-006 的 `active` 具有误导性（full 8-NodeType ontology 未实现）。

### DOC-03: Design Docs Alignment

**Files:**
- `docs/design/README.md` — 新增 "当前状态说明" 区块：声明 RFC/SDD 为 historical/reference（2026-05-14~17 Draft，不代表当前实现），2026-05-26 设计文档状态以 CPS 为准，obsidian-binding 明确非目标
- `docs/design/obsidian-binding-design.md` — frontmatter `status: draft` → `status: deferred — Obsidian vault write is a hard non-goal`

### State Docs Update

**Files:**
- `docs/dev/documentation-debt-ledger.md` — DOC-01/DOC-02/DOC-03 状态从 open → resolved (v3.7)

---

## Gates

| Gate | Command | Exit Code | Timeout |
|------|---------|-----------|---------|
| git diff | `git diff --check` | 0 | no |
| ruff | `ruff check src/ tests/` | — | — |
| npm build | `npm --prefix web run build` | — | — |

docs-only changes — 仅运行 git diff --check 是必要的。

---

## Safety

- 未修改产品代码
- 未修改 API contract
- 未修改 approval 语义
- 未引入新依赖
- 未删除任何文件
- 所有改动均为非破坏性的状态标记和文档翻译
- 遵循 index-first, no-moves 策略
