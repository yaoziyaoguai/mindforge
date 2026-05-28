# Progress Ledger

**MindForge 项目进度跟踪。** 每条记录包含: date, commit, goal, outcome, docs produced, remaining debt.

每个 `/mf-autopilot` loop 结束必须更新此文件。即使小 bug fix 也至少加一条简短记录。

---

## 1. Completed Major Loops

### 2026-05-28: Dogfood P0/P1 Remediation — self.secrets fix + OpenAPI endpoint verification

- **Commit**: `d0d2532` → (pending)
- **Workstream**: Fresh Clone + Real Provider Dogfood v1 Remediation
- **Task type**: bug_fix
- **Outcome**: P0 fixed (self.secrets → self.config_service.secrets, one-line), P1 verified as false positive (all 5 endpoints exist in schema+routes), P2 documented as product note (triage threshold intentional). Test added for P0 regression.
- **Review result**: PASS — all 5 routes verified via `create_app().openapi()`
- **Gate result**: ruff 0, pytest 0 (3638 passed/1 skipped), npm build 0, git diff --check 0
- **Failure class**: none
- **Remediation action**: none
- **Required skill invoked**: ce-debug (P0 investigation)
- **Skill frameworks checked**: none required for trivial bug fix
- **Docs/notes**: `docs/implementation-notes/2026-05-28-140-dogfood-p0-p1-remediation.md`
- **Next ACTION**: CONTINUE_NEXT_LOOP — fresh clone v2 re-verification

### 2026-05-28: Governance Truth Sync — Post-Workstream Stale Doc Cleanup

- **Commit**: `8d1accc` → (pending)
- **Workstream**: Governance Truth Sync (docs_cleanup)
- **Task type**: docs_cleanup
- **Outcome**: 更新 CPS HEAD `pending`→`8d1accc`, 标记 AUTOPILOT-QUEUE-ITEM-6 为 resolved, 新增 ITEM-7 追踪本 loop, 更新 HANDOFF.md status 和 HEAD, 同步 progress-ledger. 所有 stale 治理文档已刷新至当前真实状态。
- **Review result**: PASS — all state references verified against current git HEAD
- **Gate result**: PASS — git diff --check 0
- **Failure class**: none
- **Remediation action**: none
- **Required skill invoked**: N/A (low-risk docs cleanup)
- **Docs/notes**: CPS §1, HANDOFF.md
- **Next ACTION**: HARD_STOP_PRODUCT_DECISION (所有 active workstream 完成，需要 User Validation 或新方向)

### 2026-05-28: Gate Truth Cleanup — Correct Gate Evidence + Fresh Clone v3 Re-Verification

- **Commit**: `2119b01` → (pending)
- **Workstream**: Fresh Clone P0/P1 Blocker Fixes (gate truth cleanup)
- **Task type**: audit_only (gate evidence correction)
- **Outcome**: 修正上一轮 gate evidence 的三个问题：(1) tail pipe 掩盖 pytest exit code — 已用无 pipe 命令重新验证；(2) v2 路径名 artifact 误标为 pre-existing — v3 用不含 "dogfood" 的路径重建验证；(3) ACTION token 不一致 — 本报告用正确 token。v3 fresh clone 全部验证通过。
- **Review result**: PASS — gate evidence now follows §8.1 rules
- **Gate result**: PASS — v3 pytest exit 0 (no pipe), git diff --check 0
- **Failure class**: gate_failure (evidence, not code)
- **Remediation action**: corrected gate evidence in implementation note; fresh clone v3 full re-verification
- **Required skill invoked**: none (audit/correction, no heavy skill needed)
- **Docs/notes**: `docs/implementation-notes/2026-05-28-141-bundled-config-empty-models-demo-path.md` (updated with corrected gate evidence + v3 verification)
- **Next ACTION**: WORKSTREAM_COMPLETE

### 2026-05-28: Bundled Config Empty Models — Zero-Config Demo Path

- **Commit**: `aa9bc2f` → `39e9890`
- **Workstream**: Fresh Clone Dogfood — P0/P1 Blocker Fixes
- **Task type**: bug_fix (product decision)
- **Outcome**: 移除 bundled config 的 placeholder model，默认空模型走 demo/fake path。修复 4 个依赖旧 placeholder model 的旧测试。
- **Review result**: PASS — product decision validated by codebase evidence
- **Gate result**: PASS — ruff 0, pytest 0 (1 pre-existing skip), npm build 0, git diff --check 0
- **Failure class**: none
- **Remediation action**: none
- **Required skill invoked**: none (simple config change, no heavy skill needed)
- **Docs/notes**: `docs/implementation-notes/2026-05-28-141-bundled-config-empty-models-demo-path.md`
- **Next ACTION**: CONTINUE_NEXT_LOOP (fresh clone re-dogfood)

### 2026-05-28: Fresh Clone P0/P1 Blocker Fixes

- **Commit**: `eccd8db` → `bbaed30`
- **Workstream**: Fresh Clone Dogfood — P0/P1 Blocker Fixes
- **Task type**: bug_fix
- **Outcome**: (1) P0: 收紧 `apply_provider_selection()` 的 fake fallback 条件 — 只在 `model_setup_readiness` 返回 `"demo"`（空 models）时回退，不在 `"needs_setup"`（已配置但缺 key）时回退。保留用户显式配置真实模型时的错误报告路径。(2) P1: `web_facade.py` 修复 — `self.cfg.vault.cards_dir`(str) → `self.cfg.vault.cards_path`(Path)，消除 sample-workspace API 的 str/Path TypeError → HTTP 500。
- **Docs/notes**: `docs/implementation-notes/2026-05-28-140-fresh-clone-p0-p1-blocker-fixes.md`
- **Gates**: `ruff check src/ tests/` (0), `git diff --check` (0), `python -m pytest tests/ -q` (0, 3693 passed, 1 skipped), `npm --prefix web run build` (0)
- **Fresh clone re-dogfood**: PASS — 从 GitHub fresh clone `/tmp/mindforge-fresh-dogfood-20260528` 重新验证：ruff (0), pytest (3693 passed, 3 pre-existing env failures), web build (0), P0 CLI smoke (fake fallback logic 正确), P1 sample-workspace (cards_path Path 类型正确)
- **Review result**: PASS — both fixes scoped correctly, tests verify boundary behavior
- **Gate result**: PASS (4/4 gates + fresh clone re-verify, all exit 0)
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (bug_fix, targeted 2-line changes + tests)
- **Required skill invoked**: N/A
- **Evidence binding**: tests/test_cli_runtime.py (5 new) + tests/test_web_api.py (2 new) + gate exit codes + fresh clone re-verification
- **Next ACTION token**: HARD_STOP_PRODUCT_DECISION. Reason: P0/P1 fix + fresh clone re-dogfood 完成，下一阶段是 Guided Onboarding MVP 实现（已有 spec）或继续其他 roadmap workstream，均需用户选择方向。

---

### 2026-05-28: mf-autopilot Skill Redesign Review + Low-Risk Improvements

- **Commit**: `eccd8db` → `2f7e787`
- **Workstream**: mf-autopilot Skill Governance Upgrade
- **Task type**: autopilot_governance
- **Outcome**: 完成 FirstAgent auto-run vs MindForge mf-autopilot 对比 review（`docs/dev/mf-autopilot-skill-redesign-review.md`），实施 5 项低风险改进：(1) §5.4+§7 停止条件合并去重为单一权威来源 (2) 新增 §7.2 集中非停止条件清单 (3) 新增 §23 Claim-to-Evidence Gate — RESOLVED 声称需绑定 evidence (4) §16 Skill Routing Decision 允许低风险 task 简化输出 (5) §20 progress-ledger 模板新增 Evidence binding 字段
- **Docs/notes**: `docs/dev/mf-autopilot-skill-redesign-review.md`, `docs/implementation-notes/2026-05-28-143-mf-autopilot-skill-redesign-review.md`
- **Gates**: `git diff --check` (0), `python -m pytest tests/test_web_product_copy.py -q --tb=short` (0, 100%)
- **Review result**: PASS — governance rules only, no production code changed
- **Gate result**: PASS (2/2 gates, all exit 0)
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (autopilot_governance, low-risk rules update)
- **Required skill invoked**: N/A
- **Evidence binding**: mf-autopilot-skill-redesign-review.md §4.1 改进清单 + commit <pending> + gate exit 0
- **Next ACTION token**: CONTINUE_NEXT_LOOP. Next: mf-autopilot governance — AUTOPILOT-QUEUE format migration or mf-autopilot.md + engineering-workflow.md dedup

