"""v0.2 Wiki Renderer Interface。

Renderer abstraction boundary — 当前只提供 text/markdown 标记和 graph
extension point。实际 Markdown → safe HTML 渲染在前端完成，不在后端实现。

RFC_0002 §5.4 / SDD_WIKI_PRESENTATION_V2 §4.2, §10。

设计边界：
- 后端不做 Markdown → HTML 渲染
- WikiGraphRenderer.render() → raises NotImplementedError
- get_wiki_renderer() 提供 registry 查询
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class WikiRenderer(ABC):
    """Wiki 渲染器抽象基类。

    为未来多视图扩展（text/markdown/graph）留接口。
    v0.2 唯一活跃路径：前端 Markdown → safe HTML。
    """

    name: str

    @abstractmethod
    def render(self, view_model: object, options: object | None = None) -> object:
        """将 WikiPageViewModel 渲染为目标输出格式。

        v0.2 默认行为：后端不调用此方法。实际渲染在前端完成。
        """
        ...


class WikiMarkdownRenderer(WikiRenderer):
    """Markdown 渲染器（v0.2 interface-only marker）。

    v0.2 中 Markdown → HTML 渲染在前端完成（Markdown library + DOMPurify）。
    后端只提供 WikiPageViewModel JSON，section.body 为 canonical Markdown text。
    """

    name = "markdown"

    def render(self, view_model: object, options: object | None = None) -> object:
        """v0.2：后端不渲染 Markdown → HTML。

        前端通过 /api/wiki/page 获取 WikiPageViewModel JSON，
        使用前端 Markdown library + DOMPurify 完成渲染。
        """
        return view_model  # pass-through: 后端不做渲染


class WikiGraphRenderer(WikiRenderer):
    """Graph visualization renderer（v0.2 only interface — NotImplementedError）。

    未来 v0.3+ 可从 WikiPageViewModel 的 card_refs 构建节点-边图。
    当前保留注册点，不实现任何 graph database / visualization。
    """

    name = "graph"

    def render(self, view_model: object, options: object | None = None) -> object:
        raise NotImplementedError(
            "Graph renderer is not implemented in v0.2. "
            "This is a reserved extension point for future graph view support. "
            "See docs/rfc/RFC_0002_WIKI_PRESENTATION_V2.md §5.4."
        )


# =============================================================================
# Renderer Registry
# =============================================================================

_WIKI_RENDERERS: dict[str, WikiRenderer] = {
    "markdown": WikiMarkdownRenderer(),
    # "graph": WikiGraphRenderer(),  # uncomment when implemented
}


def get_wiki_renderer(name: str) -> WikiRenderer | None:
    """按 name 查找 WikiRenderer。

    v0.2 注册：
    - "markdown" → WikiMarkdownRenderer（interface-only marker）
    - "graph" → 未注册，返回 None（future extension point）

    Args:
        name: "markdown" | "graph" | ...

    Returns:
        WikiRenderer 实例或 None
    """
    return _WIKI_RENDERERS.get(name)


__all__ = [
    "WikiRenderer",
    "WikiMarkdownRenderer",
    "WikiGraphRenderer",
    "get_wiki_renderer",
]
