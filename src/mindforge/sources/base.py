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
#   3. README.md 的 SourceDocument 协议
#   4. 一个具体 adapter 实现
# ---------------------------------------------------------------------------
SourceType = Literal[
    "cubox_markdown",
    "cubox_api",
    "plain_markdown",
    "webclip_markdown",
    "pdf",
    "docx",
    "chat_export",
    "manual_note",
    "obsidian_note",
    "common_document",
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

    13 个字段对应 ``README.md`` 中的"SourceDocument 数据契约"。
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

    # ------------------------------------------------------------------
    # v0.9 Slice 1：provenance-completeness 查询面（仅查询，不抛错）。
    #
    # 为什么不在 ``__post_init__`` 里强制 ``adapter_name`` 非空？
    # ----------------------------------------------------------
    # 历史决策（v0.4.2，见 ``src/mindforge/scanner.py`` L80-86 与本文件
    # ``adapter_name`` 字段 docstring）：adapter 自身可以省略 adapter_name，
    # 由 Scanner 在派发后统一回填。这把"我是谁"的样板代码集中在框架，
    # 是 Information Hiding 的体现，不是疏漏。
    #
    # v0.9 Slice 1 的契约升格因此采用**查询接口**而非构造期断言：
    # - 构造仍允许空 ``adapter_name``，保留 Scanner-backfill 的优雅；
    # - 但任何对外发出（emit / persist / state.json 写入 / 下游消费）
    #   的 ``SourceDocument`` 必须能通过 ``is_provenance_complete()``，
    #   否则说明 backfill 链路出 bug，应在 Scanner 出口做校验，而不是
    #   倒逼每个 adapter 重复同一行 ``adapter_name=self.name``。
    #
    # 这同时避免了"为加一行校验而修改 7 个 adapter + 5 个测试 fixture"
    # 的机械搬运式扩散，保住了 Slice 1 "最小、聚焦、不制造新巨石" 原则。
    # ------------------------------------------------------------------
    def is_provenance_complete(self) -> bool:
        """provenance 是否齐全到可以对外发出。

        v0.9 Slice 1 契约：齐全 = ``adapter_name`` 非空字符串。

        其余 provenance 字段（``title`` / ``author`` / ``source_url`` /
        ``created_at`` / ``captured_at``）属于"尽力而为" 元信息，**不**
        纳入 completeness 判定 —— 例如手写 ``manual_note`` 通常没有
        ``source_url``，强制要求会让正常路径失败。

        返回 ``True`` 表示 ``adapter_name`` 已被填入；否则 ``False``。
        本方法不抛异常、不修改状态、不做 IO，是纯函数。
        """
        return bool(self.adapter_name)


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

    # ------------------------------------------------------------------
    # v0.9 Slice 2：capability 自我声明（Airbyte spec/discover 模式的本地化）
    #
    # 为什么是普通方法而非抽象方法？
    # ------------------------------
    # 抽象方法会强迫 8 个 adapter 全部 override，等价于"为加 capability
    # 而把同一行复制 8 遍"——这正是机械搬运反模式。提供一个安全的
    # 默认实现 ``frozenset({"local_file", "fake_safe", "dry_run"})``：
    # - 7 个本地文件 adapter 用默认即可（它们都是读本地文件、无网络、
    #   fake-default 安全）；
    # - ``CuboxApiAdapter`` override 后追加 ``"real_api"``，显式标记自己
    #   持有真实 API 路径（实际真实调用仍由 ``fetch_inbox`` 的
    #   ``NotImplementedError`` opt-in 闸门把守，capability 只是声明）。
    #
    # capability 词表（v0.9 Slice 2 起锁定）
    # --------------------------------------
    # - ``local_file``：从本地文件 / 目录 / 导出包读取，**不**触网络。
    # - ``fake_safe``：实例化 / can_handle / capabilities 三个调用必定
    #   不做副作用（无文件写、无网络、无 .env 读、无 secret 暴露）。
    # - ``dry_run``：可在不消费真实凭据的前提下端到端跑通"扫描 → 解析
    #   → 输出 SourceDocument"，便于 CLI ``--dry-run`` 链路。
    # - ``real_api``：**显式 opt-in** 的真实远端 API 路径；声明此能力
    #   不等于默认调用，只意味着该 adapter 持有真实 API 入口（且必须
    #   通过单独的凭据注入才能真正打开）。
    #
    # 设计边界
    # --------
    # capabilities() 必须是**纯查询**：不打开文件、不发网络、不读 env。
    # ``tests/test_source_adapter_capabilities.py::test_capabilities_does_no_io``
    # 用 monkeypatch 把 ``builtins.open`` / ``socket.socket`` 替换为抛错
    # 哨兵以静态守卫这条契约。
    # ------------------------------------------------------------------
    def capabilities(self) -> frozenset[str]:
        """返回 adapter 自我声明的能力标签集合（不可变 frozenset[str]）。

        默认实现覆盖所有"本地文件、fake-default 安全、可 dry-run"的
        adapter；持有真实 API 路径的 adapter（目前只有
        ``CuboxApiAdapter``）应 override 并 union 进 ``"real_api"``。

        本方法**不得**触发任何 IO / 网络 / .env 读取，调用方可以在
        runtime 早期廉价获取所有 adapter 的能力集合，做"先 spec 再
        invoke"的安全检查。
        """
        return frozenset({"local_file", "fake_safe", "dry_run"})

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