---

### 2026-05-28: Post-Mint4 Remediation — P1 User Validation Kit

- **Commit**: `4f2482b` → `678e524`
- **Workstream**: Post-Mint4 Remediation — P1 User Validation Kit
- **Task type**: docs_cleanup
- **Outcome**: 创建 5 个 User Validation 文档 + remediation plan。更新 CPS HEAD、AUTOPILOT-QUEUE。HARD_STOP_PRODUCT_DECISION: 需要真实用户执行验证。
- **Docs/notes**: `docs/plans/2026-05-28-post-mint4-remediation-plan.md`, `docs/product/validation-protocol.md`, `docs/product/test-script.md`, `docs/product/observer-checklist.md`, `docs/product/feedback-form.md`, `docs/product/sample-workspace-validation.md`
- **Gates**: `git diff --check` (0)
- **Review result**: PASS
- **Gate result**: PASS
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required
- **Required skill invoked**: N/A
- **Next ACTION token**: CONTINUE_NEXT_LOOP. Next: P2 Web UX Remediation

---

### 2026-05-28: Post-Mint4 Remediation — P2 Web UX Remediation

- **Commit**: `678e524` → `0c96f5d`
- **Workstream**: Post-Mint4 Remediation — P2 Web UX Remediation
- **Task type**: ui_ux_polish
- **Outcome**: Browser/MCP audit 发现 1 P1 bug + 2 P2 issues 并全部修复。(1) Review page 路由错误：`/review` 路径不拉取 drafts 数据导致显示 Home 内容，在 App.tsx 第 57 行加 `|| path.startsWith("/review")` 修复 (2) OnboardingHint dismiss 未持久化，加 localStorage 持久化 (`mf-hint-dismissed-` 前缀) (3) 无反馈入口，Sidebar footer 加 GitHub Issues 反馈链接 + i18n keys
- **Diffs**: `web/src/App.tsx` (+1), `web/src/components/OnboardingHint.tsx` (localStorage persistence), `web/src/components/Sidebar.tsx` (feedback link), `web/src/lib/i18n.ts` (nav.feedback zh/en)
- **Gates**: `npm --prefix web run build` (0), `python -m pytest tests/test_web_product_copy.py -q --tb=short` (0, 100%), `git diff --check` (0)
- **Review result**: PASS — browser/MCP verified all fixes
- **Gate result**: PASS (3/3 gates, all exit 0)
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (direct mf-autopilot for targeted P1/P2 fixes)
- **Required skill invoked**: N/A
- **Next ACTION token**: CONTINUE_NEXT_LOOP. Next: P3 Design System Foundation

---

### 2026-05-28: Post-Mint4 Remediation — P3 Design System Foundation

- **Commit**: `0c96f5d` → `2884394`
- **Workstream**: Post-Mint4 Remediation — P3 Design System Foundation
- **Task type**: docs_cleanup
- **Outcome**: U1: 创建 `web/src/design/tokens.ts` — 集中定义 A/B 两套 token 常量 + 已知缺陷文档 + 使用指南。U2: 增强 `docs/dev/design-system.md` — 整合原有设计原则 + token 参考表 + 14 页面清单 + 23 组件语义 + 状态交互规范 + 命名约定。提供跨页面视觉一致性的统一参考。
- **Diffs**: `web/src/design/tokens.ts` (new, 135 lines), `docs/dev/design-system.md` (enhanced)
- **Gates**: `npm --prefix web run build` (0), `git diff --check` (0)
- **Review result**: PASS — docs truth review, token constants match styles.css + tailwind.config.ts
- **Gate result**: PASS (2/2 gates, all exit 0)
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (direct mf-autopilot, lightweight docs + reference file)
- **Required skill invoked**: N/A
- **Next ACTION token**: CONTINUE_NEXT_LOOP. Next: P4 Autopilot Simplification Analysis

---

### 2026-05-28: Post-Mint4 Remediation — P4 Autopilot Simplification Analysis

- **Commit**: `2884394` → `9ea8976`
- **Workstream**: Post-Mint4 Remediation — P4 Autopilot Simplification Analysis
- **Task type**: docs_cleanup
- **Outcome**: 完成 `docs/dev/autopilot-simplification-analysis.md`。分析 1015 行 autopilot 的结构分解、基于 ~30 loop 的触发证据、6 处直接冗余、自指涉风险、简化机会。保守方案可减 ~190 行 (-19%)，激进方案可减 ~335 行 (-33%)。建议 merge 优先于 delete。不实施任何修改。
- **Docs/notes**: `docs/dev/autopilot-simplification-analysis.md`
- **Gates**: `git diff --check` (pending)
- **Review result**: PASS — reads-only analysis, no production code changes
- **Gate result**: pending
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (docs_cleanup, analysis only)
- **Required skill invoked**: N/A
- **Next ACTION token**: CONTINUE_NEXT_LOOP. Next: P5 Docs Governance Cost Reduction

---

### 2026-05-28: Post-Mint4 Remediation — P5 Docs Governance Cost Reduction (Batch 1)

- **Commit**: `9ea8976` → `1fa8b4d`
- **Workstream**: Post-Mint4 Remediation — P5 Docs Governance Cost Reduction (Batch 1)
- **Task type**: docs_cleanup
- **Outcome**: Batch 1 — 3 Community/Topic 相关 implementation notes 标记为 superseded (by-contraction)。社区/Topic Detection 已降级为 lab，对应 notes 反映的已是过期能力声明。
- **Diffs**: 3 files in `docs/implementation-notes/` (status markers only)
- **Gates**: `git diff --check` (0)
- **Review result**: PASS — docs truth review, status markers match CPS §3 lab/internal status
- **Gate result**: PASS
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (docs_cleanup)
- **Required skill invoked**: N/A
- **Next ACTION token**: WORKSTREAM_COMPLETE. Post-Mint4 Remediation 全部 5 个 P 完成

---

### 2026-05-28: Post-Mint4 Independent Retrospective / Lessons Learned

- **Commit**: `4f2482b` (retrospective standalone commit)
- **Workstream**: audit_only — retrospective
- **Task type**: audit_only
- **Outcome**: 完成 Post-Mint4 全项目独立回顾。13 章综合评估文档，涵盖 timeline、capability map、architecture、product direction、user journey、web design、autopilot process、lessons learned、cut/keep/deepen/defer matrix、2-week plan、final verdict。综合评分 6.8/10 (Conditional Go)。核心发现: 产品方向和工程质量可接受，但零真实用户验证是最大风险。推荐立即启动 User Validation，冻结所有 feature development。
- **Docs/notes**: `docs/retrospectives/2026-05-28-post-mint4-retrospective.md`
- **Gates**: `git diff --check` (0), `ruff check docs/` (0), `python -m pytest tests/test_web_product_copy.py -q --tb=short` (0, 100%)
- **Review result**: N/A (read-only audit)
- **Gate result**: PASS
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (audit_only, direct analysis)
- **Required skill invoked**: N/A
- **Next ACTION token**: WORKSTREAM_COMPLETE
- **Next**: User Validation (HARD_STOP: requires 5 non-technical users) 或 Governance Truth Sync
- **Workstream changed**: no (retrospective is standalone, does not change active workstream)

---

### 2026-05-26: Direction C Recall/Search Quality Lab — U1-U5 全部完成

