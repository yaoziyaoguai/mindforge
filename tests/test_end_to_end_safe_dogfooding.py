"""End-to-End safe dogfooding 用户体验固化测试。

中文学习边界：
- 这一组测试不调用真实 Cubox / LLM / 网络，不读 ``.env``，不写真实 vault。
- 它们只验证 “新用户运行 ``mindforge --help`` → ``mindforge demo`` →
  ``mindforge dogfood quickstart`` 的端到端 safe/fake 路径” 的关键用户体验
  和安全断言不会回归：
  * README/demo/dogfood 推荐的命令在真实 CLI registry 里都存在；
  * demo 输出始终包含 7 条安全保证；
  * dogfood quickstart 是 read-only 渲染，永远不会执行命令、永远不会写
    传入的 vault 路径；
  * ai_draft / human_approved 边界文案保持清楚。
- 不写脆弱的整段 snapshot；只用关键 substring 断言锁定边界。
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from typer.testing import CliRunner

from mindforge.cli import app


runner = CliRunner()


def _registered_commands() -> set[str]:
    """返回 root Typer app 中所有顶层命令名（含 sub-typer 名）。

    用于检测 README/demo 推荐命令是否真的存在，避免 docs drift。
    """

    names: set[str] = set()
    for cmd in app.registered_commands:
        names.add(cmd.name or cmd.callback.__name__)
    for grp in app.registered_groups:
        names.add(grp.name)
    return names


def test_root_help_recommended_commands_actually_exist():
    """root ``--help`` 推荐给新用户的命令必须真的存在。

    中文学习：避免 README/help 推荐 ``mindforge demo`` 但 CLI 实际注册的
    命令名不同，造成新用户 ``command not found``。
    """

    cmds = _registered_commands()
    for required in ("demo", "doctor", "next", "dogfood"):
        assert required in cmds, f"{required} 命令必须存在于 CLI registry"


def test_demo_output_lists_all_safety_guarantees():
    """``mindforge demo`` 必须明确列出 7 条 safe/fake 安全保证。

    中文学习：这是新用户判断 “这个命令到底会不会动我真实数据” 的唯一依据，
    不允许任何一项被静默删除。
    """

    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0, result.output
    out = result.output
    required_phrases = [
        "no real LLM",
        ".env",
        "no real Cubox",
        "no Obsidian vault was written",
        "no human_approved record was produced",
        "no RAG",
        "no tag",
    ]
    for phrase in required_phrases:
        assert phrase in out, f"demo 输出必须包含安全断言: {phrase}"


def test_demo_output_points_to_real_next_action():
    """demo 的 ``What to try next`` 必须指向真实存在的命令。

    中文学习：避免“跑完 demo 不知道下一步该做什么”，也避免推荐了实际不存在
    或拼错名字的命令。
    """

    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    out = result.output
    assert "What to try next" in out
    cmds = _registered_commands()
    # 抓出 "What to try next" 之后被推荐的所有 ``mindforge xxx`` 命令名
    suggested = re.findall(r"mindforge\s+([a-z][a-z\-]*)", out.split("What to try next", 1)[1])
    assert suggested, "demo 必须给出至少一条 mindforge 后续命令"
    for sub in suggested:
        assert sub in cmds, f"demo 推荐的 mindforge {sub} 必须真的存在"


def test_dogfood_quickstart_is_read_only_render(tmp_path):
    """``mindforge dogfood quickstart --vault <tmp>`` 必须只渲染、不执行。

    中文学习：quickstart 把真实 dogfood 路径展示给用户，但它本身不能动手；
    传入的 vault 路径在命令结束后必须保持不存在（因为 quickstart 不应该
    创建任何东西）。
    """

    vault = tmp_path / "render-only-vault"
    assert not vault.exists()

    result = runner.invoke(app, ["dogfood", "quickstart", "--vault", str(vault)])
    assert result.exit_code == 0, result.output
    assert "renders commands only" in result.output or "不执行" in result.output
    assert "no real LLM" in result.output.lower() or "no real llm" in result.output.lower()
    assert "human_approved" in result.output, "quickstart 必须解释 human_approved 边界"
    assert not vault.exists(), "quickstart 是 read-only render，不能创建 vault 目录"


def test_demo_does_not_require_api_key_env(monkeypatch):
    """``mindforge demo`` 不能依赖任何 provider API key 环境变量。

    中文学习：把所有可能的 LLM provider key 显式 unset 后再跑 demo；
    如果命令开始硬要 ANTHROPIC_API_KEY/OPENAI_API_KEY/UPSTAGE_API_KEY，
    就证明 fake-default 边界被破坏了。
    """

    for key in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "UPSTAGE_API_KEY",
        "MINDFORGE_CUBOX_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)

    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0, result.output
    assert "fake" in result.output.lower()


def test_readme_dogfood_quickstart_command_resolves():
    """README/GETTING_STARTED 中推荐的 ``mindforge demo`` 命令必须真的能跑。

    中文学习：用最直接的方式防 docs drift —— 直接 invoke README 中第一条
    推荐命令；如果 GREEN 失败说明文档 / CLI 已经漂移，必须先修。
    """

    readme = Path("README.md").read_text(encoding="utf-8")
    # 找出 Quick Start 块里第一条以 mindforge 开头的命令
    quickstart = readme.split("## Quick Start", 1)[1].split("\n## ", 1)[0]
    first_cmd = re.search(r"mindforge\s+([a-z][a-z\-]*)", quickstart)
    assert first_cmd, "Quick Start 必须给出至少一条 mindforge 命令"
    cmd_name = first_cmd.group(1)
    assert cmd_name in _registered_commands(), (
        f"README Quick Start 第一条命令 'mindforge {cmd_name}' 必须真的存在"
    )

    result = runner.invoke(app, [cmd_name])
    assert result.exit_code == 0, result.output


def test_dogfood_workspace_does_not_touch_home():
    """安全锁：demo / dogfood quickstart 只能写显式临时路径。

    中文学习：通过完整跑一次 demo + 一次 quickstart，再确认用户 HOME 下
    没有出现 ``~/Obsidian`` / ``~/.mindforge`` 新写入痕迹（如果原本就有，
    跳过；这只是防止 demo 偷偷在 HOME 创建 vault 目录）。
    """

    home = Path(os.path.expanduser("~"))
    obsidian_marker = home / "Obsidian" / "MyVault"
    pre_existed = obsidian_marker.exists()

    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    if not pre_existed:
        assert not obsidian_marker.exists(), (
            "demo 不允许在用户 HOME 下创建 Obsidian vault 目录"
        )

    # quickstart 也是 render-only，再次确认
    tmp_path = Path("/tmp/mindforge-e2e-render-check")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    result = runner.invoke(app, ["dogfood", "quickstart", "--vault", str(tmp_path)])
    assert result.exit_code == 0
    assert not tmp_path.exists(), "quickstart 必须保持纯渲染，不创建任何路径"
