# MindForge Current Capability Map

**日期**: 2026-05-25
**阶段**: docs/research/planning loop
**范围**: 当前真实能力审计，不实现新功能，不扩张 Graph/Sensemaking/Entity/Community，不调用真实 LLM，不做 RAG/embedding/vector DB。

---

## Executive Summary

**一句话定位**: MindForge 当前是一个本地优先、显式审批驱动的知识卡片工作台，把本地 source 处理成 `ai_draft`，经用户确认后进入 `human_approved` Library，并提供 BM25 Recall、派生 Wiki 和可审阅导出。

**当前真实可用主路径**:

```text
Source / Import → ai_draft → Review → explicit approval → human_approved
→ Library → Recall / Wiki → Export
```

该路径已经通过 fake/local dogfood 证明能跑通：首次 Product Main Path dogfood 记录 30/30 张卡片完成处理，后续 hardening 把 Recall 从 7/10 提升到 10/10；`quality-debt-ledger.md` 记录最终基线为 synthetic Markdown 样本、全部 gate clean、无 approval bypass。

**当前不可夸大的能力**:

- Dogfood 成功来自 synthetic/fake/local 数据，不等价于真实用户在私人资料、大 vault、复杂 PDF/DOCX、长文档上的成功。
- FakeProvider 只保证 schema 和确定性输出，不代表真实 LLM 卡片质量。
- Recall 是 BM25/词法检索，不是语义搜索、RAG、embedding 或向量数据库。
- Wiki 可以走 LLM synthesis，但默认 fresh config 不应触发真实模型；fake provider 下的 Wiki 结构质量有限，`card_ids` 为空时依赖 additional cards fallback。
- Export 主要是 Web API/UI 能力，没有稳定的一线 CLI `mindforge export` 主命令，也不写真实 Obsidian vault。

**当前仍是 lab/internal 的能力**:

- Graph 独立页、Sensemaking Workspace、Entity Resolution、ConceptCandidate、Community/Topic graph、GraphRepository、Extension Plugin、Dogfood metrics 都不是主产品承诺。
- 当前正式 Graph NodeType 只有 `card` / `source` / `tag` / `wiki_section`。`community` / `topic` / `entity` / `concept_candidate` 只属于 ontology/lab/internal，不能恢复 8 NodeType mature graph 叙事。

---

## Evidence Base

本次审计读取并交叉核对了以下证据：

- 工作流与授权: `.claude/commands/mf-autopilot.md`, `docs/dev/engineering-workflow.md`
- Dogfood 证据: `docs/implementation-notes/2026-05-25-090-product-main-path-dogfood-execution.md`, `docs/implementation-notes/2026-05-25-091-product-main-path-hardening.md`, `docs/dev/quality-debt-ledger.md`, `docs/dogfood.md`, `docs/dogfood-runbook.md`, `scripts/expanded_dogfood.sh`, `scripts/generate_dogfood_samples.py`
- 方向和审计: `docs/plans/2026-05-25-087-post-stabilization-direction.md`, `docs/plans/2026-05-25-089-product-main-path-dogfood-plan.md`, `docs/audits/2026-05-25-v4_2-post-remediation-red-team-re-audit.md`, `docs/audits/2026-05-25-v2.0-v3.6-independent-audit.md`
- 当前用户/架构文档: `README.md`, `docs/dev/architecture.md`, `docs/en/user-guide.md`, `docs/zh-CN/user-guide.md`, `docs/en/sources.md`, `docs/zh-CN/sources.md`, `docs/zh-CN/library-recall-wiki.md`
- 代码 truth check: source/import/review/approval/library/recall/wiki/export/provider/graph/sensemaking 相关模块和 Web 路由。

`docs/dogfood/` 目录不存在；当前 dogfood 文档是 `docs/dogfood.md` 和 `docs/dogfood-runbook.md`。

---

## Capability Inventory

### A. Source / Import

**当前支持什么**

- CLI: `mindforge import <path>` 一次性导入，`mindforge watch add <path>` 注册 file/folder 并启动后台 processing。
- Web: Sources 页支持 watched source、一次性 import、Process now、frequency 管理；Web 边界拒绝相对路径和不存在路径。
- Adapter 层: 默认 internal config 启用 Markdown、TXT、本地 HTML、文本型 PDF、DOCX；旧 `.doc` 明确不支持。PDF/DOCX 依赖可选包，缺失时应友好跳过。
- Library import API: 手动 Markdown 内容导入、batch paste、folder preview/import 可以创建 `ai_draft`，不调用 LLM。