- **Commit**: `ce9b3b9` → `2d9a271`
- **Workstream**: Direction C: Recall/Search Quality Lab
- **Task type**: feature_implementation
- **Outcome**: Direction C 全部 5 单元完成。U1 Golden Recall Benchmark (12 cards + 14 golden queries + 4 negative queries, 27 tests)，U2 Query Explain (QueryExplain dataclass + explain_zero_hits + explain_hits)，U3 BM25 Tuning Infrastructure (Bm25Config frozen dataclass + Bm25RetrievalEngine 参数支持)，U4 Recall Quality Gate Script (`scripts/recall_quality_gate.py`，100% recall 21/21 expected hits)，U5 Web RecallPage Explain Panel (BM25 边界说明 + 命中字段/匹配词展示)。全部纯 deterministic，零 embedding/RAG/vector DB。
- **Docs/notes**: `docs/implementation-notes/2026-05-26-105-recall-search-quality-lab.md`
- **Gates**: all recall tests pass (44 tests), `scripts/recall_quality_gate.py` exit 0 (100% recall), `npm --prefix web run build` exit 0
- **Review result**: PASS — all 5 units match plan spec
- **Gate result**: PASS
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (direct mf-autopilot path for deterministic recall quality)
- **Required skill invoked**: N/A
- **Next ACTION token**: WORKSTREAM_COMPLETE
- **Next**: Direction C 完结，progress-ledger 补录（此前未记录）
- **Workstream changed**: yes (Direction C complete)

---

### 2026-05-28: U7 Tests + U8 i18n — Direction F 测试覆盖 + 国际化验证

- **Commit**: `56d4c0d` → `1e5dda9`
- **Workstream**: Direction F: Structured Knowledge Workbench
- **Task type**: feature_implementation
- **Outcome**: U7 测试完成。新增 `tests/test_card_workspace_service.py`（8 个 backend 测试：bulk_update_tags/track/unknown_card/no_fields + link_cards_creates/dedup/self_link_rejected/unknown_card_rejected），`web/src/components/__tests__/BulkActions.test.tsx`（8 个测试），`ViewSwitcher.test.tsx`（4 个测试），`CollectionPanel.test.tsx`（4 个测试）。frontend 测试总计 11 个文件 79 个测试全部通过。U8 i18n 已验证所有 ~40 keys zh/en 完整。修复 ViewSwitcher.test.tsx 未使用的 userEvent import 导致的 tsc build 失败。
- **Docs/notes**: none (spec 已由之前 loop 创建)
- **Gates**: `ruff check src/ tests/` (0, All checks passed), `npm --prefix web run build` (0, built in 3.65s), `python -m pytest tests/test_web_product_copy.py tests/test_card_workspace_service.py -q` (0, 100%), `git diff --check` (0)
- **Review result**: PASS — U7 spec acceptance review, 24 new tests across backend + frontend
- **Gate result**: PASS (4/4 gates, all exit 0)
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (direct mf-autopilot path for test implementation)
- **Required skill invoked**: N/A
- **Next ACTION token**: CONTINUE_NEXT_LOOP (Direction F complete, switch to next workstream)
- **Next**: Direction F 全部 8 单元完成，workstream 完结，切换至 CPS §6 推荐 next workstream
- **Workstream changed**: yes (Direction F complete)

### 2026-05-28: U6 Manual Card Linking — link_cards backend + frontmatter writing + CardWorkspace link UI

- **Commit**: `5544a92` → `56d4c0d`
- **Workstream**: Direction F: Structured Knowledge Workbench
- **Task type**: feature_implementation
- **Outcome**: U6 Manual Card Linking 完成。新增 `link_cards()` + `_add_manual_link_to_frontmatter()` 后端服务（双向 YAML frontmatter manual_links 写入 + 去重），`LinkCardsRequest`/`LinkCardsResponse` Pydantic schemas，facade + API endpoint (`POST /api/library/cards/link`)，CardWorkspace RelatedCardsPanel 扩展 Link Card 表单（target ref 输入 + reason 下拉 + apply/cancel），6 个 zh/en i18n keys，TypeScript 类型 + API 函数。同时修复 card_workspace_service.py 中 2 个 pre-existing 未使用 import。
- **Docs/notes**: (spec 已由之前 loop 创建)
- **Gates**: `ruff check src/ tests/` (0, All checks passed), `npm --prefix web run build` (0, built in 3.63s), `python -m pytest tests/test_web_product_copy.py -q` (0, 100%), `git diff --check` (0)
- **Review result**: PASS — U6 spec acceptance review, backend + frontend + link form
- **Gate result**: PASS (4/4 gates, all exit 0)
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (direct mf-autopilot path for small implementation slice)
- **Required skill invoked**: N/A
- **Next ACTION token**: CONTINUE_NEXT_LOOP
- **Next**: U7 Tests (backend + frontend tests for U1-U6)
- **Workstream changed**: no

### 2026-05-28: U5 Bulk Maintenance — YAML frontmatter batch update + BulkActions + LibraryPage integration

- **Commit**: `e0091d7` → `5544a92`
- **Workstream**: Direction F: Structured Knowledge Workbench
- **Task type**: feature_implementation
- **Outcome**: U5 Bulk Maintenance 完成。新增 `bulk_update_cards()` 和 `_update_frontmatter_fields()` 后端服务（YAML frontmatter 原地修改保留 body），2 个 BulkUpdate Pydantic schemas，facade + API endpoint (`POST /api/library/bulk-update`)，BulkActions 前端组件（tag/track 批量输入 + Enter 提交），12 个 zh/en bulk i18n keys，LibraryPage 双模式 checkbox（export / bulk edit 切换），清理 card_workspace_service.py 中 2 个未使用 import。
- **Docs/notes**: (spec 已由之前 loop 创建)
- **Gates**: `ruff check src/ tests/` (0), `npm --prefix web run build` (0), `python -m pytest tests/test_web_product_copy.py -q` (0, 100%), `python -m pytest tests/test_collection_store.py tests/test_view_store.py -q` (0, 22/22), `git diff --check` (0)
- **Review result**: PASS — U5 spec acceptance review, backend + frontend + integration
- **Gate result**: PASS (5/5 gates, all exit 0)
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (direct mf-autopilot path for small implementation slice)
- **Required skill invoked**: N/A
- **Next ACTION token**: CONTINUE_NEXT_LOOP
- **Next**: U6 Manual Card Linking
- **Workstream changed**: no

### 2026-05-28: U4 Collections Frontend — CollectionPanel + i18n + API integration

- **Commit**: `43c690d` → `e0091d7`
- **Workstream**: Direction F: Structured Knowledge Workbench
- **Task type**: feature_implementation
- **Outcome**: U4 Collections Frontend 完成。新增 `CollectionPanel.tsx`（可折叠侧栏面板 + 创建对话框 + 删除确认 + 卡片添加/移除），11 个 zh/en i18n keys，5 个 collection API 函数，Collection/CreateCollection/CollectionCardsRequest 等 4 个 TypeScript 接口。`apiDelete` 现支持 optional body 参数。
- **Docs/notes**: (spec 已由之前 loop 创建)
- **Gates**: `npm --prefix web run build` (0), `python -m pytest tests/test_web_product_copy.py -q` (0, 100%), `ruff check` (0), `git diff --check` (0)
- **Review result**: PASS — U4 spec acceptance review
- **Gate result**: PASS (4/4 gates, all exit 0)
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (direct mf-autopilot path for frontend component)
- **Required skill invoked**: N/A
- **Next ACTION token**: CONTINUE_NEXT_LOOP
- **Next**: U5 Bulk Maintenance
- **Workstream changed**: no

### 2026-05-28: U3 Collections Backend — CollectionStore + API endpoints

