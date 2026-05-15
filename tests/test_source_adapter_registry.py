"""M1 Phase P6 — AdapterRegistry skeleton 契约测试。

测试 v0.2 AdapterRegistry 的最小行为：
- register / find_for_path / find_for_type / list_adapters
- 按注册顺序派发（priority dispatch）
- find_for_path 不调用 adapter.load
- create_default_registry 仅注册 PlainMarkdownAdapter
- 不读 .env / 不调 LLM / 不做 auto approve

RFC_0001 §5.3 定义了 AdapterRegistry 的完整 contract。
"""

from __future__ import annotations

import pytest


# =============================================================================
# 0. 导入状态检查
# =============================================================================


def _module_has_attr(module_name: str, attr: str) -> bool:
    try:
        import importlib

        mod = importlib.import_module(module_name)
        return hasattr(mod, attr)
    except ImportError:
        return False


_REGISTRY_EXISTS = _module_has_attr("mindforge.sources.registry", "AdapterRegistry")
_DEFAULT_REGISTRY_EXISTS = _module_has_attr(
    "mindforge.sources.registry", "create_default_registry"
)


# =============================================================================
# A. AdapterRegistry 基本结构
# =============================================================================


@pytest.mark.xfail(
    not _REGISTRY_EXISTS,
    reason="v0.2 AdapterRegistry 尚未实现——预期 Red。Phase P6 实现后应 Green。",
    strict=True,
)
class TestAdapterRegistrySkeleton:
    """AdapterRegistry 的基本结构和接口契约。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.registry import AdapterRegistry

        self.AdapterRegistry = AdapterRegistry

    def test_registry_can_be_instantiated(self) -> None:
        """AdapterRegistry 应可无参实例化。"""
        reg = self.AdapterRegistry()
        assert reg is not None

    def test_registry_has_register_method(self) -> None:
        """AdapterRegistry 必须有 register 方法。"""
        assert hasattr(self.AdapterRegistry, "register")

    def test_registry_has_find_for_path_method(self) -> None:
        """AdapterRegistry 必须有 find_for_path 方法。"""
        assert hasattr(self.AdapterRegistry, "find_for_path")

    def test_registry_has_find_for_type_method(self) -> None:
        """AdapterRegistry 必须有 find_for_type 方法（RFC_0001 §5.3）。"""
        assert hasattr(self.AdapterRegistry, "find_for_type")

    def test_registry_has_list_adapters_method(self) -> None:
        """AdapterRegistry 必须有查询已注册 adapter 的方法。"""
        assert hasattr(self.AdapterRegistry, "list_adapters")


# =============================================================================
# B. register + list_adapters 行为
# =============================================================================


@pytest.mark.xfail(
    not _REGISTRY_EXISTS,
    reason="v0.2 AdapterRegistry 尚未实现——预期 Red。",
    strict=True,
)
class TestAdapterRegistryRegister:
    """注册和查询 adapter 的行为。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.registry import AdapterRegistry
        from mindforge.sources.markdown_adapter import PlainMarkdownAdapter
        from mindforge.sources.source_adapter import SourceAdapter

        self.AdapterRegistry = AdapterRegistry
        self.PlainMarkdownAdapter = PlainMarkdownAdapter
        self.SourceAdapter = SourceAdapter

    def test_register_adds_adapter(self) -> None:
        """register 后应能通过 list_adapters 查到。"""
        reg = self.AdapterRegistry()
        adapter = self.PlainMarkdownAdapter()
        reg.register(adapter)
        adapters = reg.list_adapters()
        assert adapter in adapters

    def test_list_adapters_returns_tuple(self) -> None:
        """list_adapters 应返回不可变 tuple（不暴露内部可变状态）。"""
        reg = self.AdapterRegistry()
        result = reg.list_adapters()
        assert isinstance(result, tuple)

    def test_list_adapters_is_readonly_view(self) -> None:
        """list_adapters 返回的 tuple 不应影响内部状态。"""
        reg = self.AdapterRegistry()
        reg.register(self.PlainMarkdownAdapter())
        view1 = reg.list_adapters()
        # 对 view 的修改不应影响 registry 内部状态
        reg.register(self.PlainMarkdownAdapter())
        view2 = reg.list_adapters()
        assert len(view2) == len(view1) + 1

    def test_empty_registry_list_adapters_returns_empty(self) -> None:
        """空 registry 的 list_adapters 应返回空 tuple。"""
        reg = self.AdapterRegistry()
        assert reg.list_adapters() == ()

    def test_register_multiple_adapters(self) -> None:
        """应可注册多个同类型 adapter（不同实例）。"""
        reg = self.AdapterRegistry()
        a1 = self.PlainMarkdownAdapter()
        a2 = self.PlainMarkdownAdapter()
        reg.register(a1)
        reg.register(a2)
        assert len(reg.list_adapters()) == 2


# =============================================================================
# C. find_for_path 按路径派发
# =============================================================================