**sample/fake/local 范围**

- Dogfood 配置只启用 `plain_markdown`，使用 `/tmp` workspace 和 fake provider。
- Product Main Path dogfood 的成功主要覆盖 synthetic Markdown 样本，不覆盖真实私人目录、真实 Obsidian vault、大规模混合目录或外部服务。

**是否真实用户可用**

- 对非敏感、小规模、本地文件，主路径是 dogfoodable。
- 对真实个人资料，当前仍应先小批量、非敏感验证；不建议直接处理私人敏感资料、公司机密资料或大规模 vault。

**欠缺点**

- 没有真正顺手的 first-run import wizard。
- Folder dry-run、manual paste、provenance preview、dedupe preview 分散在 Web/Library/Sources，不是统一主路径体验。
- 没有移动端 capture、浏览器 clipper、阅读器 highlight capture、URL 抓取或 OCR。
- Cubox/API/外部账号导入当前不能作为默认可用能力宣传。

### B. ai_draft Generation

**FakeProvider 当前能做什么**

- 对五段 processing stage 生成 schema-conformant JSON。
- 为 dogfood 提供确定性、零网络、零密钥的 `[fake]` 输出。
- 已加入标题关键词提取，让 fake cards 的 tags/summary 更适合 BM25 dogfood。
- 已支持 `wiki_synthesis` stage，用于 fake Wiki rebuild 路径。

**real LLM 是否默认关闭**

- Fresh user config 不应自动调用真实模型。模型需要通过 Web Setup 配置，API key 存 local secret store。
- `model_setup_readiness()` 只做 metadata 和 secret presence 判断，不读 raw key、不调用 provider。
- Dogfood 默认使用 fake provider，不发起 HTTP 请求。

**ai_draft 的质量边界**

- FakeProvider 不模拟真实模型语言能力，只证明 pipeline/schema/approval 边界。
- 真实 LLM 质量未在本轮调用验证。
- `ai_draft` 是草稿，不是正式知识；任何进入 Library/Wiki/Recall 主路径的正式知识必须 `human_approved`。

**欠缺点**

- 缺少真实 LLM opt-in 下的稳定质量评估报告。
- 缺少卡片生成失败的用户友好分层解释。
- 缺少 source → draft 的质量对比、regenerate/retry UX 和版本差异查看。

### C. Review / Approval

**explicit approval 边界**

- CLI `approve` 必须传明确目标和 `--confirm`。
- Web approve 必须 `confirm=true` 且 `reviewed_source=true`。
- `approve_explicit_card()` 不替用户选择默认卡片，不做自动 approve。
- `approve_card()` 只允许 `ai_draft → human_approved`，其他 status 拒绝；已审批重复 approve 是幂等。

**human_approved 语义**

- `human_approved` 表示用户显式确认后的正式知识。
- Library 默认只显示 `human_approved`。
- Wiki 只从 approved cards 派生。
- Recall 默认过滤到 `human_approved`，除非显式 include drafts。

**用户路径是否清楚**

- CLI 路径清楚：`approve list/show/approve --confirm`。
- Web Review 有 draft list/detail/approve；文档解释了 `ai_draft` 和 `human_approved`。

**欠缺点**

- Web reject 当前是 unavailable，不持久化拒绝。
- `ApprovalDecision` 预留了 reject/defer/append/link/merge/split，但只有 approve 接通。
- 缺少清晰的 approval status timeline、变更历史、批量 review guardrail 和 queue 分组。

### D. Library

**approved card 浏览能力**

- CLI `library list/show` 只读展示 approved cards，正文需显式 `--show-content`。
- Web Library 提供卡片列表、详情、质量标识、Related Cards、Local Graph Preview、Community Browser、导入/导出入口。
- `library_service.py` 会标注 fake provider note，防止把 offline test double 当真实质量。

**用户主工作区能力**

- Library 是当前最接近“用户主工作区”的页面。
- 它承接已审批知识浏览、卡片详情、关系导航和 export。

**欠缺点**

- 缺少 Obsidian/Logseq/Tana 那种成熟的组织模型：saved views、properties/bases、nested collections、queries、canvas。
- Tag/project/track 组织仍偏 metadata，不是可配置工作区。
- 批量选择、批量导出、批量维护、card merge/split/link 等深度工作流仍不完整。

### E. Recall / Search

**BM25 / lexical / non-RAG 能力**

