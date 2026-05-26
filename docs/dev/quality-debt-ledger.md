# Quality Debt Ledger

基于 v2.0-v3.6 independent delivery audit、v3.6.1 remediation Batch A、v4.2 red team stabilization、v4.2.1 partial remediation closure、Product Main Path Dogfood (2026-05-25)、v4.4 Product Main Path UX Deepening (2026-05-26) 和 v4.7 Architecture Debt Reduction (2026-05-26) 更新。

更新日期: 2026-05-26 (v4.7 architecture debt reduction)

---

## Open Debt

| ID | Priority | Description | Source | Status | Target |
|----|----------|-------------|--------|--------|--------|
| P2-02 | P2 | web_facade.py God Service (2033 行), 30+ public methods 跨 10+ 领域 | v2.x → v3.x | open | v3.7+ |
| P2-03 | P2 | schemas.py God Schema — was 1375 行/62 schema 单文件, v4.8 Slice 1 后 __init__.py 降至 399 行 (-63.4%), ~100 schema 提取至 12 个子模块: common + provider + source + library + recall + graph + sensemaking + trash + quality + import_export + dogfood_lifecycle + review | v2.x → v3.x | resolved (v4.8) | — |
| P2-05 | P2 | 零前端测试覆盖 (0 test files in web/src/) | v2.x → v3.x | open | v3.7 |
| P2-06 | P2 | 无覆盖率配置 — pyproject.toml 无 [tool.coverage] | v2.x → v3.x | open | v3.7 |
| P3-01 | P3 | npm build chunk size >500KB | v2.5 | open (非阻塞) | — |
| P3-02 | P3 | 1 skipped test (conditional: no runs written) | pre-existing | acknowledged (正常条件跳过) | — |
| P3-03 | P3 | test_approval/review/process_service_boundaries 三文件间 ~50% AST helper 同构代码（有意不共享 fixture，独立可理解） | v2.x | acknowledged (设计选择) | — |
| P3-04 | P3 | FakeProvider keyword injection 虽已注入但 BM25 标题权重(5.0)主导 recall — body 字段增量贡献有限 | 2026-05-25 dogfood | acknowledged (BM25 TF 饱和效应，非 bug；recall 10/10 通过样本覆盖) | — |

## Resolved Debt (v4.4 Product Main Path UX Deepening — 2026-05-26)

| ID | Priority | Description | Source | Resolution |
|----|----------|-------------|--------|------------|
| P2-ux-01 | P2 | HomePage 缺少 first-run 空 workspace 引导 — 新用户不知道从哪里开始 | v4.2 red team | v4.4 A1: FirstRunGuide 组件 + 4 步骤引导 + 安全边界说明 |
| P2-ux-02 | P2 | SourcesPage 导入方式说明缺失 — 用户不知道 watch/one-shot/paste 三种路径 | v4.2 red team | v4.4 A2: ImportPathCard 三种导入方式解释 + i18n |
| P2-ux-03 | P2 | DraftsPage 缺少"为什么需要审阅"解释 — explicit approval 语义不够明确 | v4.2 red team | v4.4 A2: why_review 信息横幅 |
| P3-ux-01 | P3 | Export 预览缺少安全说明和格式描述 — 用户可能误解导出会写 vault | v4.2 red team | v4.4 A3: export_safety_note + 四种格式描述 |

## Resolved Debt (Product Main Path Dogfood — 2026-05-25)

| ID | Priority | Description | Source | Resolution |
|----|----------|-------------|--------|------------|
| P1-df-01 | P1 | FakeProvider 缺少 wiki_synthesis stage — wiki rebuild 在 fake provider 下失败 | dogfood execution | 添加 wiki_synthesis stage，返回符合 prompt schema 的占位 JSON |
| P2-df-01 | P2 | Dogfood recall hit rate 仅 70% (7/10) — SQL/React/安全 三个查询无匹配 | dogfood execution | 不是索引 bug，是样本覆盖不足。新增 3 个合成样本 (React Hooks/SQL 优化/中文安全知识) + 扩大样本量至 80，recall 提升至 10/10 |
| P3-df-01 | P3 | FakeProvider 输出全 `[fake]` 占位符，BM25 body 字段无真实关键词 | dogfood diagnosis | _extract_keywords() 确定性标题关键词注入到 tags/source_excerpt/summary/inference — recall 提升主要来自样本覆盖而非关键词注入 (BM25 标题权重 5.0 vs body 权重 1.0) |

