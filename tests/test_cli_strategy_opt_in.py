"""v0.10 Slice 3 TDD Red — CLI ``--strategy`` opt-in seam contract。

设计意图（中文学习型）
======================

为什么需要 ``--strategy`` opt-in？
----------------------------------

v0.10 引入了多策略 seam：``DefaultKnowledgeCardStrategy`` 是离线、确定
性、无 LLM 的 fake-first 策略；``five_stage`` 是依赖 LLM 的默认策略。
要让用户能够在不修改配置文件的前提下，**显式**切换策略以做对照
（例如离线 dry-run 时用 default_knowledge_card），CLI 必须暴露一个
**opt-in** 的 ``--strategy`` 选项。

为什么是 opt-in，而不是 auto-detect？
-------------------------------------

策略选择必须**只**依赖用户显式意图（CLI flag）或既有 default —— 绝不
能从 source_type / adapter / SourcePlugin concrete class 反推。否则
"切换源" 会暗中改变"语义模型"，破坏 source 与 strategy 的正交性。

为什么默认行为必须保持不变？
----------------------------

任何已有的 `mindforge process --config ...` 调用方都不应受本次新增选
项影响。默认仍是 ``DEFAULT_STRATEGY_NAME == "five_stage"``，沿用原有
fake provider 子系统；no-real-LLM-by-default 不变。

为什么未知 strategy 必须友好失败？
----------------------------------

如果用户 ``--strategy typo``，Typer 默认只会吐 "no such option" 风格
错误。我们希望产出策略名相关的清晰错误（registry 已有
``UnknownStrategyError``），exit code 非零但不抛 stack trace —— 这是
CLI adapter 友好性的最低线。

本文件的预期 Red
================

- ``test_process_help_exposes_strategy_option``：``--help`` 文本中应包
  含 ``--strategy``。当前 production 未实现 → 预期 Red。
- ``test_process_accepts_strategy_default_knowledge_card``：显式
  ``--strategy default_knowledge_card`` 应 exit 0 且写出 ai_draft 卡片。
  当前 Typer 会拒绝未知选项 → 预期 Red。
- ``test_process_unknown_strategy_fails_with_readable_message``：
  ``--strategy nope`` 应 exit ≠ 0，且 stderr/output 中包含策略名以及
  registry 可选项。当前会以 "No such option" 返回 → 预期 Red。

预期 Green（回归基线）
======================

- ``test_process_default_strategy_unchanged``：不传 ``--strategy`` 时，
  CLI 必须仍走 five_stage，输出格式不变。即使 Slice 3 Green 落地，
  这条也必须仍 Green —— 它是 "无回归" 的护栏。
- ``test_cli_strategy_selection_does_not_couple_to_source_adapter``：
  AST 静态护栏，确保 strategy 选择代码路径不 import 任何 source
  adapter concrete class。当前已满足 → 预期 Green。

不属于本切片
============

- 不实现 ``--strategy`` 选项（那是 Slice 3 Green）；
- 不调真实 LLM；
- 不读 .env；
- 不调真实 Cubox API；
- 不写正式 Obsidian vault；
- 不生成 human_approved；
- 不自动 approve；
- 不做 dogfooding。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.cli import app

runner = CliRunner()

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
TEMPLATE_PATH = REPO_ROOT / "templates" / "knowledge_card.md.j2"
TRACKS_PATH = REPO_ROOT / "configs" / "learning_tracks.yaml"


def _build_fake_vault(tmp_path: Path) -> tuple[Path, Path]:
    """构造最小 vault + fake-only mindforge.yaml，返回 (cfg_path, vault)。

    与 ``test_process_e2e._build_vault_with_fake_llm`` 同形态，但精简到
    Slice 3 测试需要的字段。fake provider，no .env，no real LLM。
    """
    vault = tmp_path / "vault"
    inbox = vault / "00-Inbox"
    (inbox / "ManualNotes").mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)

    src_file = inbox / "ManualNotes" / "n1.md"
    src_file.write_text(
        "---\ntitle: Strategy Opt-in Smoke\ntags: [strategy]\n---\n\n"
        "## 笔记正文\n\n用于验证 CLI --strategy opt-in seam 的最小笔记。\n",
        encoding="utf-8",
    )

    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir()
    cfg = {
        "version": 0.1,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {
            "enabled": ["plain_markdown"],
            "registry": {
                "plain_markdown": {
                    "adapter": "PlainMarkdownAdapter",
                    "inbox_subdir": "ManualNotes",
                    "file_glob": "*.md",
                    "enabled": True,
                },
            },
        },
        "state": {
            "workdir": str(tmp_path / ".mindforge"),
            "state_file": "state.json",
            "runs_dir": "runs",
            "index_file": "index.jsonl",
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {
                "fake": {
                    "triage": "f1",
                    "distill": "f1",
                    "link_suggestion": "f1",
                    "review_questions": "f1",
                    "action_extraction": "f1",
                }
            },
            "models": {
                "f1": {
                    "provider": "fake-local",
                    "type": "fake",
                    "base_url": "fake://",
                    "model": "fake-1",
                    "timeout_seconds": 5,
                    "max_retries": 0,
                }
            },
        },
        "prompts": {
            "triage_version": "v1",
            "distill_version": "v1",
            "link_suggestion_version": "v1",
            "review_questions_version": "v1",
            "action_extraction_version": "v1",
        },
        "logging": {"level": "INFO", "file": str(tmp_path / "mf.log")},
    }
    cfg_path = cfg_dir / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return cfg_path, vault


def _common_process_args(cfg_path: Path) -> list[str]:
    return [
        "process",
        "--config",
        str(cfg_path),
        "--prompts-dir",
        str(PROMPTS_DIR),
        "--tracks",
        str(TRACKS_PATH),
        "--template",
        str(TEMPLATE_PATH),
    ]


# ---------------------------------------------------------------------------
# Red 期望：production 尚未实现 ``--strategy``
# ---------------------------------------------------------------------------


def test_process_direct_help_is_retired() -> None:
    """legacy process 不再通过 direct help 暴露第二套处理入口。"""
    r = runner.invoke(app, ["process", "--help"])
    assert r.exit_code != 0
    assert "--strategy" not in r.output


def test_process_rejects_internal_default_knowledge_card_strategy(tmp_path: Path) -> None:
    """``default_knowledge_card`` 是 internal baseline，不能证明生产主流程。

    中文学习型说明：测试应该替身化 LLM response，而不是通过 CLI 选择
    deterministic strategy 绕过 Knowledge Card Strategy prompt pipeline。
    """
    cfg_path, _ = _build_fake_vault(tmp_path)
    args = _common_process_args(cfg_path) + [
        "--dry-run",
        "--strategy",
        "default_knowledge_card",
    ]
    r = runner.invoke(app, args)
    assert r.exit_code != 0
    assert "internal/not production-ready" in r.output


def test_process_unknown_strategy_fails_with_readable_message(tmp_path: Path) -> None:
    """``--strategy nope_xyz`` 必须 exit 非零，且消息包含策略名。

    Slice 3 contract：错误必须是用户可读的（提到策略名 + 可选项），
    而非 Typer 默认的 "Got unexpected extra arguments" 或 "No such
    option" 风格。当前没有 ``--strategy`` 选项 → 预期 Red（行为不
    满足消息约定）。
    """
    cfg_path, _ = _build_fake_vault(tmp_path)
    args = _common_process_args(cfg_path) + ["--strategy", "nope_xyz_strategy"]
    r = runner.invoke(app, args)
    assert r.exit_code != 0, "未知 strategy 必须以非零 exit code 失败"
    combined = (r.output or "") + (str(r.exception) if r.exception else "")
    assert "nope_xyz_strategy" in combined, (
        "错误信息必须显式包含用户提供的策略名，便于自助排查。"
        f"实际 output:\n{r.output}\nexception: {r.exception!r}"
    )


# ---------------------------------------------------------------------------
# Green 期望：默认行为与边界静态契约
# ---------------------------------------------------------------------------


def test_process_default_strategy_is_knowledge_card(tmp_path: Path) -> None:
    """不传 ``--strategy`` 时 CLI 必须走 Knowledge Card Strategy。

    这是 "Slice 3 Green 之后也不能回归" 的护栏：默认行为是历史契约，
    不能因新增 opt-in 选项而被改写。
    """
    cfg_path, vault = _build_fake_vault(tmp_path)
    r = runner.invoke(app, _common_process_args(cfg_path))
    assert r.exit_code == 0, r.output
    assert "processed=" in r.output  # 现有 e2e 输出契约
    cards = list((vault / "20-Knowledge-Cards").rglob("*.md"))
    assert len(cards) == 1
    text = cards[0].read_text("utf-8")
    assert "status: ai_draft" in text
    # 默认 knowledge_card 通过 LLM provider test double 走完整 5 stage 管线，会带 distill
    # 占位符；这是历史契约，不允许 default 路径悄悄换策略。
    assert "[fake] excerpt placeholder" in text
    assert 'strategy_id: "knowledge_card"' in text


def test_cli_strategy_selection_does_not_couple_to_source_adapter() -> None:
    """CLI 中 strategy selection 不能 import 任何 source adapter concrete class。

    防止 strategy 选择路径反向依赖 source 子系统。任何 strategy 选择的
    "灵活性" 都必须只来自 explicit option / DEFAULT_STRATEGY_NAME /
    registry —— 不能依赖 CuboxAdapter / PlainMarkdownAdapter 等具体类。
    """
    cli_path = REPO_ROOT / "src" / "mindforge" / "cli.py"
    tree = ast.parse(cli_path.read_text("utf-8"))

    forbidden = {
        "CuboxAdapter",
        "CuboxApiAdapter",
        "PlainMarkdownAdapter",
        "ObsidianVaultAdapter",
        "PdfAdapter",
        "SourcePlugin",
    }
    seen: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in forbidden:
                    seen.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                tail = alias.name.rsplit(".", 1)[-1]
                if tail in forbidden:
                    seen.add(tail)

    assert not seen, (
        f"cli.py 不应直接 import source adapter concrete class："
        f"{sorted(seen)} —— strategy 选择必须独立于 source 子系统。"
    )


# ---------------------------------------------------------------------------
# 安全边界：production 路径不依赖 source adapter（已由
# test_cli_strategy_selection_does_not_couple_to_source_adapter 强制）
# ---------------------------------------------------------------------------


if __name__ == "__main__":  # pragma: no cover - 便于本地手跑
    pytest.main([__file__, "-v"])