- Recall 是本地 BM25 lexical search，不联网、不调 LLM、不读 `.env`、不做 embedding/RAG。
- 索引只使用 card frontmatter 安全字段和白名单 body sections，不索引 raw source、Source Excerpt、Human Note、prompt、completion、secret。
- 支持 `--explain` 字段贡献解释；还支持 hybrid ranking，但 hybrid 只叠加本地信号 `value_score` / `review_due`，不是 semantic hybrid。

**dogfood recall 10/10 的真实性边界**

- 10/10 是 synthetic sample 覆盖改善后的结果。
- 根因分析显示 7/10 不是索引 bug，而是样本未覆盖 SQL/React/安全关键词。
- 提升来自新增样本和扩大 sample count，不等价于任意真实查询都能 100% 命中。

**是否只是 sample 覆盖好**

- 是。当前结论应写成“fake/local sample recall 10/10”，不能写成“真实个人知识库召回已解决”。

**欠缺点**

- 没有语义同义词、查询改写、拼写纠错、短语/字段可视化调参 UI。
- 没有失败查询 review loop 和固定 retrieval fixtures 报告作为产品质量面板。
- 不应通过 embedding/vector DB 解决下一阶段问题；先做 lexical quality lab。

### F. Wiki

**approved-only Wiki**

- Wiki 只从 `human_approved` cards 构建，不读取 raw source，不绕过审批。
- CLI/Web 支持 status/content/rebuild。
- LLM synthesis 的输入是 `CardDigest`，只含 card 安全摘要；provenance 由代码追加。
- deterministic rebuild 是 troubleshooting/internal fallback。

**当前是否真的有用**

- 对 dogfood 主路径有用：能证明 approved cards 可以生成派生 Wiki 文件并保持 provenance。
- 对真实用户价值仍未充分证明：fake provider 的 section `card_ids` 为空，fake Wiki 更像结构和安全验证，不是高质量 synthesis。

**欠缺点**

- 缺少真实 LLM opt-in 下的 Wiki 质量评估证据。
- 缺少用户可理解的 “为什么这张卡被放进这个 section” 说明。
- 缺少 Wiki edit/rebuild diff、section-level accept/reject、staleness repair loop。

### G. Export

**safe / reviewable export**

- Web API 支持选中卡片导出 Markdown/JSON/OPML，Zip download 包含 `cards.md` 和 `manifest.json`。
- Export 不写真实 Obsidian vault，不包含 API key 或 secret store。
- 导出入口在 Library，不是独立 Import/Export 页面。

**不写真实 Obsidian vault**

- 当前安全边界明确：不写正式 Obsidian notes，不自动修改真实 vault。

**欠缺点**

- 没有一线 CLI `mindforge export` 主命令；Product Main Path dogfood 也明确记录了这一限制。
- 当前 Web export 是 reviewable/safe，但字段较保守，不应夸大为完整保留所有 provenance/frontmatter/relations。
- 缺少导出预览、导出差异、目标应用 profile、round-trip/interoperability 测试。

### H. Provider Readiness

**fake/local default**

- Dogfood 默认 fake provider，零密钥、零网络。
- Fresh config 不应自动调用真实模型；用户通过 Web Setup 配置后才进入真实 provider 路径。

**real opt-in readiness**

- Web Setup 存储 API key 到 local secret store。
- Readiness 路径只检查 metadata/presence，不返回 raw secret。
- Provider factory 支持 `fake`、`openai/openai_compatible`、`anthropic/anthropic_compatible`。

**欠缺点**

- `provider_readiness.py` 仍保留 legacy active_profile 语义，和新 Web Setup/model setup readiness 有历史层次差异。
- 没有本轮真实 LLM smoke；不应把 real opt-in 写成已 dogfood 的默认体验。
- 需要更清楚的 first-run “缺模型时下一步” 指引。

### I. Dogfood / Quality

**dogfood script/report**

- `scripts/expanded_dogfood.sh` 覆盖 S0-S13：生成样本、scan、process、确认不 auto approve、approve、Library、Wiki、index、Recall、Export 验证和清理。
- `docs/implementation-notes/090` 记录 30/30 初始处理、Recall 7/10、Wiki pass。
- `docs/implementation-notes/091` 记录 Recall 7/10 → 10/10、FakeProvider 关键词注入、样本扩展、full gate clean。
- `quality-debt-ledger.md` 记录 final baseline、resolved debt 和 full pytest/npm build/expanded dogfood gate。

**quality-debt-ledger**

