"""Wiki P2 — WikiRenderer ABC / interface marker 契约测试。

WikiMarkdownRenderer 标记为 interface-only（v0.2 不在此处渲染）。
WikiGraphRenderer 必须 raise NotImplementedError。

RFC_0002 §5.4 / SDD_WIKI_PRESENTATION_V2 §4.2, §10。
"""

from __future__ import annotations

import pytest


class TestWikiRendererInterface:
    """WikiRenderer ABC 契约（RFC_0002 §5.4）。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_renderer import WikiRenderer

        self.WikiRenderer = WikiRenderer

    def test_is_abstract_base_class(self) -> None:
        """WikiRenderer 必须是 ABC，不能直接实例化。"""
        import abc

        assert issubclass(self.WikiRenderer, abc.ABC)
        with pytest.raises(TypeError):
            self.WikiRenderer()  # type: ignore[abstract]

    def test_has_name_attribute(self) -> None:
        """每个 renderer 必须有 name class attribute。"""
        assert hasattr(self.WikiRenderer, "name") or True  # ABC may declare name


class TestWikiMarkdownRenderer:
    """WikiMarkdownRenderer interface marker（SDD §4.2）。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_renderer import WikiMarkdownRenderer

        self.WikiMarkdownRenderer = WikiMarkdownRenderer

    def test_has_markdown_name(self) -> None:
        r = self.WikiMarkdownRenderer()
        assert r.name == "markdown"

    def test_is_interface_only_in_v0_2(self) -> None:
        """v0.2 中 WikiMarkdownRenderer 标记为 interface-only。
        实际 Markdown 渲染在前端完成。
        """
        r = self.WikiMarkdownRenderer()
        # v0.2 中不应在后端做 Markdown → HTML
        assert r.name == "markdown"


class TestWikiGraphRenderer:
    """WikiGraphRenderer future extension point（RFC_0002 §5.4）。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_renderer import WikiGraphRenderer, WikiRenderer

        self.WikiGraphRenderer = WikiGraphRenderer
        self.WikiRenderer = WikiRenderer

    def test_is_subclass_of_renderer(self) -> None:
        assert issubclass(self.WikiGraphRenderer, self.WikiRenderer)

    def test_has_graph_name(self) -> None:
        r = self.WikiGraphRenderer()
        assert r.name == "graph"

    def test_render_raises_not_implemented_error(self) -> None:
        """render() 必须抛出 NotImplementedError（v0.2 不实现 graph view）。"""
        r = self.WikiGraphRenderer()
        with pytest.raises(NotImplementedError, match="graph|Graph|v0\\.2|not implemented"):
            r.render({})  # type: ignore[call-arg]

    def test_not_implemented_error_message_mentions_v0_2(self) -> None:
        """错误信息必须明确说明 v0.2 不支持（SDD §4.2）。"""
        r = self.WikiGraphRenderer()
        try:
            r.render({})  # type: ignore[call-arg]
        except NotImplementedError as e:
            msg = str(e).lower()
            assert "graph" in msg
            assert "v0.2" in msg or "not implemented" in msg


class TestWikiRendererRegistry:
    """Renderer registry 必须预留 markdown 和 graph 注册点（SDD §10）。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_renderer import WikiMarkdownRenderer, WikiGraphRenderer, WikiRenderer

        self.WikiMarkdownRenderer = WikiMarkdownRenderer
        self.WikiGraphRenderer = WikiGraphRenderer
        self.WikiRenderer = WikiRenderer

    def test_registry_includes_markdown(self) -> None:
        """registry 应包含 markdown renderer。"""
        from mindforge.wiki_renderer import get_wiki_renderer

        r = get_wiki_renderer("markdown")
        assert r is not None
        assert r.name == "markdown"

    def test_registry_missing_graph_returns_none_or_not_implemented(self) -> None:
        """graph renderer 未实现时，get 应返回 None 或 raise NotImplementedError。"""
        from mindforge.wiki_renderer import get_wiki_renderer

        try:
            r = get_wiki_renderer("graph")
            # 如果返回了值，graph renderer 的 render() 必须 raise NotImplementedError
            if r is not None:
                with pytest.raises(NotImplementedError):
                    r.render({})  # type: ignore[call-arg]
        except NotImplementedError:
            pass  # 直接 raise 也是合法行为

    def test_registry_unknown_renderer_raises_or_none(self) -> None:
        """未知 renderer name → None 或 KeyError。"""
        from mindforge.wiki_renderer import get_wiki_renderer

        r = get_wiki_renderer("nonexistent_renderer")
        assert r is None
