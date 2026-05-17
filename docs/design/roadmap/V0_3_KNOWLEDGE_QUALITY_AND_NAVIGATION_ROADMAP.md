# MindForge v0.3 Roadmap: Knowledge Quality & Navigation

> **Status**: Draft
> **Branch**: feat-wiki-llm-synthesis
> **Date**: 2026-05-17
>
> v0.3 不做新 ingestion format、不做 Vector DB、不做 Embedding、不做 Graph DB。
> v0.3 唯一主题：让已生成的知识更高质量、更高可追溯性、更高可维护性。

---

## TL;DR for Coding Agents

1. **Read** `docs/internal/V0_3_DEVELOPMENT_RULES.md` first。
2. **Implement M1 only** — 不跳步，不提前做 M2-M6。
3. **所有 quality metadata 是只读附属于 ai_draft / human_approved** — 不自动修改卡片 body/status。
4. **不引入新依赖** — 无 Vector DB、无 Graph DB、无 embedding 库。
5. **Provenance 增强向后兼容 v0.2**。
6. **Local graph 只用已有确定性关系，不做语义相似度**。
7. **Every commit** 必须引用对应 RFC/SDD section。

---

## 1. 背景

v0.2 完成时 MindForge 已具备：

- 多格式 source ingestion (Markdown / TXT / HTML / PDF / DOCX)
- AI draft → explicit approve → human_approved 审批链路
- Library (仅 human_approved) / Recall (BM25) / Wiki (LLM synthesis)
- Wiki stale indicator / references clickable / card provenance actions
- 完整用户文档和 dogfood 验证

当前缺陷：

1. **卡片质量不透明**：用户不知道哪张卡片质量高/低，为什么。
2. **Wiki 综合质量不透明**：哪些 approved cards 进入 Wiki，哪些没进入，无法追溯。
3. **卡片之间无关系浏览**：Library 卡片列表是线性列表，没有 "related cards" 探索。
4. **Source provenance 精度不足**：卡片引用 source 只有 path，不知道来自 source 的哪个段落/行。
5. **无知识健康感知**：用户不知道库中有重复、过期、孤立卡片的维护问题。
6. **无 local graph 浏览**：关系存在于数据中但不可视化。

---

## 2. Why No Vector DB / Embedding / Graph DB in v0.3

| 技术 | Why NOT in v0.3 |
|------|----------------|
| Vector DB / Embedding | 增加部署复杂度、依赖外部 API 或大模型本地推理、维护成本高。v0.3 用确定性规则和 BM25 就足够了。 |
| Graph DB (Neo4j 等) | 引入新的持久化层、schema migration、运维负担。v0.3 的图是 in-memory deterministic graph，不需要 graph DB。 |
| GraphRAG | 依赖 embedding + graph DB，不在 v0.3 范围内。 |

Future extension: 如果 v0.4 或 v0.5 需要 semantic search / embedding-based dedup，可以在不破坏确定性关系层的前提下接入。

---

## 3. v0.3 总目标

**让 MindForge 知识库从"生成层"升级为"质量层"和"导航层"：**

- 每张卡片有 quality metadata，低质量卡片可建议 regenerate / split / merge
- Wiki 能报告覆盖面、faithfulness、staleness、knowledge gaps
- 卡片 / Source / Wiki section 之间能确定性地发现关系
- 卡片能精确定位到 source 的具体位置
- 用户能收到知识健康体检报告
- 围绕当前卡片/Wiki section 能看到 local graph preview

---

## 4. Six Milestones

### M1 Card Quality

| 维度 | 定义 |
|------|------|
| **Goal** | 每张 ai_draft 生成附带 quality metadata；用户能看到质量评分和 warning |
| **User value** | 审批时知道哪些卡片值得读、哪些需要改进；维护时知道哪些卡片需要 regenerate |
| **Scope** | Card Quality Rubric, Quality Score, Quality Warnings, Card type (fact/claim/decision/method/risk/question/insight), Regeneration Suggestion, Split/Merge/Dedup Candidate |
| **Non-goals** | 不自动 approve、不自动修改 human_approved 内容、不引入 embedding-based quality |
| **Done Criteria** | 1) ai_draft 附带 quality metadata 2) Web Card detail 显示 quality score + warnings 3) 低质量卡有 regenerate/split/merge 建议 4) 质量评分可测试确定 |
| **Test Strategy** | 用 synthetic cards 做 golden quality test — 已知好/坏卡片应该有确定性的 high/low score |
| **Dogfood Scenario** | 生成 5 张质量不等的 ai_draft cards，在 Review 页面验证 quality display，确认 regenerate 建议合理 |
| **Risks** | Quality rubric 过于机械导致误判；用户对 quality score 的期望过高 |
| **Stop Conditions** | quality score 在 golden test 上相关性 < 80%；Web display 造成混淆而非帮助 |

