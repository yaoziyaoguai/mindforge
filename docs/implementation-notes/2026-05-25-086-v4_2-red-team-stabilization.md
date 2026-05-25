# v4.2 Red Team Stabilization — Implementation Notes

**日期**: 2026-05-25
**状态**: complete
**基于**: 红队审计结论 (Overall 5.1/10, No-Go for feature expansion, Stop feature expansion and stabilize)

---

## 审计结论

- Overall score: 5.1/10
- Verdict: No-Go for feature expansion / public claims
- Final recommendation: Stop feature expansion and stabilize
- 用户接受审计结论

---

## 实现范围

按照红队审计发现的 P1/P2 问题执行稳定化，不新增功能。

### A1. 修复 Package Secret Risk (P1)

**问题**: `pyproject.toml` 中 `include = ["src/mindforge/assets/**"]` 会将 `src/mindforge/assets/.mindforge/secrets.json` 打包进 wheel。

**修复**:
- `pyproject.toml`: 新增 `exclude = ["src/mindforge/assets/.mindforge/**"]`，移除冗余 `artifacts`
- `tests/test_package_safety.py`: 新增 5 个 package safety 测试
  - `.gitignore` 阻塞 `.mindforge/` 模式验证
  - `.gitignore` 阻塞 `.env` 验证
  - `pyproject.toml` exclude 规则验证
  - git-tracked files 无敏感文件验证
  - `assets/**` include 伴随 exclude 验证

**安全声明**: 未读取 `secrets.json` 内容（39 bytes），只修复 packaging risk。

### A2. 收缩 Graph 暴露范围 (P1)

**问题**: Graph API/UI/docs 声称支持 8 种 NodeType，但 `DeterministicGraphBuilder` 只实现 card/source/tag/wiki_section。community/topic/entity/concept_candidate 返回空图或 None。

**修复**:
- `graph_models.py`: NodeType docstring 更新，明确当前支持 4 种 vs ontology 定义 8 种
- `graph.py` router: `/api/graph/explore` 新增 `_UNSUPPORTED_EXPLORE_TYPES` 检查，传入 community/topic/entity/concept_candidate 返回 422
- `web_facade.py`: `get_graph_explore` 新增 `_SUPPORTED_GRAPH_NODE_TYPES` 集合和 unsupported type 检查
- `test_graph_builder.py`: 替换 `test_get_node_concept_candidate_returns_none`（将缺失实现当作预期）为 `test_get_node_unsupported_types_return_none`（明确标记为 backend 限制）和 `test_get_graph_unsupported_types_return_empty`
- `test_graph_api.py`: 新增 `test_explore_unsupported_type_returns_422`、`TestGraphExposedNodeTypes`（3 tests）

### A3. 降级 Sensemaking (P1)

**问题**: Sensemaking 语义虚胖 — BridgeNode（简单社区交集计数）、CardEvolutionPath（按 card_id 排序）、SourceInfluencePath（简单 BFS）包装为产品能力。

**修复**:
- `sensemaking.py`: 模块 docstring 标记为 LAB/INTERNAL，各类 docstring 明确算法限制
  - BridgeNode: community_count >= 2 即桥接，不涉及 centrality
  - CardEvolutionStep: 按 card_id 排序，不代表真实演化
  - SourceInfluencePath: 简单 BFS，不涉及 causal inference
  - SensemakingAnalysis: 聚合实验性分析，不是产品主路径
- `Sidebar.tsx`: 移除 Graph 和 Sensemaking 主导航项（保留 Library GraphExplorer 入口）
- 路由 `/graph` 和 `/sensemaking` 保留（内部链接仍可用）

### A4. 修复 Gate 假阳性 (P1)

**问题**: 多个 no-op tests 和将缺失实现当作正确的测试。

**修复**:
- `test_sensemaking.py`: 替换 `assert len(result) >= 0` 为真实语义断言
- `test_graph_api.py`: 替换 `assert len(data["direct_matches"]) >= 0` 为类型断言
- `test_graph_builder.py`: 替换 unsupported-type-as-expected 测试
- `test_graph_api.py`: 新增 `TestGraphExposedNodeTypes`（3 tests）验证暴露类型与 backend 对齐
- `test_sensemaking.py`: 新增 `test_module_docstring_marks_lab_internal`、`test_sensemaking_not_production_ready`

### A5. 文档 Truth Reset (P1)

**问题**: README/docs 过度声明 Graph 能力、Web UI 页面列表等。

**修复**:
- `README.md`: 
  - 新增 "Lab / Internal 功能" 章节，列举 Graph/Sensemaking/Entity/GraphRepository/Extension/Dogfood 的状态
  - 更新 Graph 描述为 "4 NodeTypes"
  - 移除重复的 "当前范围与已知限制" 章节
  - 更新 Web UI 表格，移除 Graph/Sensemaking 独立页面，新增 Health/Dogfood
  - 更新安全边界 Graph 行
