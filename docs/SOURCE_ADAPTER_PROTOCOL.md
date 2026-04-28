# SourceAdapter Protocol — MindForge 多源接入层

> v0.4.2 起作为正式协议固化。**新增数据源 = 写一个 Adapter + 在 registry 注册**，
> 不需要改 scanner / processor / pipeline / cli 任何一行。

## 1. 为什么有这一层

MindForge 的输入是异构的：Cubox / Obsidian 手写笔记 / Web Clipper / PDF /
Docx / ChatGPT 导出 …… 如果加工管线（Triager / Distiller / Linker / Writer）
直接读这些原始格式，就会永远在做"格式分支"：

```python
if source_type == "cubox":
    ...
elif source_type == "pdf":
    ...
```

这是 v0.1 明确禁止的反模式。我们把所有异构性都收敛在 Adapter 内部消化掉，
对下游永远只暴露一个 **`SourceDocument`** 契约。

## 2. 协议三件套

### 2.1 `SourceDocument`（不可变快照）

```
source_id        # 稳定主键（state.json 索引）
source_type      # 枚举：cubox_markdown / plain_markdown / webclip_markdown
                 #       / pdf / docx / chat_export / manual_note
source_path      # 路径
title            # 可选元信息
author
source_url
created_at
captured_at
tags             # 原始标签，adapter 不清洗
highlights       # 原文划线（部分 source 适用）
raw_text         # 统一纯文本/markdown，**LLM 真正读到的东西**
metadata         # adapter 私有字段（如 PDF page_count）
content_hash     # sha256(raw_text + 关键 metadata)，checkpoint 用
adapter_name     # v0.4.2 新增 — Scanner 自动回填，便于追溯
```

`@dataclass(frozen=True)`：下游不能改其内容。

### 2.2 `SourceAdapter`（抽象基类）

```python
class SourceAdapter(ABC):
    name: str = ""              # 写入 state.json 的稳定标识
    source_type: SourceType     # 本 adapter 输出的 source_type

    @abstractmethod
    def can_handle(self, path: str) -> bool: ...
    @abstractmethod
    def load(self, path: str) -> SourceDocument: ...
```

**契约（强制）**：
- adapter 不调用 LLM；
- adapter 不写文件；
- adapter 不修改 inbox；
- adapter 默认 **local-only**；未来若需要联网必须在 yaml 中显式声明 `network: true`
  且在 `M5.X` 协议里走单独评审；
- PDF/Docx adapter **不**做 OCR、**不**做复杂版式；
- ChatExport adapter **不**做隐私脱敏推断。

### 2.3 `AdapterRegistry`（`_BUILTIN_ADAPTERS` + `build_active_adapters`）

```python
_BUILTIN_ADAPTERS = {
    "CuboxMarkdownAdapter": CuboxMarkdownAdapter,
    "PlainMarkdownAdapter": PlainMarkdownAdapter,
    "WebClipMarkdownAdapter": WebClipMarkdownAdapter,
    "PdfAdapter": PdfAdapter,
    "DocxAdapter": DocxAdapter,
    "ChatExportAdapter": ChatExportAdapter,
}
```

`build_active_adapters(cfg.sources)` 根据 yaml 实例化 adapter，并校验
`adapter.source_type == registry 中的 source_type`，对不上直接 fail-fast。

## 3. 加一个新 source（举例：NotionAdapter）

最少改动：

1. 写 `src/mindforge/sources/notion.py`：实现 `NotionAdapter(SourceAdapter)`；
2. 在 `src/mindforge/sources/registry.py` 的 `_BUILTIN_ADAPTERS` 加一行：
   `"NotionAdapter": NotionAdapter,`；
3. 在 `src/mindforge/sources/base.py` 的 `SourceType` 加 `"notion"`；
4. 用户 yaml 中加：
   ```yaml
   sources:
     enabled: [..., notion]
     registry:
       notion:
         adapter: NotionAdapter
         inbox_subdir: Notion
         file_glob: "*.md"
   ```
5. 写 1-2 个测试（参考 `tests/test_v0_4_2.py`）。

**完全不需要**改：scanner、processor、pipeline、cli、recall、index、review、
project context。

## 4. 安全边界（再次强调）

- adapter 可以读取原始文件；
- runs / telemetry / state.json **绝不**记录 raw_text 全文（只记 hash + 元信息）；
- adapter 不能读取 `.env`；
- adapter 不能联网，除非未来某个 adapter 明确声明 `network=true` 并经评审；
- v0.x 默认所有 adapter 都是 local-only。

## 5. 数据流

```
00-Inbox/<sub>/file.ext
        │
        ▼
   SourceAdapter.load()       ← 异构格式在此被消化
        │
        ▼
    SourceDocument            ← 唯一对下游可见的契约
        │
        ▼
LLM Pipeline (Triager → Distiller → Linker → Writer)
        │
        ▼
  20-Knowledge-Cards/*.md   (status: ai_draft)
        │
        ▼ mindforge approve
  status: human_approved
        │
        ▼
  Recall / Review / Project Context
```

## 6. 与 v0.4.2 之前的差异

| 项 | 之前 | v0.4.2 |
|---|---|---|
| `SourceDocument.adapter_name` | ❌（仅 ScanResult / state.json） | ✅ 新字段，默认空，Scanner 自动回填 |
| AdapterRegistry | ✅ 已存在 | 文档化为正式协议 |
| 新增 source 是否动核心 | 否 | 否（已固化） |
| 文档化程度 | 散落在 `MINDFORGE_PROTOCOL.md` | 独立成文（本文件） |

## 7. 不做（明示）

- 不做"adapter 自动发现"；新 adapter 必须在 `_BUILTIN_ADAPTERS` 显式注册；
- 不做"adapter 链式 fallback"；一个文件只能由 1 个 adapter 处理（按子目录派发）；
- 不做"远程 adapter"；v0.x 全部本地；
- 不做"adapter 配置热加载"；改 yaml 后重启 CLI 进程即可。
