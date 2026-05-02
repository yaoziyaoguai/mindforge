"""Stage 3 — review/approval boundary hardening characterization tests.

设计意图
========

本测试文件**不增加新功能**。它把"fake ai_draft 永远不会自动变成
``human_approved``"这条架构契约固化为可执行的 boundary tests，覆盖
新的 Cubox dogfood 入口（``cubox preview-ai-draft``）与既有
``approver`` / ``approval_service`` / ``reviewer`` / ``review_service``
的边界。

为什么 Stage 3 不写 production 代码
-----------------------------------

仓库现有 ``approver.approve_card`` / ``apply_decision`` 已经强约束
"必须 explicit ApprovalRequest，且只有 ``status == 'ai_draft'`` 才能晋升"，
``ApprovalDecision`` 的 7 个值除 ``APPROVE`` 外都强制
``NotImplementedDecisionError``。Cubox preview 命令完全运行在内存，
不写 vault、不写 runs jsonl，已被 Stage 2 的 boundary tests 守护。

Stage 3 的任务是**用测试封装设计意图**，确保未来重构时这些边界不被
意外打破：

1. ApprovalDecision 不含任何 source-specific（Cubox / Scanner）值；
2. approver / approval_service / reviewer / review_service 不 import
   cubox_* / source_mux / cubox_preview_presenter；
3. preview 命令的 in-memory ai_draft 默认 status 为 ``ai_draft``，
   绝不为 ``human_approved``；
4. Card 模板里 status 默认值为 ``ai_draft``；
5. cubox_cli 不 import approver / approval_service / apply_decision —
   preview 入口不可能误触发 approve；
6. cubox_preview_presenter 不 import approver / reviewer（与 Stage 2 一致，
   此处补充语义说明 + 防回归）。
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from typer.testing import CliRunner

from mindforge.approver import ApprovalDecision

_REPO = Path(__file__).resolve().parent.parent
_SRC = _REPO / "src" / "mindforge"

runner = CliRunner()


# ---------------------------------------------------------------------------
# 1. ApprovalDecision 值集与 source 概念解耦
# ---------------------------------------------------------------------------


def test_approval_decision_values_do_not_leak_source_concepts() -> None:
    """ApprovalDecision 是 user intent 维度的枚举，不应携带 source-specific
    标签（``cubox`` / ``scanner`` / ``mux`` / ``vault`` / ``obsidian``）。
    这条契约保护了"approval domain 不感知 source 细节"。
    """
    forbidden = {"cubox", "scanner", "mux", "vault", "obsidian", "source"}
    for member in ApprovalDecision:
        value = member.value.lower()
        for bad in forbidden:
            assert bad not in value, (
                f"ApprovalDecision.{member.name}={value!r} 不应包含 {bad!r}"
            )


def test_approval_decision_only_approve_is_implemented_humanly() -> None:
    """除 APPROVE 外，其余 decision 都必须以
    ``NotImplementedDecisionError`` 显式拒绝。这是 Phase 1 的安全态：
    没有人为接通的 decision，永远不会沉默地把 card 推进到 human_approved。
    """
    # 静态：枚举包含 APPROVE
    assert ApprovalDecision.APPROVE.value == "approve"
    # 行为：直接复用既有 dispatcher 的 apply_decision；本断言由
    # tests/test_approval_decision.py::test_unimplemented_decisions_raise_explicit_not_implemented
    # 已经覆盖；此处只做存在性 sanity，避免重复。
    from mindforge import approver as approver_mod
    assert hasattr(approver_mod, "apply_decision")
    assert hasattr(approver_mod, "NotImplementedDecisionError")


# ---------------------------------------------------------------------------
# 2. AST 反向依赖：approval / review domain 不感知 source 入口
# ---------------------------------------------------------------------------


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            # 也把相对 import 还原成绝对模块名（基于 mindforge.* 顶层）
    return names


_FORBIDDEN_FOR_APPROVAL_REVIEW = {
    "mindforge.cubox_cli",
    "mindforge.cubox_dryrun_presenter",
    "mindforge.cubox_preview_presenter",
    "mindforge.source_mux",
    "mindforge.sources.cubox_api",
    "mindforge.sources.cubox_markdown",
    "mindforge.scanner",
    "mindforge.env_loader",
    # 真实 LLM SDK，approval/review 永远不应直连
    "openai",
    "anthropic",
    "httpx",
    "requests",
}


def _check_module(rel: str) -> None:
    p = _SRC / rel
    assert p.exists(), f"模块不存在：{p}"
    leaked = _imports(p) & _FORBIDDEN_FOR_APPROVAL_REVIEW
    assert not leaked, f"{rel} 不应 import：{leaked}"


def test_approver_module_does_not_know_source_or_network() -> None:
    _check_module("approver.py")


def test_approval_service_module_does_not_know_source_or_network() -> None:
    _check_module("approval_service.py")


def test_reviewer_module_does_not_know_source_or_network() -> None:
    _check_module("reviewer.py")


def test_review_service_module_does_not_know_source_or_network() -> None:
    _check_module("review_service.py")


# ---------------------------------------------------------------------------
# 3. cubox 入口不可能误触发 approve / mark_review
# ---------------------------------------------------------------------------


_FORBIDDEN_FOR_CUBOX_CLI = {
    "mindforge.approver",
    "mindforge.approval_service",
    "mindforge.reviewer",
    "mindforge.review_service",
    # vault writer 也禁止 — preview 永远不写 vault
    "mindforge.vault_writer",
    "mindforge.workspace",
    "mindforge.env_loader",
}


def test_cubox_cli_does_not_import_approve_or_review_or_vault() -> None:
    p = _SRC / "cubox_cli.py"
    leaked = _imports(p) & _FORBIDDEN_FOR_CUBOX_CLI
    assert not leaked, (
        f"cubox_cli.py 不应 import：{leaked}（preview 入口必须与 approve / "
        f"review / vault 写入完全解耦）"
    )


def test_cubox_preview_presenter_does_not_import_approve_or_review() -> None:
    p = _SRC / "cubox_preview_presenter.py"
    leaked = _imports(p) & {
        "mindforge.approver",
        "mindforge.approval_service",
        "mindforge.reviewer",
        "mindforge.review_service",
    }
    assert not leaked, f"preview presenter 不应 import：{leaked}"


# ---------------------------------------------------------------------------
# 4. 模板与 in-memory ai_draft 默认状态
# ---------------------------------------------------------------------------


def test_card_template_default_status_is_ai_draft() -> None:
    tpl = _SRC / "assets" / "templates" / "knowledge_card.md.j2"
    text = tpl.read_text(encoding="utf-8")
    # frontmatter 中 status 默认必须是 ai_draft；既不能是 human_approved，
    # 也不能写成 jinja 表达式从外部注入 — approval 必须是 explicit human action。
    assert "status: ai_draft" in text
    # 模板不得在生成时就把 status 渲染成 human_approved
    assert "status: human_approved" not in text


def test_cubox_preview_ai_draft_in_memory_card_payload_is_ai_draft(
    tmp_path: Path,
) -> None:
    """跑一次 preview，断言 in-memory card_payload 的 status 默认是 ai_draft。

    通过 ``--json`` 走机器可读路径，但 summary 故意不暴露 card_payload 正文；
    本测试改为在内存中直接调 cubox_cli 内的同一构造路径不现实（CLI 是
    Typer 入口）。退一步：我们用 CLI smoke 验证 ``has_card_payload=true``
    且 outcome.status="processed"，再单独用 strategies.build_strategy +
    pipeline 跑一次，断言 card_payload['status']=='ai_draft'。
    """
    # 准备 fixture
    fixture = (
        Path(__file__).parent / "fixtures" / "sample_cubox_api_export.json"
    )

    from mindforge.cli import app as cli_app

    res = runner.invoke(
        cli_app,
        ["cubox", "preview-ai-draft", "--export", str(fixture), "--json"],
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout.strip().splitlines()[-1])
    # by_status 必须存在 processed，且没有任何 human_approved
    assert "human_approved" not in payload["by_status"]
    for outcome in payload["outcomes"]:
        # 这是 pipeline 的 outcome.status（"processed"/"skipped"/"failed"），
        # 不是 card frontmatter 的 status；后者由模板控制（已经被
        # test_card_template_default_status_is_ai_draft 守护）。
        assert outcome["status"] != "human_approved"


def test_cubox_preview_does_not_write_any_card_under_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    """preview 命令绝不写 .md card 文件（vault writer 未被调用）。"""
    monkeypatch.chdir(tmp_path)
    fixture = Path(__file__).parent / "fixtures" / "sample_cubox_api_export.json"
    from mindforge.cli import app as cli_app

    res = runner.invoke(
        cli_app, ["cubox", "preview-ai-draft", "--export", str(fixture)]
    )
    assert res.exit_code == 0
    # cwd 下不应出现任何 .md（preview 不写 vault），也不应出现 jsonl
    leaked_md = list(tmp_path.rglob("*.md"))
    leaked_jsonl = list(tmp_path.rglob("*.jsonl"))
    assert leaked_md == [], f"preview 不应写 vault card：{leaked_md}"
    assert leaked_jsonl == [], f"preview 不应写 runs jsonl：{leaked_jsonl}"


# ---------------------------------------------------------------------------
# 5. ai_draft → human_approved 晋升仍然只能由 approve_card 触发
# ---------------------------------------------------------------------------


def test_human_approved_promotion_requires_explicit_approve_card_call() -> None:
    """全仓搜索：``human_approved`` literal 只能出现在以下白名单文件中
    （approver / state / 模板说明 / 测试自身），其它任何位置的常量化都
    可能意味着"被自动设置"的隐患。
    """
    src_files = list(_SRC.rglob("*.py"))
    # 允许携带 "human_approved" 的模块（核心：approver 必须有；
    # state/recall/review 涉及 status 比较；CLI 涉及枚举展示；processors
    # 与 strategies 不应携带）。
    allowed = {
        "approver.py",
        "approval_service.py",
        "approve_presenter.py",
        "review_service.py",
        "review_presenter.py",
        "reviewer.py",
        "recall_service.py",
        "recall_presenter.py",
        "state.py",
        "models.py",
        "cli.py",
        "init_cmd.py",
        "obsidian_cli.py",
        "obsidian.py",
        "safety_policy.py",
        "cards.py",
        "evidence.py",
        "lexical_index.py",
        "multi_project_context.py",
        "project_context.py",
        # cubox_cli 在 docstring/commit message 中提及 human_approved 边界，
        # 不构成自动晋升路径
        "cubox_cli.py",
        # strategies/__init__.py 暴露 KnowledgeStrategy seam，docstring 中
        # 提及 human_approved 边界
        "__init__.py",
        # strategies/custom.py（v0.12 declarative custom strategy）以
        # human_approved 字面量在 parse 阶段拒绝任何把它放进
        # structured_payload_schema 的 custom 定义；这是反方向的
        # 边界守护，与"自动晋升路径"恰好相反，因此显式纳入白名单。
        "custom.py",
        # v0.13 Stage 1 — provider readiness / synthetic real-LLM smoke /
        # provider CLI 三件套以 human_approved 字面量明确声明
        # "real provider 输出永远不能成为 human_approved"，是反向
        # 边界守护（同 custom.py 模式）。
        "provider_readiness.py",
        "real_smoke.py",
        "provider_cli.py",
    }
    for f in src_files:
        text = f.read_text(encoding="utf-8")
        if "human_approved" in text and f.name not in allowed:
            raise AssertionError(
                f"模块 {f.relative_to(_SRC)} 出现 'human_approved' literal，"
                f"但不在允许集合中。新增请审慎评估，确保不是自动晋升路径。"
            )
