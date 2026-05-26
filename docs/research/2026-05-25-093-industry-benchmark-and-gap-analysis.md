# MindForge Industry Benchmark and Gap Analysis

**日期**: 2026-05-25
**阶段**: docs/research/planning loop
**性质**: 产品形态对标，不作为实现授权；不引入 RAG/embedding/vector DB/真实 LLM 默认路径。

---

## Benchmark Scope

本对标基于公开常识层面的产品形态分析，不做联网抓取，不读取任何私人资料。目的不是把 MindForge 变成这些产品，而是识别哪些能力值得学习，哪些不应复制。

### A. Obsidian

**核心形态**

- local-first Markdown vault
- backlinks / outgoing links
- graph view
- Canvas / whiteboard
- properties / bases-like structured views
- plugin ecosystem

**强项**

- Markdown 文件就是 source of truth，可迁移、可手工编辑、可长期保存。
- 双链和 graph view 让用户可以从自己的写作中自然形成网络。
- Canvas/whiteboard 适合思考和空间化组织。
- Plugin ecosystem 把长尾工作流交给社区扩展。

**MindForge 应该学习**

- local-first trust model 和可迁移文件格式。
- 清楚的 vault/workspace 概念。
- 可解释的 links/backlinks，而不是黑盒关系。
- “用户拥有数据，工具是派生层”的姿态。

**MindForge 不应复制**

- 不做完整 Markdown 编辑器。
- 不做 Obsidian plugin 生态。
- 不把 graph view 当核心差异化。
- 不写真实 Obsidian vault。

### B. Logseq

**核心形态**

- local-first outliner
- page/block references
- backlinks / graph
- powerful queries
- tasks / SRS / Zotero-like integrations

**强项**

- Block 作为知识单位，天然适合引用、重组和查询。
- Page/block references 能表达细粒度关系。
- Query 系统和 task/SRS 让知识库变成工作台。
- Outliner 心智适合 daily notes、研究、任务和复习。

**MindForge 应该学习**

- 细粒度 reference 的价值，尤其是 card/source/provenance 的可追溯性。
- Query/filtered views 对 Library organization 的价值。
- 复习和 recall 可以和知识卡片生命周期结合。

**MindForge 不应复制**

- 不做 block database/outliner。
- 不把每段 source 拆成可编辑 block。
- 不做完整 task manager 或 Zotero-style reference manager。

### C. Readwise / Reader

**核心形态**

- capture highlights from reading sources
- revisit/review highlights
- library search
- AI chat with highlights / Ghostreader-like assistant

**强项**

- Capture 很顺手，能从 Kindle、网页、PDF、RSS、newsletter 等入口收集 highlight。
- Review/revisit 让知识从“保存”进入“记住”。
- Reader 把阅读、highlight、library、search 和 AI 辅助聚合到一个体验里。
- AI assistant 围绕用户已保存 highlights 工作，输入边界清晰。

**MindForge 应该学习**

- Capture/import 的低摩擦体验。
- Review cadence 和 resurfacing 对长期记忆的价值。
- Library search 应该帮用户回到已确认内容。
- AI 输出应该围绕可追溯来源和用户确认边界。

**MindForge 不应复制**

- 不做完整 reader/read-it-later。
- 不做外部账号同步、浏览器阅读器、RSS/newsletter 收件箱。
- 不做 AI chat with highlights，至少当前阶段不做。

### D. Tana-like structured workspace

**核心形态**

- typed objects / supertags
- structured notes
- AI-assisted workflows
- meeting/action/decision capture
- knowledge graph updates

**强项**

- Supertags 把松散笔记升级为 typed objects。
- 结构化字段让 views/query/automation 更可控。
- Meeting/action/decision workflows 把 capture、结构和执行连接起来。
- AI 可以辅助生成结构、更新 graph、提取 action。

**MindForge 应该学习**

- Card 类型、状态、来源、质量、review 字段可以成为更强的结构化工作区能力。
- Review queue 和 Library views 可以学习 structured workspace 的 clarity。
- AI 应该产出 draft，用户确认后才改变长期知识。

