"""AdapterResult / ExtractionWarning / ProvenanceBlock — SourceAdapter.load() 的返回契约。

v0.2 M1 把 ``SourceAdapter.load()`` 的返回类型从裸 ``SourceDocument`` 升级为三态
``AdapterResult``（loaded / skipped / failed），让 skip 和 fail 成为一等正常路径，
不再通过 bare exception 表达。

设计边界
--------

- 本模块的类型**仅供 adapter 层使用**。SourceDocument 中 ``extraction_warnings``
  和 ``provenance_blocks`` 字段暂保持 ``list``（非 ``list[ExtractionWarning]`` /
  ``list[ProvenanceBlock]``），以避免 ``base.py`` → ``adapter_result.py`` 的循环
  依赖。
- AdapterResult.document 的运行时类型是 ``SourceDocument``，此处用 ``TYPE_CHECKING``
  导入以避免 adapter_result.py → base.py 的循环依赖（base.py 不 import 本模块，
  所以实际不是循环，但保持导入方向清晰：base.py 是叶子，adapter_result.py 引用它）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mindforge.sources.base import SourceDocument


@dataclass(frozen=True)
class ExtractionWarning:
    """解析过程中产生的非致命 warning。

    adapter 在 load() 过程中遇到可恢复的问题时产生（如编码退化、表格丢失、
    空文件等），不中断解析流程，但记录在案供 Scanner 报告。
    """

    code: str
    """机器可读的 warning code（如 ``"encoding_fallback"``、``"table_loss"``）。"""

    message: str
    """人类可读的描述。"""

    location: str | None = None
    """可选的位置信息（page / line / section）。不是所有 warning 都能定位。"""


@dataclass(frozen=True)
class ProvenanceBlock:
    """source 中单个逻辑块的来源信息。

    对 Markdown baseline 可为空 list；PDF/HTML/DOCX adapter 填充，
    记录每个提取块的物理位置（page / section / byte offset）。
    """

    source_type: str
    """源类型标识（如 ``"pdf"``、``"docx"``、``"txt"``、``"html"``）。"""

    page: int | None = None
    """PDF 页码；非 PDF source 为 None。"""

    section: str | None = None
    """section heading 文本；无 section 结构的 source 为 None。"""

    offset_start: int | None = None
    """块在源文件中的起始字节偏移。"""

    offset_end: int | None = None
    """块在源文件中的结束字节偏移。"""

    extracted_as: str = "text"
    """提取后的格式（``"text"`` / ``"markdown_table"`` / ``"markdown_list"``）。"""


@dataclass(frozen=True)
class AdapterResult:
    """``SourceAdapter.load()`` 的唯一返回类型。

    v0.2 三态契约：
    - ``"loaded"`` → document 非 None，传给 processor。
    - ``"skipped"`` → skip_reason 非空，记录后继续下一个文件。
    - ``"failed"`` → error_message 非空，记录后继续下一个文件。
    """

    status: str
    """三态值：``"loaded"`` / ``"skipped"`` / ``"failed"``。"""

    document: SourceDocument | None = None
    """status == ``"loaded"`` 时非 None；其余状态为 None。"""

    skip_reason: str | None = None
    """status == ``"skipped"`` 时必填。"""

    error_message: str | None = None
    """status == ``"failed"`` 时必填。"""

    warnings: list[ExtractionWarning] = field(default_factory=list)
    """解析过程中产生的 warning 列表（loaded 状态下可能非空）。"""


@dataclass(frozen=True)
class SkipReason:
    """预定义 skip reason 常量词汇表。

    在 ``AdapterResult.skip_reason`` 中使用，确保跨 adapter 的 skip reason
    统一可查询。
    """

    UNSUPPORTED_LEGACY_DOC: str = "unsupported_legacy_doc"
    SCANNED_PDF_NO_TEXT: str = "scanned_pdf_no_text"
    ENCRYPTED_PDF: str = "encrypted_pdf"
    DECODE_ERROR: str = "decode_error"
    BINARY_FILE: str = "binary_file"
    FILE_TOO_LARGE: str = "file_too_large"
    UNSUPPORTED_FORMAT: str = "unsupported_format"
    MISSING_OPTIONAL_DEPENDENCY: str = "missing_optional_dependency"
    EMPTY_FILE: str = "empty_file"


__all__ = [
    "ExtractionWarning",
    "ProvenanceBlock",
    "AdapterResult",
    "SkipReason",
]
