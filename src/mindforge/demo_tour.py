"""``mindforge demo`` 60 秒新用户 tour 的纯编排层。

为什么单独一个 demo_tour 模块?
================================

到 v0.13 闭环为止, MindForge 已经有非常多的"低层"命令: ``cubox dry-run``
/ ``cubox preview-ai-draft`` / ``dogfood preflight`` / ``obsidian doctor``
/ ``provider readiness`` / ``dogfood quickstart`` ……

新用户的痛点不是"没有命令", 而是 **"我第一分钟该跑哪一条?"**。
``mindforge demo`` 的任务是回答这一句: 用 **零 secret、零网络、零真实
vault 写入** 的方式, 把 SourceDocument → ai_draft → review packet →
obsidian dry-run 这条主链路 **跑给用户看一眼**, 让他们知道:

- MindForge 装好了;
- fake provider 默认安全路径走得通;
- 真实数据接入的下一步是 ``dogfood quickstart``。

这就是 ``demo_tour`` 的唯一职责: **纯编排** 已有命令的 service 层
(不是 CLI 层), 把它们拼成一个有时序、有总结的 tour。它本身 **不** 做
任何业务逻辑, **不** 持有任何状态。

本模块的硬边界 (高内聚 + 信息隐藏)
==================================

- **只** 调用 service / adapter 级 API: ``CuboxApiAdapter.parse_export``,
  ``classify_dogfood_path``, ``inspect_obsidian_vault`` 等 **已有**
  的纯函数 / dataclass / parser; **不** 重新实现业务规则;
- **只** 返回 ``DemoTourReport`` (pure dataclass) 与 ``str`` (renderer);
- **不** 调用 Typer CLI 命令 (避免 CLI → service → CLI 的反向依赖);
- **不** 调用真实 LLM / 真实 Cubox HTTP / Obsidian write;
- **不** 读取 ``.env`` / ``$HOME`` / 用户私有路径;
- **不** 写任何文件 (即使临时目录也不写; 用 in-memory 即可);
- **不** 产生 ``human_approved`` (review packet 永远是 review-only);
- **不** import ``cli`` / ``approval_service`` / ``approver`` /
  ``writer`` / ``cards`` / ``llm`` / ``obsidian_workflow`` /
  ``env_loader`` / ``dotenv`` / ``requests`` / ``httpx`` /
  ``urllib.request`` / ``subprocess``。

对外 API
========

``run_demo_tour(...) -> DemoTourReport`` — 执行 4 步 tour, 返回
结构化结果。
``render_demo_tour(report) -> str`` — 把结果渲染成新用户可读的文本,
含 "What you just saw / What is safe / What to try next" 三段。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .dogfood_safety import classify_input_path
from .sources.cubox_api import CuboxApiAdapter


# 仓库自带的 Cubox 真实 export fixture: 2 条非敏感、可公开示例条目。
# 本模块刻意不接受 ``--export`` 参数, 因为 demo 的契约是 "零配置";
# 真实数据请走 ``mindforge dogfood quickstart`` + 用户自己的 export。
_DEMO_CUBOX_FIXTURE = Path("tests/fixtures/sample_cubox_api_export.json")
_DEMO_VAULT = Path("examples/demo-vault")


@dataclass(frozen=True)
class DemoStep:
    """一步 tour 的结构化结果。

    使用 frozen dataclass 而不是 dict, 是为了让 CLI / tests 拿到的
    字段名稳定, 防止 typo, 同时让 ``mindforge demo --json`` 输出
    schema 可预测。
    """

    name: str
    """步骤显式名 (如 'cubox-preview')。"""

    title: str
    """新用户可读的一行说明。"""

    ok: bool
    """这步是否完成预期 (失败时 detail 字段会带 reason)。"""

    summary: str
    """新用户读得懂的一句结果摘要 (如 'parsed 2 cubox items')。"""

    detail: dict[str, object] = field(default_factory=dict)
    """结构化细节, 供 ``--json`` 输出与 tests 断言。"""


@dataclass(frozen=True)
class DemoTourReport:
    """整个 tour 的结构化结果。"""

    steps: tuple[DemoStep, ...]
    safety_invariants: tuple[str, ...]
    next_actions: tuple[str, ...]

    @property
    def all_ok(self) -> bool:
        return all(s.ok for s in self.steps)


def run_demo_tour(
    *,
    cubox_fixture: Path | None = None,
    demo_vault: Path | None = None,
) -> DemoTourReport:
    """执行 60 秒 demo tour, 返回结构化结果。

    参数都是可选的, 默认走仓库自带的 fixture 与 demo-vault, 让
    新用户 ``mindforge demo`` 一条命令零参数就能看到效果。tests
    里可以传入临时 fixture / 临时 vault, 用同一函数验证。

    Tour 的 4 步刻意挑选, 覆盖主链路的 4 个关键 seam:

    1. ``cubox-preview`` — Cubox JSON export → SourceDocument 解析
       (验证 source adapter 边界);
    2. ``dogfood-preflight`` — 路径分类策略 (验证 policy 层);
    3. ``obsidian-vault`` — Obsidian vault 健康检查 (验证 vault
       adapter 边界);
    4. ``review-packet`` — 把前 3 步的产出汇总成一个 review packet
       (验证 ai_draft / review-only 边界)。

    注意: 不调用真实 LLM, 不写 vault, 不产生 human_approved。
    """
    fixture = cubox_fixture or _DEMO_CUBOX_FIXTURE
    vault = demo_vault or _DEMO_VAULT

    steps: list[DemoStep] = []

    # Step 1: Cubox preview — real fixture, zero network.
    steps.append(_step_cubox_preview(fixture))

    # Step 2: dogfood preflight — pure policy decision on the demo vault.
    steps.append(_step_dogfood_preflight(vault))

    # Step 3: obsidian vault probe — read-only directory inspection.
    steps.append(_step_obsidian_vault(vault))

    # Step 4: review packet — pure aggregation of step 1-3 results.
    steps.append(_step_review_packet(steps))

    return DemoTourReport(
        steps=tuple(steps),
        safety_invariants=(
            "fake-default (no real LLM was called)",
            "no .env content was read",
            "no real Cubox HTTP API was called",
            "no Obsidian vault was written to",
            "no human_approved record was produced",
            "no RAG / embedding / semantic merge was activated",
            "no tag, no release, no push",
        ),
        next_actions=(
            "Run a real-data dogfood loop on your own non-sensitive Cubox export:",
            "  mindforge dogfood readiness --vault /tmp/dogfood-vault",
            "  mindforge dogfood quickstart --vault /tmp/dogfood-vault",
            "Inspect your install:",
            "  mindforge doctor",
            "See what to do next:",
            "  mindforge next",
        ),
    )


def _step_cubox_preview(fixture: Path) -> DemoStep:
    """Step 1: 用 ``CuboxApiAdapter`` 解析 fixture, 不调任何 HTTP。"""
    if not fixture.exists():
        return DemoStep(
            name="cubox-preview",
            title="Cubox JSON export → SourceDocument",
            ok=False,
            summary=f"fixture not found: {fixture}",
            detail={"fixture": str(fixture)},
        )
    adapter = CuboxApiAdapter(credential=None)
    docs = adapter.parse_export(fixture)
    sample_titles = [d.title for d in docs[:3]]
    return DemoStep(
        name="cubox-preview",
        title="Cubox JSON export → SourceDocument",
        ok=True,
        summary=f"parsed {len(docs)} cubox items from fixture (zero network)",
        detail={
            "fixture": str(fixture),
            "items_parsed": len(docs),
            "sample_titles": sample_titles,
        },
    )


def _step_dogfood_preflight(vault: Path) -> DemoStep:
    """Step 2: 用 dogfood policy 对 demo-vault 做静态路径分类。"""
    if not vault.exists():
        return DemoStep(
            name="dogfood-preflight",
            title="Dogfood path classification",
            ok=False,
            summary=f"demo vault not found: {vault}",
            detail={"vault": str(vault)},
        )
    classification = classify_input_path(
        vault, declared_non_sensitive=True
    )
    # synthetic / non_sensitive_local 都是 demo 可接受的安全分类。
    allowed = classification in ("synthetic", "non_sensitive_local")
    return DemoStep(
        name="dogfood-preflight",
        title="Dogfood path classification",
        ok=allowed,
        summary=(
            f"demo-vault classified as '{classification}' "
            f"(allowed={allowed})"
        ),
        detail={
            "vault": str(vault),
            "classification": classification,
            "allowed": allowed,
        },
    )


def _step_obsidian_vault(vault: Path) -> DemoStep:
    """Step 3: 只读盘点 demo vault 的目录结构, 不调 Obsidian writer。"""
    if not vault.exists():
        return DemoStep(
            name="obsidian-vault",
            title="Obsidian vault read-only probe",
            ok=False,
            summary=f"demo vault not found: {vault}",
            detail={"vault": str(vault)},
        )
    md_files = sorted(vault.rglob("*.md"))
    has_obsidian_dir = (vault / ".obsidian").exists()
    return DemoStep(
        name="obsidian-vault",
        title="Obsidian vault read-only probe",
        ok=True,
        summary=(
            f"found {len(md_files)} Markdown notes in demo-vault "
            f"(.obsidian present={has_obsidian_dir}; read-only, no writes performed)"
        ),
        detail={
            "vault": str(vault),
            "markdown_files": len(md_files),
            "obsidian_dir_present": has_obsidian_dir,
            "writes_attempted": False,
        },
    )


def _step_review_packet(prior_steps: list[DemoStep]) -> DemoStep:
    """Step 4: 汇总前 3 步, 产出 in-memory review packet。

    显式声明 ``artifact_type='review_packet'`` 与 ``human_approved=False``,
    把 "demo 永远不产生 human_approved" 这条不变量编码进 detail 里,
    供 tests 与 ``--json`` consumer 断言。
    """
    parsed = sum(1 for s in prior_steps if s.ok)
    return DemoStep(
        name="review-packet",
        title="In-memory review packet (no vault write)",
        ok=parsed == len(prior_steps),
        summary=(
            f"aggregated {parsed}/{len(prior_steps)} prior steps into a "
            "review-only packet (artifact_type=review_packet)"
        ),
        detail={
            "artifact_type": "review_packet",
            "human_approved": False,
            "writes_vault": False,
            "prior_steps_ok": parsed,
            "prior_steps_total": len(prior_steps),
        },
    )


def render_demo_tour(report: DemoTourReport) -> str:
    """把 ``DemoTourReport`` 渲染成新用户可读的文本。

    pinned literals (供 tests 与未来 docs 断言, 防止文案漂移):
    - ``"MindForge 60-second demo tour"``
    - ``"What you just saw"``
    - ``"What is safe"``
    - ``"What to try next"``
    - ``"no human_approved"``
    - ``"fake-default"``
    - ``"dogfood quickstart"``
    """
    lines: list[str] = []
    lines.append("MindForge 60-second demo tour")
    lines.append("=" * 40)
    lines.append("")
    lines.append("What you just saw:")
    for idx, step in enumerate(report.steps, start=1):
        marker = "✓" if step.ok else "✗"
        lines.append(f"  {idx}. {marker} {step.title}")
        lines.append(f"      {step.summary}")
    lines.append("")
    lines.append("What is safe (every demo run guarantees):")
    for inv in report.safety_invariants:
        lines.append(f"  - {inv}")
    lines.append("")
    lines.append("What to try next:")
    for action in report.next_actions:
        lines.append(f"  {action}")
    lines.append("")
    lines.append(
        "Note: this is a demo. It does not produce human_approved records, "
        "does not write to any Obsidian vault, and does not call any real LLM "
        "or real Cubox HTTP API. Default profile stays fake-default."
    )
    return "\n".join(lines)