**MindForge 不应复制**

- 不做 Tana 式 structured notes 全平台。
- 不做 meeting agent。
- 不让 AI 自动更新知识图谱事实。
- 不把 supertags 变成下一阶段主线。

### E. AI PKM / GraphRAG-like systems

**核心形态**

- graph/context/community/search
- relation-aware retrieval
- community/topic view
- graph-grounded question answering
- embedding/vector indexes and semantic retrieval in many systems

**强项**

- Relation-aware retrieval 可以提升复杂问题的上下文选择。
- Community/topic view 能让用户看到知识结构。
- Graph/context pipeline 对 enterprise corpus 和问答系统有价值。

**MindForge 当前 non-goals**

- no RAG answering
- no embedding
- no vector DB
- no real LLM by default
- no GraphRAG
- no mature community/entity/sensemaking product promise

**MindForge 应该学习**

- Explainability: 每条关系和召回结果都要说清楚为什么出现。
- Context boundary: 只从 approved cards 派生长期知识和 Wiki。
- Quality evaluation: 检索和关系质量要有 fixtures/report，而不是靠 demo。

**MindForge 不应复制**

- 不做 GraphRAG。
- 不为了 graph 形态引入 graph database UI。
- 不为了“AI PKM”叙事恢复 Graph/Sensemaking 大扩张。

---

## Comparison Matrix

| Product / pattern | Core input model | Knowledge unit | Organization model | Search/retrieval | Graph/network capability | Review/approval capability | AI role | Local-first/privacy posture | What MindForge already has | What MindForge lacks | What MindForge should not copy |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Obsidian | User writes/imports Markdown files | Note/page | Folders, links, tags, properties, Canvas, plugins | File search, backlinks, plugins | Graph view over links/tags | User edits directly, no AI approval gate by default | Plugin/user-added AI optional | Strong local-first vault | local workspace, source provenance, exported Markdown-like artifacts, local graph preview | native note editing, backlinks, Canvas, plugin ecosystem, mature properties/views | full notes app, plugin ecosystem, vault writes |
| Logseq | Outliner pages and blocks | Block/page | Outliner, namespaces, tasks, refs, queries | Block/page search and Datalog-like queries | Backlinks and graph | Direct user-authored blocks | Optional AI/plugins | local-first file-backed modes | approved card lifecycle, review scheduling primitives, BM25 recall | block references, queries, task/SRS depth, outliner UX | block database/outliner, task manager |
| Readwise / Reader | Highlights and reading captures | Highlight/document | Reading library, tags, review queue | Library search, highlight search, AI chat | Minimal graph; relation mostly via source/tags | User highlights first; no `human_approved` card gate | Summarize/chat/extract over highlights | Cloud-centric with integrations | review mindset, Library/Recall, approved cards | frictionless capture, mobile/browser/Kindle/RSS, reading UI, highlight review | read-it-later, external account sync, AI chat by default |
| Tana-like workspace | Structured notes, typed objects, meetings | Node/object with fields | Supertags, views, graph, workflows | Structured search/views | Graph of typed nodes | User edits/accepts structure; AI can assist | Structure/action extraction, workflow agents | mixed, product-dependent | card schema, status, review metadata, human gate | supertags, typed object views, agentic meeting/workflow, graph updates | meeting agent, full structured notes platform |
| AI PKM / GraphRAG-like systems | Corpus ingestion plus semantic/graph index | Chunk/entity/community/context | Graph/community/topic layers | Semantic, vector, graph-aware retrieval | relation-aware graph/community | Usually weak approval semantics unless custom built | Answering, retrieval, synthesis | varies; often cloud/model dependent | deterministic relations, BM25, approved-only Wiki, no RAG boundary | semantic retrieval, entity graph, answer generation, graph QA | RAG, embedding, vector DB, GraphRAG, mature sensemaking claims |
| MindForge current | Local source file/import to `ai_draft` | Knowledge Card | Review queue, Library, track/tag/project metadata, Wiki, local relations | BM25 lexical over approved cards by default | 4 NodeType local graph/lab standalone graph | Strong explicit approval gate | Draft generation and Wiki synthesis only after setup; fake dogfood default | local-first, secret-safe, no telemetry upload | approval-based workflow, dogfood evidence, local recall, approved-only Wiki, safe export | capture UX, Library organization, real LLM quality evidence, mobile/browser capture, docs simplification | notes app, reader, graph DB UI, meeting agent, RAG stack |

