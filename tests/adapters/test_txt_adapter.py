"""M2 Phase P2 — TxtAdapter Green tests（最小生产实现）。

中文学习型说明
================

本文件定义 v0.2 M2 TXT adapter 的目标行为，覆盖 RFC_0001 §5.1/§5.4/§5.6、
§5.13/§5.14 与 SDD §4.2/§10/§11。P1 阶段这些测试以 strict xfail 进入
测试套件；P2 阶段移除 xfail，让同一组 contract 验证真实 ``TxtAdapter``。

测试约束
--------

- 不在 tests 里伪造 production TxtAdapter。
- 不 monkeypatch 一个假 adapter 让测试变绿。
- 只允许最小 ``TxtAdapter`` 实现，不接 import/watch/process 主链路。
- 不读取真实 ``.env`` / ``.mindforge/secrets.json``，不调用 LLM，不触发审批语义。
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from mindforge.sources.adapter_result import AdapterResult, SkipReason


def _write_large_text_file(path: Path, size_bytes: int) -> None:
    """为 SDD §4.2 的 >50MB guard 写 synthetic ASCII 文件，不使用真实资料。"""
    chunk = "a" * (1024 * 1024)
    remaining = size_bytes
    with path.open("w", encoding="utf-8", newline="") as f:
        while remaining > 0:
            piece = chunk[: min(len(chunk), remaining)]
            f.write(piece)
            remaining -= len(piece)


def _public_result_text(result: AdapterResult) -> str:
    """把 AdapterResult 的公开字段转成字符串，用来确认错误信息不泄露原始 bytes。"""
    if dataclasses.is_dataclass(result):
        return repr(dataclasses.asdict(result))
    return repr(result)


class TestTxtAdapterM2Green:
    """TxtAdapter contract/behavior tests。

    覆盖 RFC_0001 §5.6 TXT Policy 与 SDD §4.2 TxtAdapter 行为。
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        """延迟导入真实 TxtAdapter；模块缺失时由 class-level xfail 表达 expected Red。"""
        from mindforge.sources.adapter_result import ProvenanceBlock
        from mindforge.sources.txt import TxtAdapter

        self.ProvenanceBlock = ProvenanceBlock
        self.adapter = TxtAdapter()

    def test_can_handle_only_txt_suffix(self) -> None:
        """RFC_0001 §5.6 / SDD §4.2：TxtAdapter 只处理 .txt 后缀。"""
        assert self.adapter.can_handle("note.txt") is True
        assert self.adapter.can_handle("NOTE.TXT") is True
        assert self.adapter.can_handle("note.md") is False
        assert self.adapter.can_handle("note.html") is False
        assert self.adapter.can_handle("note.pdf") is False
        assert self.adapter.can_handle("note.docx") is False
        assert self.adapter.can_handle("note.bin") is False

    def test_utf8_text_loads_successfully(self, tmp_path: Path) -> None:
        """RFC_0001 §5.1/§5.4/§5.6：UTF-8 .txt 返回 loaded SourceDocument。"""
        txt = tmp_path / "valid_utf8.txt"
        text = "Title line\n\nBody line one.\nBody line two.\n"
        txt.write_text(text, encoding="utf-8", newline="")

        result = self.adapter.load(str(txt))

        assert isinstance(result, AdapterResult)
        assert result.status == "loaded"
        assert result.skip_reason is None
        assert result.error_message is None
        assert result.document is not None
        assert result.warnings == []

        document = result.document
        assert document.source_type == "txt"
        assert document.raw_text == text
        assert document.source_path == str(txt)
        assert document.content_hash.startswith("sha256:")
        assert document.extraction_warnings == []
        assert len(document.provenance_blocks) == 1
        block = document.provenance_blocks[0]
        assert block.source_type == "txt"
        assert block.offset_start == 0
        assert block.offset_end == len(text)
        assert block.extracted_as == "text"

        second_result = self.adapter.load(str(txt))
        assert second_result.document is not None
        assert second_result.document.content_hash == document.content_hash

    def test_preserves_original_newlines(self, tmp_path: Path) -> None:
        """RFC_0001 §5.6：TXT 换行保留原样，不做 CRLF/LF normalize。"""
        txt = tmp_path / "mixed_newlines.txt"
        raw_bytes = b"one\r\ntwo\nthree\r\n"
        txt.write_bytes(raw_bytes)

        result = self.adapter.load(str(txt))

        assert result.status == "loaded"
        assert result.document is not None
        assert result.document.raw_text == "one\r\ntwo\nthree\r\n"

    def test_empty_txt_loads_with_empty_file_warning(self, tmp_path: Path) -> None:
        """RFC_0001 §5.6 / SDD §4.2：空 TXT loaded，raw_text 为空并记录 empty_file warning。"""
        txt = tmp_path / "empty.txt"
        txt.write_text("", encoding="utf-8")

        result = self.adapter.load(str(txt))

        assert result.status == "loaded"
        assert result.skip_reason is None
        assert result.document is not None
        assert result.document.raw_text == ""
        warning_codes = {warning.code for warning in result.warnings}
        document_warning_codes = {warning.code for warning in result.document.extraction_warnings}
        assert SkipReason.EMPTY_FILE in warning_codes
        assert SkipReason.EMPTY_FILE in document_warning_codes

    def test_binary_txt_is_friendly_skip(self, tmp_path: Path) -> None:
        """RFC_0001 §5.6 / §5.14：二进制 .txt skipped，skip_reason=binary_file，不 crash。"""
        txt = tmp_path / "binary_as_txt.txt"
        txt.write_bytes(b"\x00\x01\x02\x03not text\x00")

        result = self.adapter.load(str(txt))

        assert isinstance(result, AdapterResult)
        assert result.status == "skipped"
        assert result.document is None
        assert result.skip_reason == SkipReason.BINARY_FILE
        assert result.error_message is None

    def test_decode_error_is_friendly_skip_without_raw_bytes(self, tmp_path: Path) -> None:
        """RFC_0001 §5.6 / §5.14：无法解码的 TXT skipped，且错误输出不泄露原始 bytes。"""
        txt = tmp_path / "invalid_utf8.txt"
        invalid_bytes = b"valid prefix \xff\xfe\xfa invalid suffix"
        txt.write_bytes(invalid_bytes)

        result = self.adapter.load(str(txt))

        assert result.status == "skipped"
        assert result.document is None
        assert result.skip_reason == SkipReason.DECODE_ERROR
        public_text = _public_result_text(result)
        assert repr(invalid_bytes) not in public_text
        assert "valid prefix" not in public_text
        assert "invalid suffix" not in public_text

    def test_unsupported_extensions_remain_unsupported(self, tmp_path: Path) -> None:
        """RFC_0001 §5.1/§5.6：HTML/PDF/DOCX 不由 TxtAdapter 处理。"""
        for suffix in [".html", ".pdf", ".docx"]:
            source = tmp_path / f"source{suffix}"
            source.write_text("synthetic content", encoding="utf-8")
            assert self.adapter.can_handle(str(source)) is False

    def test_large_txt_over_50mb_is_friendly_skip(self, tmp_path: Path) -> None:
        """RFC_0001 §5.6 / SDD §4.2：>50MB TXT friendly skip，reason=file_too_large。"""
        txt = tmp_path / "large_file.txt"
        _write_large_text_file(txt, 50 * 1024 * 1024 + 1)

        result = self.adapter.load(str(txt))

        assert result.status == "skipped"
        assert result.document is None
        assert result.skip_reason == SkipReason.FILE_TOO_LARGE
        assert result.error_message is None

    def test_txt_adapter_does_not_emit_pipeline_or_approval_state(
        self, tmp_path: Path
    ) -> None:
        """RFC_0001 §5.1/§5.13：TxtAdapter 只读 source，不生成 ai_draft/approval 状态。"""
        txt = tmp_path / "plain.txt"
        txt.write_text("plain synthetic text", encoding="utf-8")

        result = self.adapter.load(str(txt))

        assert result.status == "loaded"
        assert result.document is not None
        public_fields: dict[str, Any] = dataclasses.asdict(result.document)
        public_text = repr(public_fields)
        assert "ai_draft" not in public_text
        assert "human_approved" not in public_text
        assert "explicit approve" not in public_text
        assert "approval" not in public_text
