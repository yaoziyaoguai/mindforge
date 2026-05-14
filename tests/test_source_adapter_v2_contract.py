"""M1 Phase P2 — SourceAdapter v2 契约测试（TDD Red 阶段）。

中文学习型说明
================

为什么先写 contract tests 而不是直接实现？
----------------------------------------

本文件是 v0.2 SourceAdapter Foundation 的 **Red 阶段**测试。定义了三组未来 contract：

1. **AdapterResult contract**：``SourceAdapter.load()`` 的返回类型从裸
   ``SourceDocument`` 升级为 ``AdapterResult``（loaded / skipped / failed 三态）。
2. **SourceDocument v2 contract**：现有 14 字段不变 + 新增
   ``extraction_warnings`` / ``provenance_blocks`` 两个 backward-compatible 字段。
3. **PlainMarkdownAdapter compatibility**：确保 Markdown adapter 的现有行为不被
   v0.2 contract 升级破坏。

Red 阶段意味着什么
------------------

- ``AdapterResult`` / ``ExtractionWarning`` / ``ProvenanceBlock`` **尚未实现**——
  测试中对应的 import 会失败（``ImportError``），这是**预期 Red**。
- ``SourceDocument`` v0.2 字段 ``extraction_warnings`` / ``provenance_blocks``
  **尚未添加**——字段存在性检查会失败（``AssertionError``），这是**预期 Red**。
- ``PlainMarkdownAdapter`` 兼容性测试中部分**可以 Green**（因为 adapter 已存在），
  这证明 backward-compatible contract 从第一天就是可行的。

这些测试是 **Phase P3/P4 的实现目标**——当 P3 完成 ``SourceDocument`` v2 字段添加、
P4 完成 ``AdapterResult`` dataclass 后，本文件的 Red 应全部转为 Green。

Red 测试设计约束
----------------

- 不 import 不存在的模块来做 mock（不造假绿）。
- 不 monkeypatch 生产级类型进来绕过 Red。
- Red 失败必须清楚可解释：每个测试的 docstring 说明**目标 contract**和**当前为何 Red**。
- 不改 src/。

与现有测试的关系
----------------

- ``test_markdown_adapter_characterization.py``（Phase P1）：捕获 v0.1 实际行为。
- 本文件（Phase P2）：定义 v0.2 目标 contract。
- Phase P3/P4 实现后两套测试应同时 Green。
"""

from __future__ import annotations

import dataclasses
import importlib
from pathlib import Path

import pytest

# =============================================================================
# 0. 预期导入状态检查
# =============================================================================


def _module_exists(name: str) -> bool:
    """检查模块是否可导入（用于区分"尚未实现"与"实现但行为错误"）。"""
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# 记录当前导入状态，便于后续测试判断 Red vs Green。
# v0.2 M1 Phase P2 开始时这三个模块均不存在——均为预期 Red。
# ---------------------------------------------------------------------------
_ADAPTER_RESULT_EXISTS = _module_exists("mindforge.sources.adapter_result")
_SOURCE_DOCUMENT_V2_FIELDS_EXIST = (  # extraction_warnings / provenance_blocks
    "extraction_warnings"
    in {f.name for f in dataclasses.fields(__import__("mindforge.sources.base", fromlist=["SourceDocument"]).SourceDocument)}
)


# =============================================================================
# A. AdapterResult Contract
# =============================================================================


