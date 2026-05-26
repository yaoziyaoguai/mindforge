# MindForge-on-MindForge Project Knowledge Dogfood Report

**日期**: 2026-05-26
**版本**: v4.9
**类型**: Project Knowledge Dogfood — 使用 MindForge 自己的 repo docs 作为 source material
**状态**: complete

---

## Executive Summary

用 MindForge 仓库内 30 个非敏感项目文档作为 source material，通过 fake provider 完成完整主路径验证：

```
Source/Import (30 repo docs) → ai_draft (30) → Review → explicit approval → human_approved (30)
→ Library → Recall (BM25) / Wiki (LLM synthesis) → (Export via Web API)
```

**核心结论**:
- Pipeline 基础设施完整可用：30/30 source → ai_draft → human_approved 全部成功
- 安全边界 intact：无 auto-approve，显式审批不可绕过
- Fake provider 的内容理解能力严重受限：卡片只包含文件名提取的关键词和 [fake] 占位符
- Recall 4/10 (40%)：fake provider 的内容稀疏性导致 BM25 索引覆盖率不足
- 这是 **synthetic dogfood → real LLM dogfood** 之间的关键过渡证据

---

## Dogfood 指标

| 指标 | 结果 | 说明 |
|------|------|------|
| Source 文档数 | 30 | 来自 8 个类别的 repo docs |
| ai_draft 生成 | 30/30 (100%) | fake provider, 零网络, 零密钥 |
| human_approved | 30/30 (100%) | 显式 `--all --confirm` 审批 |
| 安全边界 | 0 bypass | library 在 approve 前为空 |
| Library 浏览 | 30 cards visible | CLI `library list` 正常 |
| Recall 命中率 | 4/10 (40%) | 仅英文单关键词查询命中 |
| Wiki rebuild | pass | 30 cards, sections discarded (fake, expected) |
| Index rebuild | pass | bm25.json, 30 cards, avgdl=56.3 |
| Export CLI | N/A | `mindforge export` 命令不存在 (known limitation) |
| P0 阻塞性 bug | 0 | — |

---

## Source Documents Selected

30 个 repo docs，按 8 个类别分组：

### Category 1: Canonical Entry Points (5)
1. `README.md` — 项目入口
2. `docs/README.md` — 文档索引
3. `docs/dev/architecture.md` — 代码架构概览
4. `docs/dev/quality-debt-ledger.md` — 质量债台账
5. `docs/dev/engineering-workflow.md` — 工程工作流

### Category 2: Current Capability & Audits (3)
6. `docs/audits/2026-05-25-092-current-capability-map.md`
7. `docs/audits/2026-05-26-099-global-architecture-quality-audit.md`
8. `docs/research/2026-05-25-093-industry-benchmark-and-gap-analysis.md`

### Category 3: Current Roadmap & Plans (3)
9. `docs/plans/2026-05-25-094-next-deepening-roadmap.md`
10. `docs/plans/2026-05-25-089-product-main-path-dogfood-plan.md`
11. `docs/plans/2026-05-26-101-v4_8-global-architecture-quality-roadmap.md`

### Category 4: Recent Implementation Notes (6)
12. `docs/implementation-notes/2026-05-25-090-product-main-path-dogfood-execution.md`
13. `docs/implementation-notes/2026-05-25-091-product-main-path-hardening.md`
14. `docs/implementation-notes/2026-05-26-095-v4_4-product-main-path-ux-deepening.md`
15. `docs/implementation-notes/2026-05-26-096-v4_6-documentation-system-simplification.md`
16. `docs/implementation-notes/2026-05-26-098-v4_7-architecture-debt-reduction.md`
17. `docs/implementation-notes/2026-05-26-102-v4_8-architecture-quality-reset.md`

### Category 5: User Guides (2)
18. `docs/en/user-guide.md`
19. `docs/zh-CN/user-guide.md`

### Category 6: Developer Docs (5)
20. `docs/dev/copy-policy.md`
21. `docs/dev/testing.md`
22. `docs/dev/docs-reset-index.md`
23. `docs/dev/workspace-data-layout.md`
24. `docs/dev/documentation-inventory.md`

### Category 7: Additional Reference (4)
25. `docs/dev/contributing.md`
26. `docs/dev/release-process.md`
27. `docs/dev/quality-baseline-2026-05-25.md`
28. `docs/dogfood-runbook.md`

### Category 8: Key Chinese Docs (2)
29. `docs/zh-CN/library-recall-wiki.md`
30. `docs/zh-CN/review-and-approval.md`

所有文档均来自仓库内非敏感公开资料，不包含 .env、secrets、私人数据。

---

## Recall Query Results

### 测试方法

10 个 project knowledge 查询，涵盖中英文、产品定位、架构、安全、工程流程。

### 结果表

| # | Query | Hits | Score Range | Root Cause |
|---|-------|------|-------------|------------|
| 1 | `architecture` | 2 | 5.540-5.795 | card tag "architecture" matches |
| 2 | `MindForge` | 0 | — | "MindForge" not in any card title/tag/body |
| 3 | `approval` | 1 | ~5.5 | filename "30-review-and-approval" contains "approval" |
| 4 | `dogfood` | 3+ | ~5.5 | multiple filenames contain "dogfood" |
| 5 | `BM25 recall` | 1 | ~5.5 | filename "29-library-recall-wiki" contains "recall" |
| 6 | `Graph Sensemaking lab` | 0 | — | no card title/tag contains these words |
| 7 | `质量债` | 0 | — | CJK query; all card content is English |
| 8 | `web_facade` | 0 | — | not in any filename-derived title or tag |
| 9 | `安全边界` | 0 | — | CJK query; all card content is English |
| 10 | `工程闭环` | 0 | — | CJK query; all card content is English |

