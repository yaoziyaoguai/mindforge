# MindForge Next Deepening Roadmap

**日期**: 2026-05-25
**状态**: proposed
**输入**:

- `docs/audits/2026-05-25-092-current-capability-map.md`
- `docs/research/2026-05-25-093-industry-benchmark-and-gap-analysis.md`
- Product Main Path dogfood/hardening evidence

**硬边界**: 本 roadmap 只授权后续 plan/spec loop，不授权本轮实现。不进入 v4.3/v5.0 implementation，不恢复 Graph/Sensemaking/Entity/Community 扩张，不做 real LLM 默认路径，不做 RAG/embedding/vector DB。

---

## Roadmap Decision Summary

推荐下一阶段主方向：**Direction A — Product Main Path UX Deepening**。

推荐并行/次方向：**Direction C — Recall/Search Quality Lab, no embedding**。

理由：当前代码和 dogfood 已证明主路径能跑通，但真实用户的顺手程度、first-run 成功率、Review/Library/Recall/Wiki/Export 的解释力仍是最大风险。Recall 10/10 是 synthetic sample coverage 的结果，最需要建立质量实验室来防止未来再次把 demo recall 当成真实 recall。

暂不推荐 Direction E。Graph/Sensemaking 刚从 overclaim 中收缩，下一阶段不应该重新打开扩张通道。

---

## Direction A — Product Main Path UX Deepening

### Goal

把 Source/Import → `ai_draft` → Review → approve → Library → Recall/Wiki → Export 做成用户真正顺手的 Web/CLI 主路径。

### Why now

- Product Main Path Golden Path 已经 fake/local dogfood solid，但这是“能跑通”，不是“用户顺手”。
- 当前最大产品风险不是缺功能，而是用户是否能在不理解内部实现的情况下完成第一轮。
- 这是 MindForge 与 Obsidian/Logseq/Readwise/Tana 区分开的核心：approval-based knowledge card workflow。

### Focus

- first-run onboarding
- sample workspace
- import wizard or guided CLI
- review queue clarity
- approval status timeline
- Library organization
- Recall/Wiki user-facing explanation
- Export clarity
- Web smoke and user journey tests

### Candidate loops

1. **First-run guided path**
   - 明确 fresh workspace 的第一屏：配置模型或使用 safe sample/fake path。
   - 一键生成 sample workspace 或引导用户导入非敏感 sample。
   - 成功标准：用户能从空 workspace 到第一张 approved card。

2. **Import and Review clarity**
   - Sources/Import 入口统一解释：watch vs one-shot import vs manual paste/folder import。
   - Review queue 展示 source、stage、quality、provenance、draft status。
   - 成功标准：用户知道哪些是待审草稿、为什么不能直接进入 Library。

3. **Approval timeline**
   - 展示 `ai_draft → human_approved` 的状态、确认动作、approved_at、index refresh。
   - 保持 no auto approve。
   - 成功标准：每张卡都能解释何时、如何、由谁确认。

4. **Library organization MVP**
   - 不做 notes app/bases/outliner。
   - 只围绕 cards: track/tag/project/source/quality/review status 做 filters/saved view candidates。
   - 成功标准：用户能按来源、主题、质量和最近审批找到卡。

5. **Recall/Wiki/Export explanation**
   - Recall 明确 BM25 lexical boundary 和为什么命中。
   - Wiki 明确 approved-only 派生视图。
   - Export 明确 Web/API 能力、Zip/JSON/OPML 的字段范围和不写 vault。

6. **User journey tests**
   - 不需要一开始引入大型前端框架。
   - 至少建立 Web smoke/user journey gate，覆盖 Home → Sources → Review → Library → Recall → Wiki → Export 文案和关键 affordance。

### Non-goals

- 不新增外部 capture 服务。
- 不做 real LLM 默认路径。
- 不做 graph/sensemaking 扩张。
- 不做 notes editor、read-it-later、meeting agent。

### Gates for implementation loop

- `git diff --check`
- `ruff check src/ tests/ docs/`
- `python -m pytest tests/test_web_product_copy.py -q --tb=short`
- 针对变更的 pytest
- `npm --prefix web run build`
- Web smoke/user journey gate，需记录 exact exit code

### Risks

- 过度 polish 变成大 UI rewrite。
- 为了解释导入而新增一堆 source integrations。
- 试图把 Library 做成 notes app。

### Decision

**Primary direction**。下一阶段首个大 loop 应从 first-run guided path 和 Review/Library clarity 开始。

---

## Direction B — Capture / Import Expansion, still local/fake-safe

### Goal

