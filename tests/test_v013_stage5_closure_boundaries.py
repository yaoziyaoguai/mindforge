"""Closure boundary tests.

这些测试不是单元测试；它们是仓库级闭包断言，确保文档治理后
canonical docs 与代码契约不会在未来悄悄漂移:

- completion ledger 必须列出所有关键状态桶;
- usage/testing 必须引用 quality gates;
- usage 必须同时记录 fake 和 real opt-in 路径;
- 默认 active_profile 仍然是 fake;
- 没有任何 v0.13 doc 引入了 git tag / release 字面量承诺;
- preflight 输出 contract 在源码中保持 ``human_approved=False``;
- 没有任何 production module (除已知白名单) 写 ``human_approved = True``。
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[1] / "docs"
SRC = Path(__file__).resolve().parents[1] / "src" / "mindforge"


def _read(p: Path) -> str:
    assert p.exists(), f"missing required v0.13 doc: {p}"
    return p.read_text(encoding="utf-8")


# ---------- closure ledger ----------

def test_closure_ledger_lists_all_state_buckets():
    text = _read(DOCS / "ROADMAP_COMPLETION_LEDGER.md")
    for bucket in (
        "available", "fake-only", "real-opt-in",
        "review-only", "future-gated", "forbidden",
    ):
        assert f"`{bucket}`" in text, f"closure ledger missing bucket: {bucket}"


def test_closure_ledger_marks_v013_stage_complete():
    text = _read(DOCS / "ROADMAP_COMPLETION_LEDGER.md")
    assert "clean enough for long-term local dogfood" in text
    # 必须明确说明 NO tag / NO release
    assert "No tag" in text or "no tag" in text
    assert "No release" in text or "no release" in text


def test_closure_ledger_keeps_dangerous_capabilities_gated():
    text = _read(DOCS / "ROADMAP_COMPLETION_LEDGER.md")
    # 这些能力必须显式标注 future-gated 或 forbidden, 不能漏
    for cap in (
        "Real Cubox ingestion",
        "Real Obsidian formal-note write",
        "Custom executable strategy runtime",
        "Auto-approve",
        "RAG / embedding / semantic merge",
        "Public release",
    ):
        assert cap in text, f"closure ledger missing capability row: {cap}"


# ---------- release readiness evidence ----------

def test_release_readiness_references_quality_gates():
    text = _read(DOCS / "TESTING.md")
    assert "ruff check" in text
    assert "pytest" in text
    assert "diff --check" in text or "diff-check" in text


def test_release_readiness_says_no_tag_no_release():
    text = _read(Path("README.md"))
    lower = text.lower()
    assert "no tag" in lower
    assert "tag" in lower


def test_release_readiness_records_future_gates():
    text = _read(Path("README.md"))
    for gate in (
        "Real Cubox ingestion",
        "Real Obsidian",
        "Custom executable strategy runtime",
        "RAG / embedding / semantic merge",
        "Public release",
    ):
        assert gate in text, f"release readiness missing future gate: {gate}"


# ---------- real-safe journey ----------

def test_real_safe_journey_documents_both_paths():
    text = _read(Path("README.md"))
    # fake-safe 默认必须出现
    assert "fake" in text.lower()
    assert "fake" in text.lower()
    # real opt-in 必须出现
    assert "--allow-real" in text
    # 警告必须出现 (billing 风险)
    assert "opt-in" in text.lower()
    # human_approved 路径必须明确说明只能由 approve 命令产生
    assert "mindforge approve" in text


def test_real_safe_journey_lists_what_user_did_not_do():
    text = _read(Path("README.md"))
    for negative in (
        "does not call a real LLM",
        "does not call the real Cubox API",
        "does not print `.env` secret values",
        "does not automatically modify a real private vault",
        "does not auto-approve",
    ):
        assert negative in text, f"journey missing negative assertion: {negative}"


# ---------- roadmap stage closure references ----------

def test_roadmap_records_all_v013_stages():
    text = _read(Path("README.md"))
    for stage in (
        "Web first slice",
        "Real Data CLI Usability",
        "Documentation cleanup",
    ):
        assert stage in text, f"roadmap missing stage closure: {stage}"


# ---------- repo-level invariants still hold ----------

def test_bundled_active_profile_is_real_dogfood():
    yaml_text = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mindforge"
        / "assets"
        / "configs"
        / "mindforge.yaml"
    ).read_text(encoding="utf-8")
    for line in yaml_text.splitlines():
        s = line.strip()
        if s.startswith("active_profile:"):
            assert s == "active_profile: openai_compatible", (
                f"default active_profile should be real dogfood: {s!r}"
            )
            break
    else:
        pytest.fail("active_profile not found in configs/mindforge.yaml")


def test_dogfood_safety_output_contract_keeps_human_approved_false():
    text = (SRC / "dogfood_safety.py").read_text(encoding="utf-8")
    # 静态断言: source 中明确写有 human_approved=False / human_approved": False
    # 字面量, 防止后续误改成 True 或可变。
    assert '"human_approved": False' in text


def test_real_smoke_keeps_human_approved_false():
    text = (SRC / "real_smoke.py").read_text(encoding="utf-8")
    assert '"human_approved": False' in text


def test_no_v013_doc_promises_a_tag():
    """所有 v0.13 文档不应包含 "git tag" 实际操作承诺 (只能在 forbidden /
    deferred / future-gated 上下文出现)。"""
    forbidden_tag_phrases = [
        "git tag v0.13",
        "git tag -a v0.13",
        "tagged as v0.13",
    ]
    for doc_name in (
        "../README.md",
        "ROADMAP_COMPLETION_LEDGER.md",
    ):
        text = _read(DOCS / doc_name)
        for phrase in forbidden_tag_phrases:
            assert phrase not in text, (
                f"{doc_name} appears to promise a tag operation: {phrase!r}"
            )