---

## MindForge Differentiation

### MindForge 和 Obsidian/Logseq 最大不同是什么？

Obsidian/Logseq 的核心是用户直接写作和组织笔记。MindForge 的核心是 **source → AI draft → human approval → approved knowledge card**。MindForge 不应该把自己变成用户每天写笔记的主编辑器，而应该把“资料加工成可审阅、可追溯、可检索的已确认知识”做深。

### MindForge 和 Readwise 最大不同是什么？

Readwise/Reader 的核心是 reading/highlight capture 和回顾。MindForge 当前没有低摩擦阅读器、移动 capture、Kindle/网页/RSS 集成。MindForge 的差异化不是“保存 highlight”，而是把本地 source 经人工审批变成正式知识卡片，并保持 approval boundary。

### MindForge 和 Tana 最大不同是什么？

Tana 的核心是 structured workspace 和 typed objects。MindForge 当前有结构化 card metadata，但不是通用 object database。MindForge 不应做 supertags/meeting agent，而应把 card status、provenance、review、quality、recall 这些已有结构化字段用于更清楚的知识工作流。

### MindForge 的独特机会是什么？

MindForge 的机会是做成 **approval-based knowledge card workflow**：

1. 输入可以是本地 source，而不是手写笔记。
2. AI 只能生成 `ai_draft`，不能污染长期知识。
3. 人工确认后的 `human_approved` 才进入 Library、Recall、Wiki 和 Export。
4. 检索、Wiki、关系、导出都能解释来源和边界。
5. 先把这个闭环做顺，而不是争夺 notes app/read-it-later/GraphRAG 的完整地盘。

### MindForge 是否应该做成 notes app？

不应该。可以导出、引用、展示 Markdown，但不应做完整 Markdown 编辑器、双链系统、Canvas、plugin ecosystem。

### MindForge 是否应该做成 read-it-later？

不应该。可以学习 capture/review 的低摩擦，但不应做 Reader、RSS、newsletter、browser reading、Kindle sync。

### MindForge 是否应该做成 graph database UI？

不应该。Local Graph Preview 可以作为 Library 里的关系解释层；独立 graph DB UI 会把产品带回 v3.7-v4.1 的扩张陷阱。

### MindForge 是否应该聚焦 approval-based knowledge card workflow？

应该。这是当前代码、测试、dogfood、文档边界最一致的方向，也是和上述产品形态真正不同的地方。

---

## Gap Analysis

### Capture / Import gap

- 缺少一体化 import wizard。
- 缺少 mobile/browser capture、URL reader、highlight capture、Kindle/RSS/newsletter 等入口。
- 当前支持本地文件格式，但真实混合目录、可选依赖缺失、长文档、大目录的用户体验未被充分 dogfood。
- Folder dry-run、manual paste、batch import、source watch 分散，用户很难理解哪个是主路径。

### Review / approval UX gap

- Review queue 需要更清楚的状态、来源、质量、下一步。
- Reject/defer/merge/split/link-to-existing 只是领域模型预留，没有产品闭环。
- 缺少 approval status timeline 和“我审过什么/为什么批准”的历史。
- 批量 approve 虽存在 guardrail，但需要更强的用户理解和防误操作 UX。

### Library organization gap

- 缺少 saved views、collections、properties/bases-like views、query builder。
- Tag/project/track 是字段，不是完整组织体验。
- 缺少 card merge/split、manual links、bulk maintenance、curation 工作台。

### Search / recall quality gap

- BM25 可用且可解释，但 lexical-only 对同义词、概念改写、跨语言、拼写错误弱。
- 10/10 dogfood recall 是 sample coverage 结果，不代表真实资料库 recall 达标。
- 缺少 failed query review、query explain UI、retrieval fixture dashboard、BM25 tuning report。
- 下一步不应上 embedding/vector DB；应先建立 Recall/Search Quality Lab。