- `docs/implementation-notes/2026-05-25-085-v4_1-graph-backend-decision.md`: 追记 v4.2 Truth Reset

### B1. Web 主导航收缩 (P2)

**问题**: Graph/Sensemaking 独立主导航暴露了未完成功能。

**修复**:
- `Sidebar.tsx`: 移除 `/graph` 和 `/sensemaking` 导航项及对应 Brain/GitBranch 图标导入
- 保留 Library 页面的 GraphExplorer 组件作为受控入口
- 保留 App.tsx 路由（内部链接和书签仍可用）

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `pyproject.toml` | MODIFIED | 新增 exclude .mindforge/**、移除冗余 artifacts |
| `tests/test_package_safety.py` | NEW | 5 个 package safety 测试 |
| `src/mindforge/relations/graph_models.py` | MODIFIED | NodeType/Graph docstring truth reset |
| `src/mindforge_web/routers/graph.py` | MODIFIED | 新增 unsupported NodeType 422 错误 |
| `src/mindforge_web/services/web_facade.py` | MODIFIED | 新增 _SUPPORTED_GRAPH_NODE_TYPES 检查 |
| `src/mindforge/relations/sensemaking.py` | MODIFIED | 模块和数据类 docstring 标记 LAB/INTERNAL |
| `web/src/components/Sidebar.tsx` | MODIFIED | 移除 Graph/Sensemaking 主导航 |
| `tests/relations/test_graph_builder.py` | MODIFIED | 替换 fake green tests 为 unsupported type 测试 |
| `tests/relations/test_graph_api.py` | MODIFIED | 替换 no-op test、新增 unsupported type 测试 |
| `tests/test_sensemaking.py` | MODIFIED | 替换 no-op test、新增 lab/internal 断言 |
| `README.md` | MODIFIED | 新增 Lab/Internal 章节、Graph 描述修正 |
| `docs/implementation-notes/2026-05-25-085-v4_1-graph-backend-decision.md` | MODIFIED | 追记 v4.2 Truth Reset |

---

## Gate 结果

| Gate | 命令 | Timeout | Exit Code | 备注 |
|------|------|---------|-----------|------|
| ruff check | `ruff check src/ tests/ docs/` | no | 0 | clean |
| pytest focused | `python -m pytest tests/relations/test_graph_builder.py tests/relations/test_graph_api.py tests/test_sensemaking.py tests/test_package_safety.py -q --tb=short` | no | 0 | all passed |
| pytest full | `python -m pytest tests/ -q --tb=short` | no | 0 | ~3200+ passed, 1 skipped (pre-existing) |
| npm build | `npm --prefix web run build` | no | 0 | build succeeded |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | no | 0 | all passed |
| approval boundary | `python -m pytest tests/test_review_approval_boundary.py -q --tb=short` | no | 0 | all passed |
| git diff --check | `git diff --check` | no | 0 | clean |

---

## 安全性审计

- [x] 不读取 `src/mindforge/assets/.mindforge/secrets.json` 内容
- [x] 不调用 LLM / embedding / vector DB
- [x] 不处理真实私人资料
- [x] 不写真实 Obsidian vault
- [x] 不破坏 explicit approval / human_approved 语义
- [x] 不引入新依赖
- [x] 不新增功能
- [x] 不改变核心产品语义

---

## Deferred Items

- B2: web_facade / schemas 最小拆分（围绕 Graph/Sensemaking 小 extraction）— 本轮未做
- B3: 文档归档计划 — 本轮未做
- B3 (v3.6.1): coverage threshold — 待下一轮
- B4 (v3.6.1): frontend smoke tests with vitest/happy-dom — 待下一轮
- B5 (v3.6.1): web_facade.py 分解 — 待单独 spec/plan

---

## 当前 Graph 支持状态

| NodeType | Backend 支持 | API 暴露 | 说明 |
|----------|-------------|---------|------|
| CARD | 已实现 | 已暴露 | `get_node()` / `get_graph()` |
| SOURCE | 已实现 | 已暴露 | `_source_centered_graph()` |
| TAG | 已实现 | 已暴露 | `_tag_centered_graph()` |
| WIKI_SECTION | 已实现 | 已暴露 | `_wiki_section_centered_graph()` |
| COMMUNITY | 未实现 | 422 | ontology 定义，backend 待实现 |
| TOPIC | 未实现 | 422 | ontology 定义，backend 待实现 |
| ENTITY | 未实现 | 422 | ontology 定义，需用户确认流程 |
| CONCEPT_CANDIDATE | 未实现 | 422 | candidate graph，需用户确认 |
