# MindForge Current Project State

**这是 MindForge 项目所有 agent 的第一入口。** 每次 `/mf-autopilot` 运行必须先读取本文档。

更新日期: 2026-05-28 (v4.0 — 产品创新审计完成，方向重组，AUTOPILOT-QUEUE 重排)

---

## 1. Current Repo Snapshot

| 字段 | 值 |
|------|-----|
| 日期 | 2026-05-27 |
| 当前 HEAD | `e6f6d09` (治理 ITEM-3 完成 + AUTOPILOT-QUEUE 重置，Codex audit 三项全部完成) |
| Codex 审计基线 HEAD | `4ef9ed2` (Codex Independent Strategic Red Team Audit) |
| 分支 | `main` |
| 工作树 | clean |
| vs origin/main | `0 0` (对齐) |
| 最新全局审计 | `docs/audits/2026-05-27-118-post-governance-global-red-team-audit.md` |
| 最新 Web IA/UX 审计 | `docs/audits/2026-05-27-120-web-ia-ux-loop-2-audit.md` |
| 最新 autopilot governance | `docs/implementation-notes/2026-05-27-121-mf-autopilot-auto-continue-policy.md` |
| 最新 architecture reset notes | `docs/implementation-notes/2026-05-27-123-architecture-quality-reset-plan-slice-0.md` |
| 最新 v3.7 Quality Platform notes | `docs/implementation-notes/2026-05-27-127-v3.7-quality-platform.md` |
| 最新 dogfood v2 notes | `docs/implementation-notes/2026-05-27-135-product-main-path-real-dogfood-v2.md` |
| 最新 P1 修复 notes | `docs/implementation-notes/2026-05-27-136-p1-pipeline-blocker-auto-fallback-fake.md` |
| 最新 Web UX Deepening notes | `docs/implementation-notes/2026-05-27-137-web-product-ux-deepening-loop-1.md` |
| 最新产品创新审计 | `docs/product/2026-05-28-001-mindforge-product-innovation-review.md` |

最近关键 commits:
```
8eb3fd4 test: add Slice 0 architecture boundary tests for targeted quality reset
1b39edb chore: finalize HANDOFF.md with accurate repo snapshot
56b3d23 chore: harden mf-autopilot auto-continue policy
3c829da chore: update implementation notes with final commit hash
6145b72 fix: reduce post-dogfood web IA debt
97d57fb feat: improve FakeProvider keyword extraction — title + raw_text
7312245 docs: update commit hash in state/ledger after residual refs cleanup
ac6aa47 docs: clean residual references after docs batch 1
49c138c docs: update commit hash references post batch 1
fcb96c7 docs: remove stale documentation batch 1
64d7a52 chore: harden mf-autopilot loop governance
0248755 docs: add canonical project state, progress ledger, and task-type-aware autopilot
6f5db2c docs: add export page MVP implementation notes
fb87ce0 feat: add safe export page MVP with preview, download, and safety notice
9eb4108 docs: specify export page product direction + backend copy sanitization notes
7bb4a76 fix: sanitize backend generated web copy — health/wiki labels → Chinese
a1556f9 docs: Web IA simplification implementation notes
f0427e7 fix: Web IA simplification — hide internal labels, format timestamps, replace BM25 jargon
54110d4 fix: map internal enum labels to user-friendly display values
```

---

## 2. Product Identity

**MindForge 是 local-first, approval-first personal knowledge compiler.**

主路径:
```
Source / Import
→ ai_draft (AI 生成草稿)
→ Review (人工审阅)
→ explicit approval (显式确认)
→ human_approved (正式知识卡片)
→ Library (浏览) / Recall (BM25 检索) / Wiki (LLM synthesis)
→ Export (Markdown / ZIP 本地下载)
```

**MindForge 不是:**
- 不是 RAG 平台
- 不做 embedding / vector DB
- 不是 GraphRAG
- 不是 Obsidian plugin
- 不是云端 SaaS
- 不自动审批
- 不默认调用真实 LLM

---

## 3. Current Real Capabilities

### production-like / dogfoodable

