# MindForge Current Project State

**这是 MindForge 项目所有 agent 的第一入口。** 每次 `/mf-autopilot` 运行必须先读取本文档。

更新日期: 2026-05-28 (Post-Mint4 Remediation 完成 → mf-autopilot Skill Redesign Review)

---

## 1. Current Repo Snapshot

| 字段 | 值 |
|------|-----|
| 日期 | 2026-05-28 |
| 当前 HEAD | `98cab46` (docs: add real provider dogfood v2 main path verification report) |
| Codex 审计基线 HEAD | `4ef9ed2` (Codex Independent Strategic Red Team Audit) |
| 分支 | `main` |
| 工作树 | clean |
| vs origin/main | `0 0` (对齐) |
| 最新全局审计 | `docs/audits/2026-05-27-118-post-governance-global-red-team-audit.md` |
| 最新 Web IA/UX 审计 | `docs/audits/2026-05-27-120-web-ia-ux-loop-2-audit.md` |
| 最新 autopilot governance | `docs/implementation-notes/2026-05-28-143-mf-autopilot-skill-redesign-review.md` |
| 最新 mf-autopilot skill review | `docs/dev/mf-autopilot-skill-redesign-review.md` |
| 最新 Guided Onboarding | `docs/implementation-notes/2026-05-27-142-guided-onboarding-mvp.md` |
| 最新 Dogfood P0/P1 Remediation | `docs/implementation-notes/2026-05-28-140-dogfood-p0-p1-remediation.md` |
最新 Real Provider Dogfood v2 | `docs/implementation-notes/2026-05-28-144-real-provider-dogfood-v2-main-path.md` |
最新 P0/P1 修复 notes | `docs/implementation-notes/2026-05-28-140-fresh-clone-p0-p1-blocker-fixes.md` |
| 最新 bundled config 修复 | `docs/implementation-notes/2026-05-28-141-bundled-config-empty-models-demo-path.md` |
| 最新 governance truth sync | `docs/implementation-notes/2026-05-28-140-p1-fix-verified-queue-advanced-to-guided-onboarding.md` |
| 最新 Post-Mint4 回顾 | `docs/retrospectives/2026-05-28-post-mint4-retrospective.md` |
| 最新 Remediation Plan | `docs/plans/2026-05-28-post-mint4-remediation-plan.md` |
| 最新 User Validation Protocol | `docs/product/validation-protocol.md` (v1.1 — scope clarified) |
最新 Validation Scope Clarification | `docs/implementation-notes/2026-05-28-144-real-provider-dogfood-v2-main-path.md` §0 |
| 最新产品创新审计 | `docs/product/2026-05-28-001-mindforge-product-innovation-review.md` |

