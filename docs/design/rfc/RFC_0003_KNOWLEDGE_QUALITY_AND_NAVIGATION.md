# RFC 0003: Knowledge Quality & Navigation

> **Status**: Draft
> **Date**: 2026-05-17
> **Author**: MindForge Team
> **Related**: [V0_3_ROADMAP.md](../roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md), [SDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md](../sdd/SDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)

---

## Abstract

v0.2 完成了知识的"生成层"：多格式 source ingestion、AI draft → human_approved 审批链路、Library/Recall/Wiki 三个知识消费通道。但知识本身缺乏质量评估、追踪精度和导航能力。

v0.3 不对 ingestion 或 AI pipeline 做任何扩展，而是专注于"质量层"和"导航层"：每张卡片有 quality metadata，Wiki 有 coverage/faithfulness 报告，卡片之间能确定性地发现关系，卡片精确定位到 source 的具体位置，知识库整体有健康体检报告，局部图谱可浏览。

---

## 1. Context

### 1.1 Current State (v0.2)

v0.2 已完成的能力：

- **Source Ingestion**: 5 种格式 (Markdown/TXT/HTML/PDF/DOCX)，source adapter 注册表
- **AI Pipeline**: ai_draft → explicit approve → human_approved，卡片生命周期管理
- **Library**: 仅 human_approved 卡片列表，线性展示
- **Recall**: BM25 关键词搜索
- **Wiki**: LLM synthesis，stale indicator，references clickable，card provenance actions
- **Web UI**: CardWorkspace detail，WikiPage structured view，WikiReferenceCard 导航

### 1.2 Known Pain Points

1. **卡片质量不透明**：用户不知道哪张卡片质量高/低，为什么
2. **Wiki 综合质量不透明**：哪些 approved cards 进入 Wiki，哪些没进入，无法追溯
3. **卡片之间无关系浏览**：Library 是线性列表，没有 "related cards" 探索
4. **Source provenance 精度不足**：卡片引用 source 只有 path，不知道来自 source 的哪个段落/行
5. **无知识健康感知**：用户不知道库中有重复、过期、孤立卡片的维护问题
6. **无 local graph 浏览**：关系存在于数据中但不可视化

---

## 2. Problem

MindForge v0.2 的知识库是一个"黑盒生成器"：用户扔 source 进去，得到 approved cards 出来，但对知识质量、关系网络、健康状况毫无感知。

核心问题：
- **Quality gap**: 没有质量元数据，用户审批时只能凭主观判断
- **Provenance gap**: 卡片引用只有文件路径，无法精确追溯
- **Navigation gap**: 卡片之间是孤岛，用户只能通过 Recall 搜索关联
- **Health gap**: 知识库维护是盲操作，不知道哪些卡片需要关注

---

## 3. Goals

1. **Card Quality**: 每张 ai_draft 附带 quality metadata（rubric + score + warnings + card type），用户能在审批和维护时获得质量信号
2. **Wiki Quality**: Wiki rebuild 附带 quality report（used/unused cards, section references, staleness, faithfulness, knowledge gaps）
3. **Related Cards**: 每张卡片看到 deterministic related cards（6 种关系类型），不用 vector/embedding
4. **Source Location**: 每种 source_type 的精确位置格式（heading/line/page/paragraph），provenance 从文件级升级到段落级
5. **Knowledge Health**: 知识库维护健康报告（review backlog, duplicates, orphans, stale sections, low quality cards）
6. **Local Graph Preview**: 围绕当前 card/Wiki section 的 1-hop deterministic graph

---

## 4. Non-goals

- **不新增 ingestion format**
- **不引入 Vector DB / Embedding / Graph DB / GraphRAG**
- **不自动 approve / 不自动修改 human_approved**
- **不自动 rebuild Wiki**
- **不自动删除/修改卡片**
- **不做 semantic similarity**（关系发现仅用确定性规则）
- **不做全局大图**（local graph 限于 1-hop neighbors）
- **不做 force-directed canvas 图**（先用 list view + mini graph）
- **不改 knowledge card schema 核心结构**（quality metadata 为只读附属）
- **不新增持久化层**（不引入 Neo4j、Pinecone、Chroma 等）

