"""SourceDocument / Highlight / SourceAdapter — MindForge 多源接入协议层。

设计意图（学习要点）
====================

为什么要这一层？
----------------
MindForge 的输入是异构的：Cubox 同步的 Markdown、Obsidian 手写笔记、Web
Clipper 网页快照、PDF、Docx、ChatGPT 对话导出 …… 如果加工管线（Triager /
Distiller / Linker / Writer）直接读这些原始格式，它将永远在做"格式分支"：

    if source_type == "cubox":
        ...
    elif source_type == "pdf":
        ...

这是 v0.1 明确禁止的反模式。我们用一个统一的 ``SourceDocument`` 作为
**adapter 与下游加工的契约**，把所有异构性都收敛在 adapter 内部消化掉。

协议边界
--------
- ``SourceDocument``：纯数据，**不可变快照**，由 adapter 在 ``load()`` 时构造。
- ``Highlight``：原文中的划线 / 批注（部分 source 适用，例如 Cubox）。
- ``SourceAdapter``：抽象基类，子类必须实现 ``can_handle`` 与 ``load``。

后续 adapter（cubox_markdown / plain_markdown / pdf / docx / ...）只需继承
``SourceAdapter`` 并把自己的格式细节翻译成 ``SourceDocument`` 即可，下游永远
看到同一种数据形状。
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

# ---------------------------------------------------------------------------
# v0.1 支持的 source_type 枚举（与 configs/mindforge.yaml.sources.registry 对齐）
#
# 加新类型必须同步：
#   1. 此处 SourceType
#   2. configs/mindforge.yaml.sources.registry
#   3. docs/MINDFORGE_PROTOCOL.md §SourceDocument 协议
#   4. 一个具体 adapter 实现
# ---------------------------------------------------------------------------
SourceType = Literal[
    "cubox_markdown",
    "plain_markdown",
    "webclip_markdown",
    "pdf",
    "docx",
    "chat_export",
    "manual_note",
]


@dataclass(frozen=True)
class Highlight:
    """原文划线 / 批注。

    并非所有 source 都有 highlight：
    - Cubox 通常有；
    - PlainMarkdown 通常没有（除非用户在文中显式标注）；
    - PDF v0.1 不实现；

    设计为 ``frozen=True``：highlight 是历史快照，不应在加工管线中被改写。
    """

    text: str
    note: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class SourceDocument:
    """Adapter 的统一输出 / 下游加工的统一输入。

    13 个字段对应 ``docs/MINDFORGE_PROTOCOL.md`` 中的"SourceDocument 数据契约"。
    任何字段语义变更都必须同步更新协议文档与 ``state.json`` schema。

    字段说明
    --------
    source_id : str
        稳定主键，建议 ``sha1(source_path)`` 或 adapter 自定义。下游用它做
        ``state.json`` 的索引、卡片 frontmatter 反向引用。
    source_type : SourceType
        来源类型枚举，决定使用哪个 adapter 重新读取。
    source_path : str
        相对 vault 或绝对路径。用于人类阅读和回放定位。
    title, author, source_url : Optional[str]
        基础元信息；不是所有 source 都齐全。
    created_at : Optional[datetime]
        原文创建时间（如网页发布时间）。
    captured_at : Optional[datetime]
        被你 capture 的时间（如 Cubox 收藏时间）。
    tags : list[str]
        原始标签（adapter 不负责清洗，只负责忠实搬运）。
    highlights : list[Highlight]
        原文划线列表，可为空。
    raw_text : str
        统一的纯文本 / Markdown 表达，**这是 LLM 真正读到的东西**。
        adapter 的核心职责就是把异构格式转换成它。
    metadata : dict
        adapter 特有字段，**不污染主结构**。例如 Cubox 的 highlight color，
        PDF 的 page_count 等都进这里，下游加工不感知。
    content_hash : str
        ``sha256(raw_text + 关键 metadata)``。用于 checkpoint 判断"内容是否
        变化"——没变就跳过 LLM 加工，省钱省时间。
    adapter_name : str
        v0.4.2 显式回填：解析出本文档的 adapter 类名（如 ``"PlainMarkdownAdapter"``）。
        用于追溯"这条记录是哪个 adapter 解析出来的"，与 ``state.json`` 中
        的 ``adapter_name`` 字段对齐。adapter 自身可不填；Scanner 会在派发后
        统一回填，避免每个 adapter 重复 boilerplate。
    """

    source_id: str
    source_type: SourceType
    source_path: str
    title: str | None = None
    author: str | None = None
    source_url: str | None = None
    created_at: datetime | None = None
    captured_at: datetime | None = None
    tags: list[str] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)
    raw_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    adapter_name: str = ""

    def __post_init__(self) -> None:
        # 强契约：source_id / source_type / source_path / content_hash 必填。
        # raw_text 允许为空字符串（极端情况下原文确实没有正文），但 adapter
        # 应该尽力提供。
        if not self.source_id:
            raise ValueError("SourceDocument.source_id 不能为空")
        if not self.source_type:
            raise ValueError("SourceDocument.source_type 不能为空")
        if not self.source_path:
            raise ValueError("SourceDocument.source_path 不能为空")
        if not self.content_hash:
            raise ValueError(
                "SourceDocument.content_hash 不能为空；"
                "请在 adapter.load() 中调用 compute_content_hash()"
            )


def compute_content_hash(raw_text: str, key_metadata: dict[str, Any] | None = None) -> str:
    """计算 SourceDocument.content_hash 的标准实现。

    协议：``sha256(raw_text || "\\x00" || sorted_json(key_metadata))``。

    - ``raw_text`` 为主，因为它是 LLM 真正消费的内容。
    - ``key_metadata`` 仅放"会影响加工结果"的 metadata 子集（如 source_url、
      author 等）。**不要**放时间戳之类每次都变的字段，否则 checkpoint 永远
      命中不上。
    - adapter 必须使用此函数，确保 hash 算法跨 adapter 一致。
    """
    h = hashlib.sha256()
    h.update(raw_text.encode("utf-8"))
    if key_metadata:
        # sort_keys=True 保证同一组 metadata 总是同一 hash，与字典插入顺序无关
        h.update(b"\x00")
        h.update(json.dumps(key_metadata, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return f"sha256:{h.hexdigest()}"


class SourceAdapter(ABC):
    """所有 source adapter 的抽象基类。

    子类契约
    --------
    - 类属性 ``name``：adapter 的稳定标识（如 ``"CuboxMarkdownAdapter"``），
      用于 ``state.json`` 的 ``adapter_name`` 字段以追溯"这条记录是哪个
      adapter 解析出来的"。
    - 类属性 ``source_type``：本 adapter 输出的 ``SourceDocument.source_type``。
    - ``can_handle(path)``：根据路径 / 后缀 / 子目录决定能否处理。
      Scanner 用它在派发歧义时做兜底判断；通常 registry 已按子目录派发，
      adapter 自身做的是二次确认。
    - ``load(path)``：读文件、解析、构造 ``SourceDocument``。**adapter 的
      所有"格式特异性"都在这一步消化掉，**不得向上层暴露原始格式细节。

    禁止
    ----
    - 在 adapter 中调用 LLM；
    - 在 adapter 中写文件；
    - 在 adapter 中改写 ``00-Inbox/`` 下任何文件（**只读**原则）。
    """

    #: adapter 的稳定标识（写入 state.json）
    name: str = ""
    #: 本 adapter 输出的 source_type
    source_type: SourceType = "plain_markdown"  # type: ignore[assignment]

    @abstractmethod
    def can_handle(self, path: str) -> bool:
        """判断此 adapter 能否处理给定路径的文件。

        实现建议：检查文件后缀、可选地 peek 文件头几行 frontmatter。
        **不要**做完整解析（那是 ``load`` 的事）。
        """

    @abstractmethod
    def load(self, path: str) -> SourceDocument:
        """加载并解析路径，返回 ``SourceDocument``。

        失败时应抛出明确异常（``FileNotFoundError`` / ``ValueError`` 等），
        由 Scanner 决定是否将此条目标记为 ``failed`` 并继续后续文件。
        """

    def __repr__(self) -> str:  # pragma: no cover - 仅调试可读性
        return (
            f"<{self.__class__.__name__} "
            f"name={self.name!r} source_type={self.source_type!r}>"
        )


__all__ = [
    "SourceType",
    "Highlight",
    "SourceDocument",
    "SourceAdapter",
    "compute_content_hash",
]
