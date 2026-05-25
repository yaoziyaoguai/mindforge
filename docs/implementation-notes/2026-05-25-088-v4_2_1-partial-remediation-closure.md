# v4.2.1 Partial Remediation Closure — Implementation Notes

**日期**: 2026-05-25
**状态**: complete
**基于**: `docs/audits/2026-05-25-v4_2-post-remediation-red-team-re-audit.md`
**上游**: v4.2 Red Team Stabilization (`715f44c`)

---

## 背景

v4.2 post-remediation re-audit 复审发现 4 项 PARTIAL findings 需要闭合后才能进入 Product Main Path Dogfood：

| Finding | 状态 | 闭合方式 |
|---------|------|---------|
| P1. Package secret risk | PARTIAL → **PASS** | 新增 `TestWheelArtifactSafety`：实际构建 wheel → 解压检查 → 断言无敏感文件 |
| P2. Graph NodeType truth reset | PARTIAL → **PASS** | GraphPage selector 收缩为 SUPPORTED_TYPES (4) + UNSUPPORTED_TYPES lab note |
| P3. Sensemaking downgrade | PARTIAL → **PASS** | SensemakingPage 顶部 warning banner + LAB badge + heuristic limits disclosure |
| P4. Docs truth reset | PARTIAL → **PASS** | ADR-006/007 + roadmap 追记 + docs-reset-index.md |

---

## 实现范围

### P1. Package Artifact-Level Safety Test

**`tests/test_package_safety.py`** — 新增 `TestWheelArtifactSafety` 类：

```python
class TestWheelArtifactSafety:
    SENSITIVE_PATTERNS = (".mindforge", "secrets.json", ".key", ".token", ".env")

    def test_wheel_artifact_excludes_sensitive_files(self):
        # 构建 wheel → 解压 zip → 逐文件检查敏感模式

    def test_wheel_artifact_builds_successfully(self):
        # 验证 wheel 可正常构建且为有效 zip
```

设计要点：
- 使用 `pip wheel --no-deps --no-cache-dir` 构建到临时目录
- 通过 `zipfile.ZipFile` 检查产物内容
- `finally` 块清理临时构建目录
- 120s timeout 防止构建挂起
- 不读取任何 secret 内容
- 构建产物不加入 git

### P2. GraphPage 4-Type Selector

**`web/src/pages/GraphPage.tsx`** — 三处修改：

1. 拆分 `EXPLORABLE_TYPES` → `SUPPORTED_TYPES` (4) + `UNSUPPORTED_TYPES` (数组, 4)
2. Selector 仅渲染 `SUPPORTED_TYPES.map()` 按钮
3. 新增 lab/internal note 区域说明 unsupported 类型状态
4. 空状态文案更新为诚实的 "当前支持 4 种"

### P3. SensemakingPage LAB/INTERNAL Banner

**`web/src/pages/SensemakingPage.tsx`** — 四处修改：

1. 页面顶部新增橙色 warning banner（LAB / INTERNAL + heuristics 限制列表）
2. 标题旁新增 LAB badge
3. 空状态文案改为 LAB 语言
4. 详细列出 BridgeNode / CardEvolution / SourceInfluence / Evidence Trail 的 heuristics 限制

### P4. Docs Truth Reset

三份旧文档的追记 + 一份新索引：

| 文件 | 操作 | 说明 |
|------|------|------|
| `docs/adr/2026-05-25-007-graph-backend-decision.md` | 追记 | 8 NodeType workload 声明修正为 4 |
| `docs/adr/2026-05-25-006-graph-ontology-v1.md` | 追记 | ontology 定义 vs 实现状态澄清 |
| `docs/plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md` | 追记 | historical planning artifact 标记 |
| `docs/dev/docs-reset-index.md` | NEW | 文档索引：canonical / superseded / lab-internal / archive-candidates |

### Product Copy Tests

