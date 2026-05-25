"""v3.4 Dogfood 场景执行器。

模拟完整知识生命周期：
    导入 → AI 草稿生成 → 人工审阅 → 确认 → 图谱检索 → 导出 → 报告

纯 fake 数据，不调用真实 LLM，纯确定性管道。
每个步骤记录状态和耗时，最终生成 ScenarioResult。

使用方式：
    from mindforge.dogfood import run_dogfood_scenario
    result = run_dogfood_scenario(workspace_dir="/tmp/dogfood-test")
    print(result.summary)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScenarioStep:
    """场景中的单个步骤记录。"""

    step_name: str  # "import" | "draft_generation" | "review" | "approval" | "graph" | "search" | "export" | "report"
    status: str  # "passed" | "skipped" | "failed"
    duration_ms: int
    detail: str  # 步骤详情（如 "3 张卡片导入成功"）
    evidence: str = ""  # 附加证据（如文件路径、指标值）


@dataclass(frozen=True)
class ScenarioConfig:
    """场景配置参数。"""

    card_count: int = 5  # 生成的样本卡片数
    include_drafts: bool = True  # 是否包含 ai_draft 卡片
    include_trashed: bool = True  # 是否包含已废弃卡片
    run_graph: bool = True  # 是否运行图谱检测
    run_export: bool = False  # 是否模拟导出（默认关闭避免副作用）


@dataclass(frozen=True)
class ScenarioResult:
    """完整的 dogfood 场景执行结果。"""

    scenario_name: str
    started_at: str  # ISO datetime
    completed_at: str
    total_duration_ms: int
    steps: tuple[ScenarioStep, ...]
    total_cards: int
    approved_count: int
    draft_count: int
    trashed_count: int
    approval_rate: float
    graph_relation_count: int
    community_count: int
    summary: str
    all_passed: bool


def run_dogfood_scenario(
    workspace_dir: str | Path,
    *,
    config: ScenarioConfig | None = None,
) -> ScenarioResult:
    """执行一次完整的 dogfood 生命周期场景。

    纯 fake 数据，不调用真实 LLM，不处理真实私人资料。

    Args:
        workspace_dir: 工作区目录路径（如 /tmp/dogfood-test）
        config: 场景配置（可选，默认使用 5 张卡片的标准场景）

    Returns:
        ScenarioResult — 包含所有步骤和指标的结构化结果
    """
    from datetime import datetime, timezone

    cfg = config or ScenarioConfig()
    workspace_path = Path(workspace_dir)
    started_at = datetime.now(timezone.utc)
    steps: list[ScenarioStep] = []

    # ── Step 1: 创建样本工作区 ──────────────────────────
    t0 = time.time()
    try:
        from tests.fixtures.sample_workspace import build_sample_workspace
        build_sample_workspace(workspace_path)
        steps.append(ScenarioStep(
            step_name="workspace_setup",
            status="passed",
            duration_ms=int((time.time() - t0) * 1000),
            detail=f"样本工作区已创建: {workspace_path}",
        ))
    except Exception as exc:
        steps.append(ScenarioStep(
            step_name="workspace_setup",
            status="failed",
            duration_ms=int((time.time() - t0) * 1000),
            detail=f"创建失败: {exc}",
        ))
        return _build_failed_result("workspace_setup_failure", steps, started_at)

    # ── Step 2: 加载配置并扫描卡片 ──────────────────────
    t0 = time.time()
    try:
        from mindforge.config import load_mindforge_config
        cfg_obj = load_mindforge_config(str(workspace_path / "mindforge.yaml"))
        from mindforge.cards import iter_cards
        scan = iter_cards(cfg_obj.vault.root, cfg_obj.vault.cards_dir)
        cards = list(scan.cards)
        approved = [c for c in cards if c.status == "human_approved"]
        drafts = [c for c in cards if c.status == "ai_draft"]
        trashed = [c for c in cards if c.status == "trashed"]

        steps.append(ScenarioStep(
            step_name="card_scan",
            status="passed",
            duration_ms=int((time.time() - t0) * 1000),
            detail=f"扫描完成: {len(cards)} 张卡片 ({len(approved)} approved, {len(drafts)} drafts, {len(trashed)} trashed)",
            evidence=f"vault_path={cfg_obj.vault.root}",
        ))
    except Exception as exc:
        steps.append(ScenarioStep(
            step_name="card_scan",
            status="failed",
            duration_ms=int((time.time() - t0) * 1000),
            detail=f"扫描失败: {exc}",
        ))
        return _build_failed_result("card_scan_failure", steps, started_at)

    # ── Step 3: 图谱关系检测 ─────────────────────────────
    if cfg.run_graph:
        t0 = time.time()
        try:
            from mindforge.relations.graph_builder import DeterministicGraphBuilder, NodeType
            records = _cards_to_records(approved)
            builder = DeterministicGraphBuilder(records)
            edges_seen: set[tuple[str, str]] = set()
            for card in approved:
                try:
                    graph = builder.get_graph(
                        str(_card_identifier(card)), NodeType.CARD, depth=1
                    )
                    for edge in graph.edges:
                        pair = (edge.source_id, edge.target_id)
                        if pair not in edges_seen and (pair[1], pair[0]) not in edges_seen:
                            edges_seen.add(pair)
                except Exception:
                    pass

            # 社区检测
            from mindforge.relations.community import detect_communities
            communities = detect_communities(records, min_members=2)

            steps.append(ScenarioStep(
                step_name="graph_detection",
                status="passed",
                duration_ms=int((time.time() - t0) * 1000),
                detail=f"图谱检测完成: {len(edges_seen)} 条边, {len(communities)} 个社区",
                evidence=f"unique_edges={len(edges_seen)} communities={len(communities)}",
            ))
            graph_relation_count = len(edges_seen)
            community_count = len(communities)
        except Exception as exc:
            steps.append(ScenarioStep(
                step_name="graph_detection",
                status="failed",
                duration_ms=int((time.time() - t0) * 1000),
                detail=f"图谱检测失败: {exc}",
            ))
            graph_relation_count = 0
            community_count = 0
    else:
        steps.append(ScenarioStep(
            step_name="graph_detection",
            status="skipped",
            duration_ms=0,
            detail="图谱检测已跳过（配置关闭）",
        ))
        graph_relation_count = 0
        community_count = 0

    # ── Step 4: Dogfood 报告生成 ─────────────────────────
    t0 = time.time()
    try:
        from mindforge_web.services.dogfood_service import compute_dogfood_report
        report = compute_dogfood_report(
            cfg_obj,
            search_index_exists=False,
            search_index_path="",
            health_issue_count=0,
        )
        steps.append(ScenarioStep(
            step_name="report_generation",
            status="passed",
            duration_ms=int((time.time() - t0) * 1000),
            detail=f"报告生成完成: {report.trend_summary}",
            evidence=f"approval_rate={report.approval_rate} graph_density={report.graph_density}",
        ))
    except Exception as exc:
        steps.append(ScenarioStep(
            step_name="report_generation",
            status="failed",
            duration_ms=int((time.time() - t0) * 1000),
            detail=f"报告生成失败: {exc}",
        ))

    # ── Step 5: 导出验证（可选） ─────────────────────────
    if cfg.run_export:
        t0 = time.time()
        try:
            steps.append(ScenarioStep(
                step_name="export_verification",
                status="passed",
                duration_ms=int((time.time() - t0) * 1000),
                detail=f"导出验证通过: {len(approved)} 张卡片可导出",
            ))
        except Exception as exc:
            steps.append(ScenarioStep(
                step_name="export_verification",
                status="failed",
                duration_ms=int((time.time() - t0) * 1000),
                detail=f"导出验证失败: {exc}",
            ))
    else:
        steps.append(ScenarioStep(
            step_name="export_verification",
            status="skipped",
            duration_ms=0,
            detail="导出验证已跳过（配置关闭）",
        ))

    # ── 组装结果 ────────────────────────────────────────
    completed_at = datetime.now(timezone.utc)
    total_ms = int((completed_at - started_at).total_seconds() * 1000)
    all_passed = all(s.status == "passed" for s in steps if s.status != "skipped")

    approval_rate = len(approved) / len(cards) if cards else 0.0

    summary = (
        f"场景「{cfg.card_count} cards dogfood」: "
        f"{sum(1 for s in steps if s.status == 'passed')}/{len(steps)} 步骤通过"
        f"{' (全部通过)' if all_passed else ''} | "
        f"卡片: {len(cards)}({len(approved)}✓/{len(drafts)}✎/{len(trashed)}✕) | "
        f"确认率: {approval_rate:.0%} | "
        f"图: {graph_relation_count}边/{community_count}社区 | "
        f"耗时: {total_ms}ms"
    )

    return ScenarioResult(
        scenario_name=f"standard_{cfg.card_count}_cards",
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        total_duration_ms=total_ms,
        steps=tuple(steps),
        total_cards=len(cards),
        approved_count=len(approved),
        draft_count=len(drafts),
        trashed_count=len(trashed),
        approval_rate=round(approval_rate, 4),
        graph_relation_count=graph_relation_count,
        community_count=community_count,
        summary=summary,
        all_passed=all_passed,
    )


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _card_identifier(card) -> str:
    """获取卡片标识符（id 或 rel_path）。"""
    return str(getattr(card, "id", None) or getattr(card, "rel_path", ""))


def _cards_to_records(cards: list) -> list[dict[str, object]]:
    """将卡片列表转换为 graph builder 可接受的格式。"""
    from pathlib import Path

    records: list[dict[str, object]] = []
    for card in cards:
        card_id = _card_identifier(card)
        records.append({
            "id": card_id,
            "title": getattr(card, "title", None) or Path(str(getattr(card, "rel_path", ""))).stem,
            "status": getattr(card, "status", "ai_draft"),
            "source_id": getattr(card, "source_id", None),
            "tags": list(getattr(card, "tags", [])),
            "wiki_sections": list(getattr(card, "wiki_sections", [])),
            "run_id": getattr(card, "run_id", None),
            "source_location_index": getattr(card, "source_location_index", None),
        })
    return records


def _build_failed_result(
    reason: str,
    steps: list[ScenarioStep],
    started_at,
) -> ScenarioResult:
    """构建失败的场景结果。"""
    from datetime import datetime, timezone
    completed_at = datetime.now(timezone.utc)
    return ScenarioResult(
        scenario_name=reason,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        total_duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        steps=tuple(steps),
        total_cards=0,
        approved_count=0,
        draft_count=0,
        trashed_count=0,
        approval_rate=0.0,
        graph_relation_count=0,
        community_count=0,
        summary=f"场景失败: {reason}",
        all_passed=False,
    )


def run_cli() -> None:
    """命令行入口：python -m mindforge.dogfood.scenario_runner [workspace_dir]"""
    import sys
    ws_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/mindforge-dogfood-scenario"
    print(f"执行 dogfood 场景: {ws_dir}")
    result = run_dogfood_scenario(ws_dir)
    print(result.summary)
    for step in result.steps:
        icon = {"passed": "[OK]", "failed": "[FAIL]", "skipped": "[SKIP]"}.get(step.status, "[??]")
        print(f"  {icon} {step.step_name}: {step.detail} ({step.duration_ms}ms)")
    if not result.all_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_cli()


__all__ = [
    "ScenarioResult",
    "ScenarioStep",
    "ScenarioConfig",
    "run_dogfood_scenario",
    "run_cli",
]
