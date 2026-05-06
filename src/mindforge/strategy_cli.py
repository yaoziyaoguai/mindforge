"""Strategy discovery CLI adapter.

只展示 registry/custom declarative 元数据，不执行 strategy、不构造 LLMClient。
"""
from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import console
from .config import PromptVersions
from .strategies import (
    DEFAULT_STRATEGY_NAME,
    StrategyMetadata,
    UnknownStrategyError,
    get_strategy_metadata,
    list_strategies,
)

# v0.11 Slice 1：strategies 子命令组只做"策略发现"。它纯查询 registry
# 元数据，不会触发 LLMClient 构造、不会读 .env、不会写 workspace、不会
# approve；这条边界让用户能在任何环境下安全运行 `mindforge strategies list`。
strategies_app = typer.Typer(
    add_completion=False,
    help="知识归纳策略发现（只读元数据：strategy_id / version / 描述）。",
)


@strategies_app.command("list")
def strategies_list(
    include_internal: bool = typer.Option(
        False,
        "--include-internal",
        help=(
            "显示 internal/debug/planned strategy metadata。默认隐藏测试替身，"
            "避免把 deterministic baseline 包装成用户产品能力。"
        ),
    ),
    custom_path: Path | None = typer.Option(
        None,
        "--custom-path",
        help=(
            "可选的 custom strategy 目录（显式路径，必须由用户提供）。"
            "传入后会把该目录下的 declarative custom 定义并入展示，"
            "标记为 [custom]，仍标记为 not executable / preview / planned。"
            "discovery is not execution —— 不会触发任何 LLM / .env / vault 写入。"
        ),
    ),
) -> None:
    """列出所有内建知识归纳策略的元数据；可选地把 ``--custom-path`` 目录
    下的 custom declarative 定义并入展示。

    本命令是纯查询：不构造 LLMClient、不读 ``.env``、不写 vault、不
    approve、不调用 strategy 本身的 ``run()``。

    输出包含每个策略的 ``strategy_id`` / ``strategy_version`` /
    ``display_name`` / ``status`` / ``provider_mode`` / ``safety_policy`` /
    ``output_schema_id`` / ``description``；custom 定义额外标 ``[custom]``
    与 ``not executable``，built-in 标 ``[built-in]``。

    Custom 错误处理：每个 custom 文件**逐个**通过
    :func:`load_strategy_definition_from_file` 加载，**任一**文件校验
    失败时只对该文件输出一行可读的 ``validation error``（包含文件路径
    + 失败原因），不中断其它文件 + built-in 的展示，也不会把非法定义
    悄悄注册进 :func:`available_strategies` —— 校验失败的 custom 不会
    出现在元数据列表里。
    """

    for meta in list_strategies(include_internal=include_internal):
        _print_strategy_meta(meta, kind="built-in")

    if custom_path is None:
        return

    from mindforge.strategies.custom_loader import (
        StrategyDefinitionFileError,
        iter_strategy_definition_files,
        load_strategy_definition_from_file,
    )

    try:
        candidate_paths = iter_strategy_definition_files(custom_path)
    except StrategyDefinitionFileError as exc:
        # 中文学习型注释：目录本身不存在 / 不是目录 / symlink-escape
        # 等"目录级"错误，CLI 给一行可读输出后正常返回（exit 0），
        # 不裸抛栈 —— discovery UX 的硬约束。
        console.print(f"[red]validation error[/red] {exc}")
        return

    for path in candidate_paths:
        try:
            definition = load_strategy_definition_from_file(path)
        except StrategyDefinitionFileError as exc:
            # 中文学习型注释：单文件错误 → 单行友好展示，继续处理后续
            # 文件。绝不把 raw Traceback / Python repr 漏到终端，也
            # 绝不把非法定义注册成可执行 —— 后者由 discover_strategies
            # 完全不写入 registry 来保证。
            console.print(
                f"[red]validation error[/red] {path.name}: {exc}"
            )
            continue
        _print_strategy_meta(definition.to_metadata(), kind="custom")