**`tests/test_web_product_copy.py`** — 新增 7 个 v4.2.1 regression guard tests：

- `test_graph_page_selector_only_shows_supported_node_types`
- `test_graph_page_unsupported_types_not_selectable`
- `test_graph_page_has_lab_internal_note`
- `test_sensemaking_page_has_lab_internal_banner`
- `test_sensemaking_page_has_lab_badge`
- `test_sensemaking_page_disclaims_heuristic_limits`
- `test_sensemaking_page_empty_state_is_lab_language`
- `test_graph_page_empty_state_is_truthful`

### Quality Debt Ledger

**`docs/dev/quality-debt-ledger.md`** — P1-01/P1-02/P2-01/P2-02 (re-audit) 移至 Resolved Debt。

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `tests/test_package_safety.py` | MODIFIED | 新增 TestWheelArtifactSafety 类 (2 tests) |
| `web/src/pages/GraphPage.tsx` | MODIFIED | SUPPORTED_TYPES/UNSUPPORTED_TYPES split + lab note |
| `web/src/pages/SensemakingPage.tsx` | MODIFIED | LAB/INTERNAL warning banner + badge + copy reset |
| `tests/test_web_product_copy.py` | MODIFIED | 新增 8 个 v4.2.1 regression guard tests |
| `docs/adr/2026-05-25-007-graph-backend-decision.md` | MODIFIED | v4.2 truth reset 追记 |
| `docs/adr/2026-05-25-006-graph-ontology-v1.md` | MODIFIED | v4.2 truth reset 追记 |
| `docs/plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md` | MODIFIED | v4.2 truth reset 追记 |
| `docs/dev/quality-debt-ledger.md` | MODIFIED | P1/P2 re-audit findings → Resolved |
| `docs/dev/docs-reset-index.md` | NEW | 文档索引 |
| `docs/implementation-notes/2026-05-25-088-v4_2_1-partial-remediation-closure.md` | NEW | 本笔记 |

---

## Gate 结果

| Gate | 命令 | Timeout | Exit Code | 备注 |
|------|------|---------|-----------|------|
| git diff --check | `git diff --check` | no | 0 | clean |
| ruff check | `ruff check src/ tests/ docs/` | no | 0 | — |
| package safety | `python -m pytest tests/test_package_safety.py -q --tb=short` | no | 0 | — |
| graph focused | `python -m pytest tests/relations/test_graph_builder.py tests/relations/test_graph_api.py tests/test_sensemaking.py -q --tb=short` | no | 0 | — |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | no | 0 | — |
| npm build | `npm --prefix web run build` | no | 0 | — |
| full pytest | `python -m pytest tests/ -q --tb=short` | no | 0 | — |

---

## 安全性审计

- [x] 不读取 `src/mindforge/assets/.mindforge/secrets.json` 内容
- [x] wheel 测试仅检查文件路径列表，不读取内容
- [x] 不调用 LLM / embedding / vector DB
- [x] 不处理真实私人资料
- [x] 不写真实 Obsidian vault
- [x] 不破坏 explicit approval / human_approved 语义
- [x] 不引入新依赖
- [x] 不新增功能
- [x] 不恢复 Graph / Sensemaking / Entity / Community 扩张

---

## Product Main Path Dogfood Unblocked?

**Yes.** 四项 PARTIAL findings 已全部闭合：
- Package secret risk: artifact-level wheel test ✅
- Graph NodeType truth reset: UI selector 4-type + lab note ✅
- Sensemaking downgrade: LAB/INTERNAL banner + badge ✅
- Docs truth reset: supersession notes + reset index ✅

## What Still Must NOT Be Done Next

- 不启动 v4.3
- 不恢复 Graph / Sensemaking / Entity / Community 扩张
- 不补齐 8 类型大实现
- 不做新图谱能力
- 不做 RAG / embedding / vector DB
- 不调用真实 LLM / Cubox / Upstage
