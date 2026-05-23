"""M4 Source Location Parser — SDD §8.1。

把 v0.2 ProvenanceBlock 转换为 v0.3 SourceLocation。
每种 source_type 的映射规则由 RFC_0003 §7 FR4.1-4.5 定义。
"""

from __future__ import annotations

from typing import Any

from mindforge.provenance.location import SourceLocation
from mindforge.sources.adapter_result import ProvenanceBlock


def parse_source_location(
    source_type: str,
    provenance_blocks: list[Any] | None,
) -> SourceLocation | None:
    """从 ProvenanceBlock 列表中提取最佳 SourceLocation。

    按 source_type 选择第一个有意义的 provenance block 进行转换。
    返回 None 表示无可用位置信息。
    """
    if not provenance_blocks:
        return None

    for block in provenance_blocks:
        loc = _block_to_location(source_type, block)
        if loc is not None and _has_meaningful_data(loc):
            return loc

    return None


def _block_to_location(
    source_type: str,
    block: Any,
) -> SourceLocation | None:
    """单个 provenance block 转 SourceLocation。"""
    if isinstance(block, ProvenanceBlock):
        return _from_provenance_block(source_type, block)
    if isinstance(block, dict):
        return _from_dict(source_type, block)
    return None


def _from_provenance_block(
    source_type: str,
    block: ProvenanceBlock,
) -> SourceLocation:
    """从强类型 ProvenanceBlock 构造 SourceLocation。"""
    heading_path: tuple[str, ...] | None = None
    if block.section:
        heading_path = tuple(p.strip() for p in block.section.split(">"))

    return SourceLocation(
        source_type=source_type,
        heading_path=heading_path,
        line_start=_offset_to_line(block.offset_start),
        line_end=_offset_to_line(block.offset_end),
        page_number=block.page,
        paragraph_start=block.offset_start,
        paragraph_end=block.offset_end,
    )


def _from_dict(
    source_type: str,
    block: dict,
) -> SourceLocation:
    """从 dict 形态的 provenance block 构造 SourceLocation。"""
    section = block.get("section")
    heading_path: tuple[str, ...] | None = None
    if isinstance(section, str) and section.strip():
        heading_path = tuple(p.strip() for p in section.split(">"))

    return SourceLocation(
        source_type=source_type,
        heading_path=heading_path,
        line_start=_offset_to_line(block.get("offset_start")),
        line_end=_offset_to_line(block.get("offset_end")),
        page_number=_int_or_none(block.get("page")),
        paragraph_start=_int_or_none(block.get("offset_start")),
        paragraph_end=_int_or_none(block.get("offset_end")),
        css_selector=_str_or_none(block.get("css_selector")),
    )


def source_location_to_dict(loc: SourceLocation | None) -> dict | None:
    """将 SourceLocation 序列化为适合模板渲染的 dict。"""
    if loc is None:
        return None
    return {
        "source_type": loc.source_type,
        "heading_path": list(loc.heading_path) if loc.heading_path else None,
        "line_start": loc.line_start,
        "line_end": loc.line_end,
        "page_number": loc.page_number,
        "paragraph_start": loc.paragraph_start,
        "paragraph_end": loc.paragraph_end,
        "css_selector": loc.css_selector,
        "display": loc.to_display(),
    }


def _has_meaningful_data(loc: SourceLocation) -> bool:
    """检查 SourceLocation 是否包含至少一个有意义的位置字段。"""
    return (
        loc.heading_path is not None
        or loc.line_start is not None
        or loc.page_number is not None
        or loc.paragraph_start is not None
        or loc.css_selector is not None
    )


def _offset_to_line(offset: int | None) -> int | None:
    """字节偏移近似为行号（假设平均 80 字节/行）。

    这是近似值 — 精确行号需要读取源文件，不在 location_parser 职责范围。
    """
    if offset is None:
        return None
    return max(1, offset // 80 + 1)


def _int_or_none(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _str_or_none(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip() or None
    return str(v).strip() or None