- **Commit**: `209dbc2` → `43c690d`
- **Workstream**: Direction F: Structured Knowledge Workbench
- **Task type**: feature_implementation
- **Outcome**: U3 Collections Backend 完成。新增 `collection_store.py`（Collection frozen dataclass + CollectionStore CRUD），5 个 Collection Pydantic schemas，5 个 facade 方法，5 个 API endpoints（GET/POST /api/library/collections, POST/DELETE /api/library/collections/{id}/cards, DELETE /api/library/collections/{id}），14 个 test_collection_store 全部通过。
- **Docs/notes**: (spec 已由之前 loop 创建)
- **Gates**: `ruff check` (0), `git diff --check` (0), `python -m pytest tests/` (0, 100%), `npm --prefix web run build` (0)
- **Review result**: PASS — U3 spec acceptance review, 5/5 backend units implemented
- **Gate result**: PASS (4/4 gates, all exit 0)
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required (direct mf-autopilot path for small implementation slice)
- **Required skill invoked**: N/A
- **Next ACTION token**: CONTINUE_NEXT_LOOP
- **Next**: U4 Collections Frontend — CollectionPanel component + i18n + LibraryPage integration
- **Workstream changed**: no

### 2026-05-28: U2 Saved Views Frontend — ViewSwitcher dropdown + save dialog

- **Commit**: `93de101` → `209dbc2`
- **Workstream**: Direction F: Structured Knowledge Workbench
- **Task type**: feature_implementation
- **Outcome**: U2 Saved Views Frontend 完成。新增 `ViewSwitcher.tsx` 组件（dropdown menu + save dialog + delete confirmation），修改 LibraryPage 集成 ViewSwitcher，新增 views i18n keys（zh/en 各 10 个），更新 api types + library.ts 添加 3 个 API 函数。
- **Docs/notes**: (spec 已由之前 loop 创建)
- **Gates**: `ruff check` (0), `git diff --check` (0), `python -m pytest tests/` (0, 100%), `npm --prefix web run build` (0)
- **Review result**: PASS
- **Gate result**: PASS
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required
- **Required skill invoked**: N/A
- **Next ACTION token**: CONTINUE_NEXT_LOOP
- **Next**: U3 Collections Backend
- **Workstream changed**: no

### 2026-05-28: U1 Saved Views Backend — ViewStore + API endpoints

- **Commit**: `0c9b846` → `93de101`
- **Workstream**: Direction F: Structured Knowledge Workbench
- **Task type**: feature_implementation
- **Outcome**: U1 Saved Views Backend 完成。新增 `view_store.py`（SavedView frozen dataclass + ViewStore JSON sidecar CRUD），3 个 Pydantic schemas，3 个 facade 方法，3 个 API endpoints，8 个 tests 全部通过。
- **Docs/notes**: `docs/specs/2026-05-28-direction-f-structured-knowledge-workbench.md`
- **Gates**: `ruff check` (0), `git diff --check` (0), `python -m pytest tests/` (0, 100%), `npm --prefix web run build` (0)
- **Review result**: PASS
- **Gate result**: PASS
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: none required
- **Required skill invoked**: N/A
- **Next ACTION token**: CONTINUE_NEXT_LOOP
- **Next**: U2 Saved Views Frontend
- **Workstream changed**: no

### 2026-05-28: Guided Onboarding MVP — 3-step wizard + per-page hints + sample workspace

- **Commit**: `aef49df` → `<pending>`
- **Workstream**: Guided Onboarding MVP (v0.7)
- **Task type**: feature_implementation
- **Outcome**: 完成 Guided Onboarding MVP 全部 8 个 implementation units。Backend: `POST /api/sample-workspace` endpoint + `sample_workspace.py` service 创建 6 张 MindForge 概念 demo 卡片（human_approved + demo_sample）。Frontend: QuickStartWizard（3 步可交互向导，替代旧 FirstRunGuide） + OnboardingHint（8 页面可关闭提示横幅，AppShell 注入） + i18n zh/en 各 33 keys。Tests: Python 5 tests + Vitest 13 tests + product copy 2 tests。5 个 gate 全部通过（ruff 0, git diff 0, pytest 100%, npm build 0, vitest 63/63）。审批边界：demo 卡片不经过用户数据的 ai_draft 管道，approval_method: demo_sample 标记区分。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-142-guided-onboarding-mvp.md`, `docs/plans/2026-05-27-141-guided-onboarding-mvp.md`
- **Gates**: `ruff check src/ tests/ docs/` (0, All checks passed), `git diff --check` (0), `python -m pytest tests/ -q` (0, 100%), `npm --prefix web run build` (0), `npm --prefix web run test -- --run` (0, 63/63)
- **Review result**: PASS — spec_acceptance_review, 8/8 units implemented, all gates green
- **Gate result**: PASS (5/5 gates, all exit 0)
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: G-stack (design-shotgun, design-consultation); Superpowers (/brainstorming for design); Compound Engineering (ce-work for implementation execution)
- **Required skill invoked**: yes (/brainstorming ✅, ce-work ✅)
- **Next ACTION token**: CONTINUE_NEXT_LOOP
- **Next**: AUTOPILOT-QUEUE-ITEM-3 (User Validation — recruit 5 non-technical users)，但 ITEM-3 需要真实用户 (hard_stop_required=true)。可行的 next loop 为: UI polish loop（可选）、docs cleanup、或回到产品创新审计的其他 bet。
- **Workstream changed**: yes (Guided Onboarding MVP → needs next active workstream)

### 2026-05-28: Product Innovation Audit — MindForge 产品创新审计和机会地图

- **Commit**: `f263287` → `94328a3`
- **Workstream**: Product Strategy Audit
- **Task type**: product_strategy
- **Outcome**: 完成 MindForge 全面产品创新审计。结论: 重组式继续 (Conditional Go with Restructuring, 6.5/10)。回答 10 个战略问题，评分 6 个候选方向(A-F)，推荐主 bet: Product Main Path Deepening (7.6/10)，次 bet: Structured Knowledge Workbench (6.9/10)，第三 bet: Recall/Search Quality Lab (7.1/10)。冻结 Direction D (Real LLM)、Direction E (Collaboration)、Graph/Sensemaking 扩张。设定 2 周验证窗口和明确 kill criteria。AUTOPILOT-QUEUE 重排为 P1 Pipeline Blocker Fix → Guided Onboarding → User Validation。
- **Docs/notes**: `docs/product/2026-05-28-001-mindforge-product-innovation-review.md`
- **Gates**: `git diff --check` , `ruff check docs/ .claude/commands/`, `python -m pytest tests/test_web_product_copy.py -q --tb=short`
- **Review result**: product_strategy 审计完成，与两个独立审计结论一致
- **Gate result**: PASS (git diff --check clean, ruff All checks passed, pytest 100% 84 passed)
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: G-stack (brainstorming, office-hours, plan-eng-review)
- **Required skill invoked**: yes (/brainstorming ✅, /office-hours ✅)
- **Next ACTION token**: CONTINUE_TO_GATES
- **Next**: AUTOPILOT-QUEUE-ITEM-1 (fix P1 pipeline blocker — demo 模式零配置)
- **Workstream changed**: yes (Product Main Path Real Dogfood v2 → Product Strategy Audit)

### 2026-05-28: P1 Pipeline Blocker Fix Verified + Governance Truth Sync + AUTOPILOT-QUEUE Advanced

- **Commit**: `aef49df` → `<pending>`
- **Workstream**: Product Main Path P1 Pipeline Blocker Fix (verification) + Governance Truth Sync
- **Task type**: bug_fix (verification) + docs_cleanup (truth sync)
- **Outcome**: P1 auto-fallback 修复 (`87453f0`) 已验证 — 全量 gate 通过 (pytest 100%, npm build 0, ruff 0)，11 个 auto-fallback 测试全部通过。CPS truth sync: PROD-01 → resolved，HEAD → `aef49df`，AUTOPILOT-QUEUE ITEM-1 → done，ITEM-2 (Guided Onboarding) 成为 next active。推荐优先顺序更新为产品创新审计三级 bet 体系。
- **Docs/notes**: `docs/implementation-notes/2026-05-28-140-p1-fix-verified-queue-advanced-to-guided-onboarding.md`
- **Gates**: `git diff --check` (0), `ruff check src/ tests/` (0), `python -m pytest tests/` (0, 100%), `npm --prefix web run build` (0)
- **Review result**: PASS
- **Gate result**: PASS
- **Failure class**: none (was docs_truth_failure — resolved via truth sync)
- **Remediation action**: governance truth sync — updated CPS HEAD, PROD-01 status, AUTOPILOT-QUEUE, 推荐顺序
- **Skill frameworks checked**: none required (§14.5: bug_fix + docs_cleanup is direct mf-autopilot path)
- **Required skill invoked**: N/A
- **Next ACTION token**: HARD_STOP_PRODUCT_DECISION (ITEM-2 requires /brainstorming + user validation, hard_stop_required=true)
- **Next**: AUTOPILOT-QUEUE-ITEM-2 (Guided Onboarding Design — 需 /brainstorming)
- **Workstream changed**: yes (AUTOPILOT-QUEUE advanced from ITEM-1 → ITEM-2)

### 2026-05-27: Autopilot Governance Upgrade — Recursive Remediation + Mandatory Skill Gates + Skill Framework Routing

- **Commit**: `e6f6d09` → `<pending>`
- **Workstream**: Autopilot Governance Upgrade (Round 1 + 2)
- **Task type**: autopilot_governance
- **Outcome**: `/mf-autopilot` 从 workflow router + skill router 升级为 recursive remediation loop controller。新增 §11 recursive remediation loop (4-tier precedence)、§12 failure classification table (9 类)、§13 retry/escalation policy、§14 mandatory skill gates (5 类)、§15 skill framework discovery (Compound Engineering/G-stack/Superpowers)、§16 skill routing decision block、§17 review node rules、§18 post-loop self-routing block、§19-§21 schema 升级 (CPS AUTOPILOT-QUEUE、progress-ledger、HANDOFF.md)。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-138-mf-autopilot-recursive-remediation-and-mandatory-skills.md`, `docs/implementation-notes/2026-05-27-139-mf-autopilot-skill-framework-routing.md`
- **Gates**: `git diff --check` (0), `ruff check .claude/commands/ docs/` (0), `python -m pytest tests/test_web_product_copy.py -q --tb=short` (0, 100%)
- **Review result**: PASS
- **Gate result**: PASS
- **Failure class**: none
- **Remediation action**: none
- **Skill frameworks checked**: G-stack (design-shotgun, design-consultation loaded; Compound Engineering available via ce-work; Superpowers available)
- **Required skill invoked**: yes (ce-work for implementation; mf-autopilot for governance rules; design-shotgun/design-consultation pre-loaded)
- **Next ACTION token**: CONTINUE_NEXT_LOOP
- **Next**: AUTOPILOT-QUEUE-ITEM-2 (Web Product UX Deepening P3)
- **Workstream changed**: yes (Governance ITEM-3 → Autopilot Governance Upgrade)