- 当前开放质量债主要是 `web_facade.py`/`schemas.py` God module、前端测试缺失、coverage 配置缺失、chunk size、FakeProvider body 增量有限。
- v4.2.1 已关闭 Graph/Sensemaking truth reset 的关键 partial findings。

**gates**

- 最近 hardening 记录 full pytest clean、npm build clean、expanded dogfood clean。
- 本轮是 docs-only，应只新增规划文档并跑 docs gates。

**欠缺点**

- Dogfood 仍是 synthetic/fake/local，未覆盖真实非敏感用户资料集合。
- 前端仍缺少真正的 Web journey tests。
- `docs/` 数量很大，旧 notes/ADR 仍容易误导后续 agent。

### J. Graph / Sensemaking / Entity / Community

**当前必须标为 lab/internal**

- Graph backend/API 正式支持 4 NodeType: `card` / `source` / `tag` / `wiki_section`。
- GraphPage 只展示这 4 种 supported types，并有 Lab/Internal note；unsupported types 会返回 422。
- SensemakingPage 已有 LAB/INTERNAL warning banner，说明是 deterministic heuristics，不是成熟产品能力。
- `sensemaking.py` 明确标为 LAB/INTERNAL。

**真实支持范围**

- Library/Card detail 内的 Local Graph Preview 和 GraphNavigationPanel 可用于局部关系导航。
- 独立 `/graph` 路由仍存在，但应视作 internal/full-page lab surface，不是主导航承诺。
- Community Browser 可以作为 Library 内的确定性分组辅助，但不应上升为 graph/community/topic 大叙事。
- Entity/ConceptCandidate 当前是候选/实验层，不能自动升级为 fact graph。

**不能恢复 8 NodeType / mature sensemaking 叙事**

- ADR-006/ADR-007 已加 truth reset 追记：8 NodeType 是 ontology/history，不是当前实现完成度。
- `community` / `topic` / `entity` / `concept_candidate` 不能被描述为当前已完成 Graph API 能力。

**欠缺点**

- Graph/Sensemaking 仍有路由和历史文案残留，容易诱导后续 agent 扩张。
- Edge explain 和 node picker 可以作为未来 narrow graph v2 的基础，但必须等主路径稳定后再做。

---

## Capability Status Table

| Capability | Status | User value | Evidence | Gap | Recommended next action |
|---|---|---|---|---|---|
| Source import/watch | Dogfoodable | 把本地文件进入处理流水线 | `import_cli.py`, `watch_cli.py`, `WebSourceService`, sources docs | first-run wizard 和真实混合资料 dogfood 不足 | Direction A/B 下做 guided import 和 dry-run preview |
| SourceAdapter formats | Dogfoodable | 支持 md/txt/html/pdf/docx 本地文件 | bundled config, sources registry, docs | dogfood 主要覆盖 Markdown；PDF/DOCX 依赖/复杂文件未充分验证 | 扩展本地 fake-safe fixtures，不接真实私人资料 |
| Manual Markdown import / batch / folder | Dogfoodable | 快速创建 `ai_draft` | `web_facade.import_card`, folder preview/import endpoints | 与 Sources 主路径分散；真实私人资料边界需更清楚 | 合并到 Import UX，不扩大外部服务 |
| FakeProvider ai_draft | Dogfoodable | 零密钥验证主路径 | `llm/fake.py`, dogfood notes | 不是真实模型质量 | 保留为 test double，不把 fake 质量当产品质量 |
| Real LLM processing | Deferred | 真实卡片质量潜力 | Web Setup/model setup readiness | 本轮未调用真实 LLM；需用户 opt-in | 不做默认；未来单独 safe real dogfood gate |
| Review queue | Dogfoodable | 防止 AI 草稿直接入库 | `approval_service.py`, `WebReviewService` | reject/defer/merge/split 未接通 | Direction A 打磨 queue clarity 和 status timeline |
| Explicit approval / `human_approved` | Production-like | 核心信任边界 | `approve_card()`, approval tests, dogfood no bypass | 批量审批 UX 仍需谨慎 | 不破坏语义；任何新 decision 先做 service + tests |
| Library browsing | Dogfoodable | 已审批知识主工作区 | `library_service.py`, Web Library | 组织能力浅；缺 saved views/collections | Direction A 加深 Library organization |
| Related cards / Local Graph Preview | Dogfoodable | 局部导航和可解释关系 | `related_cards.py`, Graph components | 不是成熟 graph workspace | 留在 Library/Card detail，避免主线扩张 |
| BM25 Recall | Dogfoodable | 本地可解释搜索 | `recall_service.py`, `lexical_index.py`, 10/10 dogfood | 10/10 是 synthetic sample；无 semantic recall | Direction C 建立 Recall Quality Lab |
| Wiki rebuild | Dogfoodable | 从 approved cards 生成派生回顾页 | `wiki_service.py`, `wiki_cli.py`, dogfood pass | fake Wiki 质量有限；real LLM 未验证 | 保持 approved-only，做 quality explanation |
| Export via Web API | Dogfoodable | 可审阅导出选中卡片 | `routers/library.py` export endpoints | 无一线 CLI export；metadata/provenance 保守 | Direction A 做 export clarity，不写真实 vault |
| Provider readiness | Internal | 避免缺 key/错误配置的黑盒失败 | `model_setup_readiness.py`, Setup docs | legacy/new readiness 叙事需统一 | 纳入 onboarding，不读 raw secret |
| Dogfood automation | Internal | 保护主路径和安全边界 | `expanded_dogfood.sh`, quality ledger | synthetic-only | 保留为 gate，新增 journey evidence |
| Graph standalone page | Lab | 实验性图探索 | `GraphPage.tsx`, graph router | 只支持 4 NodeType；不是主导航 | 保持 Lab/Internal；不要扩张 |
| Sensemaking Workspace | Lab | 实验性 heuristics 展示 | `SensemakingPage.tsx`, `sensemaking.py` | 非成熟分析；路由仍存在 | 保持隐藏/label，不进入主线 |
| Entity / ConceptCandidate | Lab | 未来候选实体探索 | `entity_resolution.py`, graph ontology docs | 无用户确认升级闭环 | 不做下一阶段 |
| Community / Topic graph | Lab/Internal | Library 分组辅助 | `community.py`, docs reset | 不支持为 Graph API fact NodeType | 不恢复大叙事 |
| Extension Plugin | Lab/Deferred | 架构预留 | `extensions/export_adapter.py`, docs | 无真实插件生态/闭环 | 不做下一阶段 |

