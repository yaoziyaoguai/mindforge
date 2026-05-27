# Docs Cleanup Residual References — Implementation Notes

**Date:** 2026-05-27
**Workstream:** Documentation Reset
**Task type:** docs_cleanup
**Prerequisite:** `docs/implementation-notes/2026-05-27-116-docs-cleanup-batch-1.md`

## 1. Scope

Batch 1 删除了 8 个 stale docs 文件后，全仓仍有 ~40+ 个跨文档引用。本轮的目
标是修复这些残留引用，确保不会产生死链接或误导性指向。

## 2. Files Changed

### 2.1 Management docs（更新为已删除状态）

| File | Change |
|------|--------|
| `docs/plans/2026-05-26-097-documentation-archive-plan.md` | 6 条引用标记为 strikethrough + "已删除" |
| `docs/design/README.md` | 更新目录树 + V0_2_ROADMAP 链接改为删除说明 |
| `docs/plans/2026-05-22-002-feat-web-ux-improvement-plan.md` | 1 条 dogfood plan 引用标记为 removed |
| `docs/dev/documentation-reset-plan.md` | Batch 1 已在 Phase C 更新 |
| `docs/dev/documentation-inventory.md` | 已在 Phase C 更新 |
| `docs/dev/docs-reset-index.md` | 已在 Phase C 更新 |

### 2.2 Historical RFC/SDD（header 引用更新）

| File | Deleted File Referenced |
|------|------------------------|
| `docs/design/rfc/RFC_0001_SOURCE_ADAPTER_V2.md` | V0_2_ROADMAP → ~~strikethrough~~ + removed note |
| `docs/design/rfc/RFC_0002_WIKI_PRESENTATION_V2.md` | V0_2_ROADMAP → ~~strikethrough~~ + removed note |
| `docs/design/rfc/RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md` | V0_3_ROADMAP + SDD_KNOWLEDGE → ~~strikethrough~~ + removed note |
| `docs/design/rfc/RFC_0003_LEGACY_DOC_EVALUATION.md` | V0_2_ROADMAP → ~~strikethrough~~ + removed note |
| `docs/design/sdd/SDD_SOURCE_ADAPTER_V2.md` | V0_2_ROADMAP → ~~strikethrough~~ + removed note |
| `docs/design/sdd/SDD_WIKI_PRESENTATION_V2.md` | V0_2_ROADMAP → ~~strikethrough~~ + removed note |
| `docs/design/sdd/SDD_WIKI_WEB_PRESENTATION_ADDENDUM.md` | V0_2_ROADMAP + V0_2_DEVELOPMENT_RULES + 2 处 References → ~~strikethrough~~ + removed note |

### 2.3 Historical specs/implementation notes

| File | Deleted File Referenced |
|------|------------------------|
| `docs/specs/2026-05-24-007-m1-card-quality-integration-spec.md` | V0_3_ROADMAP → removed note in frontmatter `roadmap:` field |
| `docs/specs/2026-05-24-008-m2-wiki-quality-integration-spec.md` | 同上 |
| `docs/implementation-notes/2026-05-24-010-m3-related-cards.md` | V0_3_ROADMAP → removed note |
| `docs/implementation-notes/2026-05-24-011-m5-knowledge-health.md` | V0_3_ROADMAP → removed note |
| `docs/implementation-notes/2026-05-24-012-m6-local-graph-preview.md` | V0_3_ROADMAP → removed note |

## 3. Residual Reference Audit Result

对每个已删除文件名的全仓 rg 结果：

| Deleted File | Residuals After Fix | Status |
|-------------|---------------------|--------|
| V0_2_ROADMAP | reset-plan, archive-plan, batch-1 notes, 7 historical docs (annotated) | OK — mgmt docs are intentional |
| V0_3_ROADMAP | reset-plan, archive-plan, batch-1 notes, 3 impl notes, 2 specs (annotated) | OK |
| TDD_KNOWLEDGE_QUALITY | reset-plan, batch-1 notes, archive-plan (all mgmt) | OK |
| SDD_KNOWLEDGE_QUALITY | RFC_0003 (annotated), batch-1 notes, reset-plan, inventory (mgmt) | OK |
| V0_2_DEVELOPMENT_RULES | reset-plan, batch-1 notes, SDD_WIKI_WEB (annotated) | OK |
| V0_3_DEVELOPMENT_RULES | reset-plan, inventory (mgmt + annotated), batch-1 notes | OK |
| dogfood-readiness-plan | reset-plan, archive-plan (mgmt + annotated), batch-1 notes | OK |
| real-llm-dogfood-plan | reset-plan, archive-plan (mgmt + annotated), web-ux-plan (annotated), batch-1 notes | OK |

**结论**: 所有残留引用要么已在 management docs 中正确标记为已删除（intentional），要么已在 historical docs 中标注 `(removed 2026-05-27)`。没有死链接残留。

## 4. Gates

| Gate | Command | Exit Code | Timeout |
|------|---------|-----------|---------|
| git diff --check | `git diff --check` | 0 | no |
| ruff check | `ruff check docs/ .claude/commands/` | 0 | no |
| product copy tests | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 | no |

## 5. Safety Confirmation

- 未修改 `src/` 或 `web/src/`
- 未新增/删除功能
- 未读取 `.env` 或 secrets
- 未调用真实 LLM
- 未处理私人资料
- 未写 Obsidian vault
- 所有改动仅限 docs/ 下的 markdown 文件

## 6. Batch 2 Readiness

Batch 2 (Archive Candidates) 在 `documentation-reset-plan.md` 中定义为 "保留但标记历史" 的候选文件。本轮 residual references cleanup 实际上已完成了部分 Batch 2 的前置工作（标注历史文档中的删除引用）。

Batch 2 仍需解决的核心问题：
- 是否有明确的 delete vs archive 规则
- 哪些文件标记为 superseded/historical vs 直接删除

**建议**: Batch 2 在下一轮 `/mf-autopilot` 中由 Autopilot 根据 
`CURRENT_PROJECT_STATE.md` §6 判断是否已明确。
