# Documentation Debt Ledger

**日期**: 2026-05-26
**状态**: active
**说明**: 追踪 MindForge 文档系统的已知债项、superseded 状态和补救计划。

---

## 文档债策略

基于 v4.6 Documentation System Simplification 确立的 index-first, no-moves 策略：

1. **不移动文件** — 避免链接大面积断裂
2. **不删除历史证据** — audits / implementation notes / ADR 作为项目演化证据保留
3. **不改写历史** — 旧文档可标记 superseded/lab/internal，不修改原始内容到失真
4. **索引先行** — 通过 `docs/README.md` 和 `docs/dev/documentation-inventory.md` 帮助读者导航
5. **状态标记** — 高风险旧文档顶部添加 non-destructive status note

---

## Superseded 文档追踪

以下文档已被标记为 superseded，表示其内容不代表当前产品能力：

### Graph/Sensemaking 相关（已标记）

| 文件 | 原声明 | 修正后状态 | 标记日期 |
|------|--------|-----------|---------|
| `docs/adr/2026-05-25-007-graph-backend-decision.md` | 8 NodeType workload 已验证 | 仅 4 NodeType 已实现 | v4.2 truth reset |
| `docs/adr/2026-05-25-006-graph-ontology-v1.md` | 8 NodeType ontology | ontology 定义有效，仅 4 种已实现 | v4.2 truth reset |
| `docs/plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md` | Graph/Sensemaking 全能力路线 | 已降级为 lab/internal, historical | v4.2 truth reset |
| `docs/implementation-notes/2026-05-25-085-v4_1-graph-backend-decision.md` | 8 NodeType | 仅 4 正式支持，GraphRepository internal-only | v4.6 |
| `docs/implementation-notes/2026-05-25-081-v3_7-graph-ontology.md` | 8 NodeType 定义 | 仅 4 正式支持 | v4.6 |
| `docs/implementation-notes/2026-05-25-083-v3_9-entity-resolution.md` | Entity Resolution 能力描述 | 仅 ConceptCandidate 检测，lab/internal | v4.6 |
| `docs/implementation-notes/2026-05-25-075-v3_3-community-topic-sensemaking.md` | Community/Topic/Sensemaking 能力 | lab/internal，非主产品路径 | v4.6 |
| `docs/implementation-notes/2026-05-24-045-v1_2-u3-knowledge-community.md` | Knowledge Community 描述 | lab/internal，已收缩 | v4.6 |
| `docs/implementation-notes/2026-05-25-049-v1_4-w2-knowledge-community-browser.md` | Community Browser 描述 | lab/internal，已收缩 | v4.6 |

### 已有 truth reset 注释（无需额外标记）

| 文件 | 已有注释 | 标记日期 |
|------|---------|---------|
| `docs/implementation-notes/2026-05-25-082-v3_8-graph-view-mvp.md` | v4.2 truth reset: 8→4 NodeType | v4.2 |
| `docs/implementation-notes/2026-05-25-084-v4_0-sensemaking-workspace.md` | v4.2 truth reset: lab/internal | v4.2 |

---

## Historical/Archive Candidate 文档

以下文档目录中的文件属于历史记录，不代表当前产品承诺：

| 目录 | 文件数 | 状态 | 处理建议 |
|------|--------|------|---------|
| `docs/specs/` | 19 | historical | 全部为历史规格，实现可能已偏离 |
| `docs/design/rfc/` | 4 | historical | 设计阶段 RFC |
| `docs/design/sdd/` | 4 | historical | 设计产物，不代表当前实现 |
| `docs/design/roadmap/` | 2 | historical | v0.2/v0.3 早期路线 |
| `docs/design/tdd/` | 1 | historical | 早期 TDD 文档 |
| `docs/plans/` (14 early plans) | 14 | historical | 早期计划，已被后续路线图取代 |
| `docs/implementation-notes/` (2026-05-24 及之前) | ~50 | historical | 早期执行记录 |

---

## 开放文档债

| ID | Priority | Description | Status | Target |
|----|----------|-------------|--------|--------|
| DOC-01 | P3 | 无英文 docs/README.md 翻译 | resolved (v3.7): docs/README-en.md 已创建，完整英文翻译 | — |
| DOC-02 | P3 | 部分旧 ADR 缺少 "当前状态" 更新 | resolved (v3.7): ADR-006 frontmatter status 从 active 更新为 partial (4/8 NodeType implemented) | — |
| DOC-03 | P3 | `docs/design/` 下较多设计文档未与当前实现对齐 | resolved (v3.7): docs/design/README.md 新增 historical/reference 状态说明，obsidian-binding-design.md 标记为 deferred | — |
| DOC-04 | P3 | 无文件级归档机制（`docs/archive/` 目录） | deferred | 单独 spec |

---

## 已解决文档债

| ID | Priority | Description | Resolution | 日期 |
|----|----------|-------------|------------|------|
| DOC-R1 | P1 | architecture.md 引用不存在的 import_service.py/export_service.py | 修正为 web_facade.py + routers/library.py | v3.6.1 |
| DOC-R2 | P1 | zh-CN user-guide 未同步 v2.5+ 能力 | B1: 同步更新 Import/Export/Dogfood/Provider/Lifecycle/Community/Topic/Graph/Retrieval/Workbench | v3.6.1 |
| DOC-R3 | P2 | 缺少 canonical docs 入口页面 | v4.6: 创建 docs/README.md | v4.6 |
| DOC-R4 | P2 | 缺少文档清单和分类 | v4.6: 创建 docs/dev/documentation-inventory.md | v4.6 |
| DOC-R5 | P2 | Graph/Sensemaking/Community 旧文档缺少 superseded 标记 | v4.6: 11 个文件添加 status note | v4.6 |

---

## 下一步

1. 创建 `docs/archive/` 目录并迁移 archive candidates（需单独 spec）
2. 更新 `docs/adr/` 中较旧 ADR 的 "当前状态" 部分
3. 编写 docs/README.md 英文版
4. 清理 `docs/design/` 中过时的设计文档
