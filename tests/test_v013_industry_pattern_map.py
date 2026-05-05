"""v0.13 Stage 1 — product-positioning invariants now live in canonical docs.

学习型说明：旧的阶段性 industry map 已被清理为历史噪音。
这里不再钉住某个临时调研文件，而是保护仍然有价值的产品边界：MindForge
借鉴本地知识工具与 source capture 工具，但不滑向 SaaS、RAG 或自动写 vault。
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOCS = (
    Path("README.md"),
)

REQUIRED_TOKENS = [
    "local-first",
    "single-user",
    "SourceAdapter",
    "Cubox",
    "Obsidian",
    "BM25",
    "not RAG",
    "not embedding",
    "explicit approval",
    "human_approved",
    "fake provider",
    "real provider",
    "opt-in",
]


def _canonical_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in DOCS)


@pytest.mark.parametrize("path", DOCS)
def test_positioning_lives_in_canonical_docs(path: Path) -> None:
    assert path.exists(), f"{path} missing"


@pytest.mark.parametrize("token", REQUIRED_TOKENS)
def test_product_positioning_tokens_are_preserved(token: str) -> None:
    assert token in _canonical_text(), f"token {token!r} missing from canonical docs"