### Wiki / synthesis quality gap

- Wiki approved-only 边界清楚，但真实 LLM synthesis 质量未在本轮验证。
- Fake wiki_synthesis 无有效 card_ids，section 价值有限。
- 缺少 section-level citations explanation、diff、accept/reject、manual repair loop。

### Graph/network gap

- 当前正式支持 4 NodeType，不支持 entity/community/topic fact graph。
- Sensemaking 是 lab/internal heuristics，不是成熟分析。
- Graph/Sensemaking 的历史 docs 很容易误导后续方向。
- 如果未来做 graph，只应在 Library/Card detail 中做 honest graph v2。

### Export / interoperability gap

- Web export 可用，但无一线 CLI export 主命令。
- 当前 Web export 字段保守，不应夸大为完整 frontmatter/provenance/relations round-trip。
- 不写真实 Obsidian vault是正确边界，但需要更清楚的 preview 和 interoperability profile。

### Local-first workspace gap

- local-first 基础强，但没有成熟的 workspace backup/restore/sync/conflict story。
- 没有移动端或跨设备体验。
- 用户仍需要理解 workspace、vault、config、secret store 的区别，first-run 可以更简单。

### Plugin/extensibility gap

- ExtensionManifest/ExportAdapter 是 lab/architecture reserve。
- 没有真实 plugin ecosystem、权限 UI、安装/启用/禁用/沙箱闭环。
- 当前不应继续投资 plugin system。

### AI assistant / real LLM readiness gap

- Web Setup 和 provider factory 已有基础，但没有本轮真实 LLM dogfood。
- 没有 chat with approved cards/highlights。
- 没有 RAG answering，且明确不应做。
- 需要安全 opt-in、prompt preview、cost/latency/failure explanation，而不是默认真实调用。

### Onboarding / first-run gap

- `mindforge start/status/doctor` 和 Web Setup 已存在，但还不是一个顺滑的 guided journey。
- Sample workspace、guided import、review queue、Recall/Wiki/Export 的首轮引导需要打磨。
- 用户需要能在 10-15 分钟内完成第一张 approved card 和第一次 recall/wiki/export。

### Mobile / capture gap

- 没有 mobile app、share sheet、browser extension、clipper。
- 这是真实 Capture 差距，但不是下一阶段优先实现对象。

### Documentation gap

- docs 数量过大，旧 plans/ADRs/implementation notes 仍含历史扩张叙事。
- 新用户和后续 agent 难以判断 canonical docs。
- 需要 docs index/current limitations/archive plan。

---

## No-Go / Do-Not-Copy

- 不要为了对标 Obsidian 就做完整笔记编辑器。
- 不要为了对标 Logseq 就做 block database/outliner。
- 不要为了对标 Readwise 就做完整 reader/read-it-later。
- 不要为了对标 Tana 就做 meeting agent。
- 不要为了 GraphRAG 就做 RAG/embedding/vector DB。
- 不要恢复 Graph/Sensemaking 大叙事。
- 不要把 synthetic dogfood 成功写成真实用户成功。
- 不要默认调用真实 LLM。
- 不要自动 approve。

---

## Self-Review

- **是否又想恢复 Graph/Sensemaking 扩张？** 没有。GraphRAG-like 对标只用于说明 non-goals。
- **是否又把 sample dogfood 误认为真实用户成功？** 没有。对比和 gap 都区分 synthetic dogfood 与真实用户资料。
- **是否过度对标导致产品变形？** 没有。每个对标对象都列了 should not copy。
- **是否建议做了 notes app / read-it-later / graph DB UI / meeting agent？** 没有，全部明确 No-Go。
- **是否忽略 MindForge 的 approval-based knowledge workflow 差异化？** 没有，差异化章节把它作为核心机会。
- **是否给了可以执行的大 loop，而不是空泛战略？** 是。gap 明确导向 Product Main Path UX Deepening 和 Recall/Search Quality Lab。