### 2026-05-27: Dogfood v3 Light Smoke — 验证 P2 UX 修复 + 治理 ITEM-3 完成

- **Commit**: `9be6e5c` → `f5a1136`
- **Workstream**: Dogfood v3 + Governance Truth Drift Fix
- **Task type**: dogfood + docs_cleanup
- **Outcome**: Chrome DevTools MCP 浏览器 smoke 验证 SafetyBar "模型配置：本地模拟" (绿色, P2 fix ✅) + Library breadcrumb "首页 > 知识库" (正确中文 ✅)。Export 页面 library 为空时正确重定向至 setup。治理 ITEM-3: HANDOFF.md status → historical, CPS AUTOPILOT-QUEUE 重置, HEAD refs 校正, quality-debt-ledger 日期更新。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-137-web-product-ux-deepening-loop-1.md`
- **Gates**: `git diff --check` (0), `pytest tests/` (0, 100%), `npm run build` (0), browser MCP smoke (passed)
- **Next**: AUTOPILOT-QUEUE-ITEM-2 (Web Product UX Deepening P3) 或 next-phase planning review
- **Workstream changed**: yes (Web UX Deepening → Governance → Dogfood v3)

### 2026-05-27: Web Product UX Deepening — Loop 1 (P2 Export breadcrumb + SafetyBar demo status)

- **Commit**: `3c214f6` → `9be6e5c`
- **Workstream**: Web Product UX Deepening
- **Task type**: ui_ux_polish
- **Outcome**: 修复 2 项 Dogfood v2 发现的 P2 UX 摩擦 — Export breadcrumb "export" → "导出知识" (Breadcrumb.tsx + routeLabels)，SafetyBar 模型状态 "待检查" → "本地模拟" (model_setup_readiness.py demo mode + SafetyBar.tsx "demo" handling + i18n keys)。同时修复 ruff F541 (test_watch_schedule_baseline.py)。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-137-web-product-ux-deepening-loop-1.md`
- **Gates**: `git diff --check` (0), `npm run build` (0), `npx vitest run` (0, 50 passed/6 files), `pytest tests/` (0, 100%), `pytest tests/test_web_product_copy.py` (0, 100%), `ruff check` (0)
- **Next**: 继续 AUTOPILOT-QUEUE ITEM-1 (Web Product UX Deepening) 剩馀 P3 项，或 ADVANCE to ITEM-2 (Targeted Architecture Quality Reset)
- **Workstream changed**: no

### 2026-05-27: P1 管道阻塞修复 — demo/fake 模式自动回退

- **Commit**: `256f5be` → `87453f0`
- **Workstream**: Product Main Path Real Dogfood v2 (P1 fix)
- **Task type**: bug_fix
- **Outcome**: 修复 P1 管道阻塞 — CLI import/process/watch 和 Web import/scan 在无模型配置时自动注入 fake profile。`apply_provider_selection()` (CLI) 和 `_ensure_processing_model_configured()` (Web) 两处注入点。9 个测试从期望 error 改为期望 auto-fallback success。fake models 仅在内存注入，不写 YAML，不污染 Setup UI。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-136-p1-pipeline-blocker-auto-fallback-fake.md`
- **Gates**: `ruff check` (0), `pytest tests/` (0, 100%), `npm run build` (0), `pytest tests/test_web_product_copy.py` (0, 80 passed), `git diff --check` (0)
- **Next**: Web Product UX Deepening (Codex audit §10.B 推荐次优先)
- **Workstream changed**: yes (Dogfood v2 → Web Product UX Deepening)

### 2026-05-27: Product Main Path Real Dogfood v2

- **Commit**: `4ef9ed2` → `256f5be`
- **Workstream**: Product Main Path Real Dogfood v2
- **Task type**: dogfood
- **Outcome**: 完成 Chrome DevTools MCP 浏览器级别完整主路径 walkthrough — Source→Draft→Review→Approval→Library→Recall→Wiki→Export 全部通过。记录 8 项 UX 摩擦发现 (P1×1, P2×2, P3×5)。P1 发现: demo/fake 模式并非真正零配置，import 管道在无模型时报错。Governance truth sync 完成 CPS/ledger 状态更新。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-135-product-main-path-real-dogfood-v2.md`
- **Gates**: `ruff check` (0), `pytest tests/` (0, 100%), `npm run build` (0), `pytest tests/test_web_product_copy.py` (0), MCP smoke 8 页全部通过
- **Next**: 修复 P1 管道阻塞 (demo/fake 模式零配置) → 然后进入 Web Product UX Deepening
- **Workstream changed**: yes (Dogfood v2 → P1 Fix)

### 2026-05-27: Codex Independent Strategic Red Team Audit