---

## 5. Stakeholders

| Stakeholder | Interest |
|-------------|----------|
| **知识库维护者** | 了解卡片质量，发现需要 regenerate/split/merge 的卡片 |
| **知识消费者** | 信任 Wiki 的完整性和时效性，发现相关知识 |
| **审批者** | 审批时有 quality score 参考，知道哪些卡片值得细读 |
| **开发者/Agent** | 所有关系确定可测试，不依赖 embedding 黑盒 |

---

## 6. Architecture Decisions

### AD-1: Quality is Deterministic, Not Embedding-based

**Decision**: 所有 quality scoring 使用确定性规则（rubric check + BM25 + 结构化属性），不引入 embedding/semantic similarity。

**Rationale**: v0.3 的目标是建立质量基础层，不是做 AI 质量评估。确定性规则可测试、可解释、可调试。

**Trade-off**: 确定性规则可能不如 LLM-based quality 精细，但为 v0.4 的 semantic quality 提供结构化基础。

### AD-2: Quality Metadata is Read-only Affiliated

**Decision**: quality metadata 附属于 ai_draft / human_approved，不自动修改卡片 body/status。

**Rationale**: 质量评分是建议信号，不是强约束。用户始终保留审批和编辑的最终决定权。

**Trade-off**: 可能存在高质量评分但内容错误（或反之）的情况。需在 UI 中明确 quality score 是参考而非裁决。

### AD-3: Local Graph is In-memory Deterministic

**Decision**: 关系图谱在内存中通过确定性规则构建（JOIN on card fields），不使用 Graph DB。

**Rationale**: v0.3 节点数量在千级别，内存构建足够。引入 Graph DB 增加部署复杂度和 schema migration 负担。

**Trade-off**: 当卡片量过万时性能可能退化，但 v0.3 的使用场景远未达到这个量级。

### AD-4: No Semantic Relationships

**Decision**: Related cards 和 graph edges 仅基于已有的确定性关系（same_source, same_tag, same_wiki_section, same_review_batch, source_location_neighbor），不做 semantic similarity。

**Rationale**: Semantic similarity 需要 embedding，而 embedding 需要 Vector DB 或 in-memory vector index。不在 v0.3 范围。

**Trade-off**: 可能遗漏语义相关但结构无关的卡片对。但 6 种确定性关系已覆盖大部分导航需求。

### AD-5: Location Format per Source Type

**Decision**: 每种 source_type 定义独立的 location 格式（Markdown heading+line, TXT line, HTML selector, PDF page, DOCX paragraph），不做统一抽象。

**Rationale**: 不同格式的定位语义完全不同，强行统一会导致信息丢失或精度下降。

**Trade-off**: 前端需要为每种 source_type 显示不同的 location UI，但差异不大。

---

## 7. Functional Requirements

### FR1: Card Quality

- FR1.1: ai_draft 生成时计算 quality score（0-100 或 categorical high/medium/low）
- FR1.2: quality score 基于 deterministic rubric（completeness, structure, specificity, source_citation, consistency）
- FR1.3: 附带 quality warnings（too_short, missing_sections, no_source_citation, vague_language, possible_duplicate）
- FR1.4: 附带 card type classification（fact, claim, decision, method, risk, question, insight）
- FR1.5: 低质量卡片带 regenerate/split/merge 建议
- FR1.6: Card detail 页显示 quality metadata

### FR2: Wiki Quality

- FR2.1: Wiki rebuild 后生成 quality report
- FR2.2: Report 列出 used_cards 和 unused_cards（含原因）
- FR2.3: 每个 Wiki section 列出引用的 card references
- FR2.4: 新 approved cards 标记相关 section/page stale
- FR2.5: Faithfulness check：验证 section 内容是否忠实反映引用的 cards
- FR2.6: 报告 knowledge gaps（未使用的 approved cards 可能代表覆盖盲区）
- FR2.7: 报告 conflicting claims（同一主题的矛盾声明）

### FR3: Related Cards