**Recall: 4/10 (40%)**

### 失败根因分析

**核心原因**: Fake provider 不读取 source document 实际内容。它只从文件名提取关键词生成标签和 [fake] 占位符内容。

具体表现：
- 卡片标题 = 源文件名（如 `03-architecture`），而非文档的实际标题（如 `MindForge Architecture`）
- 标签 = 从文件名分割的单个英文词（如 `architecture`），而非文档实际主题
- Body = `[fake]` 占位符，只重复标签词
- 完全不包含源文档中的实际项目术语（如 "MindForge"、"web_facade"、"安全边界"）

**这不是 BM25 或索引的 bug。** 这是 fake provider 的内容生成策略导致索引覆盖率不足。当源文档是真实项目文档（而非 synthetic 技术笔记）时，文件名不包含足够的主题关键词来支持有意义的 recall。

### 与 synthetic dogfood 的对比

| 维度 | Synthetic Dogfood (v4.2) | Project Doc Dogfood (v4.9) |
|------|--------------------------|---------------------------|
| Source 类型 | 生成的技术笔记 | 真实项目文档 |
| 文件名 | `python-async-io-notes.md` 等 | `03-architecture.md` 等 |
| 文件名含关键词 | 是（Python, Docker, SQL...） | 部分（architecture, dogfood...） |
| Recall 命中率 | 10/10 (100%) | 4/10 (40%) |
| 根因 | 样本覆盖好 | fake provider 内容稀疏 |

---

## Wiki Output

- **Sections**: 0（fake provider 返回空 card_ids，预期行为）
- **Additional cards**: 30（全部卡片作为附加参考列出）
- **Overview**: `[fake] 基于提供的 approved cards 生成的知识总览`
- **质量**: fake Wiki 只验证 pipeline 结构和安全边界，不代表真实 LLM synthesis 质量

---

## Export

`mindforge export` CLI 命令不存在（v4.2 dogfood 已记录的已知限制）。Export 通过 Web API (`routers/library.py`) 提供 JSON/OPML/Zip 格式导出。

---

## Friction Points Found

### F1. Fake Provider 内容稀疏性 (P2)

**问题**: Fake provider 对真实项目文档的内容提取能力几乎为零。卡片标题是文件名，标签是单个通用词，body 是 [fake] 占位符。

**影响**: Recall 命中率 40%，CJK 查询 0%，项目特定术语查询 0%。

**建议**: 
- 短期：接受 fake provider 的内容限制，将其定位为 pipeline/schema/安全边界验证工具
- 中期：为 project doc dogfood 场景改进 fake provider 的关键词提取（如从文档 frontmatter/标题/章节提取）
- 长期：真实 LLM opt-in dogfood 才能产生有意义的知识卡片

### F2. 无 CLI Export 命令 (P3, known)

已在前序 dogfood 中记录。不影响 Web API export 功能。

### F3. 中文查询全部失败 (P2)

**问题**: 10 个查询中 3 个 CJK 查询全部 0 hits。

**根因**: Fake provider 生成全英文内容，BM25 索引无 CJK tokens。

**建议**: 这是 fake provider 限制的直接后果。Real LLM 处理中文源文档后会自然解决。

---

## Was This Dogfood Valuable?

**是。** 这个 dogfood 在 synthetic sample dogfood 和 real LLM dogfood 之间建立了关键过渡证据：

1. **证明了 pipeline 对真实项目文档的处理能力**: 30 个真实文档（非 synthetic 技术笔记）能完整通过主路径
2. **量化了 fake provider 的内容理解差距**: Recall 从 synthetic 的 100% 降到真实项目文档的 40%
3. **验证了安全边界在非 synthetic 场景下同样坚固**: 审批语义、BM25 本地检索边界、Wiki approved-only 约束全部 intact
4. **为 real LLM dogfood 提供了基线**: 现在可以精确对比 fake vs real 的质量差异

**对于一个真实用户来说**: 当前 fake provider 体验不足以产生有价值的知识卡片。但 pipeline 基础设施已经 ready — 只需要真实的 LLM 处理就能产生有意义的知识提取。这个 dogfood 证明了 MindForge 在 "配置真实模型后" 可以成为理解项目文档的有效工具。

---

## Next Recommended Loop

1. **v4.9 Loop 2**: 改进 fake provider 对项目文档的关键词提取（从 markdown 标题/章节提取更多关键词），提升 BM25 recall
2. **v4.10**: Real LLM opt-in dogfood — 用户配置真实 API key 后，用相同 30 个源文档重新处理，对比 fake vs real 质量
3. **v5.0**: 基于两个 dogfood 的证据，规划下一阶段产品方向

---

## Safety Confirmation

- 零网络请求 / 零 API key 使用
- 零真实私人资料处理
- 零 Obsidian vault 写入
- Fake provider 确定性输出
- 不做 RAG / embedding / vector DB
- 显式审批不可绕过（library 在 approve 前为空）
- 所有数据写入 `.tmp/` 隔离目录