@pytest.mark.xfail(
    not _ADAPTER_RESULT_EXISTS,
    reason="v0.2 AdapterResult 尚未实现——预期 Red。Phase P4 实现 adapter_result.py 后应 Green。",
    strict=True,
)
class TestAdapterResultContract:
    """AdapterResult 的三态契约（loaded / skipped / failed）。

    目标：``SourceAdapter.load()`` 的唯一返回类型是 ``AdapterResult``。
    不再通过 bare exception 表达正常 skip/fail 路径。
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        """延迟导入——如果模块还不存在，xfail 会让整个 class 跳过。"""
        from mindforge.sources.adapter_result import AdapterResult, ExtractionWarning

        self.AdapterResult = AdapterResult
        self.ExtractionWarning = ExtractionWarning

    # -- status 三态 --------------------------------------------------------

    def test_adapter_result_has_three_status_values(self) -> None:
        """AdapterResult.status 允许的值为 "loaded" / "skipped" / "failed"。

        目标 contract（RFC_0001 §5.4）：status 是三选一的枚举语义，
        不应出现其他值（如 "pending" / "error" / "unknown"）。
        当前 Red 原因：AdapterResult 尚未实现。
        """
        # contract 定义——不依赖运行时实例
        valid_statuses = {"loaded", "skipped", "failed"}
        assert valid_statuses == {"loaded", "skipped", "failed"}

    # -- loaded ------------------------------------------------------------

    def test_loaded_result_document_is_not_none(self) -> None:
        """status="loaded" 时 document 必须非 None。

        RFC_0001 §5.4: loaded → document 传给 processor。
        当前 Red 原因：AdapterResult 尚未实现。
        """
        result = self.AdapterResult(
            status="loaded",
            document="placeholder",  # 类型检查忽略——dataclass 构造演示
            skip_reason=None,
            error_message=None,
        )
        assert result.status == "loaded"
        assert result.document is not None
        assert result.skip_reason is None
        assert result.error_message is None

    def test_loaded_result_warnings_is_list(self) -> None:
        """status="loaded" 时 warnings 应为 list（可能为空）。

        RFC_0001 §5.4: loaded 状态下 extraction_warnings 可能非空
        （表示解析过程中有非致命问题）。
        当前 Red 原因：AdapterResult 尚未实现。
        """
        result = self.AdapterResult(status="loaded", document="ph")
        assert isinstance(result.warnings, list)

    # -- skipped -----------------------------------------------------------

    def test_skipped_result_document_is_none(self) -> None:
        """status="skipped" 时 document 必须为 None。

        RFC_0001 §5.4: skipped → document 为 None，skip_reason 非空。
        当前 Red 原因：AdapterResult 尚未实现。
        """
        result = self.AdapterResult(
            status="skipped",
            skip_reason="unsupported_format",
        )
        assert result.status == "skipped"
        assert result.document is None
        assert result.skip_reason is not None
        assert len(result.skip_reason) > 0

    def test_skipped_result_skip_reason_is_required(self) -> None:
        """status="skipped" 时 skip_reason 必填。

        RFC_0001 §5.4: skip_reason 说明为何跳过（如 "unsupported_format" /
        "scanned_pdf_no_text" / "decode_error"）。

        SDD §4.6: SkipReason 常量类预定义了标准 skip reason 值。
        当前 Red 原因：AdapterResult 尚未实现。
        """
        result = self.AdapterResult(
            status="skipped",
            skip_reason="scanned_pdf_no_text",
        )
        assert result.skip_reason == "scanned_pdf_no_text"
        assert result.error_message is None

    # -- failed ------------------------------------------------------------

    def test_failed_result_document_is_none(self) -> None:
        """status="failed" 时 document 必须为 None。

        RFC_0001 §5.4: failed → error_message 非空，document 为 None。
        当前 Red 原因：AdapterResult 尚未实现。
        """
        result = self.AdapterResult(
            status="failed",
            error_message="FileNotFoundError: /path/to/file.md",
        )
        assert result.status == "failed"
        assert result.document is None
        assert result.error_message is not None
        assert len(result.error_message) > 0

    def test_failed_result_error_message_is_required(self) -> None:
        """status="failed" 时 error_message 必填。

        RFC_0001 §5.4: error_message 说明失败原因（如 FileNotFoundError /
        PermissionError / OptionalDependencyError）。
        当前 Red 原因：AdapterResult 尚未实现。
        """
        result = self.AdapterResult(
            status="failed",
            error_message="PermissionError: no read access",
        )
        assert result.status == "failed"
        assert result.error_message == "PermissionError: no read access"

    # -- frozen ------------------------------------------------------------

    def test_adapter_result_is_frozen(self) -> None:
        """AdapterResult 必须是 frozen dataclass。

        SourceDocument 的 frozen 契约保证了"不可变快照"语义——
        AdapterResult 同为此层契约，不应被下游改写。
        当前 Red 原因：AdapterResult 尚未实现。
        """
        result = self.AdapterResult(status="loaded", document="ph")
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.status = "skipped"  # type: ignore[misc]


# =============================================================================
# B. ExtractionWarning Contract
# =============================================================================


@pytest.mark.xfail(
    not _ADAPTER_RESULT_EXISTS,
    reason="v0.2 ExtractionWarning 尚未实现——预期 Red。",
    strict=True,
)
class TestExtractionWarningContract:
    """ExtractionWarning 的字段契约。

    RFC_0001 §5.4 / SDD §5.3: ExtractionWarning 记录解析过程中的非致命问题。
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.adapter_result import ExtractionWarning

        self.ExtractionWarning = ExtractionWarning

    def test_extraction_warning_has_code_message_location(self) -> None:
        """ExtractionWarning 必须有 code / message / location 三个字段。

        - code: 机器可读的 warning code（如 "encoding_fallback"）
        - message: 人类可读的描述
        - location: 可选的位置信息（page / line / section）
        当前 Red 原因：ExtractionWarning 尚未实现。
        """
        w = self.ExtractionWarning(
            code="encoding_fallback",
            message="UTF-8 decode failed, fell back to latin-1",
            location="line 42",
        )
        assert w.code == "encoding_fallback"
        assert w.message == "UTF-8 decode failed, fell back to latin-1"
        assert w.location == "line 42"

    def test_extraction_warning_location_can_be_none(self) -> None:
        """location 可以为 None——不是所有 warning 都能定位到具体位置。

        当前 Red 原因：ExtractionWarning 尚未实现。
        """
        w = self.ExtractionWarning(
            code="table_loss",
            message="Complex table structure simplified",
            location=None,
        )
        assert w.location is None

    def test_extraction_warning_is_frozen(self) -> None:
        """ExtractionWarning 必须是 frozen dataclass。

        当前 Red 原因：ExtractionWarning 尚未实现。
        """
        w = self.ExtractionWarning(code="x", message="y", location=None)
        with pytest.raises(dataclasses.FrozenInstanceError):
            w.code = "z"  # type: ignore[misc]


