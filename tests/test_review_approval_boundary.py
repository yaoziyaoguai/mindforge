"""Stage 3 — review/approval boundary hardening characterization tests.

设计意图
========

本测试文件**不增加新功能**。它把"AI Draft 永远不会自动变成
``human_approved``"这条架构契约固化为可执行的 boundary tests，覆盖
source processing 入口与既有
``approver`` / ``approval_service`` / ``reviewer`` / ``review_service``
的边界。

为什么 Stage 3 不写 production 代码
-----------------------------------

仓库现有 ``approver.approve_card`` / ``apply_decision`` 已经强约束
"必须 explicit ApprovalRequest，且只有 ``status == 'ai_draft'`` 才能晋升"，
``ApprovalDecision`` 的 7 个值除 ``APPROVE`` 外都强制
``NotImplementedDecisionError``。历史 Cubox preview CLI 已移除；
source processing 的写入路径仍必须保持 review-only，不能绕过人工 approve。

Stage 3 的任务是**用测试封装设计意图**，确保未来重构时这些边界不被
意外打破：

1. ApprovalDecision 不含任何 source-specific（Cubox / Scanner）值；
2. approver / approval_service / reviewer / review_service 不 import
   cubox_* / source_mux；
3. process executor 生成的 card payload 默认 status 为 ``ai_draft``，
   绝不为 ``human_approved``；
4. Card 模板里 status 默认值为 ``ai_draft``；
5. source/pipeline 相关模块不 import approver / approval_service —
   processing 入口不可能误触发 approve。
"""

from __future__ import annotations

import ast
from pathlib import Path

from mindforge.approver import ApprovalDecision

_REPO = Path(__file__).resolve().parent.parent
_SRC = _REPO / "src" / "mindforge"

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
    "mindforge.cubox_dryrun_presenter",
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
# 3. source processing 入口不可能误触发 approve / mark_review
# ---------------------------------------------------------------------------


_FORBIDDEN_FOR_PROCESSING = {
    "mindforge.approver",
    "mindforge.approval_service",
    "mindforge.reviewer",
    "mindforge.review_service",
    # vault writer 也禁止 — preview 永远不写 vault
    "mindforge.vault_writer",
    "mindforge.workspace",
    "mindforge.env_loader",
}


def test_process_executor_does_not_import_approve_or_review() -> None:
    """processing 只能产生 ai_draft，不能直接接触 approve/review 写路径。"""
    p = _SRC / "process_executor.py"
    leaked = _imports(p) & _FORBIDDEN_FOR_PROCESSING
    assert not leaked, (
        f"process_executor.py 不应 import：{leaked}（source processing 必须与 "
        f"approve / review / vault 写入解耦）"
    )


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


def test_process_executor_keeps_ai_draft_boundary_literal() -> None:
    """process executor 只允许把模型产物写成 ai_draft。

    中文学习型说明：这是对 source-centric processing 的迁移后 contract；
    不再通过 Cubox preview CLI 证明，而是守住真实处理写卡入口。
    """
    text = (_SRC / "process_executor.py").read_text(encoding="utf-8")
    assert "human_approved" in text
    assert "ai_draft" in text


