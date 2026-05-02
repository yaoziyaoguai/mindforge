"""v0.13 Stage 1 — Industry pattern map 文档断言。

把 docs/V0_13_INDUSTRY_PATTERN_MAP.md 当成 spec, 用 token 断言钉死
关键内容不会被静默回退。
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC = Path("docs/V0_13_INDUSTRY_PATTERN_MAP.md")

REQUIRED_PRODUCTS = [
    "OpenAI Agents SDK",
    "LangGraph",
    "Dify",
    "Obsidian",
    "Readwise",
    "Cubox",
    "Logseq",
    "Tana",
    "Anytype",
]

REQUIRED_SECTIONS = [
    "## 1. 调研范围",
    "## 2. 共性模式",
    "## 3. 借鉴",
    "## 4. 拒绝",
    "## 5. 推迟",
    "## 6. MindForge 差异化",
    "## 7. 离线判断声明",
]

REQUIRED_TOKENS = [
    "differentiation",
    "rejected",
    "offline-judgement",
]


def test_industry_map_doc_exists():
    assert DOC.exists(), f"{DOC} missing"


@pytest.mark.parametrize("product", REQUIRED_PRODUCTS)
def test_industry_map_mentions_product(product: str):
    text = DOC.read_text(encoding="utf-8")
    assert product in text, f"product {product!r} missing"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_industry_map_has_section(section: str):
    text = DOC.read_text(encoding="utf-8")
    assert section in text, f"section header {section!r} missing"


@pytest.mark.parametrize("token", REQUIRED_TOKENS)
def test_industry_map_has_token(token: str):
    text = DOC.read_text(encoding="utf-8")
    assert token in text, f"token {token!r} missing"