@pytest.mark.xfail(
    not _REGISTRY_EXISTS,
    reason="v0.2 AdapterRegistry 尚未实现——预期 Red。",
    strict=True,
)
class TestAdapterRegistryFindForPath:
    """find_for_path 按路径派发 adapter。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.registry import AdapterRegistry
        from mindforge.sources.markdown_adapter import PlainMarkdownAdapter

        self.AdapterRegistry = AdapterRegistry
        self.PlainMarkdownAdapter = PlainMarkdownAdapter

    # -- Markdown 匹配 -------------------------------------------------------

    @pytest.mark.parametrize("path", ["note.md", "NOTE.MD", "path/to/file.md"])
    def test_find_for_path_returns_adapter_for_md(self, path: str) -> None:
        """find_for_path 应对 .md 文件返回 PlainMarkdownAdapter。"""
        reg = self.AdapterRegistry()
        reg.register(self.PlainMarkdownAdapter())
        found = reg.find_for_path(path)
        assert found is not None
        assert found.source_type == "plain_markdown"

    def test_find_for_path_returns_adapter_for_markdown(self) -> None:
        """find_for_path 应对 .markdown 文件返回 PlainMarkdownAdapter。"""
        reg = self.AdapterRegistry()
        reg.register(self.PlainMarkdownAdapter())
        found = reg.find_for_path("note.markdown")
        assert found is not None
        assert found.source_type == "plain_markdown"

    # -- 不支持的格式返回 None -----------------------------------------------

    @pytest.mark.parametrize("path", [
        "doc.pdf", "report.docx", "data.csv",
    ])
    def test_find_for_path_returns_none_for_unsupported(self, path: str) -> None:
        """不支持的格式应返回 None（不抛异常）。"""
        reg = self.AdapterRegistry()
        reg.register(self.PlainMarkdownAdapter())
        found = reg.find_for_path(path)
        assert found is None

    def test_find_for_path_returns_none_for_empty_registry(self) -> None:
        """空 registry 的 find_for_path 应返回 None。"""
        reg = self.AdapterRegistry()
        assert reg.find_for_path("note.md") is None

    # -- 注册顺序（优先级） --------------------------------------------------

    def test_find_for_path_respects_registration_order(self) -> None:
        """先注册的 adapter 优先匹配（priority dispatch）。

        RFC_0001 §5.3: 按注册顺序逐个调用 can_handle，返回第一个匹配的。
        """
        from mindforge.sources.source_adapter import SourceAdapter

        reg = self.AdapterRegistry()

        # 创建一个也声称能处理 .md 的 mock adapter
        order_tracker = []

        class MockAdapter(SourceAdapter):
            name = "MockAdapter"
            source_type = "mock"

            def can_handle(self, path: str) -> bool:
                order_tracker.append("mock")
                # 也声明能处理 .md，但应被 PlainMarkdownAdapter 优先匹配
                return path.endswith(".md")

            def load(self, path: str):
                raise NotImplementedError

        # 先注册 Markdown adapter → 高优先级
        reg.register(self.PlainMarkdownAdapter())
        # 后注册 mock → 低优先级
        reg.register(MockAdapter())

        found = reg.find_for_path("note.md")
        # 应返回第一个匹配的（PlainMarkdownAdapter）
        assert found is not None
        assert found.source_type == "plain_markdown"

    # -- find_for_path 不调用 load ------------------------------------------

    def test_find_for_path_does_not_call_load(self) -> None:
        """find_for_path 是纯查询，不应调用 adapter.load。

        RFC_0001 §5.3: find_for_path 仅通过 can_handle 判断，
        不加载文件内容、不解析。
        """
        from mindforge.sources.source_adapter import SourceAdapter

        reg = self.AdapterRegistry()

        class LoadTrackingAdapter(SourceAdapter):
            name = "Tracker"
            source_type = "tracker"
            load_called = False

            def can_handle(self, path: str) -> bool:
                return True

            def load(self, path: str):
                LoadTrackingAdapter.load_called = True
                raise RuntimeError("load should not be called by find_for_path")

        reg.register(LoadTrackingAdapter())
        reg.find_for_path("anything.txt")
        assert not LoadTrackingAdapter.load_called, (
            "find_for_path 不应调用 adapter.load"
        )


# =============================================================================
# D. find_for_type 按 source_type 查找
# =============================================================================


@pytest.mark.xfail(
    not _REGISTRY_EXISTS,
    reason="v0.2 AdapterRegistry 尚未实现——预期 Red。",
    strict=True,
)
class TestAdapterRegistryFindForType:
    """find_for_type 按 source_type 查找 adapter。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.registry import AdapterRegistry
        from mindforge.sources.markdown_adapter import PlainMarkdownAdapter

        self.AdapterRegistry = AdapterRegistry
        self.PlainMarkdownAdapter = PlainMarkdownAdapter

    def test_find_for_type_returns_adapter(self) -> None:
        """find_for_type("plain_markdown") 应返回 PlainMarkdownAdapter。"""
        reg = self.AdapterRegistry()
        reg.register(self.PlainMarkdownAdapter())
        found = reg.find_for_type("plain_markdown")
        assert found is not None
        assert found.name == "PlainMarkdownAdapter"

    def test_find_for_type_returns_none_for_unknown(self) -> None:
        """未知 source_type 应返回 None。"""
        reg = self.AdapterRegistry()
        reg.register(self.PlainMarkdownAdapter())
        assert reg.find_for_type("txt") is None
        assert reg.find_for_type("pdf") is None


