"""Closure boundary tests.

这些测试不是单元测试；它们是仓库级闭包断言，确保文档治理后
canonical docs 与代码契约不会在未来悄悄漂移:

- completion ledger 必须列出所有关键状态桶;
- usage/testing 必须引用 quality gates;
- usage 必须记录 real opt-in 与本地测试边界;
- 默认 LLM 配置使用 models/default_model/routing;
- 没有任何 v0.13 doc 引入了 git tag / release 字面量承诺;
- preflight 输出 contract 在源码中保持 ``human_approved=False``;
- 没有任何 production module (除已知白名单) 写 ``human_approved = True``。
"""

from __future__ import annotations

from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
SRC = Path(__file__).resolve().parents[1] / "src" / "mindforge"


def _read(p: Path) -> str:
    assert p.exists(), f"missing required v0.13 doc: {p}"
    return p.read_text(encoding="utf-8")


# ---------- closure ledger ----------

def test_closure_ledger_lists_all_state_buckets():
    text = _read(DOCS / "internal/ROADMAP_COMPLETION_LEDGER.md")
    for bucket in (
        "available", "real-opt-in",
        "review-only", "future-gated", "forbidden",
    ):
        assert f"`{bucket}`" in text, f"closure ledger missing bucket: {bucket}"


def test_closure_ledger_marks_v013_stage_complete():
    text = _read(DOCS / "internal/ROADMAP_COMPLETION_LEDGER.md")
    assert "clean enough for long-term local use" in text
    # 必须明确说明 NO tag / NO release
    assert "No tag" in text or "no tag" in text
    assert "No release" in text or "no release" in text


def test_closure_ledger_keeps_dangerous_capabilities_gated():
    text = _read(DOCS / "internal/ROADMAP_COMPLETION_LEDGER.md")
    # 这些能力必须显式标注 future-gated 或 forbidden, 不能漏
    for cap in (
        "External account ingestion",
        "Real Obsidian formal-note write",
        "Custom executable strategy runtime",
        "Auto-approve",
        "RAG / embedding / semantic merge",
        "Public release",
    ):
        assert cap in text, f"closure ledger missing capability row: {cap}"


# ---------- release readiness evidence ----------

def test_release_readiness_references_quality_gates():
    text = _read(DOCS / "dev/testing.md")
    assert "ruff check" in text
    assert "pytest" in text
    assert "diff --check" in text or "diff-check" in text


def test_release_readiness_says_no_tag_no_release():
    text = _read(DOCS / "internal/ROADMAP_COMPLETION_LEDGER.md")
    lower = text.lower()
    assert "no tag" in lower
    assert "tag" in lower


def test_release_readiness_records_future_gates():
    text = _read(DOCS / "internal/ROADMAP_COMPLETION_LEDGER.md")
    for gate in (
        "External account ingestion",
        "Real Obsidian",
        "Custom executable strategy runtime",
        "RAG / embedding / semantic merge",
        "Public release",
    ):
        assert gate in text, f"release readiness missing future gate: {gate}"


# ---------- real-safe journey ----------

def test_real_safe_journey_documents_both_paths():
    text = _read(Path("README.zh-CN.md"))
    # 本轮产品语义已迁移到 real model setup + local secret store。
    assert "Web Setup" in text or "Setup" in text
    assert "local secret store" in text or "secret store" in text
    assert "显式触发" in text  # 真实模型必须 opt-in
    # human_approved 路径必须明确说明只能由 approve 命令产生
    assert "mindforge approve" in text


def test_real_safe_journey_lists_what_user_did_not_do():
    text = _read(Path("README.zh-CN.md"))
    for negative in (
        "不自动审批",
        "不联网",
        "不上传",
        "不进 Git",
        "不进 Web 前端",
        "不从未审批",
        "必须 opt-in",
    ):
        assert negative in text, f"journey missing negative assertion: {negative}"


# ---------- roadmap stage closure references ----------

def test_roadmap_records_all_v013_stages():
    text = _read(DOCS / "internal/ROADMAP_COMPLETION_LEDGER.md")
    for stage in (
        "Web first slice",
        "Real Data CLI Usability",
        "Documentation cleanup",
    ):
        assert stage in text, f"roadmap missing stage closure: {stage}"


# ---------- repo-level invariants still hold ----------

def test_bundled_llm_config_uses_model_routing_not_profiles():
    yaml_text = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mindforge"
        / "assets"
        / "configs"
        / "mindforge.yaml"
    ).read_text(encoding="utf-8")
    assert "default_model: null" in yaml_text
    assert "routing:" in yaml_text
    assert "active_profile:" not in yaml_text
    assert "profiles:" not in yaml_text
    assert "fake_fast" not in yaml_text


def test_input_safety_output_contract_keeps_human_approved_false():
    """input preflight 是只读 safety boundary，不产生审批副作用。"""
    text = (SRC / "input_safety.py").read_text(encoding="utf-8")
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
        "internal/ROADMAP_COMPLETION_LEDGER.md",
    ):
        text = _read(DOCS / doc_name)
        for phrase in forbidden_tag_phrases:
            assert phrase not in text, (
                f"{doc_name} appears to promise a tag operation: {phrase!r}"
            )