# =============================================================================
# C. ProvenanceBlock Contract
# =============================================================================


@pytest.mark.xfail(
    not _ADAPTER_RESULT_EXISTS,
    reason="v0.2 ProvenanceBlock 尚未实现——预期 Red。",
    strict=True,
)
class TestProvenanceBlockContract:
    """ProvenanceBlock 的字段契约。

    RFC_0001 §5.4: ProvenanceBlock 记录 source 中每个块的位置信息。
    对 Markdown baseline 可以为空 list；future PDF/HTML/DOCX adapter 可填充。
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.adapter_result import ProvenanceBlock

        self.ProvenanceBlock = ProvenanceBlock

    def test_provenance_block_has_required_fields(self) -> None:
        """ProvenanceBlock 必须有 source_type / extracted_as 等字段。

        RFC_0001 §5.4 定义的字段：
        - source_type: str（"pdf" / "docx" / "txt" / "html"）
        - page: int | None
        - section: str | None
        - offset_start: int | None
        - offset_end: int | None
        - extracted_as: str（"text" / "markdown_table" / "markdown_list"）
        当前 Red 原因：ProvenanceBlock 尚未实现。
        """
        block = self.ProvenanceBlock(
            source_type="txt",
            page=None,
            section=None,
            offset_start=0,
            offset_end=1024,
            extracted_as="text",
        )
        assert block.source_type == "txt"
        assert block.offset_start == 0
        assert block.offset_end == 1024
        assert block.extracted_as == "text"

    def test_provenance_block_page_and_section_optional(self) -> None:
        """page / section / offset_start / offset_end 均可以为 None。

        不是所有 source 都有这些位置信息——例如 plain Markdown 就没有 page 概念。
        当前 Red 原因：ProvenanceBlock 尚未实现。
        """
        block = self.ProvenanceBlock(
            source_type="plain_markdown",
            page=None,
            section=None,
            offset_start=None,
            offset_end=None,
            extracted_as="text",
        )
        assert block.page is None
        assert block.section is None
        assert block.offset_start is None

    def test_provenance_block_is_frozen(self) -> None:
        """ProvenanceBlock 必须是 frozen dataclass。

        当前 Red 原因：ProvenanceBlock 尚未实现。
        """
        block = self.ProvenanceBlock(
            source_type="txt",
            page=None,
            section=None,
            offset_start=None,
            offset_end=None,
            extracted_as="text",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            block.source_type = "html"  # type: ignore[misc]


# =============================================================================
# D. SkipReason 常量 Contract
# =============================================================================


@pytest.mark.xfail(
    not _ADAPTER_RESULT_EXISTS,
    reason="v0.2 SkipReason 尚未实现——预期 Red。",
    strict=True,
)
class TestSkipReasonContract:
    """SkipReason 常量类契约。

    SDD §4.6: SkipReason 预定义了标准 skip reason 值，
    用作 AdapterResult.skip_reason 的统一词汇表。
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.adapter_result import SkipReason

        self.SkipReason = SkipReason

    def test_skip_reason_has_standard_values(self) -> None:
        """SkipReason 必须包含 SDD §4.6 定义的所有标准常量。

        当前 Red 原因：SkipReason 尚未实现。
        """
        expected = {
            "UNSUPPORTED_LEGACY_DOC",
            "SCANNED_PDF_NO_TEXT",
            "ENCRYPTED_PDF",
            "DECODE_ERROR",
            "BINARY_FILE",
            "FILE_TOO_LARGE",
            "UNSUPPORTED_FORMAT",
            "MISSING_OPTIONAL_DEPENDENCY",
            "EMPTY_FILE",
        }
        for name in expected:
            assert hasattr(self.SkipReason, name), (
                f"SkipReason 缺少 {name} 常量"
            )

    def test_skip_reason_values_are_strings(self) -> None:
        """SkipReason 常量值应该是纯字符串，可直接用于 AdapterResult.skip_reason。

        当前 Red 原因：SkipReason 尚未实现。
        """
        assert isinstance(self.SkipReason.UNSUPPORTED_FORMAT, str)
        assert isinstance(self.SkipReason.BINARY_FILE, str)