- FR3.1: 5 种确定性关系类型：same_source, same_tag, same_wiki_section, same_review_batch, source_location_neighbor。manual_link 为保留字段（reserved for future, v0.3 API 不输出）
- FR3.2: 每张 card 显示 related cards panel
- FR3.3: 每个 related card 显示 relation reason
- FR3.4: Library context 仅显示 human_approved related cards
- FR3.5: Review context 可显示 pending/rejected related drafts

### FR4: Source Location / Provenance

- FR4.1: Markdown: heading path + line range
- FR4.2: TXT: line range
- FR4.3: HTML: heading/selector-safe anchor
- FR4.4: PDF: page number
- FR4.5: DOCX: paragraph range
- FR4.6: provenance_blocks v2 支持 location 字段
- FR4.7: Card detail 显示 source location
- FR4.8: copy/reveal 走安全 allowlist 不变

### FR5: Knowledge Health

- FR5.1: CLI `mindforge health` 输出健康报告
- FR5.2: Web Health 页面或 status 区域
- FR5.3: 检测项：review backlog, pending drafts, missing provenance, duplicates, orphans, Wiki stale sections, extraction warnings, unsupported source attempts, low quality cards
- FR5.4: 每个 issue 有 severity（info/warn/critical）, reason, suggested_action
- FR5.5: 不自动 mutation

### FR6: Local Graph Preview

- FR6.1: Card-centered graph（1-hop neighbors）
- FR6.2: Wiki section-centered graph
- FR6.3: Edges 类型：from_source, referenced_by_wiki_section, shares_tag, same_source, same_review_batch, source_location_neighbor, manual_link（reserved）
- FR6.4: Nodes 类型：card, source, wiki_section, tag
- FR6.5: 节点可点击跳转
- FR6.6: 图谱数据 deterministic（不依赖 embedding/vector/graph DB）

---

## 8. Non-functional Requirements

| Requirement | Target |
|-------------|--------|
| Quality score 在 golden test 上的准确性 | ≥ 80% |
| Faithfulness check 假阳性率 | < 30% |
| Related cards 计算时间（1000 cards） | < 500ms |
| Local graph 计算时间（100 total nodes） | < 1s |
| Wiki rebuild 速度 | 不退化 > 2x vs v0.2 |
| Health report 假阳性率 | < 20% |
| 新功能测试覆盖率 | ≥ 80% |
| 不破坏 v0.2 行为 | Source / Wiki / Library / Recall / Approval 全通过 |

---

## 9. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Quality rubric 过于机械导致误判 | 用户对 score 不信任 | Golden test 验证 80%+ 准确性；UI 标注 score 为参考 |
| Faithfulness check 假阳性过高 | Wiki quality report 噪音大 | M2 stop condition: 假阳性 > 30% 时暂停 |
| Related cards 性能退化 | 1000 cards 时 > 500ms | 索引优化；缓存计算 |
| Local graph UI 复杂度 | 超出 M6 时间预算 50% | 先 list view + mini graph，canvas 留给 future |
| Health report 误报 | 用户忽略或做危险操作 | Severity 分类 + suggested_action 安全审查 |

---

## 10. Open Questions

1. Quality score 是 0-100 数值还是 categorical (high/medium/low)？建议先 categorical 再数值。
2. Local graph 是否需要画布（canvas）还是 list view 足够？建议先 list view + mini graph，后续再 canvas。
3. Knowledge health report 是否需要持久化（如保存上一次 health snapshot 做对比）？
4. Card type classification 是 AI 推断还是规则推断？建议先规则分类（如 title/body 中的关键词），可选 AI enhancement。
5. Conflicting claims detection 是 LLM-based 还是规则？建议只在 M2 做简单的规则冲突检测（claim A 和 claim B 关键词矛盾），深度冲突检测留到 v0.4。

---

## 11. References

- [V0.3 Roadmap](../roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md)
- [V0.2 Development Rules](../../internal/V0_2_DEVELOPMENT_RULES.md)
- [SDD Wiki Web Presentation Addendum](../sdd/SDD_WIKI_WEB_PRESENTATION_ADDENDUM.md)
- [Product Contracts](../../internal/product-contracts.md)
