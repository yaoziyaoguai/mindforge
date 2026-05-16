"""v0.2 TxtAdapter — 本地纯文本文件的 SourceAdapter。

RFC_0001 §5.6 要求 TXT adapter 保留原始换行、拒绝二进制文件，并把编码失败
表达为 friendly skip。这里保持实现窄而直：只处理 ``.txt``，不接 registry、
不触发 processing / approval / wiki，也不读取任何 secrets。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from mindforge.sources.adapter_result import (
    AdapterResult,
    ExtractionWarning,
    ProvenanceBlock,
    SkipReason,
)
from mindforge.sources.base import SourceDocument, compute_content_hash
from mindforge.sources.source_adapter import SourceAdapter


_BINARY_PEEK_BYTES = 1024
_MAX_TEXT_BYTES = 50 * 1024 * 1024


class TxtAdapter(SourceAdapter):
    """把本地 ``.txt`` 文件解析为 ``SourceDocument``。

    设计边界：本 adapter 只做 source-layer 读取与格式转换；不调用 LLM、不写文件、
    不接入审批语义。所有正常跳过路径都通过 ``AdapterResult.skipped`` 表达。
    """

    name = "TxtAdapter"
    source_type = "txt"

    def can_handle(self, path: str) -> bool:
        """按大小写不敏感的 ``.txt`` 后缀识别 TXT 文件。"""
        return Path(path).suffix.lower() == ".txt"

    def load(self, path: str) -> AdapterResult:
        """读取 TXT 文件并返回 AdapterResult 三态结果。"""
        p = Path(path)

        if not p.exists():
            return AdapterResult(
                status="failed",
                error_message=f"FileNotFoundError: {p}",
            )
        if not self.can_handle(path):
            return AdapterResult(
                status="skipped",
                skip_reason=SkipReason.UNSUPPORTED_FORMAT,
            )

        try:
            size = p.stat().st_size
        except OSError as exc:
            return AdapterResult(
                status="failed",
                error_message=f"{type(exc).__name__}: {p}",
            )

        if size > _MAX_TEXT_BYTES:
            return AdapterResult(
                status="skipped",
                skip_reason=SkipReason.FILE_TOO_LARGE,
            )

        try:
            with p.open("rb") as f:
                head = f.read(_BINARY_PEEK_BYTES)
                if b"\x00" in head:
                    return AdapterResult(
                        status="skipped",
                        skip_reason=SkipReason.BINARY_FILE,
                    )
                raw_bytes = head + f.read()
        except OSError as exc:
            return AdapterResult(
                status="failed",
                error_message=f"{type(exc).__name__}: {p}",
            )

        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return AdapterResult(
                status="skipped",
                skip_reason=SkipReason.DECODE_ERROR,
            )

        warnings = []
        if text == "":
            warnings.append(
                ExtractionWarning(
                    code=SkipReason.EMPTY_FILE,
                    message="Empty TXT file.",
                )
            )

        document = self._build_document(p, text, warnings)
        return AdapterResult(status="loaded", document=document, warnings=warnings)

    def _build_document(
        self,
        path: Path,
        text: str,
        warnings: list[ExtractionWarning],
    ) -> SourceDocument:
        """构造 SourceDocument，并记录 TXT 文件整体的 provenance block。"""
        title = _title_from_text_or_path(text, path)
        provenance_blocks = [
            ProvenanceBlock(
                source_type=self.source_type,
                offset_start=0,
                offset_end=len(text),
                extracted_as="text",
            )
        ]
        return SourceDocument(
            source_id="sha1:" + hashlib.sha1(str(path).encode("utf-8")).hexdigest(),
            source_type=self.source_type,
            source_path=str(path),
            title=title,
            raw_text=text,
            metadata={},
            content_hash=compute_content_hash(text, {"title": title}),
            adapter_name=self.name,
            extraction_warnings=list(warnings),
            provenance_blocks=provenance_blocks,
        )


def _title_from_text_or_path(text: str, path: Path) -> str:
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    return first_line or path.stem


__all__ = ["TxtAdapter"]
