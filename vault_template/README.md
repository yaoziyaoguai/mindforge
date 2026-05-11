# Obsidian Vault 推荐结构（MindForge v0.1）

> 本目录是一份**示例 Vault 骨架**。MindForge 不强制你的 Vault 与本结构一比一对应，
> 但 inbox 子目录与 cards 目录的命名约定必须与 `configs/mindforge.yaml` 中
> `vault.inbox_root` / `vault.cards_dir` / `sources.registry.*.inbox_subdir` 保持一致。

## 顶层约定

```
ObsidianVault/
├── 00-Inbox/                  ← MindForge 只读，所有源都进这里
│   ├── ManualNotes/           ← 自己写的临时笔记（plain_markdown）—— 推荐入口
│   ├── PDFs/                  ← 手动放入 PDF
│   ├── Docs/                  ← docx 等文档
│   ├── WebClips/              ← Web Clipper / MarkDownload
│   ├── ChatExports/           ← ChatGPT / Claude 对话导出
│   └── Cubox/                 ← （可选）Cubox Obsidian 插件同步，非默认 first-run 目录
├── 20-Knowledge-Cards/        ← MindForge Writer 唯一写入区
│   ├── agent-runtime/
│   ├── harness-engineering/
│   ├── context-engineering/
│   ├── claude-code-codex/
│   ├── software-architecture/
│   ├── data-engineering/
│   ├── stock-analysis/
│   └── unrouted/
├── 30-Projects/               ← 你手动维护的项目主笔记（MindForge 只读）
├── 40-Reviews/                ← 复习/汇总（v0.2+ 才会自动写入）
├── 90-Archive/
│   └── Skipped/               ← value_score 不达标的素材链接清单
└── _attachments/              ← 图片等附件
```

## 三条物理隔离原则

1. **`00-Inbox/**` 一律只读**：MindForge 永不写、不删、不重命名。
2. **`20-Knowledge-Cards/**` 由 MindForge 创建**：人工只改 `status` / `Human Note`。
3. **`30-Projects/**` 完全人工维护**：MindForge 只读，用作召回锚点。

## 与多源 adapter 的对应关系

| 子目录 | source_type | adapter | v0.1 状态 |
|---|---|---|---|
| `ManualNotes/` | `plain_markdown` | `PlainMarkdownAdapter` | ✅ 实现 |
| `WebClips/` | `webclip_markdown` | `WebClipMarkdownAdapter` | 🟡 stub |
| `PDFs/` | `pdf` | `PdfAdapter` | 🟡 stub |
| `Docs/` | `docx` | `DocxAdapter` | 🟡 stub |
| `ChatExports/` | `chat_export` | `ChatExportAdapter` | 🟡 stub |
| `Cubox/`（可选） | `cubox_markdown` | `CuboxMarkdownAdapter` | ✅ 实现（optional adapter） |

详细数据契约见 `docs/MINDFORGE_PROTOCOL.md`。