### M2 Wiki Quality

| 维度 | 定义 |
|------|------|
| **Goal** | Wiki rebuild 附带质量报告：用了哪些 cards、没纳入哪些、每个 section 引用回溯、staleness、faithfulness、知识缺口 |
| **User value** | 信任 Wiki 是完整的高质量综合，知道什么被遗漏、什么时候过期 |
| **Scope** | Wiki Quality Report, Coverage Report, Section References, Staleness detection, Faithfulness check, Dedup check, Knowledge Gaps, Conflicting Claims, used_cards / unused_cards |
| **Non-goals** | 不自动 rebuild Wiki、不修改 human_approved、不做 semantic similarity gap detection |
| **Done Criteria** | 1) rebuild 后附带 quality report 2) 报告 used/unused approved cards 3) 每个 section 有 card references 4) new approved cards 标记相关 section/page stale 5) faithful check 可测试 |
| **Test Strategy** | Synthetic fixture: 已知 10 cards → rebuild wiki → 验证 used=8 unused=2，每个 section references 正确 |
| **Dogfood Scenario** | 在已有 dogfood workspace 添加新 approved card，验证 stale indicator 标记相关 section |
| **Risks** | Faithfulness check 过度标记误报（LLM 改写语义相同但字面不同）；coverage 计算过于机械 |
| **Stop Conditions** | Faithfulness check 假阳性率 > 30%；Wiki rebuild 速度退化 > 2x |

### M3 Related Cards

| 维度 | 定义 |
|------|------|
| **Goal** | 每张卡片能看到 deterministic related cards（同 source / 同 tag / 同 Wiki section 等），不用 vector/embedding |
| **User value** | 读一张卡片时发现相关知识，不迷路 |
| **Scope** | RelatedCardReason, RelatedCardEdge, related cards API, card detail related panel, 6 种确定性关系类型 |
| **Non-goals** | 不做 semantic similarity、不做 embedding、不显示 ai_draft/pending/rejected（除非 Review context）、不做自动 link creation |
| **Done Criteria** | 1) card detail 有 related cards panel 2) 每个 related card 带 reason 3) Library context 只显示 human_approved 4) 关系确定可测试 |
| **Test Strategy** | Golden fixtures: 已知 5 cards 共享 3 个同一 source → 验证 related cards 正确数量 + reason |
| **Dogfood Scenario** | 在已有 dogfood workspace 打开 card detail，验证 related cards panel 显示同 source / 同 tag cards |
| **Risks** | 关系类型太少显得空；太多显得噪音；性能随卡片数量退化 |
| **Stop Conditions** | Related cards 计算时间 > 500ms for 1000 cards；假阳性关系 > 10% |

### M4 Source Location / Provenance

| 维度 | 定义 |
|------|------|
| **Goal** | 卡片能精确定位到 source 的 heading / line / page / paragraph |
| **Source** | 对每个 source_type 定义 location format：Markdown heading + line range, TXT line range, HTML heading/selector-safe anchor, PDF page number, DOCX paragraph range |
| **Non-goals** | 不做 OCR、不做 URL crawling、不做 block-level positioning (v0.4)、不执行文件内容 |
| **Done Criteria** | 1) 每种 source_type 的 location 格式定义清晰 2) card detail 显示 source location 3) provenance_blocks v2 支持 location 4) copy/reveal 仍走安全 allowlist 5) synthetic fixtures 覆盖各 source type |
| **Test Strategy** | 每种 source_type 的 synthetic fixture + golden location output |
| **Dogfood Scenario** | 打开来自 Markdown/TXT/HTML/PDF/DOCX 的 card，验证不同 source_type location display 正确 |
| **Risks** | PDF/DOCX location 精度因 library 能力受限；HTML selector 跨文档版本不稳定 |
| **Stop Conditions** | 任何 source_type 的 location 计算确定性不足；location 显示泄露不安全路径 |

### M5 Knowledge Health