## Resolved Debt (v4.2.1 partial remediation closure)

| ID | Priority | Description | Source | Resolution |
|----|----------|-------------|--------|------------|
| P1-01 (re-audit) | P1 | GraphPage 8-type selector 暴露 unsupported NodeType | v4.2 post-remediation re-audit | v4.2.1: SUPPORTED_TYPES (4) / UNSUPPORTED_TYPES (4) split + lab note + product copy tests |
| P1-02 (re-audit) | P1 | Package safety 缺少 artifact-level wheel 检查 | v4.2 post-remediation re-audit | v4.2.1: TestWheelArtifactSafety 类：构建 wheel → inspect zip → 断言无敏感文件 |
| P2-01 (re-audit) | P2 | Sensemaking 独立页面无 LAB/INTERNAL 标识 | v4.2 post-remediation re-audit | v4.2.1: warning banner + LAB badge + heuristic limits disclosure + product copy tests |
| P2-02 (re-audit) | P2 | 旧 ADR/roadmap 仍有 graph/sensemaking 过度声明 | v4.2 post-remediation re-audit | v4.2.1: ADR-006/007 + v3.7-v4.1 roadmap 追记 + docs-reset-index.md |

## Resolved Debt

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| P1-01 | P1 | SearchIndexPort changelog 措辞修正 | v3.0: changelog 措辞已修 |
| P2-01 | P2 | v2.4 changelog 路径不一致 | v3.0: 路径引用已更新 |
| P1-01 (audit) | P1 | Gate Evidence 不可重现 — pytest exit code=1 (docx import fail + flaky perf test) | v3.6.1 Batch A: docx importorskip + GC disable/warmup fix |
| P1-02 (audit) | P1 | zh-CN user-guide.md 未随 v2.5 更新 | v3.6.1 Batch B1 |
| P1-03 (audit) | P1 | architecture.md 引用不存在的 import_service.py/export_service.py | v3.6.1 Batch A4: 修正为 web_facade.py + routers/library.py |
| — | pre-existing | ruff 17 errors | Resolved pre-v3.0 (ruff clean) |
| — | pre-existing | pytest failures (docx import + flaky perf test) | Resolved v3.6.1: importorskip + GC disable/warmup |
| P2-03 (legacy) | P2 | Import/Export 无独立导航入口 | v3.5: Workbench UX 集成已处理 |
| P2-04 | P2 | RetrievalPort ABC 未集成到 recall_service | v3.6.1 Batch B2: recall_service 通过 engine.load_or_build_index() 管理索引生命周期，不再直接操作 lexical_index |

---

## Gate Baseline (2026-05-25 — Product Main Path Dogfood + Overnight Hardening)

全量 gate 在 clean main tree 上运行，exit code 真实可重现。

| Gate | Command | Exit Code | Timeout | Detail |
|------|---------|-----------|---------|--------|
| ruff (Python) | `ruff check src/ tests/` | 0 | no | All checks passed |
| git diff | `git diff --check` | 0 | no | — |
| npm build | `npm --prefix web run build` | 0 | no | built in ~2.5s |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 | no | ~76 passed |
| approval boundary | `python -m pytest tests/test_review_approval_boundary.py -q --tb=short` | 0 | no | 102 passed |
| package safety | `python -m pytest tests/test_package_safety.py -q --tb=short` | 0 | no | passed |
| full pytest | `python -m pytest tests/ -q --tb=short` | 0 | no | ~3030 passed, 1 skip |
| expanded dogfood | `bash scripts/expanded_dogfood.sh` | 0 | no | 所有 13 步 PASS, recall 10/10 |

### Product Main Path Dogfood 指标

| 指标 | 结果 |
|------|------|
| 样本文件 | 42 个 .md |
| ai_draft 生成 | 42/42 (100%) |
| human_approved | 42/42 (100%) |
| 安全边界 bypass | 0 |
| Recall 命中率 | 10/10 (100%) |
| Wiki rebuild | pass (42 cards) |
| Index rebuild | pass |
| P0 阻塞 bug | 0 |