| 能力 | 状态 | 实现位置 | 说明 |
|------|------|---------|------|
| Source Import/Watch | done | `src/mindforge/sources/` (13 adapters) | Markdown/TXT/HTML/PDF/DOCX |
| AI Draft 五段处理 | done | `src/mindforge/processors/` | Triage→Distill→Link→Questions→Actions |
| Human Review & Explicit Approval | done | `src/mindforge/review_service.py`, `approval_service.py` | `ai_draft` → `human_approved`，不可绕过 |
| Knowledge Library | done | `src/mindforge/library_service.py`, `web/src/pages/LibraryPage.tsx` | 卡片浏览、筛选、排序 |
| BM25 Recall | done | `src/mindforge/recall_service.py`, `lexical_index.py` | 本地词法检索 |
| Wiki (LLM synthesis) | done | `src/mindforge/wiki_service.py` | 从 `human_approved` 生成 Wiki |
| Knowledge Health | done | `src/mindforge/health/health_service.py` | 8 项诊断（review_backlog, low_quality, etc.），只读，不修改 |
| Source Provenance | done | `src/mindforge/provenance/` | 来源追溯 |
| Related Cards | done | `src/mindforge/relations/related_cards.py` | same_source/same_tag/same_wiki_section 确定性关系 |
| Local Graph Preview | done | `web/src/components/GraphExplorer.tsx` | 4 NodeType (card/source/tag/wiki_section)，确定性图 |
| Export (Markdown/ZIP) | done | `routers/library.py` (API) + `web/src/pages/ExportPage.tsx` | 浏览器本地下载，不写 Obsidian vault |
| Provider Setup | done | `web/src/pages/SetupPage.tsx` | Web 配置模型和 API key |
| Dogfood | done | `src/mindforge/dogfood/` | 开发者/维护者工具，`/dogfood` 页面 |
| Trash | done | `src/mindforge/trash_service.py` | 安全回收站，支持 Restore |
| Web UI (14 pages) | done | `web/src/pages/` | React SPA + Tailwind |
| i18n (zh/en) | done | `web/src/lib/i18n.ts` | 双语文案 |
| Frontend Tests | done | `web/src/components/__tests__/` | vitest + happy-dom + @testing-library/react, 6 files/50 tests |
| CLI | done | `src/mindforge/cli.py` + 各 `*_cli.py` | 完整 CLI 入口 |
| Python Coverage | done | `pyproject.toml` [tool.coverage] | pytest --cov 可用, 88% baseline |

### internal

| 能力 | 状态 | 说明 |
|------|------|------|
| Graph Page (`/graph`) | internal | 独立全页图可视化，保留路由但不在主导航 |
| GraphRepository | internal | GraphPort 之上的 Repository Pattern 封装，仅测试使用 |

### lab

| 能力 | 状态 | 说明 |
|------|------|------|
| Sensemaking (`/sensemaking`) | lab | bridge detection/card evolution 等基于简单 heuristics |
| Entity Resolution | lab | ConceptCandidate 确定性检测，不支持自动升级 |
| Extension Plugin | lab | ExtensionManifest/ExportAdapter 架构预留 |
| Community / Topic Detection | lab | 实验性，非主产品路径 |

### deferred

| 能力 | 说明 |
|------|------|
| RAG / embedding / vector DB | 明确不做 |
| Obsidian plugin / vault write | 明确不做 |
| Mail / email storage | 明确不做 |
| Auto approve | 明确不做 |
| Real provider auto-call | 默认不调用，需显式 opt-in |

### deprecated / superseded

| 能力 | 说明 |
|------|------|
| Graph/Sensemaking 8 NodeType 声明 | 已收缩至 4 种正式支持 |
| v3.x 路线图中的 Graph/Sensemaking/Community 全能力 | 已降级为 lab/internal |

---

## 4. Current Non-Goals / Hard Constraints

- 不做 RAG / embedding / vector DB
- 不做 GraphRAG
- 不默认调用真实 LLM/Cubox/Upstage
- 不处理真实私人资料
- 不写真实 Obsidian vault
- 不做 auto approve
- 不做 Graph/Sensemaking 扩张（除非显式重新授权）
- 不新增大型依赖（除非 spec 明确说明）
- 不破坏 `ai_draft` → `human_approved` explicit approval 语义
- 不做 mail/email/mail storage

