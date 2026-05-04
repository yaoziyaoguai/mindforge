"""``mindforge demo`` (60 秒新用户 tour) 的边界与契约测试。

中文学习型说明
----------------
demo tour 是 "Local User Productization Pack" 引入的唯一新顶层命令,
目的是让新用户零 token / 零网络 / 零 vault 写入就能 1 分钟看到效果。

这套测试守护 4 类不变量, 让未来任何对 demo 的扩展都不能悄悄越过:

1. **零依赖**: demo 不需要 ``.env`` / 真实 token / 真实网络;
2. **零写入**: demo 不写任何 Obsidian vault / .obsidian / state 文件;
3. **零晋升**: demo 不产生 ``human_approved`` / 不调用 approver;
4. **CLI thin**: ``mindforge demo`` 仅做 adapter, 业务在 ``demo_tour``。
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.demo_tour import (
    DemoStep,
    DemoTourReport,
    render_demo_tour,
    run_demo_tour,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# 1. service-level: run_demo_tour 默认参数即可全绿
# ---------------------------------------------------------------------------


def test_run_demo_tour_default_all_steps_ok() -> None:
    report = run_demo_tour()
    assert isinstance(report, DemoTourReport)
    assert report.all_ok, [(s.name, s.summary) for s in report.steps if not s.ok]
    names = [s.name for s in report.steps]
    assert names == [
        "cubox-preview",
        "dogfood-preflight",
        "obsidian-vault",
        "review-packet",
    ]


def test_cubox_preview_step_parses_real_fixture_zero_network() -> None:
    report = run_demo_tour()
    step = next(s for s in report.steps if s.name == "cubox-preview")
    assert step.ok
    assert step.detail["items_parsed"] == 2
    assert "sample_titles" in step.detail
    assert isinstance(step.detail["sample_titles"], list)


def test_dogfood_preflight_classifies_demo_vault_as_safe() -> None:
    report = run_demo_tour()
    step = next(s for s in report.steps if s.name == "dogfood-preflight")
    assert step.ok
    assert step.detail["classification"] in ("synthetic", "non_sensitive_local")
    assert step.detail["allowed"] is True


def test_obsidian_vault_step_is_read_only() -> None:
    report = run_demo_tour()
    step = next(s for s in report.steps if s.name == "obsidian-vault")
    assert step.ok
    assert step.detail["writes_attempted"] is False
    assert isinstance(step.detail["markdown_files"], int)
    assert step.detail["markdown_files"] >= 1


def test_review_packet_step_never_emits_human_approved() -> None:
    report = run_demo_tour()
    step = next(s for s in report.steps if s.name == "review-packet")
    assert step.ok
    assert step.detail["artifact_type"] == "review_packet"
    assert step.detail["human_approved"] is False
    assert step.detail["writes_vault"] is False


# ---------------------------------------------------------------------------
# 2. presentation: render 输出包含新用户友好关键字面量
# ---------------------------------------------------------------------------


def test_render_demo_tour_contains_pinned_user_facing_literals() -> None:
    out = render_demo_tour(run_demo_tour())
    # 标题 + 三大 section 必须在新用户视野里
    assert "MindForge 60-second demo tour" in out
    assert "What you just saw" in out
    assert "What is safe" in out
    assert "What to try next" in out
    # 安全契约关键字面量必须出现, 让用户一眼能看到边界
    assert "no human_approved" in out
    assert "fake-default" in out
    # 下一步建议必须指向已有命令, 避免出现"虚构命令"
    assert "dogfood readiness" in out
    assert "dogfood quickstart" in out


# ---------------------------------------------------------------------------
# 3. CLI thin adapter: ``mindforge demo`` 仅做调用 + 渲染
# ---------------------------------------------------------------------------


def test_cli_demo_smoke_exits_zero_and_renders_text() -> None:
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0, result.output
    assert "MindForge 60-second demo tour" in result.output
    assert "What is safe" in result.output


def test_cli_demo_json_outputs_valid_schema() -> None:
    result = runner.invoke(app, ["demo", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["all_ok"] is True
    assert isinstance(payload["steps"], list) and len(payload["steps"]) == 4
    assert all({"name", "title", "ok", "summary", "detail"} <= s.keys() for s in payload["steps"])
    assert isinstance(payload["safety_invariants"], list)
    assert isinstance(payload["next_actions"], list)


def test_cli_demo_does_not_print_token_shaped_literals(monkeypatch) -> None:
    # 即便 env 中存在 token-shape 字符串, demo 命令绝不应该把它打印出来
    monkeypatch.setenv("MF_DEMO_FAKE_TOKEN_PROBE", "sk-leaked-1234567890abcdef")
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0, result.output
    assert "sk-leaked-1234567890abcdef" not in result.output


# ---------------------------------------------------------------------------
# 4. 模块级安全边界: demo_tour 源文件不能引入危险 import
# ---------------------------------------------------------------------------


def test_demo_tour_module_has_no_banned_imports() -> None:
    src = Path("src/mindforge/demo_tour.py").read_text(encoding="utf-8")
    # 严禁任何形式的 secrets / network / shell / vault writer 入口
    for banned in (
        "import dotenv",
        "from dotenv",
        "import requests",
        "import httpx",
        "import urllib.request",
        "from urllib.request",
        "import subprocess",
        "from subprocess",
        "from .obsidian",
        "from .writer",
        "from .approver",
        "from .approval_service",
        "from .processors",
    ):
        assert banned not in src, f"demo_tour.py 引入了禁用 import: {banned}"


def test_demo_step_dataclass_is_frozen() -> None:
    step = DemoStep(name="x", title="t", ok=True, summary="s")
    try:
        step.ok = False  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("DemoStep 必须是 frozen dataclass, 防止 presenter 误改业务结果")
