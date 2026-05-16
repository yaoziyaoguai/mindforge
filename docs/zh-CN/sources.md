# Source 管理

MindForge 中 Source 是你想让 AI 处理的本地文件。支持多种格式，通过统一的 SourceAdapter 层接入处理流水线。

---

## 支持的格式

| 格式 | 扩展名 | 状态 | 可选依赖 |
|------|--------|------|----------|
| Markdown | `.md` | 已支持 | 基础安装 |
| 纯文本 | `.txt` | 已支持 | 基础安装 |
| HTML | `.html` | 已支持 | 基础安装 |
| Word 文档 | `.docx` | 已支持 | `python-docx`（可选） |
| PDF（文本型） | `.pdf` | 已支持 | `pypdf`（可选） |
| 旧版 Word | `.doc` | 不支持 | — |

## 可选依赖

基础安装（`pip install mindforge`）支持 Markdown、TXT、HTML 格式。

如需 PDF / DOCX 支持，安装可选依赖：

```bash
pip install "mindforge[pdf,docx]"
```

或直接安装对应包：

```bash
pip install pypdf python-docx
```

可选依赖缺失时 adapter 会友好跳过并提示安装方法，不影响其他格式的正常处理。

## 限制说明

- **PDF**：仅支持文本型 PDF，提取文字层文本。不含文字层的扫描件 / 图片型 PDF 会被检测并跳过，提示原因。不做 OCR。
- **DOCX**：支持现代 `.docx` 格式。
- **旧版 `.doc`**：不支持。旧版 Word 二进制 `.doc` 文件无法处理。请转换为 `.docx` 或导出为 PDF / TXT，再导入转换后的文件。
- **HTML**：仅本地文件，不抓取 URL、不跟踪链接。
- **超大文件**：超过 50 MB 的 source 会被跳过。

---

## 添加 Source

### watch add（持续监听）

```bash
mindforge watch add <path>
```

注册 source 并启动后台处理。文件变化时自动重新处理。

#### 监听频率

`watch add` 默认注册为 **manual** 频率，不会自动扫描。如需定期自动扫描，通过 `--every` / `--frequency` 指定：

```bash
mindforge watch add <path> --every daily
mindforge watch add <path> --frequency "every 6h"
```

| 频率 | 说明 |
|------|------|
| `manual` | 默认值，不自动扫描；手动运行 `mindforge watch scan` |
| `hourly` / `every 1h` | 每 1 小时扫描 |
| `every 6h` | 每 6 小时扫描 |
| `every 12h` | 每 12 小时扫描 |
| `daily` / `every 24h` | 每 24 小时扫描 |
| `weekly` | 每 7 天扫描 |

查看所有 watched source 的频率和下次扫描时间：

```bash
mindforge watch status
```

没有常驻 daemon。如需定期扫描，配合 cron / launchd / 外部调度定期运行 `mindforge watch scan`。

频率可通过 CLI（`--every` / `--frequency`）或 Web UI（Setup → Add Source 的 Frequency 下拉，或 Sources → Edit frequency）设置。`mindforge watch status` 查看当前配置。

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