---

## 5. Current Open Debts

| ID | Priority | Description | Status |
|----|----------|-------------|--------|
| P2-05 | P2 | 零前端测试覆盖 (0 test files in web/src/) | resolved (v3.7): vitest + happy-dom + @testing-library/react 基础设施已搭建 |
| P2-06 | P2 | 无覆盖率配置 — pyproject.toml 无 [tool.coverage] | resolved (v3.7): [tool.coverage.run] + [tool.coverage.report] 已配置, --cov 可用 |
| P3-01 | P3 | npm build chunk size >500KB | open (非阻塞) |
| AUDIT-118-01 | P1 | Export route 已实现，但 user guides / README Web UI 表仍存在 Export 状态漂移 | resolved (v3.7): user guides + README 已更新，Export 页面已写入 Web Console 表格，明确 browser-local download |
| AUDIT-118-02 | P1 | Dogfood 仍在主导航，和 internal 定位冲突 | resolved (v3.7): Dogfood 已在 Lab 折叠区，i18n label 加 (Internal) 标记，user guides 明确标注为内部开发工具 |
| AUDIT-118-03 | P1 | `web_facade.py` 仍是 Web 架构核心债，services 仍有反向 facade helper coupling | resolved (v4.8+Slice 1+2): core→web 层依赖已修复，presenter 模块已提取，web_facade.py 从 2163→922 行 (-57.4%) |
| AUDIT-118-04 | P1 | 缺少 fresh browser/MCP Web 主路径证据；当前 smoke 主要是 API/static | resolved (v3.7): Chrome DevTools MCP smoke 已跑，Home/Setup/Sources/Review/Library/Recall/Wiki/Export 全部加载正常 |
| AUDIT-118-05 | P1 | `docs/dev/HANDOFF.md` 模板与 autopilot 优先读取语义存在误读风险 | resolved (v3.7): HANDOFF.md 新增 status 字段 (active/completed/resolved/historical)，CPS §8 更新读取规则 |
| DOC-01 | P3 | 无英文 docs/README.md 翻译 | resolved (v3.7): docs/README-en.md 已创建 |
| DOC-03 | P3 | docs/design/ 下较多设计文档未与当前实现对齐 | resolved (v3.7): design/README.md + obsidian-binding-design.md 状态标注 |
| DOC-04 | P3 | 无文件级归档机制（docs/archive/ 目录） | deferred |
| PROD-01 | P1 | demo/fake 模式下管道仍要求显式模型配置，用户无法完成首次主路径循环 | open — 已列入 AUTOPILOT-QUEUE-ITEM-1 |

质量债台账完整记录: [`docs/dev/quality-debt-ledger.md`](quality-debt-ledger.md)
文档债台账完整记录: [`docs/dev/documentation-debt-ledger.md`](documentation-debt-ledger.md)

---

## 6. Current Recommended Next Loops

<!-- AUTOPILOT-QUEUE-START -->
<!-- AUTOPILOT-QUEUE-NEXT-ACTION: fix_p1_pipeline_blocker -->
<!-- AUTOPILOT-QUEUE-TASK-TYPE: bug_fix -->
<!-- AUTOPILOT-QUEUE-ITEM-1:
workstream=Product Main Path P1 Pipeline Blocker Fix
task_type=bug_fix
current_node=pending
next_action=auto_configure_fake_provider_when_no_real_model_in_demo_mode
required_skill=none
frameworks_checked=product_strategy_audit_2026-05-28
review_node=browser_mcp_smoke
failure_class=pipeline_blocker
remediation_target=zero_config_demo_experience
auto_continue_allowed=true
hard_stop_required=false
-->
<!-- AUTOPILOT-QUEUE-ITEM-2:
workstream=Guided Onboarding Design
task_type=feature_implementation
current_node=pending
next_action=design_sample_workspace_and_step_by_step_onboarding
required_skill=/brainstorming
frameworks_checked=product_strategy_audit_2026-05-28
review_node=user_validation
failure_class=none
remediation_target=none
auto_continue_allowed=false
hard_stop_required=true
hard_stop_reason=requires_user_validation_before_proceeding
-->
<!-- AUTOPILOT-QUEUE-ITEM-3:
workstream=User Validation — Core Hypothesis Test
task_type=dogfood
current_node=pending
next_action=recruit_5_non_technical_users_and_run_first_cycle_test
required_skill=none
frameworks_checked=product_strategy_audit_2026-05-28
review_node=go_no_go_decision
failure_class=none
remediation_target=none
auto_continue_allowed=false
hard_stop_required=true
hard_stop_reason=requires_go_no_go_product_decision
-->
<!-- AUTOPILOT-QUEUE-END -->

