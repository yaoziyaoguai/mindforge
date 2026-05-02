"""SourceMux — 跨源 SourceDocument 去重的薄包装层。

为什么需要
==========

Scanner 假设"一种 source_type 占一个 inbox 子目录、互不重叠"，所以历史
上不需要跨源仲裁。但当用户同时启用 ``cubox_markdown``（Cubox Obsidian
插件离线同步的 .md）和 ``cubox_api``（Cubox JSON export）时，**同一篇
Cubox 文章**会通过两条路径各产出一份 ``SourceDocument``，导致下游
KnowledgeStrategy 重复生成 ai_draft、approve 列表两份候选、Recall 命中
重复内容 —— 这些都是真实可观测的 bug。

设计原则（高内聚 / 低耦合 / Information Hiding）
================================================

1. **不改 Scanner**：组合优于修改。Scanner 仍按 subdir 派发，本模块
   消费它的输出流。
2. **不感知具体 source_type**：去重逻辑只看 ``content_hash``（默认）
   或用户注入的 ``key_fn``。代码里不出现任何 ``cubox`` / ``pdf`` 等
   字符串 —— 由 ``test_mux_does_not_import_any_specific_adapter``
   守护。
3. **opt-in**：默认 CLI 路径不接入 mux，避免改变既有命令行为。引入位置
   由调用方显式决定（Bundle 之外的工作）。
4. **first-seen wins**：保留 ``Iterable[ScanResult]`` 中先出现的 result，
   后到的同 key 视为 duplicate。这把"哪个源优先"的策略外置为**调用方
   的输入顺序**，mux 自身不引入优先级配置。
5. **失败结果不参与去重**：``ScanResult.document is None`` 的错误条目
   全部透传 —— 错误本身是观测信号，去重它会丢失 IO/parse 失败上下文。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Optional

from .scanner import ScanResult
from .sources.base import SourceDocument

KeyFn = Callable[[SourceDocument], str]


def _default_key(doc: SourceDocument) -> str:
    return doc.content_hash


@dataclass(frozen=True)
class MuxStats:
    """mux 运行后的可观测计数。

    - ``yielded``: 实际产出的 ScanResult 数量（含失败）；
    - ``deduped``: 因重复被丢弃的成功 ScanResult 数量；
    - ``by_source``: 每个 source_type 被丢弃的数量，便于排查"哪条链路
      与既有源冲突最多"。
    """

    yielded: int = 0
    deduped: int = 0
    by_source: Mapping[str, int] = field(default_factory=dict)


class SourceMux:
    """跨源去重器。线程不安全；调用方按需创建实例。

    用法 1（流式）::

        mux = SourceMux()
        for r in mux.iter_deduped(scanner.iter_results()):
            process(r)
        print(mux.stats)

    用法 2（单条 feed，便于和其他流水线交错）::

        mux = SourceMux()
        for r in scanner.iter_results():
            kept = mux.feed(r)
            if kept is not None:
                process(kept)
    """

    def __init__(self, *, key_fn: KeyFn | None = None) -> None:
        self._key_fn: KeyFn = key_fn or _default_key
        self._seen_keys: set[str] = set()
        self._yielded = 0
        self._deduped = 0
        self._by_source: dict[str, int] = {}

    # -- public ----------------------------------------------------------------

    def feed(self, result: ScanResult) -> Optional[ScanResult]:
        """喂入单条 ScanResult；新值返回原对象，重复返回 None。

        失败结果（document is None）始终视为新值透传，不入 seen 表，
        以保留所有错误观测信号。
        """

        if result.document is None:
            self._yielded += 1
            return result

        key = self._key_fn(result.document)
        if key in self._seen_keys:
            self._deduped += 1
            self._by_source[result.source_type] = self._by_source.get(result.source_type, 0) + 1
            return None
        self._seen_keys.add(key)
        self._yielded += 1
        return result

    def iter_deduped(self, results: Iterable[ScanResult]) -> Iterator[ScanResult]:
        """惰性流式去重。"""

        for r in results:
            kept = self.feed(r)
            if kept is not None:
                yield kept

    @property
    def stats(self) -> MuxStats:
        return MuxStats(
            yielded=self._yielded,
            deduped=self._deduped,
            by_source=dict(self._by_source),
        )


__all__ = ["SourceMux", "MuxStats"]
