"""User-friendliness polish 回归测试。

中文学习边界：
- 这一组测试不创建真实 vault、不调真实 LLM/Cubox/网络、不写 Obsidian。
- 它们只验证 vault 缺失时 ``next`` / ``start`` / ``doctor`` 都会把
  ``mindforge demo`` 推到新用户面前；以及 README 快速开始把 Web Setup
  作为 GitHub 新用户主路径，同时保留 demo 作为零配置体验。
- 所有断言走只读字符串 / NextSuggestion 列表，不触碰 Typer CLI 之外的副作用。
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from mindforge.cli import (
    NextSuggestion,
    _doctor_recovery_checks,
    _next_suggestions,
)
from mindforge.config import MindForgeConfig, load_mindforge_config
from mindforge.assets_runtime import bundled_asset_path_for_process


def _config_with_missing_vault(tmp_path: Path) -> MindForgeConfig:
    """构造一个 vault 缺失的 ``MindForgeConfig``，复用包内默认配置加载逻辑。

    通过 ``replace`` 只覆写 vault.root 和 cards_path，不复制配置加载分支，
    避免与生产路径漂移。
    """

    cfg = load_mindforge_config(bundled_asset_path_for_process("configs", "mindforge.yaml"))
    missing_vault = tmp_path / "missing_vault"
    new_vault = replace(cfg.vault, root=missing_vault)
    return replace(cfg, vault=new_vault)


def test_next_suggestions_recommend_demo_before_init_when_vault_missing(tmp_path):
    """vault 缺失时，新用户首先看到的应该是零配置 ``mindforge demo``。"""

    cfg = _config_with_missing_vault(tmp_path)
    suggestions = _next_suggestions(cfg)

    assert suggestions, "vault 缺失时必须给出至少一条建议"
    commands = [s.command for s in suggestions]
    assert "mindforge demo" in commands
    assert any(c.startswith("mindforge init") for c in commands)
    assert commands.index("mindforge demo") < next(
        i for i, c in enumerate(commands) if c.startswith("mindforge init")
    ), "demo 必须排在 init 之前，让新用户先看到零配置路径"

    demo_item: NextSuggestion = next(s for s in suggestions if s.command == "mindforge demo")
    assert demo_item.priority == "recommended"
    assert "API key" in demo_item.reason or "联网" in demo_item.reason


def test_doctor_recovery_actions_include_demo_hint_when_cards_missing(tmp_path):
    """doctor 在 cards 目录缺失时把零配置 demo 放在新用户最先看到的位置。

    UX completion: demo 现在用 ``try_first`` 优先级排序，确保新用户在
    ``Action items`` 列表里第一眼就看到 ``mindforge demo``，而不是被多条
    ``critical`` ``init`` 提示淹没。原 init critical 提示保留作为后续动作。
    """

    cfg = _config_with_missing_vault(tmp_path)
    payload = _doctor_recovery_checks(cfg)

    actions = payload["actions"]
    messages = [msg for _prio, msg in actions]
    joined = "\n".join(messages)
    assert "mindforge demo" in joined, (
        "cards 目录缺失时 doctor 必须同时提示 mindforge demo 作为零配置入口"
    )
    assert any("init" in msg for msg in messages), (
        "原有 init 提示不能被覆盖（init 仍是 vault 真正落地的必经一步）"
    )
    demo_action = next((p, m) for p, m in actions if "mindforge demo" in m)
    assert demo_action[0] == "try_first", (
        "demo 必须用 try_first 优先级，使其在 doctor Action items 中排在最前"
    )


def test_root_help_recommends_mindforge_demo_first():
    """root ``--help`` 必须把 mindforge demo 写成新用户的第一条命令。

    UX completion: ``app.help`` 是新用户运行 ``mindforge --help`` 时第一眼
    看到的文本；以前它列了 scan/process 等中间命令，没有指向零配置入口。
    现在必须把 ``mindforge demo`` 显式写成 “第一条命令”。
    """

    from mindforge.cli import app

    help_text = app.info.help or ""
    assert "mindforge demo" in help_text or "demo" in help_text.split("\n")[2:6][0]
    # 进一步：demo 推荐句必须在常用命令列表的前两行内出现
    common_block = help_text.split("常用命令", 1)[-1]
    head_lines = common_block.splitlines()[:3]
    assert any("demo" in line for line in head_lines), (
        "root --help '常用命令' 头两三行必须出现 demo，作为新用户首选入口"
    )


def test_readme_quickstart_promotes_web_setup_first():
    """README 快速开始 必须展示 GitHub 新用户可照跑的 Web 主路径。"""

    text = Path("README.md").read_text(encoding="utf-8")
    anchor = "## 快速开始"
    assert anchor in text
    after = text.split(anchor, 1)[1]
    block = after.split("\n## ", 1)[0]

    assert "git clone" in block
    assert "python -m venv .venv" in block
    assert "pip install -e ." in block
    assert "mindforge web" in block
    assert "http://127.0.0.1:8765" in block
    assert "Setup" in block
    assert "Add model" in block
    assert "API key" in block
    assert "openai_compatible" in block
    assert "anthropic" in block
    assert "mindforge watch add" in block
    assert "<profile>" not in block
    assert "--profile" not in block
    assert "MINDFORGE_LLM_API_KEY" not in block
    assert "mindforge approve" in block
    assert "mindforge approve 1 --confirm" in block
    assert 'mindforge recall --query' in block
    assert "fake provider" not in block.lower()
    assert "mindforge process --profile fake" not in block


def test_readme_marks_developer_testing_and_scan_process_as_non_primary_paths() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    collapsed = " ".join(text.split())
    assert "Developer Testing" in text
    assert "fake the LLM response, not the extraction strategy" in text
    assert "not product providers or recommended extraction strategies" in collapsed
    assert "Advanced / Troubleshooting" in text
    assert "scan/process" in text


def test_readme_first_run_explains_vault_resolution_and_query_flag() -> None:
    """README first-run 路径必须解释 cwd vault 与 recall --query，防 dogfood 漂移。"""

    text = Path("README.md").read_text(encoding="utf-8")
    quickstart = text.split("## 快速开始", 1)[1].split("\n## ", 1)[0]
    first_run = text.split("### First-run", 1)[1].split("\n## ", 1)[0] if "### First-run" in text else quickstart

    assert "cd /tmp/mindforge-first-run" in first_run or "cd /tmp/mindforge-first-run" in text
    assert "project root" in first_run or "project root" in text
    assert "vault.root` 默认是相对 project root 的 `vault`" in first_run or "vault.root" in text
    assert "cwd-first / vault-first" in first_run or "cwd-first / vault-first" in text
    assert "explicit `--vault`" in first_run or "explicit `--vault`" in text
    assert "cwd/ancestor vault" in first_run or "cwd/ancestor vault" in text
    assert "project-root-relative" in first_run or "project-root-relative" in text
    assert "active-vault-relative" in first_run or "active-vault-relative" in text
    assert "00-Inbox/" in text
    assert "configs/mindforge.yaml" in text
    assert 'mindforge recall --query "MindForge"' in text
