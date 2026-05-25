"""扩展边界(Extension Boundary) 测试。

测试 ExtensionManifest 元数据校验、ExportAdapter 端口契约、
示例适配器自注册模式、审批策略推导。

所有测试均使用 fake/local 数据，不访问外部服务。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mindforge.extensions.export_adapter import ExportAdapter, ExportResult
from mindforge.extensions.manifest import (
    Capability,
    ExtensionManifest,
    ExtensionType,
    RiskLevel,
)
from mindforge.extensions.samples.fake_export_adapter import (
    FakeMarkdownExportAdapter,
)
from mindforge.extensions.samples.fake_source_adapter import (
    FakeSourceAdapter,
)


# ── TestExtensionManifest ─────────────────────────────────


class TestExtensionManifest:
    """ExtensionManifest 数据模型测试。"""

    def test_minimal_manifest_creation(self):
        """最小字段即可创建 manifest。"""
        m = ExtensionManifest(
            name="test_ext",
            version="0.1.0",
            description="测试扩展",
            extension_type=ExtensionType.SOURCE_ADAPTER,
            capabilities=frozenset(),
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            entry_point="test.module.Class",
        )
        assert m.name == "test_ext"
        assert m.version == "0.1.0"
        assert m.dependencies == ()
        assert m.author == ""

    def test_full_manifest_creation(self):
        """全字段 manifest 创建。"""
        m = ExtensionManifest(
            name="full_ext",
            version="2.0.0",
            description="全字段扩展",
            extension_type=ExtensionType.GRAPH_BACKEND,
            capabilities=frozenset({Capability.LOCAL_FILE, Capability.READ_ONLY}),
            risk_level=RiskLevel.MEDIUM,
            requires_approval=True,
            entry_point="full.module.Class",
            dependencies=("numpy", "pandas"),
            author="Test Author",
            homepage="https://example.com",
        )
        assert m.name == "full_ext"
        assert len(m.capabilities) == 2
        assert len(m.dependencies) == 2

    def test_manifest_immutable(self):
        """frozen dataclass 不可变。"""
        m = ExtensionManifest(
            name="immutable_ext",
            version="1.0.0",
            description="不可变测试",
            extension_type=ExtensionType.SOURCE_ADAPTER,
            capabilities=frozenset(),
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            entry_point="test.Class",
        )
        with pytest.raises(Exception):
            m.name = "changed"  # type: ignore[misc]

    def test_extension_type_enum_values(self):
        """ExtensionType 覆盖全部 6 种端口类型。"""
        types = set(ExtensionType)
        assert ExtensionType.SOURCE_ADAPTER in types
        assert ExtensionType.EXPORT_ADAPTER in types
        assert ExtensionType.LLM_PROVIDER in types
        assert ExtensionType.GRAPH_BACKEND in types
        assert ExtensionType.SEARCH_BACKEND in types
        assert ExtensionType.KNOWLEDGE_STRATEGY in types

    def test_capability_values_match_source_adapter(self):
        """Capability 枚举值与 SourceAdapter 已有的 capability 标签兼容。"""
        # SourceAdapter 使用 frozenset[str] 的能力标签，如 "local_file"
        # Capability 枚举应与这些字符串值对齐
        assert Capability.LOCAL_FILE.value == "local_file"
        assert Capability.FAKE_SAFE.value == "fake_safe"
        assert Capability.DRY_RUN.value == "dry_run"
        assert Capability.REAL_API.value == "real_api"
        assert Capability.READ_ONLY.value == "read_only"
        assert Capability.WRITE.value == "write"
        assert Capability.NETWORK.value == "network"


# ── TestApprovalDerivation ────────────────────────────────


class TestApprovalDerivation:
    """审批策略推导测试。"""

    def test_low_risk_local_only_no_approval(self):
        """LOW 风险 + 纯本地能力 → 无需审批。"""
        caps = frozenset({Capability.LOCAL_FILE, Capability.FAKE_SAFE, Capability.READ_ONLY})
        assert ExtensionManifest.derive_approval(caps, RiskLevel.LOW) is False

    def test_real_api_requires_approval(self):
        """REAL_API 能力 → 始终需要审批。"""
        caps = frozenset({Capability.LOCAL_FILE, Capability.REAL_API})
        assert ExtensionManifest.derive_approval(caps, RiskLevel.LOW) is True

    def test_network_requires_approval(self):
        """NETWORK 能力 → 始终需要审批。"""
        caps = frozenset({Capability.NETWORK})
        assert ExtensionManifest.derive_approval(caps, RiskLevel.LOW) is True

    def test_high_risk_requires_approval(self):
        """HIGH 风险 → 始终需要审批，即使无 REAL_API/NETWORK。"""
        caps = frozenset({Capability.LOCAL_FILE, Capability.READ_ONLY})
        assert ExtensionManifest.derive_approval(caps, RiskLevel.HIGH) is True

    def test_critical_risk_requires_approval(self):
        """CRITICAL 风险 → 始终需要审批。"""
        caps = frozenset({Capability.READ_ONLY})
        assert ExtensionManifest.derive_approval(caps, RiskLevel.CRITICAL) is True

    def test_medium_risk_local_only_no_approval(self):
        """MEDIUM 风险 + 纯本地 → 无需审批。"""
        caps = frozenset({Capability.LOCAL_FILE, Capability.WRITE})
        assert ExtensionManifest.derive_approval(caps, RiskLevel.MEDIUM) is False

    def test_write_only_low_risk_no_approval(self):
        """WRITE 能力 + LOW 风险 → 无需审批（写本地文件属低风险）。"""
        caps = frozenset({Capability.WRITE})
        assert ExtensionManifest.derive_approval(caps, RiskLevel.LOW) is False


# ── TestExportResult ──────────────────────────────────────


class TestExportResult:
    """ExportResult 数据模型测试。"""

    def test_success_result(self):
        result = ExportResult(
            success=True,
            output_path=Path("/tmp/export.md"),
            format="markdown",
            card_count=5,
        )
        assert result.success is True
        assert result.card_count == 5
        assert result.errors == ()
        assert result.warnings == ()

    def test_failure_result(self):
        result = ExportResult(
            success=False,
            output_path=Path("/tmp/export.md"),
            format="markdown",
            card_count=0,
            errors=("card_ids 为空",),
        )
        assert result.success is False
        assert len(result.errors) == 1

    def test_with_warnings(self):
        result = ExportResult(
            success=True,
            output_path=Path("/tmp/export.md"),
            format="markdown",
            card_count=10,
            warnings=("部分卡片缺少 title", "2 张卡片 body 为空"),
        )
        assert result.success is True
        assert len(result.warnings) == 2

    def test_metadata_default(self):
        result = ExportResult(
            success=True,
            output_path=Path("/tmp/export.md"),
            format="markdown",
            card_count=3,
        )
        assert result.metadata == frozenset()


# ── TestExportAdapter ─────────────────────────────────────


class TestExportAdapterContract:
    """ExportAdapter ABC 契约测试。"""

    def test_abc_enforces_name(self):
        """name 属性必须由子类实现。"""
        with pytest.raises(TypeError):
            ExportAdapter()  # type: ignore[abstract]

    def test_concrete_implementation(self):
        """具体实现可以通过 isinstance 检查。"""

        class _MinimalExport(ExportAdapter):
            name = "minimal"
            export_format = "json"

            def can_handle(self, card_ids, target_format):
                return True

            def export(self, card_ids, output_path, **options):
                return ExportResult(
                    success=True,
                    output_path=output_path,
                    format=self.export_format,
                    card_count=len(card_ids),
                )

        adapter = _MinimalExport()
        assert isinstance(adapter, ExportAdapter)
        assert adapter.name == "minimal"
        assert adapter.can_handle(frozenset({"card-1"}), "json") is True

    def test_default_capabilities(self):
        """默认 capabilities 返回 local_file + fake_safe + read_only。"""

        class _DefaultCapsExport(ExportAdapter):
            name = "default_caps"
            export_format = "txt"

            def can_handle(self, card_ids, target_format):
                return True

            def export(self, card_ids, output_path, **options):
                return ExportResult(True, output_path, "txt", 1)

        caps = _DefaultCapsExport().capabilities()
        assert "local_file" in caps
        assert "fake_safe" in caps
        assert "read_only" in caps


# ── TestFakeSourceAdapter ─────────────────────────────────


class TestFakeSourceAdapter:
    """示例 FakeSourceAdapter 测试。"""

    def test_can_handle_fake_md(self):
        adapter = FakeSourceAdapter()
        assert adapter.can_handle(Path("test.fake.md")) is True

    def test_can_handle_fake_prefix(self):
        adapter = FakeSourceAdapter()
        assert adapter.can_handle(Path("fake_sample.txt")) is True

    def test_cannot_handle_real_file(self):
        adapter = FakeSourceAdapter()
        assert adapter.can_handle(Path("real_document.md")) is False

    def test_load_returns_adapter_result(self):
        adapter = FakeSourceAdapter()
        result = adapter.load(Path("test.fake.md"))
        assert result.status == "loaded"
        assert result.document is not None
        assert result.document.source_type == "fake"
        assert result.document.title is not None
        assert result.document.raw_text is not None
        assert result.document.content_hash is not None

    def test_load_is_deterministic(self):
        """相同输入产生相同输出。"""
        adapter = FakeSourceAdapter()
        path = Path("deterministic_test.fake.md")
        r1 = adapter.load(path)
        r2 = adapter.load(path)
        assert r1.document is not None and r2.document is not None
        assert r1.document.title == r2.document.title
        assert r1.document.raw_text == r2.document.raw_text
        assert r1.document.content_hash == r2.document.content_hash

    def test_capabilities_match_manifest(self):
        """capabilities() 输出与 manifest 声明一致。"""
        adapter = FakeSourceAdapter()
        from mindforge.extensions.samples.fake_source_adapter import (
            FAKE_SOURCE_MANIFEST,
        )

        adapter_caps = adapter.capabilities()
        manifest_caps = {c.value for c in FAKE_SOURCE_MANIFEST.capabilities}
        assert adapter_caps == manifest_caps

    def test_manifest_is_low_risk_no_approval(self):
        """FakeSourceAdapter manifest 为 LOW 风险，无需审批。"""
        from mindforge.extensions.samples.fake_source_adapter import (
            FAKE_SOURCE_MANIFEST,
        )

        m = FAKE_SOURCE_MANIFEST
        assert m.risk_level == RiskLevel.LOW
        assert m.requires_approval is False
        assert Capability.REAL_API not in m.capabilities
        assert Capability.NETWORK not in m.capabilities


# ── TestFakeExportAdapter ─────────────────────────────────


class TestFakeExportAdapter:
    """示例 FakeMarkdownExportAdapter 测试。"""

    def test_name_and_format(self):
        adapter = FakeMarkdownExportAdapter()
        assert adapter.name == "fake_export_markdown"
        assert adapter.export_format == "markdown"

    def test_can_handle_markdown_with_cards(self):
        adapter = FakeMarkdownExportAdapter()
        assert adapter.can_handle(frozenset({"card-1", "card-2"}), "markdown") is True

    def test_cannot_handle_empty_cards(self):
        adapter = FakeMarkdownExportAdapter()
        assert adapter.can_handle(frozenset(), "markdown") is False

    def test_cannot_handle_wrong_format(self):
        adapter = FakeMarkdownExportAdapter()
        assert adapter.can_handle(frozenset({"card-1"}), "json") is False

    def test_export_creates_file(self, tmp_path):
        adapter = FakeMarkdownExportAdapter()
        output = tmp_path / "export.md"
        result = adapter.export(frozenset({"card-a", "card-b"}), output)

        assert result.success is True
        assert result.card_count == 2
        assert result.format == "markdown"
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "card-a" in content
        assert "card-b" in content

    def test_export_empty_cards_fails(self, tmp_path):
        adapter = FakeMarkdownExportAdapter()
        output = tmp_path / "empty.md"
        result = adapter.export(frozenset(), output)

        assert result.success is False
        assert "card_ids 为空" in result.errors[0]

    def test_capabilities_match_manifest(self):
        adapter = FakeMarkdownExportAdapter()
        from mindforge.extensions.samples.fake_export_adapter import (
            FAKE_EXPORT_MANIFEST,
        )

        adapter_caps = adapter.capabilities()
        manifest_caps = {c.value for c in FAKE_EXPORT_MANIFEST.capabilities}
        assert adapter_caps == manifest_caps


# ── TestManifestAlignment ─────────────────────────────────


class TestManifestAlignment:
    """验证示例适配器的 manifest 与运行时行为对齐。"""

    def test_fake_source_no_real_api(self):
        """Fake 适配器不应声明 REAL_API 或 NETWORK。"""
        from mindforge.extensions.samples.fake_source_adapter import (
            FAKE_SOURCE_MANIFEST,
        )
        from mindforge.extensions.samples.fake_export_adapter import (
            FAKE_EXPORT_MANIFEST,
        )

        for manifest in (FAKE_SOURCE_MANIFEST, FAKE_EXPORT_MANIFEST):
            assert Capability.REAL_API not in manifest.capabilities, (
                f"{manifest.name} 不应声明 REAL_API"
            )
            assert Capability.NETWORK not in manifest.capabilities, (
                f"{manifest.name} 不应声明 NETWORK"
            )

    def test_fake_adapters_are_low_risk(self):
        """所有示例适配器应为 LOW 风险。"""
        from mindforge.extensions.samples.fake_export_adapter import (
            FAKE_EXPORT_MANIFEST,
        )
        from mindforge.extensions.samples.fake_source_adapter import (
            FAKE_SOURCE_MANIFEST,
        )

        assert FAKE_SOURCE_MANIFEST.risk_level == RiskLevel.LOW
        assert FAKE_EXPORT_MANIFEST.risk_level == RiskLevel.LOW

    def test_fake_adapters_no_approval_required(self):
        """所有示例适配器不需要审批。"""
        from mindforge.extensions.samples.fake_export_adapter import (
            FAKE_EXPORT_MANIFEST,
        )
        from mindforge.extensions.samples.fake_source_adapter import (
            FAKE_SOURCE_MANIFEST,
        )

        for manifest in (FAKE_SOURCE_MANIFEST, FAKE_EXPORT_MANIFEST):
            assert manifest.requires_approval is False, (
                f"{manifest.name} 不应要求审批"
            )

    def test_export_adapter_is_instance(self):
        """FakeMarkdownExportAdapter 是 ExportAdapter 的实例。"""
        assert isinstance(FakeMarkdownExportAdapter(), ExportAdapter)
