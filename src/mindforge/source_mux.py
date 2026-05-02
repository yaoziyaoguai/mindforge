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

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Optional

from .scanner import ScanResult
from .sources.base import SourceDocument

KeyFn = Callable[[SourceDocument], str]


def _default_key(doc: SourceDocument) -> str:
    return doc.content_hash


@dataclass(frozen=True)
class DedupAuditEntry:
    """单条 dedup 审计记录 —— 不可变，可序列化。

    用户排查"为什么我的某条 Cubox 文章在 OPS 里没出现"时，可以从
    ``MuxStats.audit_trail`` 反查：被丢的 source_id 是什么？同 key
    的另一份是哪条先到？dedup_key 用的是哪个值？

    注意：此 dataclass 只承载**可读审计信号**，不承载 SourceDocument
    本体（避免 audit_trail 体量随 raw_text 膨胀）。
    """

    dropped_source_id: str
    dropped_source_type: str
    dropped_adapter_name: str
    kept_source_id: str
    dedup_key: str


@dataclass(frozen=True)
class MuxStats:
    """mux 运行后的可观测计数 + 审计轨迹。

    - ``yielded``: 实际产出的 ScanResult 数量（含失败）；
    - ``deduped``: 因重复被丢弃的成功 ScanResult 数量；
    - ``by_source``: 每个 source_type 被丢弃的数量，便于排查"哪条链路
      与既有源冲突最多"；
    - ``audit_trail``: 每条 dedupe 决策的不可变记录，顺序与丢弃发生
      顺序一致。空 tuple 表示无丢弃 / 无观测——保持向后兼容默认。
    """

    yielded: int = 0
    deduped: int = 0
    by_source: Mapping[str, int] = field(default_factory=dict)
    audit_trail: Sequence[DedupAuditEntry] = field(default_factory=tuple)


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
        # key -> 先到那一份的 source_id；用于 dedup audit 中的 kept_source_id 字段。
        self._seen: dict[str, str] = {}
        self._yielded = 0
        self._deduped = 0
        self._by_source: dict[str, int] = {}
        self._audit: list[DedupAuditEntry] = []

    # -- public ----------------------------------------------------------------

    def feed(self, result: ScanResult) -> Optional[ScanResult]:
        """喂入单条 ScanResult；新值返回原对象，重复返回 None。

        失败结果（document is None）始终视为新值透传，不入 seen 表，
        以保留所有错误观测信号。
        """

        if result.document is None:
            self._yielded += 1
            return result

        doc = result.document
        key = self._key_fn(doc)
        kept = self._seen.get(key)
        if kept is not None:
            self._deduped += 1
            self._by_source[result.source_type] = (
                self._by_source.get(result.source_type, 0) + 1
            )
            self._audit.append(
                DedupAuditEntry(
                    dropped_source_id=doc.source_id,
                    dropped_source_type=result.source_type,
                    dropped_adapter_name=result.adapter_name,
                    kept_source_id=kept,
                    dedup_key=key,
                )
            )
            return None
        self._seen[key] = doc.source_id
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
            audit_trail=tuple(self._audit),
        )


__all__ = ["SourceMux", "MuxStats", "DedupAuditEntry"]
