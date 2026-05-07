"""process_service — process use-case 的领域 service 层。

中文学习型说明
================

为什么要这一层？
----------------
``mindforge process`` 是 MindForge 的核心 use-case：把已 scan 的源文件跑过
五段 pipeline，落地为 ai_draft Knowledge Card。在 v0.7.20 之前，整段
process 业务流程都内嵌在 ``cli.py::process``：profile 覆盖、fake-safety
（``active_profile != "fake"`` 才允许加载 ``.env``）、prompts/tracks/
template 资源解析、LLMClient 装配、scanner 迭代、checkpoint 写回、outcome
分流、RunLogger 事件、console 输出 …… 全部混在一个 Typer command 函数里。

这违反了几条架构原则：

1. CLI adapter 承担了核心业务判断（fake-safety、资源解析）；
2. service 层无法被独立 service-level test 覆盖；
3. fake-safety 这条系统级安全边界散落在 CLI 文案分支里，无法被静态保护。

本模块只把"最稳定的那一层"下沉到 service：

- ``ProcessRequest``：CLI 透明传入的结构化请求；
- ``ProviderSelection``：根据 ``cfg.llm.active_profile`` 计算的选择结果，
  其中 ``requires_real_env`` 表达了 fake-safety 边界（只有非 fake profile
  才需要加载 ``.env``）；
- ``ProcessAssets``：prompts/tracks/template 来源解析（用户传入 vs 包内
  默认）；
- ``ProcessRuntime``：上述两者的组合产物；
- ``ProcessError``：unsupported_provider / missing_source / malformed_input
  三类结构化错误；
- ``ProcessItemResult``：单文档 ``PipelineOutcome`` 翻译成的结构化结果，
  CLI 直接消费用于 RunLogger.emit / console.print / writer.write。

不抽什么？
----------
本轮明确**不抽**：

- scanner 循环、checkpoint 写回、RunLogger emit、writer.write、所有
  console.print —— 因为它们与 outcome 处理时序强耦合，硬抽会变成机械
  搬运；
- LLMClient / Pipeline 装配 —— 这些仍是 CLI 的"组合根"职责；
- ``load_dotenv_silently`` 实际调用 —— service 只返回 ``requires_real_env``
  标志，CLI 根据它决定是否读 ``.env``，让 IO 副作用集中在 CLI；
- processor 主链路 —— 一个字节都不动；
- ``provider_policy.py`` —— 当前 provider 选择只是"读 active_profile"，
  独立成模块会变贫血 helper。

Service 边界（运行时禁止）
--------------------------
本模块**不允许**：

1. ``import typer``；
2. ``import rich`` / ``console``；
3. 调用 ``console.print``；
4. 引用 ``RunLogger``；
5. 调用 ``load_dotenv*``；
6. 实例化真实 LLM Provider；
7. 自动 approve（不修改 frontmatter status）；
8. 写正式 Obsidian notes；
9. RAG / embedding；
10. 改变 processor 主链路；
11. 改变 provider/LLM 测试替身的离线边界；
12. 承担 Markdown / JSON / Rich 输出。

与 ``safety_policy.py`` 的关系
------------------------------
``safety_policy.py`` 已声明 ``fake_provider_default`` / ``no_env_read`` /
``no_real_llm`` 等**边界常量**。本模块不修改、不扩展 ``safety_policy``，
也不将 ``safety_policy`` 用作控制流分支（保持 safety_policy 的克制）。
``requires_real_env`` 是 process use-case 自身的局部判断，测试通过引用
``safety_policy.boundary_statement(...)`` 证明本 service 与已声明边界对齐。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .assets_runtime import asset_root, bundled_text
from .config import MindForgeConfig
from .processors.pipeline import PipelineOutcome
from .sources.base import SourceDocument

# 默认 fake provider profile 名。与 ``safety_policy.fake_provider_default``
# 边界对齐：fake provider 是默认安全路径，不需要读 ``.env`` / 不调用真实 LLM。
FAKE_PROFILE: str = "fake"

# ---------------------------------------------------------------------------
# 数据形：request / assets / runtime / result / error
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessRequest:
    """CLI 透传给 service 的结构化请求。

    ``cfg`` 必须是已通过 ``load_app_config`` 校验过的 ``MindForgeConfig``；
    profile override 由 CLI 端先用 ``_override_active_profile`` 处理掉，
    service 不接受裸字符串 profile，避免和 CLI 的 typer.Exit 文案耦合。
    """

    cfg: MindForgeConfig
    file: Path | None = None
    limit: int | None = None
    dry_run: bool = False
    prompts_dir: Path | None = None
    tracks: Path | None = None
    template: Path | None = None
    bypass_triage_gate: bool = False


@dataclass(frozen=True)
class ProcessAssets:
    """process 链路所需的运行时资源。

    设计意图：用户显式传入路径时优先使用，否则落到 package 内置资源。
    本类型与 ``cli.py`` 在 v0.7.19 之前的内联逻辑保持字节级一致，确保
    CLI 行为不变。
    """

    # prompts_dir 是 ``Path`` 或 ``importlib.resources`` Traversable。
    # ``Pipeline`` 接受 Any，本字段同样保留 Any 以避免改 processor 协议。
    prompts_dir: Any
    tracks_text: str
    # 用户显式传 template 时使用 ``template_path``；否则使用 ``template_text``。
    # 二者最多有一个非空。
    template_path: Path | None = None
    template_text: str | None = None


@dataclass(frozen=True)
class ProviderSelection:
    """provider/profile 选择的结构化结果。

    ``requires_real_env`` 表达 fake-safety 边界：只有非 fake profile 才需要
    加载 ``.env``。CLI 根据这个 flag 决定是否调用 ``load_dotenv_silently``，
    service 自身不做任何 IO。
    """

    active_profile: str
    requires_real_env: bool


@dataclass(frozen=True)
class ProcessRuntime:
    """resolve 后的运行时配置组合产物。"""

    provider: ProviderSelection
    assets: ProcessAssets
    bypass_triage_gate: bool = False


# ---- 结构化错误码 ----------------------------------------------------------

PROCESS_ERROR_UNSUPPORTED_PROVIDER: str = "unsupported_provider"
PROCESS_ERROR_MISSING_SOURCE: str = "missing_source"
PROCESS_ERROR_MALFORMED_INPUT: str = "malformed_input"


@dataclass(frozen=True)
class ProcessError:
    """service 不抛 raw exception，而是返回结构化错误对象。

    code 限定为 ``PROCESS_ERROR_*`` 三个常量之一。CLI 负责把它翻译成
    console.print + ``typer.Exit``；这样 service 自身不依赖 typer，
    单元测试也不需要 ``CliRunner``。
    """

    code: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProcessItemResult:
    """单文档 ``PipelineOutcome`` 翻译成的结构化结果。

    CLI 仍负责 ``RunLogger.emit`` / ``console.print`` / ``writer.write`` /
    ``checkpoint`` 写回。本类型只携带数据，不做副作用。

    ``status`` 沿用 ``PipelineOutcome.status`` 的三态：
    ``"processed" | "skipped" | "failed"``。任何写卡片落盘的实际副作用都
    保持在 CLI 端的 ``CardWriter.write``，service 不写文件。

    ``would_write_only`` 当 ``dry_run=True`` 且 ``status=="processed"`` 时为
    真，CLI 用它选择"would-write"提示而不是真的写卡片。
    """

    status: str
    track: str | None
    value_score: int | None
    skip_reason: str | None
    error_stage: str | None
    error_message: str | None
    source_dict: dict[str, Any]
    would_write_only: bool
    card_payload: dict[str, Any] | None


# ---------------------------------------------------------------------------
# 主接口：resolve_process_runtime / summarize_outcome
# ---------------------------------------------------------------------------


def resolve_process_runtime(req: ProcessRequest) -> ProcessRuntime | ProcessError:
    """把 ``ProcessRequest`` 解析成 ``ProcessRuntime`` 或结构化错误。

    防御式校验顺序（与配置加载层做双重保护）：

    1. ``cfg.llm.active_profile`` 必须在 ``cfg.llm.profiles`` 里 →
       否则返回 ``unsupported_provider``。
    2. ``limit``（如果给了）必须 >= 0 → 否则返回 ``malformed_input``。
    3. ``cfg.sources.enabled`` 不能为空 → 否则返回 ``missing_source``。

    校验通过后构造 ``ProviderSelection`` 与 ``ProcessAssets``。本函数：

    - 不调用 ``load_dotenv*``；
    - 不实例化任何 LLM Provider；
    - 不写文件；
    - 仅在用户显式传入 ``tracks`` 时调用 ``Path.read_text`` 读取
      learning_tracks.yaml（这是用户已知意图，不是隐式 IO）。
    """
    cfg = req.cfg

    if cfg.llm.active_profile not in cfg.llm.profiles:
        return ProcessError(
            code=PROCESS_ERROR_UNSUPPORTED_PROVIDER,
            message=(
                f"active_profile {cfg.llm.active_profile!r} 不在 "
                f"llm.profiles 中"
            ),
            detail={
                "active_profile": cfg.llm.active_profile,
                "known": sorted(cfg.llm.profiles),
            },
        )

    if req.limit is not None and req.limit < 0:
        return ProcessError(
            code=PROCESS_ERROR_MALFORMED_INPUT,
            message=f"--limit 必须 >= 0, got {req.limit}",
            detail={"field": "limit", "value": req.limit},
        )

    enabled = list(getattr(cfg.sources, "enabled", []) or [])
    if not enabled:
        return ProcessError(
            code=PROCESS_ERROR_MISSING_SOURCE,
            message="sources.enabled 为空，没有可处理的输入来源",
            detail={"field": "sources.enabled"},
        )

    provider = ProviderSelection(
        active_profile=cfg.llm.active_profile,
        requires_real_env=(cfg.llm.active_profile != FAKE_PROFILE),
    )
    assets = _resolve_assets(req)
    return ProcessRuntime(
        provider=provider,
        assets=assets,
        bypass_triage_gate=req.bypass_triage_gate,
    )


def _resolve_assets(req: ProcessRequest) -> ProcessAssets:
    """解析 prompts/tracks/template 三类资源的实际来源。

    与 v0.7.19 之前的 ``cli.py`` 内联行为字节级一致：

    - 用户显式传入路径 → 优先使用（``expanduser`` 展开 ``~``）；
    - 未传入 → 使用 package 内置 asset。

    本函数只在用户显式传入 ``tracks`` 时读取磁盘；其余 ``bundled_*`` 调用
    走 ``importlib.resources``，与文件系统状态无关，保持纯净。
    """
    prompts_dir: Any = (
        req.prompts_dir.expanduser()
        if req.prompts_dir is not None
        else asset_root().joinpath("prompts")
    )
    tracks_text: str = (
        req.tracks.expanduser().read_text("utf-8")
        if req.tracks is not None
        else bundled_text("configs", "learning_tracks.yaml")
    )
    if req.template is not None:
        template_path: Path | None = req.template.expanduser()
        template_text: str | None = None
    else:
        template_path = None
        template_text = bundled_text("templates", "knowledge_card.md.j2")
    return ProcessAssets(
        prompts_dir=prompts_dir,
        tracks_text=tracks_text,
        template_path=template_path,
        template_text=template_text,
    )


def summarize_outcome(
    outcome: PipelineOutcome,
    doc: SourceDocument,
    adapter_name: str,
    *,
    dry_run: bool,
) -> ProcessItemResult:
    """把 ``PipelineOutcome`` 翻译成 CLI 可直接消费的 ``ProcessItemResult``。

    纯函数：

    - 不调用 ``console.print``；
    - 不写文件；
    - 不调用 ``RunLogger``；
    - 不修改 ``outcome`` / ``doc``；
    - 不区分 source_type；不做 RAG / embedding。

    与 v0.7.19 之前的 CLI 三分支字段提取字节级一致：

    - ``skipped``：携带 ``triage`` 解析出的 ``track`` / ``value_score`` 与
      ``skip_reason``；
    - ``failed``：携带 ``error_stage`` / ``error_message``；triage 可能为
      空，``track`` / ``value_score`` 此时为 ``None``，CLI 端按现状不读这
      两个字段；
    - ``processed``：携带 ``track`` / ``value_score`` / ``card_payload`` /
      ``source_dict``；当 ``dry_run`` 时 ``would_write_only=True``，CLI
      据此选择 "would-write" 提示而不是真的写卡片。

    任何未知 ``status`` 都按字面值带回，不抛异常 —— pipeline 的 status
    枚举由 processor 主链路定义，service 不重新约束，保持松耦合。
    """
    triage_parsed: dict[str, Any] = (
        outcome.triage.parsed if outcome.triage else {}
    )
    track = triage_parsed.get("track")
    value_score = triage_parsed.get("value_score")
    source_dict: dict[str, Any] = {
        "source_id": doc.source_id,
        "source_type": doc.source_type,
        "adapter_name": adapter_name,
        "source_path": doc.source_path,
        "source_url": doc.source_url or "",
        "title": doc.title or "",
    }
    return ProcessItemResult(
        status=outcome.status,
        track=track,
        value_score=value_score,
        skip_reason=outcome.skip_reason,
        error_stage=outcome.error_stage,
        error_message=outcome.error_message,
        source_dict=source_dict,
        would_write_only=(outcome.status == "processed" and dry_run),
        card_payload=outcome.card_payload,
    )


__all__ = [
    "FAKE_PROFILE",
    "ProcessAssets",
    "ProcessError",
    "ProcessItemResult",
    "ProcessRequest",
    "ProcessRuntime",
    "ProviderSelection",
    "PROCESS_ERROR_MALFORMED_INPUT",
    "PROCESS_ERROR_MISSING_SOURCE",
    "PROCESS_ERROR_UNSUPPORTED_PROVIDER",
    "resolve_process_runtime",
    "summarize_outcome",
]
