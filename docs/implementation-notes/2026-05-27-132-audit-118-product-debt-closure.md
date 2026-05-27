# AUDIT-118 P1 Product Debt Closure — Implementation Notes

Date: 2026-05-27
Baseline HEAD: `8507c82`
Task type: `ui_ux_polish + docs_cleanup + smoke_evidence`
Workstream: AUDIT-118 P1 Product Debt Closure

---

## Summary

关闭审计文档 `docs/audits/2026-05-27-118-post-governance-global-red-team-audit.md` 中全部 4 项剩余 AUDIT-118 P1 产品债。

## Changes

### AUDIT-118-01: Export docs drift — resolved

**问题：** Export page (`web/src/pages/ExportPage.tsx`, route `/export`) 已实现，但 user guides 仍写 "没有独立的 Import/Export 页面"，README 表缺少 Export 行。

**修复：**
- `docs/en/user-guide.md`: Web Console 表新增 Export 行 ("Browser-local Markdown/ZIP download — safe, no Obsidian vault write")，删除 "no standalone Import/Export page" 表述，Dogfood 行标注 "Internal development tool"
- `docs/zh-CN/user-guide.md`: 同上，中文版同步更新
- `README.md`: Web UI 表新增 Export 行，Dogfood 行标注 "内部开发工具（Lab 分组下，非用户主路径）"
- `docs/en/user-guide.md` Dogfood 章节重写为 "Internal Development Tool"，明确标注 "not a user-facing product feature"

### AUDIT-118-02: Dogfood nav — resolved

**问题：** 审计时 Dogfood 在主导航。当前代码已将其移入 Lab 折叠区（commit `2b91a28`），但 i18n label 仍显示为 "使用报告" / "Usage Report"，听起来像用户功能。

**修复：**
- `web/src/lib/i18n.ts`: `nav.dogfood` label 从 "使用报告" → "使用报告 (Internal)" / "Usage Report" → "Usage Report (Internal)"
- Sidebar 结构无需改动 — Dogfood 已在 Lab 折叠区（`useState(false)` 默认折叠）
- `docs/zh-CN/user-guide.md` Dogfood 章节重写为 "内部开发工具"，明确 "不是面向用户的產品功能"
- Browser smoke 确认：Lab 区域默认折叠，Dogfood 对用户不可见

### AUDIT-118-04: Browser/MCP smoke — resolved

**执行：** 使用 Chrome DevTools MCP 真实跑通主路径页面 smoke。

**验证页面（全部加载正常）：**
| 页面 | 路由 | 状态 |
|------|------|------|
| Home | / | 状态总览、安全摘要、知识生命周期视图正常 |
| Library | /library | 卡片列表、筛选排序、Graph Explorer、Related Cards、Provenance、审批时间线正常 |
| Recall | /recall | 搜索界面正常 |
| Wiki | /wiki | Wiki 内容、TOC、Provenance、Local Graph Preview 正常 |
| Export | /export | 范围/格式选择、预览、安全说明（浏览器本地下载，不写 Obsidian vault）正常 |

**证据类型：** Fresh browser evidence（Chrome DevTools MCP），非 static inspection/product copy fallback。

### AUDIT-118-05: HANDOFF.md semantics — resolved

**问题：** HANDOFF.md 无 status 标记，agent 可能将历史/已完成 handoff 误读为 active task。

**修复：**
- `docs/dev/HANDOFF.md`: 新增 status 字段体系（active / completed / resolved / historical），当前 status: `resolved`
- `docs/dev/CURRENT_PROJECT_STATE.md` §8: 更新 Handoff Protocol，明确各 status 的 agent 行为规则
  - `active`: context 不足中断，必须从 Next Instruction 继续
  - `completed`: workstream 完成，读 CPS §6
  - `resolved`: 已被后续 commit 覆盖，参考历史
  - `historical`: 模板/存档，忽略

## Files Changed

| File | Change |
|------|--------|
| `docs/en/user-guide.md` | Web Console 表新增 Export，删除 "no standalone page" 表述，Dogfood 章节重写为 Internal |
| `docs/zh-CN/user-guide.md` | 同上，中文版同步 |
| `README.md` | Web UI 表新增 Export，Dogfood 行更新 |
| `web/src/lib/i18n.ts` | `nav.dogfood` label 加 (Internal) 后缀 |
| `docs/dev/HANDOFF.md` | 新增 status 字段体系 |
| `docs/dev/CURRENT_PROJECT_STATE.md` | §5 标记 4 项 AUDIT-118 resolved，§6 更新 AUTOPILOT-QUEUE，§8 更新 Handoff Protocol |

## Safety

- 未修改 API contract
- 未修改 approval 语义
- 未引入 RAG/embedding/vector DB
- 未调用真实 LLM
- 未处理真实私人资料
- 未写 Obsidian vault
- 仅文档 + i18n label 改动

## Gates

| Gate | Command | Exit Code |
|------|---------|-----------|
| git diff | `git diff --check` | 0 |
| npm build | `npm --prefix web run build` | 0 |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 (84 passed) |

## Deferred

- P3-01: npm build chunk size >500KB（非阻塞）
- 更多 frontend test coverage expansion（vitest + happy-dom 基础设施已就绪）
- Documentation Reset Batch 2（规则已明确，待执行）