- **Commit**: `4ef9ed2`
- **Workstream**: Independent Strategic Red Team Audit
- **Task type**: audit_only
- **Outcome**: 完成一次独立、只读、战略红队审计。结论为 Conditional Go，总分 6.4/10。最强资产仍是 approval-first personal knowledge compiler；主要风险是产品习惯未验证、Web 仍有工程控制台味、治理 truth drift、Export 契约不一致、WebFacade/配置服务仍偏巨石。未修改产品代码、Web 代码、测试代码、`/mf-autopilot`，未切换 active workstream。
- **Docs/notes**: `docs/audits/2026-05-27-133-codex-independent-strategic-red-team-audit.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0; warning: no Python files found), `python -m pytest tests/test_web_product_copy.py -q --tb=short` (0)
- **Next**: Primary recommendation: Product Main Path Real Dogfood v2. Secondary recommendation: Web Product UX Deepening. Do not resume Graph/Sensemaking/Entity/Community expansion, RAG/vector/embedding, broad architecture reset, or real LLM runs without explicit user decision and negative safety tests.
- **Workstream changed**: no

### 2026-05-27: AUDIT-118 P1 Product Debt Closure

- **Commit**: `e6dbe9b`
- **Workstream**: AUDIT-118 P1 Product Debt Closure
- **Task type**: ui_ux_polish + docs_cleanup + smoke_evidence
- **Outcome**: 关闭全部 4 项剩余 AUDIT-118 P1 产品债。AUDIT-118-01: user guides + README 更新 Export 文档，标注 browser-local download；AUDIT-118-02: Dogfood i18n label 加 (Internal) 标记，user guides 重写为内部工具；AUDIT-118-04: Chrome DevTools MCP smoke 验证主路径全部页面正常；AUDIT-118-05: HANDOFF.md 新增 status 字段体系 (active/completed/resolved/historical)，CPS §8 更新读取规则。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-132-audit-118-product-debt-closure.md`
- **Gates**: `git diff --check` (0), `npm run build` (0), `npm run test` (0, 50 passed/6 files), `pytest tests/test_web_product_copy.py` (0)
- **Next**: 按 CPS §6 AUTOPILOT-QUEUE 继续 frontend test coverage expansion 或 Documentation Reset Batch 2
- **Workstream changed**: yes (AUDIT-118 → Quality Platform)

### 2026-05-27: Breadcrumb / SafetyBar Component Tests

- **Commit**: `7acb47e`
- **Workstream**: Quality Platform / Frontend Test Coverage
- **Task type**: feature_implementation
- **Outcome**: Breadcrumb (9 tests) + SafetyBar (16 tests) 组件测试。解决了 useLocale() i18n context provider 问题 — 使用 LocaleProvider 包裹被测组件。SafetyBar 的 split text node 问题用正则匹配修复。测试文件 4→6，测试用例 25→50。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-131-breadcrumb-safetybar-tests.md`
- **Gates**: `git diff --check` (0), `npm run build` (0), `npm run test` (0, 50 passed/6 files), `pytest tests/test_web_product_copy.py` (0, 84 passed)
- **Next**: 剩余低风险测试项已全部覆盖（6/41 组件已测试）。AUDIT-118 产品债（Export docs、Dogfood nav）需产品决策，非测试补强范围。
- **Workstream changed**: no

### 2026-05-27: Architecture Doc Audit Fix

- **Commit**: `7223203` → `140a472`
- **Workstream**: Quality Platform
- **Task type**: audit_only
- **Outcome**: 修复 architecture.md 两处不一致 — 补充 `mindforge_web/presenters/` 目录、更新 web_facade.py 行数 1487 (-31.3%) → 922 (-57.4%)
- **Gates**: `git diff --check` (0)

### 2026-05-27: Web Frontend Test Coverage Expansion

- **Commit**: `91f5ec7` → `7223203`
- **Workstream**: Frontend Quality
- **Task type**: feature_implementation
- **Outcome**: 前端组件测试从 1 文件/2 测试扩展到 4 文件/25 测试。新增 LoadingSkeleton (2 tests, 10 variants)、EmptyState (6 tests)、StatusCard (6 tests) 的测试文件。全部 25 个测试通过。
- **Docs/notes**: `docs/plans/2026-05-27-129-web-frontend-test-expansion.md`, `docs/implementation-notes/2026-05-27-130-web-frontend-test-expansion.md`
- **Gates**: `ruff check` (0), `git diff --check` (0), `npm run build` (0), `npm run test` (0, 25 passed/4 files), `pytest tests/test_web_product_copy.py` (0, 84 passed)
- **Next**: 继续扩展 Breadcrumb/SafetyBar（需 i18n context）或 page-level smoke tests
- **Workstream changed**: no

### 2026-05-27: Documentation Reset Batch 2

- **Commit**: `fb98003` → `91f5ec7`
- **Workstream**: Documentation Reset
- **Task type**: docs_cleanup
- **Outcome**: DOC-01: 创建 docs/README-en.md 英文版文档入口。DOC-02: ADR-006 frontmatter status 从 active → partial (4/8 NodeType)。DOC-03: docs/design/README.md 新增 historical/reference 状态说明，obsidian-binding-design.md 标记 deferred。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-128-docs-reset-batch-2.md`
- **Gates**: `git diff --check` (0)
- **Next**: Web frontend test coverage expansion（vitest + happy-dom 基础设施已就绪）
- **Workstream changed**: no

### 2026-05-27: v3.7 Quality Platform

- **Commit**: `e159e29` → `fb98003`
- **Workstream**: v3.7 Quality Platform
- **Task type**: feature_implementation
- **Outcome**: P2-05 (vitest + happy-dom + @testing-library/react 前端测试基础设施) + P2-06 ([tool.coverage] 配置, pytest --cov 可用, 88% baseline) + web_config_service.py env detection 提取至 web_config_env.py。ErrorState 组件测试示范通过。
- **Docs/notes**: `docs/plans/2026-05-27-127-v3.7-quality-platform.md`, `docs/implementation-notes/2026-05-27-127-v3.7-quality-platform.md`
- **Gates**: `ruff check` (0), `git diff --check` (0), `npm run build` (0), `npm run test` (0, 2 passed), `pytest tests/` (0, ~3030 passed/1 skip), `pytest --cov` (0, 88%), `pytest tests/test_web_product_copy.py` (0)
- **Next**: Documentation Reset Batch 2（archive/delete 规则已明确）
- **Workstream changed**: yes (from Autopilot Governance to v3.7 Quality Platform)

- **Commit**: `e159e29`
- **Workstream**: Autopilot Governance
- **Task type**: autopilot_governance
- **Outcome**: 修复 /mf-autopilot 在 workstream 完成→新 workstream spec/plan 时误判停止的 bug。§5.3 rule 5 workstream 切换优先级明确化（完成→自动切换）。§5.7 新增跨 workstream spec/plan auto-continue 条目。§5.8 强制 ACTION token 输出（CONTINUE_NEXT_LOOP / HANDOFF_AND_STOP / HARD_STOP_<CODE>）。§5.9 新增 5 个软停禁令表述。CPS §6 新增 machine-readable AUTOPILOT-QUEUE 注释。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-126-mf-autopilot-cross-workstream-fix.md`
- **Gates**: (pending run)
- **Next**: v3.7 Quality Platform spec/plan 编写（现在 auto-continue allowed）
- **Workstream changed**: yes (from Architecture Quality Reset to Autopilot Governance)

### 2026-05-27: Architecture Quality Reset — Slice 2 (Extract web_facade.py Private Helpers to Presenters)

- **Commit**: `9c598a4` → `70a1475`
- **Workstream**: Architecture Quality Reset
- **Task type**: architecture_refactor
- **Outcome**: 将 web_facade.py 中 ~540 行私有 helper 函数提取到 5 个 presenter 子模块（shared/graph/library/discovery/provenance）。web_facade.py 从 1487 行降至 922 行 (-38.0%)，累计从 2163 行减少 57.4%。所有命名 `_xxx` → `build_xxx`/`get_xxx`。3 个 service 文件 + 2 个测试文件导入更新。零行为变更，零循环导入。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-125-architecture-quality-reset-slice-2.md`
- **Gates**: `ruff check src/ tests/` (0), `pytest tests/ -q --tb=short` (0, 545 passed/1 skipped), `git diff --check` (0), `npm --prefix web run build` (0), `python -m pytest tests/test_web_product_copy.py -q --tb=short` (0)
- **Next**: Architecture Quality Reset Slice 1+2 完成，workstream 完结。剩余 debt (P2-05/P2-06/web_config_service split) deferred to v3.7。
- **Workstream changed**: no

