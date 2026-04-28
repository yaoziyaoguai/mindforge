# MindForge v0.2 Final Review

> v0.2.5 收口。本文是 v0.2 整个 milestone 的复盘 + 不做清单 + v0.3 候选。
> 不重复每个子版本的细节（详见 `docs/V0_2_*_REVIEW.md`）。

## v0.2 整体目标回顾

> 让 MindForge 在 v0.1 的 ingest→triage→distill→write 之上，**真正可用**：
> 多源接入、可召回、可复习、可生成项目上下文、可观察、可定位问题。
> 全程**不调真实 LLM** 即可端到端验证；**不引入 RAG/embedding**；不做 Obsidian 插件。

## v0.2 子版本一览

| 版本 | 主线 | 关键交付 |
|---|---|---|
| v0.2.0 | M4 recall + project context | `mindforge recall` / `mindforge project context` 最小实现 |
| v0.2.1 | M4 强化 | recall 排序、过滤、JSON 输出；project context 字段稳定化 |
| v0.2.2 | M5.3 enhanced project context | learning track / principles / project profile / suggested prompt |
| v0.2.3 | M5.7 telemetry + multi-project context | 本地 telemetry.jsonl、multi-project pack、evidence block 幂等写回 |
| v0.2.4 | M5.2 web clip + chat export | `WebClipMarkdownAdapter` + `ChatExportAdapter`；`mindforge version` / `--debug` |
| v0.2.5 | M5.5 vault polish + M5.1 doc adapters + CLI polish #2 | `vault index/links/refresh`；真实 PDF/Docx adapter（lazy import + 友好错误）；`doctor`；`--vault` 全局 override |
| v0.2.6 | 日用化（init + approval polish） | `mindforge init` 幂等骨架；`approve list/--source-id/--all`；`doctor` action items；onboarding smoke |

## v0.2.5 增量摘要

- **M5.5 Vault 友好度**
  - 新增 `mindforge vault index` / `vault links` / `vault refresh`
  - 自动维护 `_index.md` / `_link_candidates.md`，**绝不**修改任何已有 Knowledge Card 正文
  - 同名 `_index.md` 已存在但不是 MindForge 维护的，**降级**写到 `_index.mindforge.md`，避免覆盖人手内容
  - 评分仅依赖 frontmatter 安全字段（`track` / `projects` / `tags` / `source_type` / `title` token），**不**读卡片 body
- **M5.1 PDF/Docx adapter（最小真实实现）**
  - `PdfAdapter` / `DocxAdapter` 升级为真实文本抽取
  - lazy import：未装 `pypdf` / `python-docx` 时给出 `OptionalDependencyError("pip install mindforge[pdf]")`
  - PDF 扫描件无文本层 → `PdfNoTextError`，**不**做 OCR、**不**降级到空卡片
  - 通过 `[project.optional-dependencies]` 暴露 `pdf` / `docx` / `docs` extras；默认仍 OFF
- **CLI polish #2**
  - 全局 `--vault PATH` 覆盖 `vault.root`，不改 yaml；通过 env 透传
  - `mindforge doctor` 健康检查：Python、平台、配置、vault 目录、optional deps、`.env` 是否在 `.gitignore`、git status 敏感产物嗅探
  - doctor **不**读 `.env` 文件内容（仅看是否存在 + 是否被 ignore）
- **新文档**
  - `docs/CLI_COMPLETION.md`
  - `docs/V0_2_FINAL_REVIEW.md`（本文）

## v0.2 全程没做的事（仍坚守）

- ❌ 不调用真实 LLM（fake provider 即可端到端）
- ❌ 不读 `.env` 文件内容（只确认存在 + 是否在 .gitignore）
- ❌ 不做 RAG / embedding / 向量检索
- ❌ 不做 Obsidian 插件 / 浏览器插件
- ❌ 不做 OCR / PDF 表格深度抽取 / Docx 复杂版式
- ❌ 不做自动复习调度（SM-2 / FSRS）
- ❌ 不上传 telemetry，不做远程 dashboard
- ❌ 不修改 `00-Inbox/` 任一原始文件
- ❌ 不自动 approve Knowledge Card
- ❌ 不在 Triager / Distiller 里 `if source_type == "..."`（必须经 adapter 抹平）
- ❌ 不做 LLM fallback / 投票 / 智能路由

## 测试与质量门

- 240 passed, 2 skipped（`pypdf` / `python-docx` 未安装时跳过真实抽取测试）
- `ruff check src tests` clean
- `git diff --check` clean

## v0.3 候选（仅占位，**不**承诺）

按"**好产品**而非堆功能"的原则排序：

1. **CLI polish #3** — `mindforge init`（一键铺 vault skeleton）、`mindforge logs --tail`、彩色错误码白名单
2. **M5.6 Approval workflow** — `mindforge approve <card-id>` / `mindforge unapprove`（仍只改 frontmatter，不改正文）
3. **M5.8 Project profile generator** — `mindforge project init <name>`（最小 stub，不调 LLM）
4. **M4.2 Recall sharpening** — 引入 BM25 lexical（仍不引入 embedding），评分可 explain
5. **M5.1+ PDF/Docx 增强** — 段落结构保留、表格基本抽取（仍不 OCR）
6. **v0.2 tag push 决策** — 是否推到远端、是否做 release notes 自动化

## 下一步推荐

- 先做 **CLI polish #3 / approval workflow**，这两条直接影响"我自己每周会不会用"
- **不要**在 v0.3 起手就引入 embedding / RAG；先把"用不用得起来"打透
- v0.2 系列 tag 仍**保持本地未 push**，等用户决定时机