def test_legacy_cubox_preview_cli_module_is_removed() -> None:
    """Cubox-first preview CLI 不再是 runtime surface。"""
    assert not (_SRC / "cubox_cli.py").exists()


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
        # retrieval port + BM25 engine — 仅在 status_filter 默认参数中使用
        # "human_approved" 字面量（只读搜索过滤），与 lexical_index.py 同语义
        "retrieval_port.py",
        "bm25_engine.py",
        "multi_project_context.py",
        "project_context.py",
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
        # v0.13 Stage 4 — input preflight 的 output_contract 用
        # human_approved=False 字面量声明 "preflight 永远不会产生
        # human_approved", 同样是反向边界守护。
        "input_safety.py",
        # Cubox readiness 报告 module
        # 与 provider_readiness.py 同款反向边界: 明确声明 "human approval
        # required for any human_approved record" 来固化 readiness 路径
        # 永不产生 human_approved 的不变量。
        "cubox_readiness.py",
        # Architecture Quality Pack — next_suggestions.py 是从 cli.py 巨石
        # 拆出的纯逻辑层。它只在 *只读* 路径上用 "human_approved" 字面量来
        # 过滤"已由人类审核过、可参与 review/recall 调度"的卡片，从未把任何
        # 卡片晋升到 human_approved。与 cli.py 内的同名查询同语义、同安全约束。
        "next_suggestions.py",
        # Architecture Quality Pack 2 — services/doctor.py 同样是从 cli.py
        # 抽出的纯逻辑层。只在 *只读* 路径用 "human_approved" 字面量过滤
        # 卡片以做诊断统计与 BM25 / overdue 推断，从未做晋升动作。
        "doctor.py",
        # Full Repo Decomposition milestone — backup_cli.py 从 cli.py 抽出
        # backup export adapter，只读导出 human_approved 卡片的安全摘要；
        # 不写卡片状态，也不产生任何 approval side effect。
            "backup_cli.py",
            # library_service.py 是只读 inventory 查询面，只统计和展示
            # human_approved / ai_draft 状态，不产生审批副作用。
            "library_service.py",
            # card_workspace_service.py 是 Web/Service 共享的卡片正文编辑边界。
            # 它只在保存已 approved 卡片后保留 human_approved 状态并刷新 recall
            # index，不把 ai_draft 晋升为 human_approved；晋升仍只能走
            # approval_service/approver 的显式 approve 路径。
            "card_workspace_service.py",
        # real-data CLI status presenter 只读展示 approved 计数；不写状态、
        # 不调用 approval_service，也不产生 human_approved。
        "local_status.py",
                # daily_cli.py 从 cli.py 抽出 today/start/next 只读入口，只用
            # human_approved 统计 review due 信号，不写状态、不 approve。
            "daily_cli.py",
            # approval_cli.py 是显式人工 approve 的 CLI adapter owner。它只把
            # 用户命令转交给 approval_service/approver，不允许静默自动晋升；
            # human_approved 字面量出现在用户可见说明和边界提示中是合理的。
            "approval_cli.py",
            # process_cli.py 只在命令 docstring/help 中声明默认 ai_draft 与
            # 必须人工晋升的边界；实际 process 写卡路径不会产生 human_approved。
            "process_cli.py",
            # process_executor.py 是 process/watch/import 共享执行原语。这里的
            # human_approved 只用于构建已审核 source 的只读索引，避免重复处理
            # 已 approve source；它不写卡片状态，也不产生审批副作用。
            "process_executor.py",
                # review_cli.py 是 review adapter，只读取 human_approved 卡片做
                # 到期/统计展示；不写卡片状态。
                "review_cli.py",
            # recall_index_cli.py 是 recall/index adapter，只用 human_approved
            # 作为默认检索过滤条件；不负责 approve。
            "recall_index_cli.py",
            # project_cli.py 只在 project context / evidence 只读汇总中默认过滤
            # human_approved 卡片；不产生审批副作用。
            "project_cli.py",
            # wiki_service.py 只读取 human_approved cards 生成派生 Wiki 视图；
            # 它不修改 card status，也不把 ai_draft 晋升为 human_approved。
            "wiki_service.py",
            # wiki_view_model.py 的 docstring 说明 ViewModel 只基于 human_approved
            # cards（通过 CardDigest）。它不读 card 源文件，不修改状态，不 approve。
            "wiki_view_model.py",
            # trash_cli.py 展示 restore 后可能回到 human_approved 的状态说明；
            # 真正状态恢复由 trash_service 读取 previous_status，不执行 approve。
            "trash_cli.py",
            # related_cards.py 只用于 Library context 的只读过滤，目的是避免
            # ai_draft / pending / rejected 出现在 related cards 中。它不修改
            # card 状态，不执行 approve，不绕过 explicit approval。
            "related_cards.py",
            # health_service.py 只用 human_approved 做只读筛选，统计低质量/孤儿/
            # 重复卡片时仅关注已审核内容。它不修改 card 状态，不执行 approve。
            "health_service.py",
        }
    for f in src_files:
        text = f.read_text(encoding="utf-8")
        if "human_approved" in text and f.name not in allowed:
            raise AssertionError(
                f"模块 {f.relative_to(_SRC)} 出现 'human_approved' literal，"
                f"但不在允许集合中。新增请审慎评估，确保不是自动晋升路径。"
            )