增强资料输入能力，但不碰真实私人资料、不调用外部服务。

### Why it matters

MindForge 当前最大的行业差距之一是 Capture/Import。Readwise 的 capture 很顺手，Obsidian/Logseq 的本地文件入口自然。MindForge 目前有 adapters 和 Web/CLI import，但体验分散。

### Focus

- markdown folder dry-run
- manual paste import
- file drop/sample import
- provenance preview
- dedupe preview
- import validation
- error reporting

### Candidate loops

1. 统一 import preview model：单文件、folder、paste 都先 dry-run。
2. 显示 source provenance preview：source title/path/type/hash/adapter。
3. 显示 dedupe preview：exact title 和 Jaccard candidate。
4. 增加 failure summary：unsupported extension、optional dependency missing、too large、empty file。
5. 只使用 local/fake-safe samples，不接外部账号。

### Non-goals

- 不做 browser extension、mobile share sheet、RSS、Kindle、Cubox API、Reader。
- 不抓 URL，不处理真实私人资料。
- 不写 Obsidian vault。

### Risks

- 容易扩张成 “支持所有来源”。
- 容易绕开 approval boundary，必须保证所有 import 只生成 `ai_draft`。

### Decision

**Secondary candidate**。适合作为 Direction A 的 import slice，而不是独立产品线。

---

## Direction C — Recall/Search Quality Lab, no embedding

### Goal

继续加深非 embedding 检索，建立可复现质量闭环。

### Why it matters

Recall 7/10 → 10/10 的根因是 sample coverage，不是索引 bug。这说明 Recall 需要一个质量实验室，持续回答：哪些 query 失败、为什么失败、是 tokenization、字段权重、样本覆盖还是用户语言问题。

### Focus

- query explain
- failed query review
- retrieval fixtures
- BM25 tuning
- lexical synonym rules
- recall quality report
- no RAG/no vector/no LLM judge

### Candidate loops

1. **Recall fixtures v1**
   - 固定 synthetic approved cards 和 queries。
   - 记录 expected hit IDs、negative queries、CJK queries、short queries。

2. **Query explain report**
   - 把 `--explain` 结果沉淀为报告：matched terms、fields、field weights、miss reason。
   - 给用户文案解释 “BM25 lexical only”。

3. **Failed query review**
   - 记录 query、expected concept、actual hits、miss category。
   - 不用 LLM judge，不引入 embedding。

4. **BM25 tuning**
   - 只调字段权重、tokenizer、小型 synonym rules。
   - 所有规则必须可解释、可测试、可关闭。

5. **Recall quality gate**
   - 加入 dogfood gate 或专门 script，输出 exact exit code 和 summary。

### Non-goals

- 不做 semantic search。
- 不做 embedding/vector DB。
- 不做 RAG answering。
- 不做 LLM judge。

### Risks

- “hybrid” 命名容易被误解成语义混合检索；文案必须说明当前 hybrid 是本地信号重排。
- Synonym rules 如果过度，会变成不可维护的规则泥潭。

### Decision

**Recommended secondary direction**。应与 Direction A 并行推进，尤其服务 Recall/Wiki 用户解释和质量报告。

---

## Direction D — Documentation/System Simplification

### Goal

把大量 docs 收缩成 canonical docs + archive plan。

### Why it matters

v4.2 red team 的核心教训是 stale docs 会变成产品风险。当前 `docs/` 下有大量 implementation notes、plans、ADRs，历史 Graph/Sensemaking 叙事仍可能误导后续 agent。

### Focus

- user-facing docs set
- developer docs set
- archive old implementation notes/plans
- current limitation doc
- docs index
- no massive move unless planned

### Candidate loops

1. Canonical docs index：README、user guide、architecture、current capability, current limitations, quality debt。
2. Historical docs archive marker：不大规模移动文件，先加 status/header 或维护 index。
3. Current capability and limitation pages：引用本轮 capability map 和 benchmark。
4. Old Graph/Sensemaking docs cleanup：只加 truth reset 指向，不重写历史。

### Non-goals

- 不做大规模文件移动导致链接炸裂。
- 不把历史 implementation notes 全删掉。
- 不借 docs reset 开启新功能。

### Risks

- docs reset 容易变成长时间清理，拖慢产品主路径。
- 如果先做 D 而不做 A，用户体验风险仍 unresolved。

### Decision

**Support direction**。可以在 A/C 之后或穿插做，但不是主方向。

---

## Direction E — Honest Graph View v2, only after main path

### Goal

只在主路径稳定后，基于 card/source/tag/wiki_section 做 honest graph。

### Why it matters

