# V0.1 SCOPE — MindForge v0.1 边界单页清单

> 这份文档是 v0.1 的**单页 in/out scope 清单**。任何"我们要不要做 X"的争论，先来这里查一遍。
>
> 配套文档：[`docs/ROADMAP.md`](ROADMAP.md)（Milestone 状态机）、[`docs/MINDFORGE_PROTOCOL.md`](MINDFORGE_PROTOCOL.md)（数据契约）。

---

## ✅ v0.1 IN-SCOPE（必须做）

### 输入
- 多源接入框架（`SourceAdapter` 抽象 + `SourceDocument` 协议）
- **真实实现**：`CuboxMarkdownAdapter`、`PlainMarkdownAdapter`
- **Stub 占位**：`WebClipMarkdownAdapter`、`PdfAdapter`、`DocxAdapter`、`ChatExportAdapter`、`ManualNoteAdapter`

### LLM 处理
- LLM 配置：`active_profile` + `profiles[stage] → model_alias` + `models[alias] → provider/model`
- 同一 provider 下可挂多个 model（`cheap_cloud` / `strong_cloud`、`local_fast` / `local_strong`）
- 五个 stage：`triage` / `distill` / `link_suggestion` / `review_questions` / `action_extraction`
- prompt 版本化（`prompts/<stage>/v1.md` + `manifest.yaml`，文件不可变）

### 输出
- Knowledge Card 写入 `20-Knowledge-Cards/<track>/`
- frontmatter 含 `source_id` / `source_type` / `adapter_name` / `source_url` / `prompt_version` / `profile` / `stage_models` 等多源 + 多 stage 字段
- 内容分层：source_excerpt / ai_summary / ai_inference / human_note / review_questions / suggested_links / project_hooks
- 默认 `status: ai_draft`，必须人工晋升 `human_approved`

### 可观察性
- `.mindforge/state.json`：以 `source_id` 为键，记录 `source_type` / `adapter_name` / `content_hash` / `status` / `stages.<stage>` 子结构
- `.mindforge/runs/<run_id>.jsonl`：每次执行的全事件流；`llm_call` 必须带 stage / model_alias / provider / actual_model / prompt_version / input_file_hash / tokens / latency / status / error_message / processed_at

### CLI（v0.1 四条命令）
- `mindforge scan`
- `mindforge process`
- `mindforge process --file <path>`
- `mindforge status`

### 文档与契约
- `README.md` + `docs/ROADMAP.md` + `docs/MINDFORGE_PROTOCOL.md` + `docs/V0_1_SCOPE.md`
- `configs/mindforge.yaml` + `configs/learning_tracks.yaml` + `configs/llm.example.yaml`
- `templates/knowledge_card.md.j2`
- `prompts/<stage>/v1.md` + `manifest.yaml`（5 个 stage）

---

## ❌ v0.1 OUT-OF-SCOPE（明确不做）

### 客户端集成
- ❌ Obsidian 插件
- ❌ 浏览器插件
- ❌ Cubox API 直连（v0.1 完全靠 Cubox 官方 Obsidian 插件落地的 Markdown）

### 输入源（仅 stub，不实现）
- ❌ PDF 真实解析（不做 OCR / 表格抽取 / 复杂版式）
- ❌ Docx 真实解析（不做复杂样式 / 公式）
- ❌ WebClip 网页抓取（仅消费已落地的 Markdown 文件）
- ❌ ChatExport 解析（接口预留）

### LLM
- ❌ Fallback（某 provider 失败自动切另一个）
- ❌ 多模型投票
- ❌ 按 `value_score` 动态切换模型
- ❌ Token-aware routing（按 prompt 长度自动选模型）
- ❌ Embedding / 向量检索 / RAG
- ❌ Agent loop（多轮工具调用）
- ✅ **支持** "按 stage 静态选不同 model_alias" — 这是配置，不是路由

### 输出 / 流程
- ❌ 自动晋升 `human_approved`
- ❌ 改写 `00-Inbox/**` 任何原始文件
- ❌ 自动复习调度算法（SM-2 / FSRS / Anki 集成）
- ❌ 自动双链回写（不修改其他 Card）
- ❌ 知识图谱可视化 / GUI
- ❌ 多端同步 / 云端 SaaS

### 召回 / 高级
- ❌ `mindforge recall` 等 v0.2/v0.3 命令
- ❌ Weekly review 自动化
- ❌ Project memory 自动写回

---

## 🛑 v0.1 整体停止规则（8 条硬约束）

当**全部**满足以下条件时，v0.1 必须停手、打 tag `v0.1.0`、写复盘，**不**再加功能：

1. ✅ 能扫描 `00-Inbox/`，识别多种 `source_type`
2. ✅ 能为 Cubox Markdown 与 Plain Markdown 生成统一 `SourceDocument`
3. ✅ 能通过 `LLMClient`（profile + stage routing）跑通 `triage` / `distill` / `link_suggestion` / `review_questions` / `action_extraction`
4. ✅ 能写入 `20-Knowledge-Cards/`，frontmatter 字段齐全，默认 `status: ai_draft`
5. ✅ 能在 `state.json` 与 `runs/*.jsonl` 中追溯每个文件的 stage / model_alias / provider / actual_model / prompt_version / content_hash
6. ✅ 人工把 Card `status` 改为 `human_approved` 能被识别并回写 `state.json`
7. ✅ 有最小测试覆盖（adapters / checkpoint / config 校验）
8. ✅ 有 `README.md` + `docs/ROADMAP.md` + `docs/MINDFORGE_PROTOCOL.md` + `docs/V0_1_SCOPE.md` 四份文档

---

## 反 scope creep 决策树

每当你想加一个新东西：

```
问题：这件事真的属于 v0.1 吗？
├─ 是 → 它已经在 IN-SCOPE 列表里吗？
│    ├─ 是 → 做。
│    └─ 否 → 先把它写进本文 IN-SCOPE，再做。
└─ 否 → 把它写进 docs/ROADMAP.md 的对应 Milestone（通常是 M4 或 M5 backlog）；
        v0.1 阶段不要碰。
```

**典型陷阱**（出现时立刻停下）：
- "顺手做一下 PDF 的 OCR"——M5，写进 backlog。
- "加个 fallback 反正不复杂"——v0.1 OUT-OF-SCOPE，拒绝。
- "我做个 Obsidian 插件吧，用户体验更好"——M5，写进 backlog。
- "RAG 一下也不慢"——v0.1 OUT-OF-SCOPE，拒绝。
- "顺便做个复习调度算法"——M5，写进 backlog。

---

## 学习型说明：为什么"明确不做"和"明确做"一样重要？

工程上"做什么"是显性需求，但"不做什么"才是隐性约束。后者决定了：
- **完成时间是否可预测** — 没有不做清单，每个新需求都看起来"也合理"，永远无法收口；
- **架构是否清晰** — 不做 RAG/Fallback/插件，意味着核心模块的边界更窄、更稳；
- **复盘是否可能** — v0.1 完成后，凭着这份清单可以诚实地说"我们做完了说好的事"。

MindForge 是个人项目，没有 PM 帮你抗需求。**这份清单就是你自己给自己的 PM**。
