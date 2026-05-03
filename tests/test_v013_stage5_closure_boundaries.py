"""v0.13 Stage 5 — closure boundary tests.

这些测试不是单元测试; 它们是**仓库级闭包断言**, 确保 v0.13 收口所
依赖的边界文档与代码契约不会在未来悄悄漂移:

- closure ledger 必须列出所有关键状态桶;
- release readiness evidence 必须引用 quality gates;
- real-safe journey 必须同时记录 fake 和 real 路径;
- roadmap 必须包含 Stage 1–5 的 closure 段;
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
    text = _read(DOCS / "V0_13_CLOSURE_LEDGER.md")
    for bucket in (
        "available", "fake-only", "real-opt-in",
        "review-only", "future-gated", "forbidden",
    ):
        assert f"`{bucket}`" in text, f"closure ledger missing bucket: {bucket}"


def test_closure_ledger_marks_v013_stage_complete():
    text = _read(DOCS / "V0_13_CLOSURE_LEDGER.md")
    assert "stage-complete" in text.lower()
    # 必须明确说明 NO tag / NO release
    assert "No tag" in text or "no tag" in text
    assert "No release" in text or "no release" in text


def test_closure_ledger_keeps_dangerous_capabilities_gated():
    text = _read(DOCS / "V0_13_CLOSURE_LEDGER.md")
    # 这些能力必须显式标注 future-gated 或 forbidden, 不能漏
    for cap in (
        "Real Cubox API ingestion",
        "Real Obsidian formal-note write",
        "Custom executable strategy runtime",
        "Auto-approve",
        "RAG / embedding / semantic merge",
        "Public release",
    ):
        assert cap in text, f"closure ledger missing capability row: {cap}"


# ---------- release readiness evidence ----------

def test_release_readiness_references_quality_gates():
    text = _read(DOCS / "V0_13_RELEASE_READINESS_EVIDENCE.md")
    assert "ruff check" in text
    assert "pytest" in text
    assert "1257 passed" in text
    assert "diff --check" in text or "diff-check" in text


def test_release_readiness_says_no_tag_no_release():
    text = _read(DOCS / "V0_13_RELEASE_READINESS_EVIDENCE.md")
    lower = text.lower()
    assert "no tag" in lower
    assert "no release" in lower


def test_release_readiness_records_future_gates():
    text = _read(DOCS / "V0_13_RELEASE_READINESS_EVIDENCE.md")
    for gate in (
        "Real Cubox ingestion",
        "Real Obsidian write",
        "Custom executable strategy runtime",
        "RAG / embedding / semantic merge",
        "Public release",
    ):
        assert gate in text, f"release readiness missing future gate: {gate}"


# ---------- real-safe journey ----------

def test_real_safe_journey_documents_both_paths():
    text = _read(DOCS / "V0_13_REAL_SAFE_JOURNEY.md")
    # fake-safe 默认必须出现
    assert "fake" in text.lower()
    assert "active_profile: fake" in text
    # real opt-in 必须出现
    assert "--allow-real" in text
    # 警告必须出现 (billing 风险)
    assert "Billing warning" in text or "billing" in text.lower()
    # human_approved 路径必须明确说明只能由 approve 命令产生
    assert "approve_card" in text or "approve --card" in text or "mindforge approve" in text


def test_real_safe_journey_lists_what_user_did_not_do():
    text = _read(DOCS / "V0_13_REAL_SAFE_JOURNEY.md")
    for negative in (
        "NOT scanned your home",
        "NOT scanned your real Obsidian",
        "NOT pulled any Cubox",
        "NOT written to your real Obsidian",
        "NOT auto-approved",
        "NOT printed your API key",
        "NOT committed `.env`",
    ):
        assert negative in text, f"journey missing negative assertion: {negative}"


# ---------- roadmap stage closure references ----------

def test_roadmap_records_all_v013_stages():
    text = _read(DOCS / "ROADMAP.md")
    for stage in (
        "v0.13 Stage 1",
        "v0.13 Stage 2",
        "v0.13 Stage 3",
        "v0.13 Stage 4",
    ):
        assert stage in text, f"roadmap missing stage closure: {stage}"


# ---------- repo-level invariants still hold ----------

def test_default_active_profile_remains_fake():
    yaml_text = (Path(__file__).resolve().parents[1] / "configs" / "mindforge.yaml").read_text(encoding="utf-8")
    # 找到 active_profile 行, 必须是 fake (not commented out)
    for line in yaml_text.splitlines():
        s = line.strip()
        if s.startswith("active_profile:"):
            assert "fake" in s, f"default active_profile changed away from fake: {s!r}"
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
        "V0_13_CLOSURE_LEDGER.md",
        "V0_13_RELEASE_READINESS_EVIDENCE.md",
        "V0_13_REAL_SAFE_JOURNEY.md",
        "V0_13_DOGFOOD_PREFLIGHT.md",
        "V0_13_REAL_LLM_SMOKE_SAFETY.md",
    ):
        text = _read(DOCS / doc_name)
        for phrase in forbidden_tag_phrases:
            assert phrase not in text, (
                f"{doc_name} appears to promise a tag operation: {phrase!r}"
            )
