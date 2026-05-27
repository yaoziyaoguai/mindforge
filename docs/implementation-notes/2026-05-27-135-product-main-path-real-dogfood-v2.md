# Product Main Path Real Dogfood v2 — Implementation Notes

Date: 2026-05-27
Audit reference: `docs/audits/2026-05-27-133-codex-independent-strategic-red-team-audit.md` §10.A
Plan: `docs/plans/2026-05-27-134-product-main-path-real-dogfood-v2.md`
Task type: `dogfood`

## Summary

执行了 Product Main Path Real Dogfood v2 — browser-level UX walkthrough + API pipeline smoke。覆盖所有 8 个核心页面，发现 1 个 P1 管道阻塞问题、2 个 UX 问题、1 个 Docs 问题。

## Browser Walkthrough Evidence

使用 Chrome DevTools MCP 真实导航验证所有页面：

| 页面 | 路由 | 状态 | 关键发现 |
|------|------|------|---------|
| Home | `/` | 正常 | 状态总览、开始指南、快捷操作清晰 |
| Setup | `/setup` | 正常 | 工程细节过重，模型配置为管道必需 |
| Sources | `/sources` | 正常 | 三种导入方式说明清晰 |
| Review | `/drafts` | 正常 | 空状态提示正确 |
| Library | `/library` | 正常 | 空状态干净，无 graph/community 面板 |
| Recall | `/recall` | 正常 | 搜索界面，无 BM25 术语 |
| Wiki | `/wiki` | 正常 | 空状态，生成按钮正确 disabled |
| Export | `/export` | 正常 | 安全说明清晰，breadcrumb "export" 应为中文 |
| Graph | `/graph` | Lab | Lab/Internal 标签清晰，4 node type 诚实声明 |
| Sensemaking | `/sensemaking` | Lab | ⚠️ LAB/INTERNAL 横幅优秀，heuristics 限制透明 |
| Dogfood | `/dogfood` | Internal | (Internal) 标签，默认折叠 |

## Pipeline Blocker (P1 — Product)

**问题**: 处理管道在 demo/fake 模式下仍要求显式模型配置。`mindforge import` 失败：
```
Processing failed. Reason: No model configured for stage 'triage'. Add a model in Web Setup.
```

**影响**: 用户无法完成 Source → Draft → Review → Approval → Library 主路径，即使 Web UI 宣称"正在使用本地模拟 Provider"。

**根因**: Setup 页面 "安全模式：本地模拟" 的声明与实际处理管道之间存在 gap — fake provider 可用但处理步骤（triage/distill/link_suggestion/review_questions/action_extraction）均需显式分配模型。

**推荐修复**: 在无真实模型时自动为处理步骤分配 fake provider，使 "安全模式：本地模拟" 成为真正的零配置 demo 体验。

## Friction Points (Categorized)

### Product
- **P1**: Pipeline blocked by model setup requirement (see above) — blocks acceptance criteria 1-4
- **P2**: Setup page feels like infrastructure configuration, not product onboarding

### UX
- **P2**: Export page breadcrumb shows "export" (lowercase) instead of Chinese "导出知识"
- **P3**: Setup page workflow detail (5-step pipeline with per-step model selection) overwhelms new users

### Docs
- **P2**: Export format inconsistency — docs mention JSON/OPML, Web shows Markdown/ZIP only (pre-existing per Codex audit risk #4)

### Architecture
- **P2**: Model setup is a hard blocker for demo path — consider auto-configuring fake model for all steps when no real provider is configured

## Acceptance Criteria Assessment

| Criteria | Status | Evidence |
|----------|--------|---------|
| User can complete full path without internal docs | **PARTIAL** | Pages navigable, pipeline blocked by model setup |
| Draft review is understandable and safe | **NOT TESTABLE** | No drafts — model setup blocker |
| Export produces expected output | **NOT TESTABLE** | No approved cards to export |
| Recall/Wiki returns useful results | **NOT TESTABLE** | No approved cards |
| Issues categorized into product, UX, architecture, docs | **YES** | See above |

## Positive Findings

1. **Lab/Internal labeling is honest**: Graph 和 Sensemaking 页面明确标注 Lab/Internal + 限制说明
2. **Library page is clean**: 无 graph/community 面板出现在空状态
3. **Safety messaging is consistent**: 所有页面保持 "本地运行 / 需显式确认" 的安全说明
4. **Navigation is well-organized**: 知识处理 / 知识使用 / 工具与诊断 三组清晰
5. **Empty states are helpful**: 每个空状态提供清晰的下一步操作指引

## Governance Fixes

同步修复了 Codex 审计指出的 governance truth drift:

- `CURRENT_PROJECT_STATE.md`: 更新 audit baseline HEAD `fb98003` → `4ef9ed2`，title 更新为 v3.8 Dogfood v2，§6 AUTOPILOT-QUEUE 更新
- `progress-ledger.md`: §2 Active Workstream 切换至 Dogfood v2，§3 更新推荐顺序，修复 5 个 stale `(pending)` commit 字段为真实 commit hash
- §3 Next Recommended Loop 对齐 Codex 审计优先顺序

## Safety

- 未调用真实 LLM/Cubox/Upstage
- 未处理真实私人资料
- 未写真实 Obsidian vault（使用隔离 `/tmp` workspace）
- 未做 RAG/embedding/vector DB
- 未破坏 explicit approval 语义
- 未修改产品代码

## Files Changed

| File | Change |
|------|--------|
| `docs/dev/CURRENT_PROJECT_STATE.md` | 更新 audit baseline, title, §6 AUTOPILOT-QUEUE |
| `docs/dev/progress-ledger.md` | 更新 §2 Active Workstream, §3, 修复 stale commit fields |
| `docs/plans/2026-05-27-134-product-main-path-real-dogfood-v2.md` | 新建 dogfood v2 plan |

## Deferred

- P1 管道阻塞修复（需 auto-configure fake model for demo mode）
- Export format alignment（docs vs API vs Web）
- Setup page UX simplification
- Browser smoke with full data pipeline（需先修复管道阻塞）

## Next Loop

推荐: **修复 P1 管道阻塞** → 使 demo/fake 模式真正零配置可用 → 重新跑完整主路径 dogfood。
备选: Web Product UX Deepening（基于已发现的 UX friction）。
