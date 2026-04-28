# MindForge v0.2.4 Review

> Tag：`v0.2.4`（本地，未 push）
> 主题：**WebClip / ChatExport adapter 实装 + CLI polish + PDF/Docx 协议占位**

---

## 1. 立项动机

v0.2.3 把 MindForge 推到了"能产出多 project 上下文包 + 本地 telemetry"的
节点，但仍然只能消费 Cubox 与 Plain Markdown。两类高频输入还在场外：

- 网页剪藏（Obsidian Web Clipper / MarkDownload / SingleFile）
- AI 对话导出（ChatGPT / Claude / Copilot）

v0.2.4 的目标是**让这两类材料以一等公民身份进入管线**，同时把 CLI 体验
打磨到"敢推荐给非作者本人使用"的最低水位。

> ❌ 本轮**仍然不**做：OCR、复杂 PDF 解析、Obsidian 插件、RAG / embedding、
> 自动 approve、自动复习调度、远程 telemetry 上传、读取 .env。

---

## 2. 交付清单

### 2.1 新增源 adapter（真实实装）

| 文件 | 说明 |
|---|---|
| `src/mindforge/sources/webclip_markdown.py` | 真实 WebClipMarkdownAdapter；title 三级 fallback；frontmatter 字段别名映射 |
| `src/mindforge/sources/chat_export.py` | 真实 ChatExportAdapter；H2 + 加粗双风格 role 检测；degraded plain text 降级 |

### 2.2 重构

| 文件 | 变更 |
|---|---|
| `src/mindforge/sources/stubs.py` | 删 WebClip/ChatExport stub，仅余 PDF/Docx；docstring 重写 |
| `src/mindforge/sources/registry.py` | import 改为按真实模块 + stubs 双源加载 |
| `configs/mindforge.yaml` | `sources.enabled` 增 `webclip_markdown` / `chat_export`；registry 两者 `enabled: true` |

### 2.3 CLI polish（`src/mindforge/cli.py`）

- 新增 `mindforge version`：打印版本 + 配置摘要（vault root / inbox_root /
  cards_dir / projects_dir / state.workdir / active_profile / sources.enabled /
  telemetry status）。**严禁**输出 `.env` 内容、api_key、token、Authorization。
- 新增全局 `--debug`：默认抑制 traceback，加 `--debug` 才打印完整栈。
- `main()` 兜底未捕获异常：非 debug 时只打印一行简短错误，`exit(1)`。
- `_load_cfg`：配置文件不存在时给出可操作提示，不再裸抛。
- 顶层 `--help` 文案改写：列出常用命令一览。

### 2.4 文档（新增）

| 文件 | 说明 |
|---|---|
| `docs/M5_1_PDF_DOCX_ADAPTER_PROTOCOL.md` | PDF/Docx 仍为 stub 的边界与未来约束 |
| `docs/M5_2_WEBCLIP_CHATEXPORT_PROTOCOL.md` | 两个真实 adapter 的字段映射 / role 检测 / 安全契约 |
| `docs/V0_2_4_REVIEW.md` | 本文件 |

### 2.5 测试

新增 `tests/test_v0_2_4.py`，**16** 用例，覆盖：

- WebClip：完整 frontmatter / 仅 H1 / 仅文件名 / md-only / hash 稳定
- ChatExport：H2 角色 / 加粗角色 / degraded plain text / hash 随 turn_count 变化
- PDF/Docx stub：错误消息含 `M5_1_PDF_DOCX_ADAPTER_PROTOCOL`
- CLI：`version` 不漏 secret / 缺 config 不崩 / `--help` 列出关键命令 / `--debug` 接受
- 端到端：webclip + chat_export 文件被 scan 识别 → process 走完 fake → runs / telemetry 字段白名单

---

## 3. 质量门

| 检查 | 结果 |
|---|---|
| `ruff check src tests` | ✅ All checks passed |
| `pytest -q` | ✅ **225 passed**（v0.2.3 基线 209 + 本轮 16） |
| `git diff --check` | ✅ |
| /tmp 沙箱 smoke（scan / process / version / status / telemetry summary） | ✅ 0 secret 泄漏 |

## 4. 安全契约（不变）

- 不调用真实 LLM；测试统一走 fake provider
- 不读 `.env`（`load_dotenv_silently` 仍只在 process / llm ping 入口生效，
  且不打印 value）
- `runs/*.jsonl` 与 `telemetry.jsonl` 仅元数据；正文/prompt/completion/api_key
  永不落盘
- 原始 inbox 文件零改动
- AI 卡片默认 `ai_draft`，只能由 `mindforge approve` 显式晋升

## 5. 下一步建议（任选其一，均为高价值低风险）

1. **M5.5 Obsidian 友好度**（建议）：双链候选生成命令 + `_index.md`
   自动落地，让 vault 真正"被看见"。
2. **M5.1 PDF/Docx 第一刀**：仅 pure-Python lazy import，不做 OCR；先
   消化作者已有的少量学习类 PDF。
3. **CLI polish 第二轮**：`--vault` 全局 override / shell completion /
   `mindforge doctor` 快速诊断。
