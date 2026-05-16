"""v0.2 SourceAdapter 抽象基类。

与 v0.1 ``base.SourceAdapter`` 的关键差异：
- ``load()`` 返回 ``AdapterResult``（三态），而非裸 ``SourceDocument``。
- 本接口是 v0.2 的 source-layer boundary，不改变 processing / approval / wiki 语义。

RFC_0001 §5.1 定义了本接口的完整 contract。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mindforge.sources.adapter_result import AdapterResult


class SourceAdapter(ABC):
    """v0.2 source adapter 抽象基类。

    每个具体 adapter 必须实现 ``can_handle`` 和 ``load``。
    ``load()`` 必须返回 ``AdapterResult``，不通过抛异常表达正常 skip/fail。
    """

    #: adapter 的稳定标识（如 ``"PlainMarkdownAdapter"``）。
    name: str = ""
    #: 本 adapter 输出的 source_type。
    source_type: str = ""

    @abstractmethod
    def can_handle(self, path: str) -> bool:
        """判断本 adapter 能否处理给定路径的文件。

        实现建议：按后缀判断，可选 peek 文件头做二次确认。
        不应做完整解析（那是 ``load`` 的职责）。
        """

    @abstractmethod
    def load(self, path: str) -> AdapterResult:
        """加载并解析路径，返回 ``AdapterResult``。

        三态契约：
        - ``"loaded"`` → document 非 None，传给 processor
        - ``"skipped"`` → skip_reason 非空，记录后继续
        - ``"failed"`` → error_message 非空，记录后继续

        不抛异常表达正常 skip/fail 路径。
        """

    def capabilities(self) -> frozenset[str]:
        """返回 adapter 自我声明的能力标签集合。

        默认实现覆盖本地文件 adapter 的通用能力。
        """
        return frozenset({"local_file", "fake_safe", "dry_run"})

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"name={self.name!r} source_type={self.source_type!r}>"
        )


__all__ = ["SourceAdapter"]
