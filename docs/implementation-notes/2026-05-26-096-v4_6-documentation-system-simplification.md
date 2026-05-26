# v4.6 Documentation System Simplification — Implementation Notes

**日期**: 2026-05-26
**输入**: v4.6 Documentation/System Simplification
**状态**: completed

---

## 执行摘要

v4.6 在不移动文件、不删除历史证据、不改写历史内容的前提下，引入 index-first 文档分层策略，让 ~130+ 文档可导航、可分类、可信任。

### Commits

| Loop | Commit | Description |
|------|--------|-------------|
| L1-L3 | `243bca3` | docs: v4.6 canonical docs index + inventory + superseded notes |

---

## 策略

**Index-first, no-moves**:
- 不移动任何文件到 `archive/` 目录
- 不删除任何文件
- 不修改任何文件的 frontmatter/content（superseded notes 除外）
- 不改写历史内容
- 通过 `docs/README.md` 和 `docs/dev/documentation-inventory.md` 建立导航/分类层

---

## Loop 1: Canonical Docs Index

### `docs/README.md`

新建文档入口页面，替代隐式导航，包含：

1. **Start Here** — 7 个推荐阅读文档按顺序排列（README → user guides → architecture → quality ledger → capability map → roadmap）
2. **Current Canonical Docs** — 5 组：
   - 用户文档（15 个中英文文档）
   - 开发者文档（10 个）
   - 当前能力与限制文档（4 个）
   - 当前路线图与规划文档（4 个）
   - 审计文档（3 个）
   - 实现笔记（5 个最新）
3. **Historical / Superseded Docs** — 说明哪些目录/docs 是历史/已替代
4. **Lab / Internal Feature Notice** — 表格列出 6 个 lab/internal 功能
5. **文档策略** — 不移动、不删除、不改写历史的承诺

### 设计决策
- 作为可信 canonical 入口，不假装不存在的东西
- 明确主路径 vs lab/internal 边界
- 链接到 docs-reset-index.md 获取 superseded doc 详情

---

## Loop 2: Documentation Inventory

### `docs/dev/documentation-inventory.md`

完整文档清单，分类 ~130+ 文件：

| 分类 | 内容 |
|------|------|
| 目录分类表 | 15 行，覆盖所有 14 个文档目录 + 根级 md 文件 |
| Archive Candidates | 14 early plans, 17 specs, ~50 early impl notes, 4 early design docs, 2 early internal docs |
| Superseded Candidates | 4 个已标记 superseded + 7 个额外需要状态注释的文件 |
| Lab/Internal 列表 | 8 个描述 lab/internal 功能的文档 |

### 设计决策
- 分类粒度：canonical / active / historical / superseded / lab / internal
- 明确本轮不移动任何文件
- 建议未来单独 spec 处理文件级归档

---

## Loop 3: Superseded Notes

在 4 个高风险文档顶部添加状态注释：

| 文件 | 修正内容 |
|------|---------|
| `2026-05-25-081-v3_7-graph-ontology.md` | 8 NodeType → 4 正式支持 |
| `2026-05-25-083-v3_9-entity-resolution.md` | Entity Resolution → 仅 ConceptCandidate 检测 |
| `2026-05-25-085-v4_1-graph-backend-decision.md` | GraphRepository/GraphBackendPort → internal-only |
| `2026-05-25-075-v3_3-community-topic-sensemaking.md` | Community/Topic/Sensemaking → lab/internal |

2 个文件已有足够的 v4.2 truth reset 注释，无需额外修改：
- `2026-05-25-082-v3_8-graph-view-mvp.md`（已有 8→4 NodeType 注释）
- `2026-05-25-084-v4_0-sensemaking-workspace.md`（已有 lab/internal 注释）

---

## 未做事项

以下属于 v4.6 范围但未在本轮执行：

- 文件级归档（`docs/archive/` 目录创建和文件移动）
- 旧文档内容改写或删除
- 新 canonical docs 编写（需要时单独 spec）
- 英文 docs/README.md 翻译

原因：本轮策略是 index-first, no-moves。文件归档需要单独 spec 和 review。

---

## Gate Results

| Gate | Command | Exit Code | Notes |
|------|---------|-----------|-------|
| git diff | `git diff --check` | 0 | Clean |
| ruff (docs/) | `ruff check docs/` | 0 | No Python files in docs/ |

---

## 硬红线遵守

- 未移动或删除任何文件
- 未修改历史内容（仅添加 non-destructive status notes）
- 未读取 `.env` 或 secrets
- 未调用真实 LLM、Cubox、Upstage 或外部服务
- 未处理真实私人资料
- 未写真实 Obsidian vault
- 未做 RAG/embedding/vector DB
- 未新增大型依赖
- 未破坏 explicit approval / human_approved 语义
- 未恢复 Graph/Sensemaking/Entity/Community 扩张

---

## 下一步建议

1. **v4.5 Recall/Search Quality Lab** — 建立 recall fixtures、query explain report、BM25 tuning
2. **v4.7 Architecture Contraction** — web_facade.py/schemas.py 分解（需单独 spec）
3. **File-level archival** — 创建 `docs/archive/` 并移动已分类的 archive candidates