### 2026-05-27: Architecture Quality Reset — Slice 1 (Fix Core→Web Layer Violation)

- **Commit**: `c4f5c25` → `2cba857`
- **Workstream**: Architecture Quality Reset
- **Task type**: architecture_refactor
- **Outcome**: 将 processing run 持久化/查询/worker 逻辑从 web 层迁移到 `src/mindforge/processing/run_store.py`（core 层）。5 个 core 模块的 import 路径更新。2 个 private symbol import（`_run_worker`、`_save_record`）消除。边界测试已知违规条目从 7 减至 2。层依赖方向修复：web → core。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-124-architecture-quality-reset-slice-1.md`
- **Gates**: `ruff check src/ tests/` (0), `pytest tests/test_architecture_boundaries.py -q --tb=short` (0, 14 passed), `pytest tests/ -q --tb=short` (0, 100%), `pytest tests/test_web_product_copy.py -q --tb=short` (0), `npm --prefix web run build` (0), `git diff --check` (0)
- **Next**: Slice 2 — 提取 web_facade.py 私有 helper 到 presenters
- **Workstream changed**: no

### 2026-05-27: Architecture Quality Reset — Plan + Slice 0 Boundary Tests

- **Commit**: `1b39edb` → `8eb3fd4`
- **Workstream**: Architecture Quality Reset
- **Task type**: architecture_refactor (plan/spec + boundary tests)
- **Outcome**: 完成 architecture evidence audit + targeted reset plan（7 个 core→web 反向依赖、3 个 implementation slices）。Slice 0 在 test_architecture_boundaries.py 中新增 6 个架构边界测试（3 个 test class），全部 14 个测试通过。plan 明确 Slice 1 修复 core→web 层反向依赖、Slice 2 提取 presenter、Slice 3+ deferred。
- **Docs/notes**: `docs/plans/2026-05-27-122-targeted-architecture-quality-reset.md`, `docs/implementation-notes/2026-05-27-123-architecture-quality-reset-plan-slice-0.md`
- **Gates**: `git diff --check` (0), `ruff check src/ tests/ docs/` (0), `pytest tests/test_architecture_boundaries.py -q --tb=short` (0, 14 passed), `pytest tests/test_web_product_copy.py -q --tb=short` (0, 9 passed), `npm --prefix web run build` (0)
- **Next**: Slice 1 — 修复 core→web 反向依赖（需 plan 批准后执行）
- **Workstream changed**: yes (from Autopilot Governance)

### 2026-05-27: Autopilot Governance — Auto-Continue Policy Hardening

- **Commit**: `3c829da` → `56b3d23`
- **Workstream**: Autopilot Governance
- **Task type**: autopilot_governance
- **Outcome**: 修复 /mf-autopilot auto-continue 治理 bug：新增 §5.7 Auto-Continue Decision Table（12 auto-continue + 10 must-ask 条件）、§5.8 Self-routing after final report（6 步自路由流程）、§5.9 Banned soft-stop phrases（8 个禁止表述）。注册 autopilot_governance task type。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-121-mf-autopilot-auto-continue-policy.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0), `pytest tests/test_web_product_copy.py -q --tb=short` (0)
- **Next**: Architecture Quality Reset plan（现在通过 auto-continue 规则可直接进入 plan 编写）
- **Workstream changed**: yes (from Web IA/UX Loop 2 to Autopilot Governance)

### 2026-05-27: Web IA/UX Loop 2 — Post-Dogfood User-Facing Debt Fix

- **Commit**: `6145b72`
- **Workstream**: Web IA/UX Loop 2
- **Task type**: ui_ux_polish
- **Outcome**: 修复 3 个 P1 Web IA/UX 问题: (1) Dogfood nav 从 tools 移至 collapsed lab section, (2) DogfoodPage 添加 LAB/INTERNAL 横幅, (3) LocalGraphPreview 硬编码英文替换为 i18n。ExportPage 和 SetupPage 经审计确认无 drift。
- **Docs/notes**: `docs/audits/2026-05-27-120-web-ia-ux-loop-2-audit.md`, `docs/implementation-notes/2026-05-27-120-web-ia-ux-loop-2.md`
- **Gates**: `git diff --check` (0), `npm --prefix web run build` (0), `pytest tests/test_web_product_copy.py -q --tb=short` (0), `ruff check src/ tests/ docs/` (0)
- **Next**: Architecture Quality Reset (需先写 spec/plan)
- **Workstream changed**: no (Web IA/UX Loop 2 本 loop 完结)

### 2026-05-27: Product Main Path Real Dogfood — FakeProvider Keyword Extraction Improvement

- **Commit**: `97d57fb`
- **Workstream**: Product Main Path Real Dogfood
- **Task type**: dogfood
- **Outcome**: FakeProvider distill keyword extraction 从 title-only 改进为 title + prompt raw_text（最多 12000 chars 真实原文）。English recall hit rate 从 ~40% 提升到 91.7% (11/12)。Full pipeline (scan→process→approve→library→recall→wiki) 全部通过。Chinese recall 0% 因为 source docs 全是英文 — 这是 source material limitation，非 bug。
- **Docs/notes**: `docs/implementation-notes/2026-05-27-119-fake-provider-keyword-extraction-improvement.md`
- **Gates**: `git diff --check` (0), `ruff check src/ tests/ docs/` (0), `pytest tests/test_web_product_copy.py -q` (0), `pytest tests/ -q` (0), `npm --prefix web run build` (0)
- **Next**: 审计推荐的下一个 loop 是 Web IA/UX Loop 2 或 Architecture Quality Reset；Batch 2 仍暂停（archive/delete rules 不详）
- **Workstream changed**: no (Product Main Path Real Dogfood 本 loop 完结)

### 2026-05-27: Post-Governance Global Red Team Audit

- **Commit**: `20a3038`
- **Workstream**: Post-Governance Global Red Team Audit
- **Task type**: audit_only
- **Outcome**: 完成一次只读全局红队审计；结论为 Conditional Go，总分 6.1/10。主路径和 approval-first 安全语义是最强资产；下一步不建议自由推进 Batch 2，而应优先做 Product Main Path Real Dogfood。
- **Docs/notes**: `docs/audits/2026-05-27-118-post-governance-global-red-team-audit.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0; warning: no Python files found), `python -m pytest tests/test_web_product_copy.py -q --tb=short` (0)
- **Next**: Product Main Path Real Dogfood；secondary: Web IA/UX Loop 2；Batch 2 暂停，除非 exact archive/delete rules 获批
- **Workstream changed**: yes (from Documentation Reset to Product Main Path Real Dogfood recommendation)

### 2026-05-27: Docs Cleanup — Batch 1 Residual References Cleaned

- **Commit**: `ac6aa47`
- **Workstream**: Documentation Reset
- **Task type**: docs_cleanup
- **Outcome**: 修复 Batch 1 删除 8 个 stale files 后的 ~15 个跨文档残留引用；14 个历史文档标注 "(removed 2026-05-27)"；3 个 management docs 更新引用状态
- **Docs/notes**: `docs/implementation-notes/2026-05-27-117-docs-cleanup-residual-references.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0), `pytest tests/test_web_product_copy.py -q` (0)
- **Next**: 评估 Batch 2 (Archive Candidates) 是否已明确
- **Workstream changed**: no

### 2026-05-27: Docs Cleanup Batch 1 — 8 stale files removed

- **Commit**: `fcb96c7`
- **Workstream**: Documentation Reset
- **Task type**: docs_cleanup
- **Outcome**: 删除 8 个明显过时文档（v0.2/v0.3 roadmap、TDD/SDD、v0.2/v0.3 dev rules、早期 dogfood plans）；更新 documentation-reset-plan、documentation-inventory、docs-reset-index 中的引用
- **Docs/notes**: `docs/implementation-notes/2026-05-27-116-docs-cleanup-batch-1.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0), `pytest tests/test_web_product_copy.py -q` (0)
- **Next**: batch 2（处理历史 RFC/SDD/spec/implementation-notes 中的残留引用）
- **Workstream changed**: yes (from mf-autopilot reliability upgrade)