最近关键 commits:
```
81f7751 docs: sync governance truth after dogfood P0/P1 remediation
8c62c33 fix: P0 DOGFOOD-001 — replace self.secrets with self.config_service.secrets in provider_readiness_detail
8d1accc docs: correct gate evidence + add v3 fresh clone verification
2119b01 docs: update progress ledger for bundled config empty models fix
39e9890 fix: remove placeholder model from bundled config — default to empty models for zero-config demo path
aa9bc2f docs: finalize P0/P1 fresh clone blocker fixes — update commit hashes and add re-dogfood evidence
bbaed30 fix: P0/P1 fresh clone blocker fixes — narrow fake fallback to demo-only + sample-workspace cards_path fix
2f7e787 docs: update CPS HEAD to 660e781 after mf-autopilot skill review commit
660e781 chore: mf-autopilot skill redesign review — merge stop conditions, add claim-to-evidence gate, simplify skill routing output
eccd8db docs: finalize Post-Mint4 Remediation — update HEAD and ledger hashes
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
| Frontend Tests | done | `web/src/components/__tests__/` | vitest + happy-dom + @testing-library/react, 11 files/79 tests |
| Backend Tests | done | `tests/` | pytest, 含 `test_card_workspace_service.py` (8 tests: bulk_update + link_cards) |
| Saved Views | done | `src/mindforge/view_store.py`, `web/src/components/ViewSwitcher.tsx` | 视图保存/加载/删除，local JSON store |
| Collections | done | `src/mindforge/collection_store.py`, `web/src/components/CollectionPanel.tsx` | 卡片集合 CRUD，API + frontend |
| Bulk Maintenance | done | `src/mindforge/card_workspace_service.py`, `web/src/components/BulkActions.tsx` | YAML frontmatter 批量修改 tags/track |
| Manual Card Linking | done | `src/mindforge/card_workspace_service.py`, `web/src/components/CardWorkspace.tsx` | 双向 frontmatter manual_links 写入 |
| Recall Benchmark | done | `tests/fixtures/recall_benchmark.py` | 12 cards + 14 golden queries + 4 negative queries |
| Query Explain | done | `src/mindforge/recall_service.py` (QueryExplain + explain_zero_hits + explain_hits) | BM25 命中/未命中原因分析 |
| BM25 Tuning | done | `src/mindforge/retrieval/bm25_engine.py` (Bm25Config) | 可配置字段权重/k1/b |
| Recall Quality Gate | done | `scripts/recall_quality_gate.py` | exit 0 当 recall ≥ 80%，当前 100% |
| Web Recall Explain | done | `web/src/pages/RecallPage.tsx` | explain 折叠面板 + i18n |
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
| PROD-01 | P1 | demo/fake 模式下管道仍要求显式模型配置，用户无法完成首次主路径循环 | resolved (`87453f0`): CLI `apply_provider_selection()` + Web `_ensure_processing_model_configured()` 两处 auto-fallback 注入，11 个测试验证 |
| PACK-01 | P2 | 非技术用户无法自安装 — 当前需 GitHub clone + npm/pip 多步操作 | deferred: 作为单独 packaging workstream，不混入本轮产品价值验证。validation-protocol v1.1 明确 facilitator 预先启动 Web |

质量债台账完整记录: [`docs/dev/quality-debt-ledger.md`](quality-debt-ledger.md)
文档债台账完整记录: [`docs/dev/documentation-debt-ledger.md`](documentation-debt-ledger.md)

---

## 6. Current Recommended Next Loops

<!-- AUTOPILOT-QUEUE-START -->
<!-- AUTOPILOT-QUEUE-NEXT-ACTION: continue_post_mint4_remediation_p2_web_ux -->
<!-- AUTOPILOT-QUEUE-TASK-TYPE: remediation -->
<!-- AUTOPILOT-QUEUE-ITEM-1:
workstream=Post-Mint4 Remediation: P1 User Validation Kit
task_type=docs_cleanup
current_node=done
next_action=N/A
required_skill=none
frameworks_checked=none (low-risk docs creation)
review_node=docs_truth_review
failure_class=none
remediation_target=none
auto_continue_allowed=true
hard_stop_required=false
status=resolved (5 validation docs created: protocol + test-script + observer-checklist + feedback-form + sample-workspace-validation, 2026-05-28)
hard_stop_note=HARD_STOP_PRODUCT_DECISION: User Validation Kit 就绪，需要 5 名真实非技术用户执行验证
-->
<!-- AUTOPILOT-QUEUE-ITEM-2:
workstream=Post-Mint4 Remediation: P2 Web UX Remediation
task_type=ui_ux_polish
current_node=done
next_action=N/A
required_skill=none
frameworks_checked=none (direct mf-autopilot, low-risk targeted fixes)
review_node=browser_mcp_smoke
failure_class=none
remediation_target=none
auto_continue_allowed=true
hard_stop_required=false
status=resolved (3 fixes: review page routing + OnboardingHint localStorage + sidebar feedback link, commit 0c96f5d)
-->
<!-- AUTOPILOT-QUEUE-ITEM-3:
workstream=Post-Mint4 Remediation: P3 Design System Foundation
task_type=docs_cleanup
current_node=done
next_action=N/A
required_skill=none
frameworks_checked=none (direct mf-autopilot, lightweight token extraction + doc)
review_node=docs_truth_review
failure_class=none
remediation_target=none
auto_continue_allowed=true
hard_stop_required=false
status=resolved (U1: web/src/design/tokens.ts + U2: docs/dev/design-system.md enhanced)
-->
<!-- AUTOPILOT-QUEUE-ITEM-4:
workstream=Post-Mint4 Remediation: P4 Autopilot Simplification Analysis
task_type=docs_cleanup
status=resolved (U1: autopilot-simplification-analysis.md — 1015 lines analyzed, ~19-33% reduction opportunities identified)
required_skill=none
frameworks_checked=none
review_node=docs_truth_review
failure_class=none
remediation_target=none
auto_continue_allowed=true
hard_stop_required=false
-->
<!-- AUTOPILOT-QUEUE-ITEM-5:
workstream=Post-Mint4 Remediation: P5 Docs Governance Cost Reduction
task_type=docs_cleanup
status=resolved (Batch 1: 3 Community/Topic notes marked superseded by-contraction)
required_skill=none
frameworks_checked=none
review_node=docs_truth_review
failure_class=none
remediation_target=none
auto_continue_allowed=true
hard_stop_required=false
-->
<!-- AUTOPILOT-QUEUE-ITEM-6:
workstream=Fresh Clone Dogfood — P0/P1 Blocker Fixes
task_type=bug_fix
current_node=done
next_action=N/A
required_skill=none
frameworks_checked=none (direct mf-autopilot, targeted fixes with tests)
review_node=gate_review
failure_class=none
remediation_target=none
auto_continue_allowed=true
hard_stop_required=false
status=resolved (P0: fake fallback demo-only; P1: cards_path Path fix; gate evidence corrected; v3 fresh clone verified — exit 0 all gates)
-->
<!-- AUTOPILOT-QUEUE-ITEM-7:
workstream=Governance Truth Sync
task_type=docs_cleanup
current_node=done
next_action=N/A
required_skill=none
frameworks_checked=none (direct mf-autopilot, low-risk docs update)
review_node=docs_truth_review
failure_class=none
remediation_target=none
auto_continue_allowed=true
hard_stop_required=false
status=resolved (CPS HEAD updated, stale queue items resolved, HANDOFF.md synced, progress-ledger updated)
-->
<!-- AUTOPILOT-QUEUE-ITEM-8:
workstream=Dogfood P0/P1 Remediation — self.secrets fix + OpenAPI endpoint verification
task_type=bug_fix
current_node=done
next_action=N/A
required_skill=ce-debug (P0 investigation)
frameworks_checked=none (targeted one-line fix with regression test)
review_node=gate_review
failure_class=none (P0 fixed, P1 confirmed false positive, P2 documented as product note)
remediation_target=none
auto_continue_allowed=true
hard_stop_required=false
status=resolved (P0: self.secrets → self.config_service.secrets; P1: false positive — all 5 endpoints have registered routes; P2: triage threshold intentional — documented as product note; regression test added; fresh clone v2 verified; all gates pass; commit 8c62c33)
-->
<!-- AUTOPILOT-QUEUE-ITEM-9:
workstream=Real Provider Dogfood v2 — Main Path Verification
task_type=dogfood
current_node=done
next_action=N/A
required_skill=none (direct API-driven dogfood pipeline)
frameworks_checked=none (API-driven verification, no heavy skill needed)
review_node=dogfood_evidence_review
failure_class=none
remediation_target=none
auto_continue_allowed=true
hard_stop_required=true
hard_stop_note=HARD_STOP_PRODUCT_DECISION — all workstreams complete, real provider dogfood v2 main path verified with qwen3.6-plus. Pipeline: Import → AI Draft (real LLM) → Explicit Approve → Library → Recall → Wiki → Export all PASS. No blockers. Next: User Validation with 5 real non-technical users.
status=resolved (all main path stages pass with real provider; no P0/P1 issues found; safety invariants all pass; commit 81f7751 docs only — dogfood v2 is server-side verification, no code changes needed)
-->
<!-- AUTOPILOT-QUEUE-END -->

产品创新审计 (HEAD `aef49df`) 推荐优先顺序 (已完成):
- Direction A/C/F 已全部完成
- User Validation 已列为 P0

Post-Mint4 Remediation (全部完成 ✅):
1. **P1: User Validation Kit** — 5 个验证文档已就绪 ✅ → HARD_STOP_PRODUCT_DECISION (需要真实用户)
2. **P2: Web UX Remediation** — 3 fixes 完成 ✅ (commit `0c96f5d`)
3. **P3: Design System Foundation** — tokens.ts + design-system.md ✅
4. **P4: Autopilot Simplification** — 分析文档完成 ✅
5. **P5: Docs Governance Cost Reduction** — Batch 1 完成 ✅ (3 notes marked superseded)

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
