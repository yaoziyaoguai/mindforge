# M5.2 — WebClip / ChatExport SourceAdapter Protocol（v0.2.4 ✅ 实装）

> 状态：**v0.2.4 起为真实 adapter**。本文记录两个 adapter 的字段映射、
> 启发式 role 检测策略、以及与 v0.1 安全契约的关系。

---

## 1. 为什么需要这两个 adapter

MindForge 的核心抽象是"adapter 把异构输入翻译成统一 `SourceDocument`"。
在 v0.2.3 之前，Cubox + Plain Markdown 已经覆盖了作者本人主要输入流，
但仍有两类高频材料没有官方通道：

| 输入 | 现实工具 | v0.2.3 之前的做法 | v0.2.4 起 |
|---|---|---|---|
| 网页剪藏 | Obsidian Web Clipper / MarkDownload / SingleFile | 只能伪装成 Cubox 笔记 | `WebClipMarkdownAdapter` 直接吃 |
| AI 对话导出 | ChatGPT / Claude / Copilot 的 Markdown 导出 | 完全不接 | `ChatExportAdapter` 直接吃 |

→ 这两个 adapter 让用户可以把"我自己读到的好文章"和"我自己花时间和 AI 推
出来的结论"以一等公民身份纳入知识管线，而不需要伪造成 Cubox 笔记。

---

## 2. WebClipMarkdownAdapter

- 模块：`src/mindforge/sources/webclip_markdown.py`
- 子目录：`00-Inbox/WebClips/`
- glob：`*.md`
- `source_type`：`webclip_markdown`

### 2.1 frontmatter 字段映射

| 标准字段 | 接受的别名（按优先级） |
|---|---|
| title | `title` / `Title` / `name` / `标题` |
| source_url | `source` / `source_url` / `url` / `URL` / `page_url` / `原文链接` |
| author | `author` / `byline` / `creator` / `作者` |
| tags | `tags` / `tag` / `标签` / `categories` |
| created_at | `created` / `created_at` / `date` / `publish_time` / `publishTime` / `发布时间` |
| captured_at | `captured_at` / `savedAt` / `saved_at` / `clipped_at` / `clipDate` |

### 2.2 title 三级 fallback

1. frontmatter 任一别名命中 → 用之
2. 正文首个 `# H1` → 用之
3. 否则 → 文件 stem

### 2.3 content_hash 关键 metadata

`{title, source_url, author}` —— 不放时间戳，避免 checkpoint 永不命中。

---

## 3. ChatExportAdapter

- 模块：`src/mindforge/sources/chat_export.py`
- 子目录：`00-Inbox/ChatExports/`
- glob：`*.md`（v0.2.4 暂不支持 .json 导出）
- `source_type`：`chat_export`

### 3.1 role 检测启发式

支持两种常见 Markdown 风格：

```
## User                  ← H2 标题风格（ChatGPT Web 导出常见）
...

**Human:**               ← 加粗 + 冒号风格（Claude / Copilot 导出常见）
...
```

冒号位置允许：`**Name**:` / `**Name:**` / `**Name：**`（中文冒号同样支持）。

role 同义词（覆盖中英）：

| 标准 role | 别名 |
|---|---|
| user | user / you / human / me / 用户 |
| assistant | assistant / chatgpt / gpt / claude / copilot / ai / 助手 |
| system | system / 系统 |

### 3.2 失败降级

如果一个角色都没识别到，**不报错**：

- `metadata.turn_count = 0`
- `metadata.role_detection = "degraded_plain_text"`

下游 Triager / Distiller 仍能把整个文件当一段文本处理。

### 3.3 content_hash 关键 metadata

`{title, source_url, turn_count}` —— 把 `turn_count` 放进 hash 是为了让"你
继续追问后又导出一次"能触发重新加工。

### 3.4 v0.1 不在 adapter 层做的事

ChatExport 的内容比网页更"私人"。v0.1 **明确不**在 adapter 层做任何"内容
脱敏"——因为基于关键词的脱敏正确率低、误伤大、给用户错觉。

安全靠三道闸门，不靠 adapter 推断：

1. **runs / telemetry 字段白名单**：`raw_text` / `prompt` / `completion`
   永远不写入持久化日志（详见 `docs/M5_7_TELEMETRY_PROTOCOL.md`）。
2. **approve 显式人审**：所有卡片默认 `ai_draft`，只有 `mindforge approve
   --card <path>` 才能晋升 `human_approved`。
3. **用户在 capture 时自控**：MindForge 不会从聊天记录里"自动抓"任何东西，
   是你主动把导出文件拖进 `00-Inbox/ChatExports/` 才会被处理。

---

## 4. Scanner / 配置变化

`configs/mindforge.yaml` v0.2.4：

```yaml
sources:
  enabled:
    - cubox_markdown
    - plain_markdown
    - webclip_markdown   # NEW
    - chat_export        # NEW
  registry:
    webclip_markdown:
      adapter: WebClipMarkdownAdapter
      inbox_subdir: WebClips
      file_glob: "*.md"
      enabled: true
    chat_export:
      adapter: ChatExportAdapter
      inbox_subdir: ChatExports
      file_glob: "*.md"
      enabled: true
```

Scanner 行为不变：依然只是按 `inbox_subdir + file_glob` 派发到 adapter；
adapter 自己负责解析与 `content_hash` 计算。

---

## 5. 测试清单（`tests/test_v0_2_4.py`）

- ✅ 完整 frontmatter / 仅 H1 / 仅 stem 三种 webclip 输入
- ✅ H2 风格 + 加粗风格 chat_export 各一份
- ✅ chat_export "纯文本无 marker" 降级路径
- ✅ Scanner 启用两类 adapter 后 state.json 出现两种 source_type
- ✅ 通过 fake provider 跑完 process，runs/telemetry 不漏 secret
- ✅ PDF/Docx stub 错误消息引用 `M5_1_PDF_DOCX_ADAPTER_PROTOCOL`

## 6. 不变量

| 项 | 状态 |
|---|---|
| 访问网络 | ❌ |
| 重写源文件 | ❌ |
| OCR / 复杂解析 | ❌ |
| 内容自动脱敏 | ❌（明确反模式） |
| 自动 approve | ❌ |
| 调用真实 LLM（pipeline 之外） | ❌ |
