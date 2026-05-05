"""M5.3 — Better project context 测试。

设计与 v0.2.0 / M4.1 一致：
- 不调用任何 LLM；
- 不读 .env；
- 不修改源文件；
- 用 fake LLM fixture 构造 vault；
- 重点验证：项目级 profile 优先 / 卡片级补充 / target 路由 / 空段降级 /
  安全字段约束（runs jsonl 不泄漏 profile 正文 / suggested prompt 内容）。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.project_context import (
    EXCLUDED_CONTENT,
    resolve_target,
)
from mindforge.project_profile import (
    ProjectProfile,
    ProjectProfileError,
    load_project_profile,
)

from tests.test_process_e2e import (  # type: ignore[import-not-found]
    _build_vault_with_fake_llm,
    _common_process_args,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# 通用 fixture
# ---------------------------------------------------------------------------


def _setup_vault_with_one_approved_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    """构造含 1 张 my-first-agent / human_approved 卡的 vault。

    返回 (cfg_path, vault_root, card_path)。
    """
    for k in list(os.environ.keys()):
        if k.startswith("MINDFORGE_") or k.endswith("_API_KEY"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.chdir(tmp_path)

    cfg_path, vault, _src = _build_vault_with_fake_llm(tmp_path)
    assert runner.invoke(app, ["scan", "--config", str(cfg_path)]).exit_code == 0
    assert runner.invoke(app, _common_process_args(cfg_path)).exit_code == 0

    cards_dir = vault / "20-Knowledge-Cards" / "agent-runtime"
    card = next(cards_dir.glob("*.md"))
    assert runner.invoke(
        app, ["approve", "--card", str(card), "--config", str(cfg_path), "--confirm"]
    ).exit_code == 0

    text = card.read_text("utf-8")
    fm_text, body = text.split("---\n", 2)[1], text.split("---\n", 2)[2]
    fm = yaml.safe_load(fm_text)
    fm["id"] = "card-a"
    fm["title"] = "Card A — Agent Runtime topic"
    fm["track"] = "agent-runtime"
    fm["projects"] = ["my-first-agent"]
    fm["principles"] = ["card 级原则: 看 trace 再改"]
    fm["known_risks"] = ["card 级风险: 不要捏造日志"]
    card.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body,
        encoding="utf-8",
    )
    return cfg_path, vault, card


def _write_project_profile(
    vault: Path,
    project_name: str = "my-first-agent",
    *,
    default_target: str | None = "claude-code",
    description: str = "个人 Agent Runtime 实验项目",
    principles: list[str] | None = None,
    known_risks: list[str] | None = None,
    preferred_workflow: list[str] | None = None,
) -> Path:
    projects_dir = vault / "30-Projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    fm: dict = {"project": project_name, "description": description}
    if default_target is not None:
        fm["default_target"] = default_target
    fm["principles"] = principles or [
        "项目级原则 1：先看 runtime_observer / state / 真实 events",
        "项目级原则 2：关键代码必须中文 docstring",
    ]
    fm["known_risks"] = known_risks or [
        "项目级风险 1：不要让模型自动 approve",
    ]
    fm["preferred_workflow"] = preferred_workflow or [
        "先做只读诊断", "再做最小补丁", "最后跑测试和 smoke",
    ]
    p = projects_dir / f"{project_name}.md"
    p.write_text(
        "---\n"
        + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
        + "---\n\n# "
        + project_name
        + "\n\n这里是项目笔记正文，**不应被 mindforge 读取**。SECRET=sk-should-never-leak\n",
        encoding="utf-8",
    )
    return p


def _common_args(cfg: Path, project: str = "my-first-agent") -> list[str]:
    return ["project", "context", project, "--config", str(cfg)]


# ---------------------------------------------------------------------------
# 1. profile loader 单元测试
# ---------------------------------------------------------------------------


def test_load_project_profile_missing_file_returns_not_found(tmp_path: Path) -> None:
    p = load_project_profile(tmp_path, "30-Projects", "no-such-project")
    assert p.found is False
    assert p.rel_path is None
    assert p.principles == ()
    assert p.default_target is None


def test_load_project_profile_reads_frontmatter_only(tmp_path: Path) -> None:
    _write_project_profile(tmp_path)
    p = load_project_profile(tmp_path, "30-Projects", "my-first-agent")
    assert p.found is True
    assert p.rel_path == "30-Projects/my-first-agent.md"
    assert p.default_target == "claude-code"
    assert "项目级原则 1" in p.principles[0]
    assert any("自动 approve" in r for r in p.known_risks)
    # 正文里写了"SECRET=sk-...", profile 永远不读正文 → 不应出现在任何字段
    blob = json.dumps(
        {
            "principles": list(p.principles),
            "risks": list(p.known_risks),
            "workflow": list(p.preferred_workflow),
            "desc": p.description,
        },
        ensure_ascii=False,
    )
    assert "sk-should-never-leak" not in blob


def test_load_project_profile_invalid_default_target_falls_back(tmp_path: Path) -> None:
    _write_project_profile(tmp_path, default_target="not-a-real-target")
    p = load_project_profile(tmp_path, "30-Projects", "my-first-agent")
    assert p.found is True
    assert p.default_target is None  # 非法值 → 静默丢弃，profile 其余字段保留
    assert p.principles  # 其它字段不受影响


def test_load_project_profile_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(ProjectProfileError):
        load_project_profile(tmp_path, "30-Projects", "../../etc/passwd")
    with pytest.raises(ProjectProfileError):
        load_project_profile(tmp_path, "30-Projects", "/abs/path")


# ---------------------------------------------------------------------------
# 2. resolve_target 顺序
# ---------------------------------------------------------------------------


def test_resolve_target_cli_overrides_profile() -> None:
    profile = ProjectProfile(
        project_name="x", found=True, rel_path="30-Projects/x.md",
        default_target="claude-code",
    )
    assert resolve_target("copilot", profile) == "copilot"


def test_resolve_target_falls_back_to_profile_default() -> None:
    profile = ProjectProfile(
        project_name="x", found=True, rel_path="30-Projects/x.md",
        default_target="codex",
    )
    assert resolve_target(None, profile) == "codex"


def test_resolve_target_falls_back_to_generic() -> None:
    profile = ProjectProfile(project_name="x", found=False, rel_path=None)
    assert resolve_target(None, profile) == "generic"


def test_resolve_target_invalid_raises() -> None:
    profile = ProjectProfile(project_name="x", found=False, rel_path=None)
    with pytest.raises(ValueError):
        resolve_target("gpt-99", profile)


# ---------------------------------------------------------------------------
# 3. 端到端 markdown 输出
# ---------------------------------------------------------------------------


def test_project_context_with_profile_renders_project_level_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _card = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    _write_project_profile(vault)

    res = runner.invoke(app, _common_args(cfg))
    assert res.exit_code == 0, res.stdout
    out = res.stdout

    # Source notice 显示找到 profile
    assert "project_profile_found: true" in out
    assert "30-Projects/my-first-agent.md" in out
    # Project Profile 段
    assert "## Project Profile" in out
    assert "个人 Agent Runtime 实验项目" in out
    assert "先做只读诊断" in out
    # 项目级 principles 优先
    assert "## Project-Level Principles" in out
    assert "项目级原则 1" in out
    # 卡片级 principles 是补充
    assert "## Card-Level Principles (supplementary)" in out
    assert "from [card-a]: card 级原则" in out
    # 项目级 risks
    assert "## Project-Level Known Risks" in out
    assert "项目级风险 1" in out
    # 卡片级 risks 是补充
    assert "## Card-Level Known Risks (supplementary)" in out
    assert "from [card-a]: card 级风险" in out
    # target 来自 profile.default_target
    assert "target: claude-code" in out
    # Suggested Prompt for claude-code
    assert "## Suggested Prompt for claude-code" in out
    assert "claude-code" in out
    # Excluded content 清单始终出现
    assert "## Excluded Content (safety guarantee)" in out
    for item in EXCLUDED_CONTENT:
        assert item in out
    # 项目笔记正文里塞的 SECRET 永远不应出现
    assert "sk-should-never-leak" not in out


def test_project_context_no_profile_falls_back_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, _vault, _card = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    # 故意不写 profile

    res = runner.invoke(app, _common_args(cfg))
    assert res.exit_code == 0, res.stdout
    out = res.stdout

    # 显式声明降级
    assert "project_profile_found: false" in out
    assert "using Knowledge Cards only" in out
    # 不能出现空标题：每段都给降级文案
    assert "No project-level principles configured." in out
    assert "No project-level known_risks configured." in out
    assert "No description configured." in out
    assert "No preferred_workflow configured." in out
    # 卡片级补充段仍按数据存在与否渲染
    assert "from [card-a]: card 级原则" in out
    # target 退化为 generic
    assert "target: generic" in out
    assert "## Suggested Prompt for generic" in out


def test_project_context_target_cli_overrides_profile_and_emits_run_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    _write_project_profile(vault, default_target="claude-code")

    res = runner.invoke(app, _common_args(cfg) + ["--target", "copilot"])
    assert res.exit_code == 0, res.stdout
    assert "target: copilot" in res.stdout
    assert "## Suggested Prompt for copilot" in res.stdout

    # runs jsonl 含 target / project_profile_found
    runs_dir = tmp_path / ".mindforge" / "runs"
    jsonls = list(runs_dir.glob("*.jsonl"))
    assert jsonls, "missing runs jsonl"
    contents = "\n".join(p.read_text("utf-8") for p in jsonls)
    assert '"target": "copilot"' in contents
    assert '"project_profile_found": true' in contents


def test_project_context_invalid_target_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, _, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    res = runner.invoke(app, _common_args(cfg) + ["--target", "bogus"])
    assert res.exit_code == 2


def test_project_context_invalid_format_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, _, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    res = runner.invoke(app, _common_args(cfg) + ["--format", "yaml"])
    assert res.exit_code == 2


# ---------------------------------------------------------------------------
# 4. JSON 输出
# ---------------------------------------------------------------------------


def test_project_context_json_v2_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    _write_project_profile(vault)

    res = runner.invoke(app, _common_args(cfg) + ["--format", "json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)

    assert payload["version"] == 2
    assert payload["project"] == "my-first-agent"
    assert payload["target"] == "claude-code"
    assert payload["project_profile_found"] is True
    assert payload["project_profile_path"] == "30-Projects/my-first-agent.md"
    assert payload["project_description"]
    assert payload["preferred_workflow"]
    assert payload["project_level_principles"]
    assert payload["card_level_principles"][0]["card_id"] == "card-a"
    assert payload["project_level_known_risks"]
    assert payload["card_level_known_risks"][0]["card_id"] == "card-a"
    assert payload["suggested_prompt"]
    assert "claude-code" in payload["suggested_prompt"]
    assert payload["excluded_content"]
    # v0.2.0/v0.2.1 旧字段仍在
    assert "items" in payload
    assert payload["count"] >= 1
    # 新增结构化字段进 items
    assert payload["items"][0]["principles"] == ["card 级原则: 看 trace 再改"]
    assert payload["items"][0]["known_risks"] == ["card 级风险: 不要捏造日志"]


def test_project_context_json_no_profile_returns_empty_lists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, _, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    res = runner.invoke(app, _common_args(cfg) + ["--format", "json"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["project_profile_found"] is False
    assert payload["project_profile_path"] is None
    assert payload["project_level_principles"] == []
    assert payload["project_level_known_risks"] == []
    assert payload["preferred_workflow"] == []
    assert payload["target"] == "generic"
    # card-level 仍可有
    assert payload["card_level_principles"]


# ---------------------------------------------------------------------------
# 5. Suggested prompt target-specific 内容
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target,expected_phrase",
    [
        ("claude-code", "next-action / verification / risk"),
        ("copilot", "trade-off"),
        ("codex", "如发现 root cause"),
        ("generic", "plan → patch → test → report"),
    ],
)
def test_suggested_prompt_target_specific_phrasing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    expected_phrase: str,
) -> None:
    cfg, vault, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    _write_project_profile(vault, default_target=None)
    res = runner.invoke(app, _common_args(cfg) + ["--target", target])
    assert res.exit_code == 0, res.stdout
    assert expected_phrase in res.stdout


def test_suggested_prompt_includes_project_principles_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    _write_project_profile(vault)
    res = runner.invoke(app, _common_args(cfg))
    assert res.exit_code == 0
    out = res.stdout
    # suggested prompt 段里出现"项目级 principles："小标题
    assert "项目级 principles" in out
    assert "项目级 preferred_workflow" in out


# ---------------------------------------------------------------------------
# 6. 安全反向断言（M5.3 仍是召回层）
# ---------------------------------------------------------------------------

_LEAK_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9]+"),
    re.compile(r"_API_KEY="),
    re.compile(r"Authorization:"),
    re.compile(r'"raw_response"'),
    re.compile(r'"completion"'),
]


def test_project_context_outputs_never_contain_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    _write_project_profile(vault)

    md = runner.invoke(app, _common_args(cfg))
    js = runner.invoke(app, _common_args(cfg) + ["--format", "json"])
    assert md.exit_code == 0 and js.exit_code == 0
    blob = md.stdout + "\n" + js.stdout
    for pat in _LEAK_PATTERNS:
        assert not pat.search(blob), f"leak pattern matched: {pat.pattern}"

    # runs jsonl 同样不能含 profile 正文 / 卡片正文
    runs_dir = tmp_path / ".mindforge" / "runs"
    contents = "\n".join(p.read_text("utf-8") for p in runs_dir.glob("*.jsonl"))
    assert "sk-should-never-leak" not in contents
    assert "项目级原则" not in contents
    assert "card 级原则" not in contents


def test_project_context_does_not_call_llm_or_read_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """与 v0.2.0 一致：拦截 httpx.Client.send，断言永不发请求。"""
    cfg, vault, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    _write_project_profile(vault)

    # 在 cwd 放一个 .env，里面塞假 key；mindforge project context 绝不读它
    (tmp_path / ".env").write_text("MINDFORGE_API_KEY=sk-fake-shouldnt-load\n", "utf-8")

    import httpx

    def _boom(self, *a, **kw):
        raise AssertionError("HTTP call attempted from project context")

    monkeypatch.setattr(httpx.Client, "send", _boom, raising=True)
    monkeypatch.setattr(httpx.AsyncClient, "send", _boom, raising=True)

    res = runner.invoke(app, _common_args(cfg) + ["--target", "claude-code"])
    assert res.exit_code == 0
    # 即便 .env 在场，suggested prompt / output 都不应含其值
    assert "sk-fake-shouldnt-load" not in res.stdout
    assert os.environ.get("MINDFORGE_API_KEY") in (None, "")


# ---------------------------------------------------------------------------
# 7. 卡片级补充字段不覆盖项目级（来源透明）
# ---------------------------------------------------------------------------


def test_card_level_supplementary_does_not_override_project_level(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    _write_project_profile(vault)
    res = runner.invoke(app, _common_args(cfg))
    assert res.exit_code == 0
    out = res.stdout

    # 项目级与卡片级两块都在；项目级先于卡片级出现（顺序固定）
    proj_idx = out.index("## Project-Level Principles")
    card_idx = out.index("## Card-Level Principles (supplementary)")
    assert proj_idx < card_idx, "项目级 principles 必须在卡片级之前展示"

    # 卡片级文本带 from [card-id] 来源
    assert "from [card-a]:" in out


def test_no_empty_section_titles_when_everything_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """所有结构化数据都缺失时，仍不能出现空标题。"""
    cfg, vault, card = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    # 把卡片中的 principles / known_risks 字段去掉
    text = card.read_text("utf-8")
    fm_text, body = text.split("---\n", 2)[1], text.split("---\n", 2)[2]
    fm = yaml.safe_load(fm_text)
    fm.pop("principles", None)
    fm.pop("known_risks", None)
    card.write_text(
        "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body,
        encoding="utf-8",
    )
    # 不写 profile

    res = runner.invoke(app, _common_args(cfg))
    assert res.exit_code == 0
    out = res.stdout

    # 每个段标题之后都至少有一行降级文案；用正则确认无 "## X\n\n##"
    bad = re.search(r"^##\s.+\n\s*\n##\s", out, flags=re.MULTILINE)
    assert bad is None, f"出现空标题段：{bad.group(0) if bad else ''}"
    assert "No project-level principles configured." in out
    assert "No card-level principles found." in out
    assert "No project-level known_risks configured." in out
    assert "No card-level known_risks found." in out


# ---------------------------------------------------------------------------
# 8. --output 写文件路径仍工作（M4.1 兼容）
# ---------------------------------------------------------------------------


def test_project_context_output_to_file_with_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, vault, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    _write_project_profile(vault)
    out_path = tmp_path / "ctx.md"

    res = runner.invoke(
        app,
        _common_args(cfg)
        + ["--target", "codex", "--output", str(out_path)],
    )
    assert res.exit_code == 0, res.stdout
    text = out_path.read_text("utf-8")
    assert "## Suggested Prompt for codex" in text
    assert "如发现 root cause" in text
    # 文件输出也含 excluded content 段
    assert "## Excluded Content (safety guarantee)" in text


def test_project_context_output_parent_missing_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, _, _ = _setup_vault_with_one_approved_card(tmp_path, monkeypatch)
    res = runner.invoke(
        app, _common_args(cfg) + ["--output", str(tmp_path / "no-such-dir" / "x.md")]
    )
    assert res.exit_code == 2