| 维度 | 定义 |
|------|------|
| **Goal** | 用户能看到知识库维护健康报告 |
| **User value** | 知道哪些卡片需要关注，类似系统体检 |
| **Scope** | Knowledge Health Report: review backlog, pending drafts, missing provenance, duplicate candidates, orphan cards (无 related cards / 无 wiki reference), Wiki stale sections, sources with extraction warnings, unsupported source attempts, low quality card count, maintenance suggestions |
| **Non-goals** | 不自动删除/修改卡片、不自动 approve/reject、不自动 rebuild wiki |
| **Done Criteria** | 1) CLI `mindforge health` 输出报告 2) Web Health 页面或 status 区域 3) 每个 issue 有 severity/reason/suggested_action 4) 不自动 mutation |
| **Test Strategy** | Synthetic vault with known issues → verify health report lists correct issues with correct severity |
| **Dogfood Scenario** | 在 dogfood workspace 运行 health，验证报告列出已知问题及建议 action |
| **Risks** | Severity 启发式规则过于保守或过于激进；suggested action 表达不清 |
| **Stop Conditions** | Health report 包含假阳性 > 20%；suggested action 可能引导用户做危险操作 |

### M6 Local Graph Preview

| 维度 | 定义 |
|------|------|
| **Goal** | 围绕当前 card/Wiki section 展示确定性 local graph |
| **Scope** | Card-centered graph (1-hop neighbors), Wiki section-centered graph, deterministic edges (from_source, referenced_by_wiki_section, shares_tag, same_source, same_review_batch, source_location_neighbor, manual_link reserved), nodes: card / source / wiki section / tag, clickable nodes to navigate |
| **Non-goals** | 不做全局大图、不做 semantic similarity、不做 graph DB、不做 force-directed 毛线球、不做 real-time graph computation |
| **Done Criteria** | 1) card detail 有 local graph preview 2) wiki section 有 local graph preview 3) 节点可点击跳转 4) 图谱数据 deterministic 5) 不需要 embedding / vector DB / graph DB |
| **Test Strategy** | Golden graph fixtures → verify nodes and edges for known card context |
| **Dogfood Scenario** | 在已有 dogfood workspace 打开 card detail，查看 local graph preview 正确显示同 source cards + 同 wiki section cards |
| **Risks** | UI 复杂度超出时间预算；graph 渲染性能问题 |
| **Stop Conditions** | Graph UI 实现耗时 > M6 总预算 50%；graph 计算 > 1s for 100 total nodes |

---

## 5. 推荐执行顺序

```
M1 Card Quality → M4 Source Location → M2 Wiki Quality → M3 Related Cards → M5 Knowledge Health → M6 Local Graph Preview
```

理由：
- **M1** 先做：所有后续 milestone 依赖 quality metadata
- **M4** 第二：Location 是 M2 provenance references 和 M6 graph edges 的基础
- **M2** 第三：Wiki quality 需要 M4 location 做 section references
- **M3** 第四：Related cards 需要 M1 quality score（用于关系排序）
- **M5** 第五：Health 汇总 M1-M4 的所有信号
- **M6** 第六：Graph 消费 M1-M5 的所有边和节点数据

---

## 6. One-shot Loop vs Milestone Loop

**推荐按 milestone loop（6 个独立 loop）**，理由：

- M1-M6 覆盖 6 个不同模块，同时实现容易耦合
- 每个 milestone 可以独立测试、独立 dogfood、独立 merge
- 失败时回滚范围小
- 上下文允许时可在同一 session 内连续完成多个 milestone loop

**不建议 one-shot M1-M6**：
- 跨度过大，debug 困难
- 7 个模块同时改动容易引入 cross-cutting bug
- 但 M1+M4 可以合并为一个 loop（因为它们共享 provenance 基础）

---

## 7. Release Criteria

v0.3 发布条件：

1. M1-M6 所有 done criteria 达标
2. 不破坏 v0.2 Source / Wiki / Library / Recall / Approval 行为
3. 新功能有 ≥ 80% 测试覆盖
4. 每个 milestone dogfood 通过
5. ruff clean + tsc clean
6. CI green
7. 用户文档更新（中文 + 英文）

---

## 8. Open Questions

1. Quality score 是 0-100 数值还是 categorical (high/medium/low)？建议先 categorical 再数值。
2. Local graph 是否需要画布（canvas）还是 list view 足够？建议先 list view + mini graph，后续再 canvas。
3. Knowledge health report 是否需要持久化（如保存上一次 health snapshot 做对比）？
4. Card type classification 是 AI 推断还是规则推断？建议先规则分类（如 title/body 中的关键词），可选 AI enhancement。
5. Conflicting claims detection 是 LLM-based 还是规则？建议只在 M2 做简单的规则冲突检测（如 claim A 和 claim B 关键词矛盾），深度冲突检测留到 v0.4。
