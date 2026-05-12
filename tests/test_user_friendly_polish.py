"""User-friendliness polish 回归测试。

中文学习边界：
- 这一组测试不创建真实 vault、不调真实 LLM/Cubox/网络、不写 Obsidian。
- 它们只验证 vault 缺失时 ``next`` / ``start`` / ``doctor`` 都会把
  Web Setup 推到新用户面前；以及 README 快速开始把 Web Setup
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


def test_next_suggestions_recommend_web_setup_before_init_when_vault_missing(tmp_path):
    """vault 缺失时，新用户首先看到的应该是真实 Web Setup 主路径。"""

    cfg = _config_with_missing_vault(tmp_path)
    suggestions = _next_suggestions(cfg)

    assert suggestions, "vault 缺失时必须给出至少一条建议"
    commands = [s.command for s in suggestions]
    assert "mindforge web" in commands
    assert any(c.startswith("mindforge init") for c in commands)
    assert commands.index("mindforge web") < next(
        i for i, c in enumerate(commands) if c.startswith("mindforge init")
    ), "Web Setup 必须排在 init 之前，让新用户先看到真实配置主路径"

    web_item: NextSuggestion = next(s for s in suggestions if s.command == "mindforge web")
    assert web_item.priority == "recommended"
    assert "真实模型" in web_item.reason


def test_doctor_recovery_actions_include_init_hint_when_cards_missing(tmp_path):
    """doctor 在 cards 目录缺失时指向真实初始化，不再推荐 demo 主路径。"""

    cfg = _config_with_missing_vault(tmp_path)
    payload = _doctor_recovery_checks(cfg)

    actions = payload["actions"]
    messages = [msg for _prio, msg in actions]
    joined = "\n".join(messages)
    assert any("init" in msg for msg in messages), (
        "原有 init 提示不能被覆盖（init 仍是 vault 真正落地的必经一步）"
    )
    assert "mindforge demo" not in joined


def test_root_help_recommends_web_setup_first():
    """root ``--help`` 必须把 Web Setup 写成新用户第一条真实主路径。"""

    from mindforge.cli import app

    help_text = app.info.help or ""
    assert "mindforge web" in help_text
    assert "demo" not in help_text.lower()
    # 进一步：web 推荐句必须在常用命令列表的前两行内出现
    common_block = help_text.split("常用命令", 1)[-1]
    head_lines = common_block.splitlines()[:3]
    assert any("mindforge web" in line for line in head_lines), (
        "root --help '常用命令' 头两三行必须出现 mindforge web，作为新用户首选入口"
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
    assert "Test doubles replace model responses only inside tests" in text
    assert "not product providers or recommended extraction strategies" in collapsed
    assert "Advanced / Troubleshooting" in text
    assert "scan/process" in text


def test_readme_first_run_explains_vault_resolution_and_query_flag() -> None:
    """README first-run 路径以 workspace 为主概念，解释自动查找和 recall --query。"""

    text = Path("README.md").read_text(encoding="utf-8")
    quickstart = text.split("## 快速开始", 1)[1].split("\n## ", 1)[0]
    first_run = text.split("### First-run", 1)[1].split("\n## ", 1)[0] if "### First-run" in text else quickstart

    assert "cd /tmp/mindforge-first-run" in first_run or "cd /tmp/mindforge-first-run" in text
    # workspace-first：用户只需理解 workspace，无需关心内部 config 路径
    assert "workspace" in quickstart
    assert "自动记住" in quickstart
    assert "无需关心内部 config 文件路径" in quickstart
    # source path resolution 仍保留在 README（CLI Source Path 章节）
    assert "cwd → project-root → active-vault" in text
    assert "00-Inbox/" in text
    assert "configs/mindforge.yaml" in text
    assert 'mindforge recall --query "MindForge"' in text
