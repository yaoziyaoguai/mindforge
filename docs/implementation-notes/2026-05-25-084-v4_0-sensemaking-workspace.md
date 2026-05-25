# v4.0 Graph-backed Sensemaking Workspace — Implementation Notes

**日期**: 2026-05-25
**状态**: complete
**基于**: [v3.7-v4.1 Graph View Roadmap](../plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md)

---

## 实现范围

v4.0 在 v3.9 entity resolution 之上构建了 Graph-backed Sensemaking Workspace。

### 1. Sensemaking Analysis Backend

**`src/mindforge/relations/sensemaking.py`** — 确定性知识理解分析引擎：

- **Bridge Node Detection** (`detect_bridge_nodes`): 识别连接 2+ 社区的关键卡片
- **Orphan Island Detection** (`detect_orphan_islands`): 识别无共享关系或仅在小群组内连接的孤立卡片
- **Evidence Trail** (`build_evidence_trail`): 构建两卡片间关系的完整溯源链
- **Source Influence Path** (`build_source_influence_path`): 追踪源文档的影响传播
- **Card Evolution Path** (`build_card_evolution_path`): 展示同源卡片的知识演化
- **Community Subgraphs** (`build_community_subgraphs`): 按社区聚类卡片
- **Comprehensive Analysis** (`analyze_sensemaking`): 聚合上述所有维度的综合分析

数据模型（全部 frozen dataclass）:
- `BridgeNode`, `OrphanIsland`, `EvidenceTrail`, `EvidenceTrailItem`
- `SourceInfluencePath`, `CardEvolutionPath`, `CardEvolutionStep`
- `CommunitySubgraph`, `SensemakingAnalysis`

### 2. Sensemaking API Endpoint

**`GET /api/graph/sensemaking?ref=<card_id>`**

返回综合 sensemaking 分析，包含：
- bridge_nodes, orphan_islands, evidence_trails
- source_influence, card_evolution
- community_subgraphs
- total_cards_analyzed

### 3. SensemakingPage 前端

**`web/src/pages/SensemakingPage.tsx`** — 知识理解工作台页面：

支持 6 种视图模式：
1. **Bridge Nodes** (🌉): 桥接节点列表，展示连接多个社区的卡片
2. **Orphan Islands** (🏝️): 完全孤立的卡片和孤立群组
3. **Evidence Trail** (🔍): 关系溯源链，带右侧详情面板
4. **Source Influence** (🌐): 源文档→直接派生→间接影响
5. **Card Evolution** (🌱): 同源卡片按步骤展示
6. **Community Subgraphs** (👥): 社区聚合视图

交互特性：
- 支持 `?card=xxx` URL 参数自动加载
- 桥接和孤岛卡片可点击重新分析
- Evidence trail 支持选中查看详情面板
- 视图切换保持分析结果

---

## 确定性保证

- 所有分析基于纯集合运算 + 图遍历，不使用 LLM / embedding / vector DB
- `analyze_sensemaking` 是纯函数，不修改输入数据
- 所有 data class 为 frozen
- Graph edge evidence 均为人类可读的确定性文本
- 不自动生成结论或建议

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/mindforge/relations/sensemaking.py` | NEW | Sensemaking 分析引擎 |
| `src/mindforge_web/schemas.py` | MODIFIED | 新增 sensemaking response schemas |
| `src/mindforge_web/services/web_facade.py` | MODIFIED | 新增 get_sensemaking 方法 |
| `src/mindforge_web/routers/graph.py` | MODIFIED | 新增 /api/graph/sensemaking 端点 |
| `web/src/api/types.ts` | MODIFIED | 新增 sensemaking TypeScript 类型 |
| `web/src/api/graph.ts` | MODIFIED | 新增 fetchSensemaking API 函数 |
| `web/src/lib/i18n.ts` | MODIFIED | 新增 sensemaking + nav i18n keys（中英双语） |
| `web/src/pages/SensemakingPage.tsx` | NEW | Sensemaking 工作台页面（6 种视图模式） |
| `web/src/App.tsx` | MODIFIED | 新增 /sensemaking 路由 |
| `web/src/components/Sidebar.tsx` | MODIFIED | 新增知识理解导航项（Brain 图标） |
| `tests/test_sensemaking.py` | NEW | 26 sensemaking contract tests |

---

## Gate 结果

| Gate | 命令 | Timeout | Exit Code | 备注 |
|------|------|---------|-----------|------|
| ruff check | `ruff check src/ tests/ docs/` | no | 0 | clean |
| pytest full | `python -m pytest tests/ -q --tb=short` | no | 0 | ~3122 tests passed |
| npm build | `npm --prefix web run build` | no | 0 | build succeeded (tsc + vite) |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | no | 0 | all passed |

---

## 安全性审计

- [x] 不调用 LLM / embedding / vector DB
- [x] 不读取 .env 或 secrets
- [x] 不处理真实私人资料
- [x] 不写真实 Obsidian vault
- [x] 不破坏 explicit approval / human_approved 语义
- [x] SensemakingAnalysis 不自动升级 ConceptCandidate
- [x] 所有分析结果来自确定性图数据
- [x] 纯集合运算 + 图遍历，无外部依赖

---

## 下一步

v4.1 Local Graph Backend Decision:
- 基于 v3.7-v4.0 workload 评估是否需要图数据库
- GraphBackendPort ABC + GraphRepository 设计
- ADR-007: 什么时候需要 embedded graph database
- 对比方案: in-memory vs SQLite-backed vs Kuzu spike
