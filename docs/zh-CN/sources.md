# Source 管理

MindForge 中 Source 是你想让 AI 处理的本地文件。支持多种格式，通过统一的 SourceAdapter 层接入处理流水线。

---

## 支持的格式

| 格式 | 扩展名 | 状态 |
|------|--------|------|
| Markdown | `.md` | 已支持 |
| 纯文本 | `.txt` | 已支持 |
| HTML | `.html` | 已支持 |
| Word 文档 | `.docx` | 已支持 |
| PDF（文本型） | `.pdf` | 已支持 |
| 旧版 Word | `.doc` | 不支持 |

---

## 添加 Source

### watch add（持续监听）

```bash
mindforge watch add <path>
```

注册 source 并启动后台处理。文件变化时自动重新处理。

### import（一次性导入）

```bash
mindforge import <path>
```

导入并处理一次，不持续监听。

---

## 路径规则

### Web Add Source

必须使用绝对路径：

- `~/Documents/note.md` → 自动展开为 `/Users/<name>/Documents/note.md`
- `note.md` → 返回 400，请用绝对路径
- 路径不存在 → 返回 400

### CLI

支持相对路径，按 cwd → project-root → active-vault 自动解析为绝对路径。路径不存在时 exit_code=2 + 中文错误消息。

---

## SourceAdapter 层

SourceAdapter 将不同格式归一化为统一处理流水线。文件格式差异在适配器层处理，后续 step 不感知原始格式。

---

## 管理 Source

### 查看状态

Web **Sources** 页面列出所有已注册 source 及其处理状态。

### 停止监听

在 Web Sources 页面操作。Stop watching **不删除** source 文件。

### Move to Trash

删除知识卡片不会影响原始 source 文件。

---

## 最佳实践

- Source 放在 `vault/00-Inbox/` 下即可，无需预建分类子目录
- 长文档建议先拆分为较小文件，避免 provider timeout
- 非敏感资料先小批量验证，确认流程正常后再扩大范围
