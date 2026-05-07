"""Future-gate docs and preflight UX boundary tests.

这些测试不验证未来能力本身；它们验证 canonical roadmap / ledger 仍然列出
future gates，且 evidence 命令不会教用户跑 forbidden 操作。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SRC = Path(__file__).resolve().parents[1] / "src" / "mindforge"


def _read(name: str) -> str:
    p = ROOT / "README.md" if name == "README.md" else DOCS / name
    assert p.exists(), f"missing required doc: {p}"
    return p.read_text(encoding="utf-8")


# ---------- v0.14 future gate spec ----------

def test_roadmap_exists_with_all_future_gates():
    text = _read("README.md")
    for gate in (
        "G1 Real Cubox ingestion",
        "G2 Real Obsidian formal-note write",
        "G3 Approval UX",
        "G4 Custom executable strategy runtime",
        "G5 RAG / embedding / semantic merge",
        "G6 Public release / git tag",
    ):
        assert gate in text, f"roadmap missing: {gate}"


def test_future_gates_keep_human_approved_invariant():
    text = _read("ROADMAP_COMPLETION_LEDGER.md")
    assert "only explicit human approval" in text
    assert "timer" in _read("README.md").lower() or "timer" in text.lower()
    assert "similarity" in text.lower()


def test_future_gates_release_section_forbids_automation():
    text = _read("ROADMAP_COMPLETION_LEDGER.md")
    assert "no automation may create a tag" in text.lower()


# ---------- evidence cookbook ----------

def test_usage_and_testing_list_required_evidence_sections():
    text = _read("README.md") + "\n" + _read("TESTING.md")
    for section in (
        "First Status Commands",
        "Real Provider Opt-In",
        "Safe Real Dogfood",
        "Approval",
        "Standard Quality Gate",
    ):
        assert section in text, f"canonical docs missing section: {section}"


def test_evidence_cookbook_documents_what_it_does_not_do():
    text = _read("README.md")
    for negative in (
        "does not print `.env` secret values",
        "does not call the real Cubox API",
        "does not automatically modify a real private vault",
        "does not auto-approve",
    ):
        assert negative in text, f"README.md missing negative: {negative}"


def test_evidence_cookbook_does_not_teach_forbidden_actions():
    text = _read("README.md") + "\n" + _read("TESTING.md")
    # 反例: cookbook 不能给出实际的 cat .env / auto-approve 命令行;
    # 仅扫描 fenced code 块, 排除 "Does not / ❌" 这类负向描述。
    in_code = False
    code_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
    code_text = "\n".join(code_lines)
    forbidden = [
        "cat .env",
        "git tag v",
        "git push --tags",
        "git push --force",
    ]
    for f in forbidden:
        assert f not in code_text, (
            f"cookbook code block teaches a forbidden action: {f!r}"
        )


# ---------- preflight UX hint ----------

def test_preflight_render_suggests_fake_safe_next_command_when_allowed():
    """allowed 路径必须 hint fake-safe 下一步, 不能 hint real provider。"""
    src = (SRC / "dogfood_safety.py").read_text(encoding="utf-8")
    assert "Suggested next (manual, fake-safe)" in src
    assert "--profile fake" in src
    # 反例: 不能默认教用户跑 --allow-real
    assert "--allow-real" not in src


def test_preflight_render_offers_safe_alternatives_when_refused():
    src = (SRC / "dogfood_safety.py").read_text(encoding="utf-8")
    assert "Refused. Safe alternatives" in src
    assert "examples/demo-vault" in src
