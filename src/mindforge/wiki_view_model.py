"""v0.2 Wiki Presentation View Model。

从 LLM synthesis JSON + CardDigest index 构建结构化 Wiki 页面视图。
后端输出 canonical Markdown text，不渲染 HTML。前端负责 Markdown → safe HTML。

RFC_0002 §5.1 / SDD_WIKI_PRESENTATION_V2 §4.1, §5。

设计边界：
- WikiPageViewModel 只基于 human_approved cards（通过 CardDigest）
- section.body 是 canonical Markdown text，不是 HTML
- 后端不生成最终 HTML
- 所有 ViewModel 类为 frozen dataclass（不可变）
- WikiRenderOptions 为 mutable（用户可配置）
- Graph renderer 只留接口，不做实现
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mindforge.wiki_service import CardDigest


def _slugify(text: str) -> str:
    """将 section title 转为 URL-safe anchor slug。"""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)  # remove punctuation
    slug = re.sub(r"\s+", "-", slug)       # spaces → hyphens
    slug = re.sub(r"-+", "-", slug)        # collapse hyphens
    return slug.strip("-")


def _derive_source_type(source_title: str | None) -> str | None:
    """从 source_title（文件名）推导 source_type。

    仅基于文件后缀，不做文件系统访问。
    """
    if not source_title:
        return None
    suffix = source_title.rsplit(".", 1)[-1].lower() if "." in source_title else ""
    mapping = {
        "md": "plain_markdown",
        "markdown": "plain_markdown",
        "txt": "txt",
        "html": "html",
        "htm": "html",
        "pdf": "pdf",
        "docx": "docx",
    }
    return mapping.get(suffix)


# =============================================================================
# View Model Data Classes
# =============================================================================


@dataclass(frozen=True)
class WikiReferenceView:
    """单个 card/source 引用的视图（RFC_0002 §5.1）。

    包含完整 provenance 信息，供前端 References panel 使用。
    source_type / source_path 从 CardDigest 推导，可能为 None。
    """

    card_id: str
    card_title: str
    source_title: str | None = None
    source_type: str | None = None
    source_path: str | None = None
    track: str | None = None
    tags: list[str] = field(default_factory=list)
    value_score: int | None = None
    approved_at: str | None = None
    card_rel_path: str = ""


@dataclass(frozen=True)
class WikiSectionView:
    """单个 Wiki section 的视图（RFC_0002 §5.1）。

    body 为 canonical Markdown text，非 HTML。
    anchor 用于 TOC 导航（URL-safe slug）。
    """

    id: str
    title: str
    body: str  # canonical Markdown text
    level: int = 2
    card_refs: list[WikiReferenceView] = field(default_factory=list)
    anchor: str = ""


@dataclass(frozen=True)
class WikiQuestionView:
    """Open question 的视图（RFC_0002 §5.1）。"""

    question: str


@dataclass(frozen=True)
class WikiPageViewModel:
    """Wiki 页面的结构化视图模型（RFC_0002 §5.1）。

    从 LLM synthesis JSON + CardDigest index 构建。
    overview / section.body 均为 canonical Markdown text。
    后端不渲染 HTML——前端通过 Markdown 库 + DOMPurify 完成。
    """

    title: str
    mode: str  # "llm" | "deterministic"
    model_id: str | None
    last_rebuilt_at: str | None
    overview: str  # canonical Markdown text
    sections: list[WikiSectionView]
    additional_cards: list[WikiReferenceView]
    open_questions: list[WikiQuestionView]
    included_card_count: int
    additional_card_count: int
    warnings: list[str]

    @classmethod
    def build(
        cls,
        synthesis_output: dict,
        digests: list[CardDigest],
        mode: str = "llm",
        model_id: str | None = None,
        last_rebuilt_at: str | None = None,
        warnings: list[str] | None = None,
    ) -> WikiPageViewModel:
        """从 synthesis JSON + CardDigest index 构建 WikiPageViewModel。

        构建逻辑（SDD §4.1）：
        1. 从 synthesis JSON 解析 overview, sections[], open_questions[]
        2. 每个 section 的 card_ids[] 在 CardDigest index 中查找
        3. 构建 WikiReferenceView 包含 provenance
        4. 未被任何 section 引用的 card → additional_cards
        5. 记录 synthesis warnings

        Args:
            synthesis_output: LLM synthesis JSON output dict
            digests: 所有 approved card 的 CardDigest 列表
            mode: "llm" 或 "deterministic"
            model_id: LLM model id（llm mode only）
            last_rebuilt_at: 最后重建时间
            warnings: 外部合成警告（如 LLM timeout）

        Returns:
            WikiPageViewModel with structured section/card references
        """
        # 构建 card_id → CardDigest 索引
        digest_index: dict[str, CardDigest] = {d.card_id: d for d in digests}

        all_warnings: list[str] = list(warnings or [])

        # 1. 解析 synthesis JSON
        overview = str(synthesis_output.get("overview") or "")

        # 2. 构建 sections
        raw_sections: list[dict] = synthesis_output.get("sections") or []
        if not isinstance(raw_sections, list):
            raw_sections = []

        cited_card_ids: set[str] = set()
        sections: list[WikiSectionView] = []
        for i, sec in enumerate(raw_sections):
            sec_title = str(sec.get("title") or "")
            sec_body = str(sec.get("body") or "")
            sec_card_ids: list[str] = sec.get("card_ids") or []
            if not isinstance(sec_card_ids, list):
                sec_card_ids = []

            # 查找 card_refs
            card_refs: list[WikiReferenceView] = []
            for cid in sec_card_ids:
                cited_card_ids.add(cid)
                digest = digest_index.get(cid)
                if digest is not None:
                    source_type = _derive_source_type(digest.source_title)
                    card_refs.append(
                        WikiReferenceView(
                            card_id=digest.card_id,
                            card_title=digest.title,
                            source_title=digest.source_title,
                            source_type=source_type,
                            source_path=None,  # CardDigest 不含 source_path
                            track=digest.track,
                            tags=list(digest.tags),
                            value_score=digest.value_score,
                            approved_at=digest.approved_at,
                            card_rel_path=digest.card_rel_path,
                        )
                    )
                else:
                    all_warnings.append(f"unknown card_id: {cid}")

            anchor = "#" + _slugify(sec_title)
            sections.append(
                WikiSectionView(
                    id=f"section-{i}",
                    title=sec_title,
                    body=sec_body,
                    level=2,
                    card_refs=card_refs,
                    anchor=anchor,
                )
            )

        # 3. 未被任何 section 引用的 card → additional_cards
        additional: list[WikiReferenceView] = []
        for d in digests:
            if d.card_id not in cited_card_ids:
                source_type = _derive_source_type(d.source_title)
                additional.append(
                    WikiReferenceView(
                        card_id=d.card_id,
                        card_title=d.title,
                        source_title=d.source_title,
                        source_type=source_type,
                        source_path=None,
                        track=d.track,
                        tags=list(d.tags),
                        value_score=d.value_score,
                        approved_at=d.approved_at,
                        card_rel_path=d.card_rel_path,
                    )
                )

        # 4. 解析 open_questions
        raw_questions: list = synthesis_output.get("open_questions") or []
        if not isinstance(raw_questions, list):
            raw_questions = []
        questions = [
            WikiQuestionView(question=str(q)) for q in raw_questions
        ]

        return cls(
            title="MindForge Main Wiki",
            mode=mode,
            model_id=model_id,
            last_rebuilt_at=last_rebuilt_at,
            overview=overview,
            sections=sections,
            additional_cards=additional,
            open_questions=questions,
            included_card_count=len(digests),
            additional_card_count=len(additional),
            warnings=all_warnings,
        )


@dataclass
class WikiRenderOptions:
    """Wiki 渲染选项（mutable，用户可配置）。不影响 Wiki 数据本身。"""

    show_provenance_panel: bool = True
    show_toc: bool = True
    toc_position: str = "sidebar"  # "sidebar" | "top"
    sanitize_html: bool = True
    enable_mermaid: bool = False  # future
    enable_code_highlight: bool = True


__all__ = [
    "WikiPageViewModel",
    "WikiSectionView",
    "WikiReferenceView",
    "WikiQuestionView",
    "WikiRenderOptions",
]