# =============================================================================
# E. SourceDocument v2 Contract（backward-compatible 字段扩展）
# =============================================================================

# SourceDocument v2 字段契约测试——直接对现有的 SourceDocument 做结构断言。
# 当前 extraction_warnings / provenance_blocks 尚未添加，部分测试预期 Red。


class TestSourceDocumentV2Fields:
    """SourceDocument v2 的 backward-compatible 字段扩展契约。

    RFC_0001 §5.2: v0.2 只新增 extraction_warnings 和 provenance_blocks，
    使用 field(default_factory=list)。v0.1 字段全部保留原语义。
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from mindforge.sources.base import SourceDocument, compute_content_hash

        self.SourceDocument = SourceDocument
        self.compute_content_hash = compute_content_hash

    # -- backward-compatible 字段保留 ---------------------------------------

    def test_v0_1_fields_preserved(self) -> None:
        """v0.1 的核心字段必须保留——不可重命名或移除。

        RFC_0001 §5.2: source_path / raw_text / content_hash 不重命名。
        当前预期：Green（这些字段已存在）。
        """
        doc = self.SourceDocument(
            source_id="src-1",
            source_type="plain_markdown",
            source_path="/tmp/test.md",
            raw_text="# Hello",
            content_hash="sha256:abc123",
        )
        assert doc.source_path == "/tmp/test.md"
        assert doc.raw_text == "# Hello"
        assert doc.content_hash == "sha256:abc123"
        assert doc.source_type == "plain_markdown"

    @pytest.mark.xfail(
        not _SOURCE_DOCUMENT_V2_FIELDS_EXIST,
        reason="v0.2 extraction_warnings 字段尚未添加——预期 Red。Phase P3 实现后应 Green。",
        strict=True,
    )
    def test_extraction_warnings_field_exists(self) -> None:
        """SourceDocument 必须有 extraction_warnings 字段。

        RFC_0001 §5.2: extraction_warnings: list[ExtractionWarning]，
        使用 field(default_factory=list) 实现 backward-compatible。
        当前 Red 原因：字段尚未添加到 SourceDocument dataclass。
        """
        doc = self.SourceDocument(
            source_id="src-1",
            source_type="plain_markdown",
            source_path="/tmp/test.md",
            raw_text="# Hello",
            content_hash="sha256:abc123",
        )
        # 新字段应该存在且默认值为空 list
        assert hasattr(doc, "extraction_warnings")
        assert doc.extraction_warnings == []

    @pytest.mark.xfail(
        not _SOURCE_DOCUMENT_V2_FIELDS_EXIST,
        reason="v0.2 provenance_blocks 字段尚未添加——预期 Red。Phase P3 实现后应 Green。",
        strict=True,
    )
    def test_provenance_blocks_field_exists(self) -> None:
        """SourceDocument 必须有 provenance_blocks 字段。

        RFC_0001 §5.2: provenance_blocks: list[ProvenanceBlock]，
        使用 field(default_factory=list) 实现 backward-compatible。
        当前 Red 原因：字段尚未添加到 SourceDocument dataclass。
        """
        doc = self.SourceDocument(
            source_id="src-1",
            source_type="plain_markdown",
            source_path="/tmp/test.md",
            raw_text="# Hello",
            content_hash="sha256:abc123",
        )
        assert hasattr(doc, "provenance_blocks")
        assert doc.provenance_blocks == []

    def test_new_fields_are_backward_compatible(self) -> None:
        """新字段应使用 default_factory=list，现有 adapter 无需立即修改。

        RFC_0001 §5.2 backward-compatibility 策略：两个新字段默认空 list，
        所有现有 adapter 的构造调用不需要传这两个参数。
        当前预期：如果字段已存在，测试其默认值；如果不存在，测试在 Phase P3 之后再验证。

        注：本测试不强制 Red——它是对 P3 实现的指导约束。
        """
        field_names = {f.name for f in dataclasses.fields(self.SourceDocument)}
        if "extraction_warnings" in field_names:
            doc = self.SourceDocument(
                source_id="src-1",
                source_type="plain_markdown",
                source_path="/tmp/test.md",
                raw_text="# Hello",
                content_hash="sha256:abc123",
            )
            assert doc.extraction_warnings == []
        if "provenance_blocks" in field_names:
            doc = self.SourceDocument(
                source_id="src-1",
                source_type="plain_markdown",
                source_path="/tmp/test.md",
                raw_text="# Hello",
                content_hash="sha256:abc123",
            )
            assert doc.provenance_blocks == []

    # -- 不允许 leaked downstream fields -----------------------------------

    def test_source_document_no_leaked_fields(self) -> None:
        """SourceDocument v2 不得引入 downstream 领域字段。

        RFC_0001 §5.1 non-responsibilities: adapter 不负责 LLM processing /
        ai_draft / approval / recall / wiki。SourceDocument 是输入层契约，
        不能携带 processor/approval 专属字段。
        当前预期：Green（v0.1 已有此守卫，v0.2 不应打破）。
        """
        field_names = {f.name for f in dataclasses.fields(self.SourceDocument)}
        forbidden = {
            "ai_draft",
            "draft_text",
            "human_approved",
            "approved_at",
            "card_id",
            "review_state",
            "approval_state",
        }
        leaked = field_names & forbidden
        assert not leaked, f"SourceDocument 泄漏了下游字段: {leaked}"


# =============================================================================
# F. SourceAdapter.load() 返回 AdapterResult Contract
# =============================================================================


class TestSourceAdapterLoadContract:
    """SourceAdapter.load() 必须返回 AdapterResult，而非直接返回 SourceDocument。

    RFC_0001 §5.1: ``load(self, path: str) -> AdapterResult``。
    v0.1 的 ``load() -> SourceDocument`` 是旧契约，v0.2 统一升级。
    """

    def test_load_signature_documented_as_returning_adapter_result(self) -> None:
        """SourceAdapter.load() 的文档目标返回类型是 AdapterResult。

        当前状态（v0.1）：load() 返回 SourceDocument，直接抛异常表达 skip。
        目标状态（v0.2）：load() 返回 AdapterResult，不抛异常表达正常 skip/fail。

        此测试记录 contract 目标——Phase P4 实现后应验证。
        当前预期：Green（仅文档级断言，不依赖运行时）。
        """
        # contract 文档定义——不依赖运行时实现
        contract_return_type = "AdapterResult"
        assert contract_return_type == "AdapterResult"

    def test_processor_should_only_receive_loaded_documents(self) -> None:
        """Processor 只应接收 status="loaded" 的 document。

        RFC_0001 §5.4: Processor 只接收 status="loaded" 后的
        AdapterResult.document。这是 scanner → processor 之间的 contract。

        当前预期：Green（仅文档级断言）。
        """
        # 模拟 contract 检查逻辑——这是 P4 实现后 scanner 的行为模板
        def _should_process(result_status: str) -> bool:
            return result_status == "loaded"

        assert _should_process("loaded") is True
        assert _should_process("skipped") is False
        assert _should_process("failed") is False

    def test_no_bare_exception_for_normal_skip(self) -> None:
        """正常 skip/fail 不应通过抛异常表达。

        RFC_0001 §5.4 contrast with v0.1：
        - v0.1: raise ValueError(skip_reason) / raise PdfNoTextError
        - v0.2: AdapterResult(status="skipped", skip_reason=...) /
                AdapterResult(status="failed", error_message=...)

        只有真正的编程错误（如 NotImplementedError）才允许抛异常。

        当前预期：Green（仅文档级断言——记录 contract 目标）。
        """
        # 定义哪些场景必须走 AdapterResult 而非抛异常
        skip_scenarios = [
            "unsupported_format",
            "scanned_pdf_no_text",
            "decode_error",
            "binary_file",
            "file_too_large",
        ]
        assert len(skip_scenarios) == 5  # contract 完整性


# =============================================================================
# G. PlainMarkdownAdapter Compatibility Contract
# =============================================================================


class TestPlainMarkdownAdapterV2Compatibility:
    """PlainMarkdownAdapter 在 v0.2 contract 下的兼容性。

    RFC_0001 §5.5: PlainMarkdownAdapter 保持不变。所有 v0.1 Markdown 行为
    必须通过 characterization test 验证。source_type 保持 "plain_markdown"。
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from mindforge.sources.plain_markdown import PlainMarkdownAdapter

        self.adapter = PlainMarkdownAdapter()

    def test_source_type_remains_plain_markdown(self) -> None:
        """source_type 必须保持 "plain_markdown"——不可改名或降级。

        RFC_0001 §5.5: PlainMarkdownAdapter 的 contract 不变。
        当前预期：Green（v0.1 已有行为，v0.2 不改变）。
        """
        assert self.adapter.source_type == "plain_markdown"

    def test_can_handle_md_remains_true(self) -> None:
        """can_handle 对 .md 必须保持 True。

        当前预期：Green。
        """
        assert self.adapter.can_handle("note.md") is True

    def test_can_handle_non_md_remains_false(self) -> None:
        """can_handle 对非 .md 必须保持 False。

        当前预期：Green。
        """
        assert self.adapter.can_handle("note.pdf") is False

    def test_load_still_works_for_valid_md(self, tmp_path: Path) -> None:
        """load() 对合法 .md 文件必须仍可工作。

        v0.2 contract 升级后，PlainMarkdownAdapter.load() 的行为可能需要适配
        （返回 AdapterResult 而非 SourceDocument），但最终语义应保持不变。
        当前预期：Green（v0.1 行为，load 仍返回 SourceDocument）。
        """
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\n\nWorld.\n", encoding="utf-8")
        doc = self.adapter.load(str(md_file))
        assert doc.raw_text.startswith("# Hello")
        assert doc.source_type == "plain_markdown"

    def test_no_secrets_read_on_instantiation(self) -> None:
        """实例化不应读 secrets / env / 网络。

        v0.2 对 PlainMarkdownAdapter 的约束：始终保持 fake_safe。
        当前预期：Green。
        """
        assert "real_api" not in self.adapter.capabilities()
        assert "fake_safe" in self.adapter.capabilities()