---

## Feature Focus Verdict

### 应该继续作为主线

1. **Approval-based knowledge card workflow**: Source/Import → `ai_draft` → Review → explicit approve → `human_approved`。
2. **Product Main Path UX**: first-run、sample workspace、import guidance、review queue、Library、Recall/Wiki/Export 的用户路径。
3. **Recall/Search Quality Lab**: 继续加深 BM25/lexical 的解释、失败查询回顾、fixtures 和质量报告，不引入 embedding。
4. **Docs truth and limitation clarity**: 当前能力、限制、lab/internal 边界必须持续收敛。

### 应该保持 internal/lab

- Graph standalone page
- Sensemaking Workspace
- Entity Resolution / ConceptCandidate
- Community/Topic graph
- GraphRepository
- Extension Plugin
- Dogfood metrics and scripts
- deterministic Wiki fallback

### 应该归档或隐藏

- v3.7-v4.1 期间把 8 NodeType / mature sensemaking 当作当前完成能力的旧路线叙事。
- 不再作为当前授权来源的旧 plan/spec/implementation notes，至少需要 docs reset index 或 archive marker。
- 任何把 Graph/Sensemaking 放回主导航的文案或入口。

### 当前不应该做

- 不做 RAG answering、embedding、vector DB、GraphRAG。
- 不把 MindForge 做成完整 notes app、read-it-later、graph database UI 或 meeting agent。
- 不默认调用真实 LLM。
- 不写真实 Obsidian vault。
- 不自动 approve，不改变 `human_approved` 语义。
- 不恢复 Graph/Sensemaking/Entity/Community 扩张。

---

## Self-Review

- **是否又想恢复 Graph/Sensemaking 扩张？** 没有。本图谱结论明确把 Graph/Sensemaking/Entity/Community 放在 lab/internal。
- **是否又把 sample dogfood 误认为真实用户成功？** 没有。所有 dogfood 成功都标注为 synthetic/fake/local 边界。
- **是否过度对标导致产品变形？** 没有。本文件只定义 MindForge 现有能力，不要求做 notes app/read-it-later/graph DB UI。
- **是否建议做了 notes app / read-it-later / graph DB UI / meeting agent？** 没有，均列为不应该做。
- **是否忽略 approval-based knowledge workflow 差异化？** 没有，主线 verdict 明确把显式审批工作流作为核心。
- **是否给了可以执行的大 loop，而不是空泛战略？** 是。下一阶段应进入 Product Main Path UX Deepening + Recall/Search Quality Lab，具体拆解见 roadmap 文档。
