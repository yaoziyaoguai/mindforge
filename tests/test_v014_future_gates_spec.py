"""v0.13 Roadmap Completion Pack — future-gate spec & evidence cookbook
boundary tests.

这些测试不验证未来能力本身 (它们尚未实现); 它们验证 v0.14
**future-gate 规格**与 evidence cookbook 的内容契约不会漂移:

- 每个 future gate 必须有 6 个标准 section;
- gate 文档必须列出 G1–G6 全部 6 个能力;
- 每个 gate 必须明确说明 "为什么 deferred", 不能只是 "TODO";
- evidence cookbook 必须列出 quality gates / fake confirmation /
  real refusal / dogfood preflight / approval boundary / boundary
  sweep 命令;
- evidence cookbook 不能教用户跑任何 forbidden 操作 (cat .env /
  auto-approve / git tag / Cubox real / Obsidian real write);
- preflight UX 文案: 允许时给出 fake-safe 下一步建议, 不教任何 real
  路径默认动作。
"""

from __future__ import annotations

from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
SRC = Path(__file__).resolve().parents[1] / "src" / "mindforge"


def _read(name: str) -> str:
    p = DOCS / name
    assert p.exists(), f"missing required v0.14 spec / evidence doc: {p}"
    return p.read_text(encoding="utf-8")


# ---------- v0.14 future gate spec ----------

def test_future_gates_doc_exists_with_all_six_gates():
    text = _read("V0_14_FUTURE_GATES.md")
    for gate in (
        "Gate G1 — Real Cubox Ingestion",
        "Gate G2 — Real Obsidian Formal-Note Write",
        "Gate G3 — `human_approved` Production UX",
        "Gate G4 — Custom Executable Strategy Runtime",
        "Gate G5 — RAG / Embedding / Semantic Merge",
        "Gate G6 — Public Release / Git Tag",
    ):
        assert gate in text, f"future gates doc missing: {gate}"


def test_each_gate_has_six_required_sections():
    text = _read("V0_14_FUTURE_GATES.md")
    # 6 个标准 section 必须各出现 ≥6 次 (每个 G 一次)
    for section in (
        "**Capability**",
        "**Why deferred**",
        "**Pre-conditions**",
        "**Boundary contract**",
        "**Closure criteria**",
        "**Test surface**",
    ):
        count = text.count(section)
        assert count >= 6, (
            f"section {section!r} appears {count} times, expected ≥6 "
            f"(once per gate)"
        )


def test_future_gates_keep_human_approved_invariant():
    text = _read("V0_14_FUTURE_GATES.md")
    # 必须明确写 approver.approve_card 是唯一晋升路径
    assert "approver.approve_card" in text
    # G3 必须禁止 timer-based / similarity / model-driven 自动 approve
    assert "timer-based auto-approval" in text or "No timer-based" in text
    assert "similarity" in text.lower()


def test_future_gates_release_section_forbids_automation():
    text = _read("V0_14_FUTURE_GATES.md")
    assert "No automation may create a tag" in text


# ---------- evidence cookbook ----------

def test_evidence_cookbook_lists_required_sections():
    text = _read("EVIDENCE_COMMANDS.md")
    for section in (
        "Quality gates",
        "Default-fake confirmation",
        "Real provider refusal",
        "Real provider opt-in",
        "Dogfood preflight",
        "Approval boundary check",
        "Boundary regex sweep",
        "Architecture boundary tests",
        "Roadmap state",
        "Push status",
    ):
        assert section in text, f"evidence cookbook missing section: {section}"


def test_evidence_cookbook_documents_what_it_does_not_do():
    text = _read("EVIDENCE_COMMANDS.md")
    for negative in (
        "Does not `cat .env`",
        "Does not print secrets",
        "Does not call Cubox",
        "Does not write to a real Obsidian",
        "Does not auto-approve",
        "Does not create a git tag",
    ):
        assert negative in text, f"cookbook missing negative: {negative}"


def test_evidence_cookbook_does_not_teach_forbidden_actions():
    text = _read("EVIDENCE_COMMANDS.md")
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