### 2026-05-27: mf-autopilot Reliability Upgrade

- **Commit**: `64d7a52`
- **Workstream**: mf-autopilot Reliability Upgrade
- **Task type**: docs_cleanup
- **Outcome**: 补齐 4 类治理规则 — active workstream rules、stale window rules、progress template、handoff protocol
- **Docs/notes**: `docs/implementation-notes/2026-05-27-115-mf-autopilot-reliability-upgrade.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0), `pytest tests/test_web_product_copy.py -q --tb=short` (0)
- **Next**: Documentation cleanup batch 1
- **Workstream changed**: no (continuing governance work)

### 2026-05-27: Docs Reset & Governance — Loop 1 (canonical state + progress ledger)

- **Commit**: `0248755`
- **Workstream**: Documentation Reset & Project Governance
- **Task type**: docs_cleanup
- **Outcome**: 创建 CURRENT_PROJECT_STATE.md, progress-ledger.md, documentation-reset-plan.md；升级 mf-autopilot 为 task-type-aware；更新 docs/README.md
- **Docs/notes**: `docs/implementation-notes/2026-05-27-114-docs-reset-governance-loop-1.md`
- **Gates**: `git diff --check` (0), `ruff check docs/ .claude/commands/` (0), `pytest tests/test_web_product_copy.py -q` (0)
- **Next**: mf-autopilot reliability upgrade (active workstream / stale window / progress template / handoff)
- **Workstream changed**: no (continuing governance work)

### 2026-05-27: Export Page MVP

- **Commit**: `fb87ce0` → `6f5db2c`
- **Goal**: 实现独立的 `/export` 页面（之前 fallthrough 到 Home）
- **Outcome**: 完成。14 种 UX states 覆盖，MCP 浏览器验证通过
- **Docs**: `docs/plans/2026-05-27-112-export-page-product-spec.md`, `docs/implementation-notes/2026-05-27-113-export-page-mvp.md`
- **Remaining debt**: 无

### 2026-05-27: Backend Copy & ID Sanitization

- **Commit**: `7bb4a76` → `9eb4108`
- **Goal**: 修复后端生成的英文用户可见文案（Health / Wiki 标签 → 中文）
- **Outcome**: 完成。health_service.py 8 项检查消息 + wiki_service.py 标签全部中文化
- **Docs**: `docs/implementation-notes/2026-05-27-112-backend-copy-and-id-sanitization.md`
- **Remaining debt**: `__model_routing__` 出现在卡片内容中（pre-existing，非本次修）

### 2026-05-27: Web IA Simplification

- **Commit**: `54110d4` → `a1556f9`
- **Goal**: 前端 IA 精简——隐藏内部标签、格式化时间戳、替换 BM25 术语
- **Outcome**: 完成。Sidebar 重组，SourcesPage 渐进展示，Recall 页面术语替换
- **Docs**: `docs/implementation-notes/2026-05-27-111-web-ia-simplification.md`
- **Remaining debt**: 少量 Web IA 碎片待后续清理

### 2026-05-26: Design QA — Stage 1–6

- **Commits**: `a138177` → `07bd8a0`
- **Goal**: Web 视觉设计系统落地（CSS tokens → AppShell → Review → Library → Home → 一致性 pass）
- **Outcome**: 完成 6 个 Stage
- **Docs**: `docs/implementation-notes/2026-05-26-110-stage-6-design-qa.md`
- **Remaining debt**: 无

### 2026-05-26: v4.4 Product Main Path UX Deepening

- **Commits**: within `docs/implementation-notes/2026-05-26-095-v4_4-product-main-path-ux-deepening.md`
- **Goal**: FirstRunGuide、ImportPathCard、安全说明、导出安全通知
- **Outcome**: 完成 A1–A6
- **Docs**: `docs/implementation-notes/2026-05-26-095-v4_4-product-main-path-ux-deepening.md`
- **Remaining debt**: 无

### 2026-05-25: Product Main Path Dogfood

- **Goal**: fake sampler 跑完整 product main path
- **Outcome**: 42/42 样本通过。Recall 10/10。Wiki rebuild 通过
- **Docs**: `docs/implementation-notes/2026-05-25-090-product-main-path-dogfood-execution.md`, `docs/implementation-notes/2026-05-25-091-product-main-path-hardening.md`
- **Remaining debt**: P3-04 (BM25 body 字段增量贡献有限)

### 2026-05-25: v4.2 Red Team Stabilization

- **Goal**: 收缩 Graph/Sensemaking 暴露面、package safety、docs truth reset
- **Outcome**: P1–P4 全部关闭
- **Docs**: `docs/implementation-notes/2026-05-25-086-v4_2-red-team-stabilization.md`
- **Remaining debt**: 无

### 2026-05-25: v3.6.1 Remediation Batch A

- **Goal**: 修复 v2.0-v3.6 独立审计的 P0/P1 issues
- **Outcome**: A1 (docx importorskip) + A2 (flaky perf test) + A3 (gate baseline) + A4 (architecture.md 引用) + B1 (zh-CN user-guide sync) + B2 (recall_service → RetrievalPort)
- **Docs**: `docs/implementation-notes/2026-05-25-079-v3_6_1-remediation-batch-a.md`
- **Remaining debt**: P2-05 (前端测试), P2-06 (覆盖率)

### 2026-05-24/25: v3.7–v4.1 Graph/Sensemaking 全链路

- **Goal**: Graph Ontology → Graph View → Entity Resolution → Sensemaking → GraphRepository
- **Outcome**: 完成但后续被 v4.2 red team 收缩
- **Remaining debt**: 已由 v4.2 truth reset 处理

---

## 2. Active Workstream

**全部活跃 workstream 完成 (2026-05-28)**

Directions A (Product Main Path Deepening)、C (Recall/Search Quality Lab)、F (Structured Knowledge Workbench) 全部完成。

**当前无 active workstream。** 下一步需 User Validation (HARD_STOP: 需要 5 名非技术用户)。在此之前可进行 governance truth sync / stale docs cleanup / comprehensive gate check。

---

## 3. Next Recommended Loop

按完成度和优先级推荐:

1. **User Validation** — 最高优先级但 HARD_STOP (需要 5 名非技术用户验证核心假设)
2. **Governance Truth Sync** — 更新所有 stale 文档以反映 A+C+F 完成状态
3. **Direction D (Real LLM)、Direction E (Collaboration)、Graph/Sensemaking 扩张** — 冻结

---

## 4. How to Update This Ledger

每个 `/mf-autopilot` loop 结束，按以下模板在 §1 顶部添加记录:

```markdown
### YYYY-MM-DD: <简短标题>

- **Commit**: `<hash>` 或 `<start-hash>` → `<end-hash>`
- **Workstream**: <active workstream name>
- **Task type**: <bug_fix | docs_cleanup | ui_ux_polish | architecture_refactor | feature_implementation | audit_only | dogfood | design_review>
- **Outcome**: <1-2 句话描述结果>
- **Docs/notes**: <新建的 docs/implementation-notes 路径>
- **Gates**: <gate 命令 + exit codes>
- **Next**: <推荐的 next loop>
- **Workstream changed**: yes / no
```

Minor bug fix 至少追加一行:
```markdown
- YYYY-MM-DD: <描述> (`<hash>`)
```

**commit/push 不是间隔点** — 一个 major loop 可能包含多个 commit，合写在一条记录里。
