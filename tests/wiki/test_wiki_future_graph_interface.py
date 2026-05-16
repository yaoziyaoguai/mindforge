"""Wiki P5 — Future Graph Renderer Interface 契约测试。

WikiGraphRenderer 为 v0.3+ 保留的 extension point，v0.2 中必须：
- raise NotImplementedError（不静默失败）
- 错误信息明确提及 v0.2
- API query param view=graph → 400
- Registry 不注册 graph renderer

RFC_0002 §5.4 / SDD_WIKI_PRESENTATION_V2 §10。
"""

from __future__ import annotations

import pytest


class TestWikiGraphRendererContract:
    """WikiGraphRenderer 必须做 v0.2 不做的事。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_renderer import WikiGraphRenderer, WikiRenderer

        self.WikiGraphRenderer = WikiGraphRenderer
        self.WikiRenderer = WikiRenderer

    def test_graph_renderer_is_subclass_of_wiki_renderer(self) -> None:
        assert issubclass(self.WikiGraphRenderer, self.WikiRenderer)

    def test_graph_renderer_name_is_graph(self) -> None:
        r = self.WikiGraphRenderer()
        assert r.name == "graph"

    def test_render_raises_not_implemented_error(self) -> None:
        r = self.WikiGraphRenderer()
        with pytest.raises(NotImplementedError):
            r.render({})  # type: ignore[call-arg]

    def test_error_message_mentions_v0_2_explicitly(self) -> None:
        r = self.WikiGraphRenderer()
        try:
            r.render({})  # type: ignore[call-arg]
        except NotImplementedError as e:
            assert "v0.2" in str(e).lower() or "v0.2" in str(e)

    def test_error_message_mentions_graph(self) -> None:
        r = self.WikiGraphRenderer()
        try:
            r.render({})  # type: ignore[call-arg]
        except NotImplementedError as e:
            assert "graph" in str(e).lower()

    def test_error_message_mentions_future_or_reserved(self) -> None:
        """错误信息应表明这是留给未来的 reserved extension point。"""
        r = self.WikiGraphRenderer()
        try:
            r.render({})  # type: ignore[call-arg]
        except NotImplementedError as e:
            msg = str(e).lower()
            assert "future" in msg or "reserved" in msg

    def test_graph_renderer_not_in_registry(self) -> None:
        """v0.2 中 graph renderer 不应注册——注册表中不可获取。"""
        from mindforge.wiki_renderer import get_wiki_renderer

        r = get_wiki_renderer("graph")
        assert r is None

    def test_cannot_call_render_with_none_view_model(self) -> None:
        """无论传入什么参数，render() 都应 raise NotImplementedError。"""
        r = self.WikiGraphRenderer()
        with pytest.raises(NotImplementedError):
            r.render(None)  # type: ignore[call-arg]

    def test_every_instance_raises(self) -> None:
        """每个 WikiGraphRenderer 实例都 raise——不是 singleton 特例。"""
        r1 = self.WikiGraphRenderer()
        r2 = self.WikiGraphRenderer()
        with pytest.raises(NotImplementedError):
            r1.render({})  # type: ignore[call-arg]
        with pytest.raises(NotImplementedError):
            r2.render({})  # type: ignore[call-arg]