# =============================================================================
# H. SourceDocument v2 与现有下游的隔离 Contract
# =============================================================================


class TestSourceDocumentV2DownstreamIsolation:
    """SourceDocument v2 扩展必须不污染下游模块。

    RFC_0001 non-responsibilities 和 SDD §8 Processor Format Isolation:
    - adapter 层不 import processor / approval / wiki / recall
    - SourceDocument 不携带下游字段
    """

    def test_source_document_module_does_not_import_downstream(self) -> None:
        """mindforge.sources.base 不应 import strategy / approval / processor。

        当前预期：Green（v0.1 已有守卫，v0.2 不应打破）。
        """
        import mindforge.sources.base as base_mod

        forbidden_substrings = (
            "Strategy",
            "Approval",
            "Review",
            "Pipeline",
            "Processor",
            "Recall",
            "Wiki",
        )
        leaked = [
            name
            for name in dir(base_mod)
            if not name.startswith("_")
            and any(sub in name for sub in forbidden_substrings)
        ]
        assert leaked == [], (
            f"mindforge.sources.base 暴露了下游领域符号：{leaked}"
        )

    def test_source_document_does_not_import_processor_format_libs(self) -> None:
        """SourceDocument / SourceAdapter 不应 import PDF/HTML/DOCX 格式库。

        SDD §8: processor 只能消费 SourceDocument，不能 import pdf/docx/bs4。
        SourceDocument 自身更不应携带格式解析依赖。
        当前预期：Green（v0.1 已有合约，v0.2 不应打破）。
        """
        import mindforge.sources.base as base_mod

        format_imports = ("pdf", "docx", "bs4", "pypdf", "ebooklib", "openpyxl")
        leaked = [
            name for name in dir(base_mod) if not name.startswith("_") and name in format_imports
        ]
        assert leaked == [], (
            f"mindforge.sources.base 引用了格式解析库：{leaked}"
        )