Local Graph Preview 对 Library/Card detail 有导航价值，但 v3.7-v4.1 的扩张已经产生过度声明。Graph 只有在主路径完成后，作为解释层，才值得继续。

### Focus

- graph from Library/Card detail
- edge explain
- node picker
- unsupported state
- no entity/community/sensemaking expansion

### Candidate loops

1. 收缩入口：只从 Library/Card detail 进入。
2. Edge explain：每条边必须展示 source/tag/wiki_section/review_batch/source_location 证据。
3. Node picker：只允许 `card/source/tag/wiki_section`。
4. Unsupported state：明确 community/topic/entity/concept_candidate 尚未实现。
5. Graph quality fixtures：只验证 honest graph，不验证 sensemaking。

### Non-goals

- 不做 entity/community/topic graph。
- 不做 graph database。
- 不做 GraphRAG。
- 不恢复 Sensemaking Workspace 为主产品。

### Risks

- 最容易重启大叙事。
- 会分散 A/C 的主路径焦点。

### Decision

**Defer**。只有 Direction A 和 C 完成后才可重新评估。

---

## Recommended Next Phase

### Primary direction

**Direction A — Product Main Path UX Deepening**

第一轮建议从以下两个 slices 开始：

1. First-run guided path with sample/fake-safe workspace。
2. Review queue + Library clarity，明确 `ai_draft`、`human_approved`、source provenance、approval timeline。

### Secondary direction

**Direction C — Recall/Search Quality Lab, no embedding**

与 A 并行建立最小 recall quality report，让 Recall 页面和 CLI 不只“有结果”，还能解释 “为什么命中/为什么失败”。

### Support direction

**Direction D — Documentation/System Simplification**

作为持续维护任务，先做 index/current limitations，不做大规模移动。

### What not to do next

- 不直接进入 v4.3/v5.0 implementation。
- 不恢复 Graph/Sensemaking/Entity/Community 扩张。
- 不做 real LLM 默认路径。
- 不做 RAG/embedding/vector DB。
- 不做 notes app、read-it-later、graph DB UI、meeting agent。
- 不做 Obsidian vault 写入。
- 不改 approval semantics，不做 auto approve。

### Why this recommendation

- A 直接提高用户主路径成功率，最贴近当前真实产品价值。
- C 防止 Recall 再次被 sample coverage 误判，建立可持续质量证据。
- D 降低后续 agent 被旧 docs 带偏的概率。
- E 虽有价值，但历史风险最高，必须等主路径和 recall 质量先稳。

---

## Authorization Boundary For Later Loops

本文件可以作为后续大 loop 的授权来源，但只授权以下计划方向：

1. 写 Direction A 的具体 plan/spec。
2. 写 Direction C 的具体 plan/spec。
3. 小步更新 docs index/current limitations。
4. 保持所有 Graph/Sensemaking/Entity/Community 为 lab/internal。

本文件不授权：

- 直接写 v4.3/v5.0 code。
- 新增真实 LLM调用路径或默认真实模型。
- 新增 RAG/embedding/vector DB。
- 新增 graph database 或 GraphRAG。
- 新增外部 capture 服务或 mobile/browser integrations。
- 改变 explicit approval / `human_approved` 语义。

---

## Self-Review

| Check | Verdict | Notes |
|---|---|---|
| 是否又想恢复 Graph/Sensemaking 扩张？ | No | Direction E 明确 deferred，只允许 honest 4 NodeType graph after main path。 |
| 是否又把 sample dogfood 误认为真实用户成功？ | No | Roadmap 多次标明 synthetic/fake/local 边界，A 的重点是把 dogfoodable 变顺手。 |
| 是否过度对标导致产品变形？ | No | 没有推荐 notes app/read-it-later/graph DB UI/meeting agent。 |
| 是否建议做了 notes app / read-it-later / graph DB UI / meeting agent？ | No | 全部写入 What not to do next。 |
| 是否忽略 approval-based knowledge workflow 差异化？ | No | A 是 primary，核心就是 approval-based card workflow。 |
| 是否给了可以执行的大 loop，而不是空泛战略？ | Yes | A/C/D/E 均有 slices、non-goals、risks、gates 或执行边界。 |

---

## Proposed First Loop After This Docs Phase

如果用户后续授权进入 implementation planning，下一份文档应是：

`docs/plans/<date>-product-main-path-ux-deepening-plan.md`

建议内容：

1. repo facts and safety gates
2. first-run/sample workspace journey
3. import/review/library UX slices
4. recall explain/report minimal slice
5. tests and smoke plan
6. docs updates
7. explicit non-goals and hard stops

当前不要直接实现。