@strategies_app.command("show")
def strategies_show(
    strategy_id: str = typer.Argument(..., help="要查看的 strategy id。"),
    include_internal: bool = typer.Option(
        False,
        "--include-internal",
        help="允许查看 internal/debug/planned strategy metadata。",
    ),
) -> None:
    """展示单个 built-in strategy 的只读说明。

    中文学习型说明：``show`` 是 explain，不是 execute。它只读 registry
    metadata 和内置 prompt version 映射，不构造 LLMClient、不读 ``.env``、
    不写 vault。planned strategy 仍可被展示，但明确标记 not executable。
    """

    try:
        meta = get_strategy_metadata(strategy_id)
    except UnknownStrategyError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(code=2) from None

    is_legacy = meta.canonical_id and strategy_id != meta.canonical_id
    if meta.is_internal and not is_legacy and not include_internal:
        console.print(
            f"strategy {strategy_id!r} is internal/debug metadata; "
            "rerun with --include-internal to inspect it. "
            "Production users should use `knowledge_card`.",
            markup=False,
            soft_wrap=True,
        )
        raise typer.Exit(code=2)

    _print_strategy_meta(meta, kind="built-in")
    if is_legacy:
        console.print(
            f"  legacy alias: {strategy_id} -> {meta.canonical_id}",
            markup=False,
        )
    if meta.strategy_id == DEFAULT_STRATEGY_NAME:
        console.print("  default: yes")
    console.print(f"  role: {meta.role}", markup=False)
    console.print(f"  production_ready: {'yes' if meta.production_ready else 'no'}")
    console.print(f"  user_recommended: {'yes' if meta.user_recommended else 'no'}")
    if meta.warning:
        console.print(f"  warning: {meta.warning}", markup=False, soft_wrap=True)
    if meta.status == "planned":
        console.print("  executable: no (planned / not executable)")
    else:
        console.print("  executable: yes")
    console.print("  prompt_versions:")
    for stage, version in _default_prompt_versions().items():
        # 当前只有 five_stage 消费五段 prompt；其它 deterministic / planned
        # strategy 仍展示“not used”，避免用户误以为每个策略都会调这些 prompt。
        suffix = "" if meta.strategy_id == DEFAULT_STRATEGY_NAME else " (not used by this strategy)"
        console.print(f"    {stage}: {version}{suffix}")


def _print_strategy_meta(meta: StrategyMetadata, *, kind: str) -> None:
    """统一的策略元数据展示（built-in / custom 共用）。

    custom 来源额外标 ``not executable``，让用户立刻分辨"我能否
    ``mindforge process --strategy <id>``"。
    """

    badge = "(built-in)" if kind == "built-in" else "(custom) not executable"
    console.print(
        f"[bold]{meta.strategy_id}[/bold]@{meta.strategy_version}  "
        f"[cyan]{meta.display_name}[/cyan]  "
        f"[magenta][{meta.status}][/magenta]  "
        f"[yellow]{badge}[/yellow]"
    )
    console.print(
        f"  status: {meta.status}  "
        f"role: {meta.role}  "
        f"production_ready: {'yes' if meta.production_ready else 'no'}  "
        f"user_recommended: {'yes' if meta.user_recommended else 'no'}  "
        f"provider_mode: {meta.provider_mode}  "
        f"safety_policy: {meta.safety_policy}  "
        f"output_schema_id: {meta.output_schema_id}"
    )
    console.print(f"  {meta.description}")
    if meta.warning:
        console.print(f"  warning: {meta.warning}", markup=False, soft_wrap=True)


def _default_prompt_versions() -> dict[str, str]:
    versions = PromptVersions(
        triage="v1",
        distill="v1",
        link_suggestion="v1",
        review_questions="v1",
        action_extraction="v1",
    )
    return {
        "triage": versions.triage,
        "distill": versions.distill,
        "link_suggestion": versions.link_suggestion,
        "review_questions": versions.review_questions,
        "action_extraction": versions.action_extraction,
    }