Codex 独立红队审计 (HEAD `4ef9ed2`) 推荐优先顺序:

1. **Product Main Path Real Dogfood v2** — 完整主路径 browser-level dogfood，记录 UX 摩擦
2. **Web Product UX Deepening** — 基于 dogfood 发现的摩擦进行 IA/UX 修复
3. Targeted Architecture Quality Reset — 仅在 dogfood/UX 暴露真实痛点后执行

---

## 7. Autopilot Entry Rules

`/mf-autopilot` 必须根据 task type 选择入口:

| Task Type | Entry Sequence |
|-----------|---------------|
| `feature_implementation` | repo facts → spec/plan → self-review → implementation → gates → notes → progress ledger → commit/push |
| `bug_fix` | repo facts → bug context → reproduce/inspect → fix → targeted gates → notes → progress ledger → commit/push |
| `docs_cleanup` | repo facts → docs inventory → code-truth check → cleanup/rewrite/archive → docs gates → progress ledger → commit/push |
| `ui_ux_polish` | repo facts → browser/MCP audit → P1/P2 fix → product copy/build gates → progress ledger → commit/push |
| `architecture_refactor` | repo facts → architecture audit → target design → small slice → gates → progress ledger → commit/push |
| `audit_only` | repo facts → read evidence → report → docs gates → progress ledger → commit/push (if docs changed) |
| `dogfood` | repo facts → dogfood plan → isolated workspace → run → report → fix P1/P2 → gates → progress ledger → commit/push |

每个 loop 结束必须:
- 更新 `docs/dev/progress-ledger.md` (always)
- 更新 `docs/dev/CURRENT_PROJECT_STATE.md` (if state changed)
- 更新 implementation notes (if code/docs changed significantly)

**Auto-continue:** spec/doc/gate/commit/push 都不是停止点。只有 HARD_STOP_* 条件触发停止。

---

## 8. Handoff Protocol

当 context 不足（< 15%）时，必须在 `docs/dev/HANDOFF.md` 写入 handoff 文档。

**HANDOFF.md 状态标记（必填）：**

每个 HANDOFF.md 必须在文件顶部包含 `status` 标记：

| Status | 含义 | Agent 行为 |
|--------|------|-----------|
| `active` | context 不足导致中断，workstream 未完成 | 必须从 "Next /mf-autopilot Instruction" 继续 |
| `completed` | workstream 正常完成，等待产品决策 | 读取 CPS §6 获取推荐 next loop |
| `resolved` | handoff 内容已被后续 commit 覆盖 | 参考历史，不执行其中指令 |
| `historical` | 模板或存档参考 | 忽略，不作为当前任务来源 |

**HANDOFF.md 读取规则:**
- 新 session 启动时，`/mf-autopilot` §2 必读文件包含 `docs/dev/HANDOFF.md`（如果存在）
- 如果 HANDOFF.md 的 status 为 `active`，其内容优先于 CPS §6 的 next loops 建议
- 如果 HANDOFF.md 的 status 为 `completed` / `resolved` / `historical`，以 CPS §6 为准
- 如果 HANDOFF.md 中的 active workstream 与 progress-ledger.md 不一致，且 status 为 `active`，以 HANDOFF.md 为准（它是最新的 session 出口状态）

**HANDOFF.md 生命周期:**
- context < 15% 且 workstream 未完成时写入（status: `active`）
- workstream 正常完成但需要产品决策时写入（status: `completed`）
- 新 session 成功处理 handoff 后，该 loop 的 commit 应将 status 改为 `resolved` 或删除文件
- 如果 HANDOFF.md 持续 status `active` 超过 2 个 loop 而未被处理，说明进度断裂，需要人工介入