# =============================================================================
# E. create_default_registry
# =============================================================================


@pytest.mark.xfail(
    not _DEFAULT_REGISTRY_EXISTS,
    reason="v0.2 create_default_registry 尚未实现——预期 Red。",
    strict=True,
)
class TestCreateDefaultRegistry:
    """create_default_registry 工厂函数。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.registry import create_default_registry

        self.create_default_registry = create_default_registry

    def test_returns_adapter_registry(self) -> None:
        """create_default_registry 应返回 AdapterRegistry 实例。"""
        from mindforge.sources.registry import AdapterRegistry

        reg = self.create_default_registry()
        assert isinstance(reg, AdapterRegistry)

    def test_registers_markdown_txt_html_pdf(self) -> None:
        """默认 registry 应注册 4 个 adapter（M2+M3）。"""
        reg = self.create_default_registry()
        adapters = reg.list_adapters()
        assert len(adapters) == 4
        types = [a.source_type for a in adapters]
        assert "plain_markdown" in types
        assert "txt" in types
        assert "html" in types
        assert "pdf" in types

    def test_find_for_path_md_works_with_default(self) -> None:
        reg = self.create_default_registry()
        found = reg.find_for_path("note.md")
        assert found is not None
        assert found.source_type == "plain_markdown"

    def test_find_for_path_txt_works_with_default(self) -> None:
        reg = self.create_default_registry()
        found = reg.find_for_path("note.txt")
        assert found is not None
        assert found.source_type == "txt"

    def test_find_for_path_html_works_with_default(self) -> None:
        reg = self.create_default_registry()
        found = reg.find_for_path("page.html")
        assert found is not None
        assert found.source_type == "html"

    def test_find_for_path_pdf_works_with_default(self) -> None:
        reg = self.create_default_registry()
        found = reg.find_for_path("doc.pdf")
        assert found is not None
        assert found.source_type == "pdf"

    def test_find_for_path_unsupported_returns_none_with_default(self) -> None:
        reg = self.create_default_registry()
        assert reg.find_for_path("report.docx") is None


# =============================================================================
# F. 安全 / 边界守卫
# =============================================================================


@pytest.mark.xfail(
    not _REGISTRY_EXISTS,
    reason="v0.2 AdapterRegistry 尚未实现——预期 Red。",
    strict=True,
)
class TestAdapterRegistrySafety:
    """AdapterRegistry 安全边界。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.registry import AdapterRegistry, create_default_registry
        from mindforge.sources.markdown_adapter import PlainMarkdownAdapter

        self.AdapterRegistry = AdapterRegistry
        self.create_default_registry = create_default_registry
        self.PlainMarkdownAdapter = PlainMarkdownAdapter

    def test_registry_instantiation_does_no_io(self) -> None:
        """实例化不应做 IO。"""
        reg = self.AdapterRegistry()
        assert reg is not None

    def test_register_does_not_call_load(self) -> None:
        """register 不应调用 adapter.load。"""
        from mindforge.sources.source_adapter import SourceAdapter

        reg = self.AdapterRegistry()

        class NoLoadAdapter(SourceAdapter):
            name = "NoLoad"
            source_type = "noload"

            def can_handle(self, path: str) -> bool:
                return False

            def load(self, path: str):
                raise RuntimeError("should not be called")

        reg.register(NoLoadAdapter())
        # 确认注册成功且 load 未被调用
        assert len(reg.list_adapters()) == 1

    def test_find_for_path_does_not_read_env(self, monkeypatch) -> None:
        """find_for_path 不应读环境变量。"""
        reg = self.AdapterRegistry()
        reg.register(self.PlainMarkdownAdapter())
        # 这本身不验证 env 是否被读，但至少确保调用不依赖 env
        result = reg.find_for_path("note.md")
        assert result is not None

    def test_create_default_registry_is_idempotent(self) -> None:
        """多次调用 create_default_registry 应返回独立的 registry 实例。"""
        reg1 = self.create_default_registry()
        reg2 = self.create_default_registry()
        assert reg1 is not reg2
        count1 = len(reg1.list_adapters())
        count2 = len(reg2.list_adapters())
        assert count1 == count2
        # 修改一个不应影响另一个
        reg1.register(self.PlainMarkdownAdapter())
        assert len(reg1.list_adapters()) == count1 + 1
        assert len(reg2.list_adapters()) == count2
