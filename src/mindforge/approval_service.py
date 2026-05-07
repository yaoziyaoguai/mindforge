"""Approval workflow service：集中表达 ai_draft 到 human_approved 的人审边界。

中文学习型说明：
本模块负责 approve 领域里的"业务判断与安全前置条件"，CLI 只负责参数解析、
日志和呈现。它不依赖 Typer/Rich/console，不读取 `.env`，不调用 LLM，也不会写
Obsidian 正式 notes。真正的单卡 frontmatter 状态转移仍委托给 `approver.py`，
这样 `approver.py` 保持最小写入原语，`approval_service.py` 负责 workflow 边界。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .approver import ApprovalEffect, ApprovalError, approve_card
from .cards import CardLoadValueError, CardLoadError, CardSummary, iter_cards, read_card_frontmatter
from .checkpoint import Checkpoint
from .config import MindForgeConfig
from .models import ItemState
from .source_archive_service import SourceArchiveEffect, archive_source_for_approved_card


APPROVAL_PREVIEW_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "status",
    "track",
    "source_type",
    "source_title",
    "source_id",
    "source_path",
    "source_content_hash",
    "source_archive_path",
    "strategy_id",
    "strategy_version",
    "schema_version",
    "prompt_version",
    "prompt_versions",
    "stage_models",
    "run_id",
    "created_at",
    "value_score",
)


@dataclass(frozen=True)
class ApprovalServiceError:
    """service 层结构化错误；CLI 决定如何转成文字和 exit code。"""

    kind: str
    message: str
    exit_code: int
    prev_status: str | None = None


@dataclass(frozen=True)
class ResolvedCardPath:
    """用户传入 card path 的解析结果。

    中文学习型说明：真实 CLI 使用中，``approve list/show`` 会展示 vault 内
    相对路径（例如 ``20-Knowledge-Cards/...``）。如果 approve 只接受绝对
    路径，用户必须手动拼 vault root，违背 local-first CLI 的低摩擦目标。
    因此路径解析集中在 service 层：CLI 只传入用户输入，业务层统一处理
    absolute / cwd-relative / vault-relative 三种合法形态。
    """

    original: Path
    path: Path | None
    attempts: tuple[tuple[str, Path], ...]

    @property
    def ok(self) -> bool:
        return self.path is not None


@dataclass(frozen=True)
class ApprovalListQuery:
    """approve list 的领域过滤条件，输入保持与 CLI 参数解耦。"""

    statuses: tuple[str, ...] = ("ai_draft",)
    project: str | None = None
    track: str | None = None
    limit: int = 50


@dataclass(frozen=True)
class ApprovalListResult:
    """待 approve 候选列表；只包含 CardSummary 白名单字段。"""

    candidates: tuple[CardSummary, ...]
    scan_errors: tuple[CardLoadError, ...]
    statuses: tuple[str, ...]


@dataclass(frozen=True)
class ApprovalCardLookupResult:
    """通过 source_id/card id 等稳定标识解析出的单卡路径。"""

    card_path: Path | None
    error: ApprovalServiceError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.card_path is not None


@dataclass(frozen=True)
class ApprovalPreviewResult:
    """approve show 的只读预览；fields 是前端可展示的白名单 frontmatter。"""

    card_path: Path | None
    fields: dict[str, object]
    error: ApprovalServiceError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.card_path is not None


@dataclass(frozen=True)
class ApprovalExecutionResult:
    """显式 approve 的结构化执行结果；失败不抛给 CLI。

    ``effect`` 字段（原 ``outcome``）记录系统执行后的实际变化；与领域里的
    ``ApprovalDecision``（用户意图）形成清晰二元，避免一个名字承担两件事。
    """

    effect: ApprovalEffect | None = None
    source_archive: SourceArchiveEffect | None = None
    error: ApprovalServiceError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.effect is not None


def list_approval_candidates(
    cfg: MindForgeConfig,
    query: ApprovalListQuery | None = None,
) -> ApprovalListResult:
    """列出待人审候选卡片，不读取正文、不修改文件。

    这里是 approve list 的领域边界：筛选条件只作用于 CardSummary 安全字段。
    默认只返回 `ai_draft`，避免把已审核卡片混进待办视图。
    """

    query = query or ApprovalListQuery()
    wanted = tuple(s for s in query.statuses if s)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    candidates: list[CardSummary] = []
    for card in scan.cards:
        if wanted and card.status not in wanted:
            continue
        if query.project and query.project not in card.projects:
            continue
        if query.track and card.track != query.track:
            continue
        candidates.append(card)
    return ApprovalListResult(
        candidates=tuple(candidates[: query.limit]),
        scan_errors=scan.errors,
        statuses=wanted,
    )


def build_bulk_approval_plan(cfg: MindForgeConfig, *, limit: int = 0) -> ApprovalListResult:
    """构建批量 approve 候选计划；只计划，不执行。

    批量 approve 是高风险动作，因此 service 只负责找出明确的 `ai_draft` 候选；
    是否 `--dry-run`、是否 `--confirm`、如何逐张展示仍由 CLI 层处理。
    """

    effective_limit = limit if limit > 0 else 10**9
    return list_approval_candidates(
        cfg,
        ApprovalListQuery(statuses=("ai_draft",), limit=effective_limit),
    )


def resolve_card_path_by_source_id(
    cfg: MindForgeConfig,
    source_id: str,
) -> ApprovalCardLookupResult:
    """用 state.json 中的 source_id 反查 card_path。

    该函数只解析路径，不 approve。这样 source-id 分支和真正状态转移之间仍有
    明确边界，避免"找到 source 就顺手自动批准"。
    """

    checkpoint = Checkpoint.load(cfg.state.state_path)
    match: ItemState | None = None
    for item in checkpoint.items.values():
        if item.source_id == source_id:
            match = item
            break
    if match is None:
        return ApprovalCardLookupResult(
            card_path=None,
            error=ApprovalServiceError(
                "source_id_not_found",
                f"state.json 中未找到 source_id={source_id}",
                exit_code=2,
            ),
        )
    if not match.card_path:
        return ApprovalCardLookupResult(
            card_path=None,
            error=ApprovalServiceError(
                "source_id_without_card",
                f"source_id={source_id} 还没有 card_path（也许尚未 process）",
                exit_code=3,
            ),
        )

    card_path = (cfg.vault.cards_path / match.card_path).resolve()
    if not card_path.is_file():
        # 兼容：card_path 可能是 vault-root 相对路径。
        alt = (cfg.vault.root / match.card_path).resolve()
        card_path = alt if alt.is_file() else card_path
    return ApprovalCardLookupResult(card_path=card_path)


def resolve_candidate_by_card_id(
    cfg: MindForgeConfig,
    card_id: str | None,
) -> ApprovalCardLookupResult:
    """通过 frontmatter `id` 精确查找卡片；不执行 approve。

    这是 service-level 的稳定查找能力，供测试和未来 CLI 使用。明确要求 card_id
    可以防止调用方把"没有选择目标"误解释成批量或自动 approve。
    """

    if not card_id:
        return ApprovalCardLookupResult(
            card_path=None,
            error=ApprovalServiceError(
                "missing_card_id",
                "approve 必须指定明确 card id",
                exit_code=2,
            ),
        )
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    matches = [card for card in scan.cards if card.id == card_id]
    if not matches:
        return ApprovalCardLookupResult(
            card_path=None,
            error=ApprovalServiceError(
                "card_id_not_found",
                f"未找到 card id={card_id}",
                exit_code=2,
            ),
        )
    if len(matches) > 1:
        return ApprovalCardLookupResult(
            card_path=None,
            error=ApprovalServiceError(
                "ambiguous_card_id",
                f"card id={card_id} 匹配多张卡片",
                exit_code=3,
            ),
        )
    return ApprovalCardLookupResult(card_path=matches[0].path)


def preview_approval_card(cfg: MindForgeConfig, card_path: Path) -> ApprovalPreviewResult:
    """读取 approve preview 的白名单 frontmatter；不读取正文、不改变状态。"""

    resolved = resolve_user_card_path(cfg, card_path)
    if not resolved.ok:
        return ApprovalPreviewResult(
            card_path=resolved.path,
            fields={},
            error=ApprovalServiceError(
                "card_not_found",
                _format_card_path_resolution_error(cfg, resolved),
                exit_code=2,
            ),
        )
    assert resolved.path is not None
    try:
        frontmatter = read_card_frontmatter(resolved.path)
    except (CardLoadValueError, OSError) as exc:
        return ApprovalPreviewResult(
            card_path=resolved.path,
            fields={},
            error=ApprovalServiceError(
                "frontmatter_unreadable",
                f"card frontmatter 无法读取：{type(exc).__name__}: {exc}",
                exit_code=2,
            ),
        )
    return ApprovalPreviewResult(
        card_path=resolved.path,
        fields={key: frontmatter.get(key, "-") for key in APPROVAL_PREVIEW_FIELDS},
    )


def approve_explicit_card(
    cfg: MindForgeConfig,
    card_path: Path | None,
) -> ApprovalExecutionResult:
    """执行一次显式人工 approve；没有明确目标时返回错误。

    注意：这个函数不会替调用方选择默认卡片，也不会基于列表自动 approve。调用者
    必须传入明确 card path，才能触发 `approver.approve_card` 的写入原语。
    """

    if card_path is None:
        return ApprovalExecutionResult(
            error=ApprovalServiceError(
                "missing_card",
                "approve 必须指定明确 card path",
                exit_code=2,
            )
        )
    resolved = resolve_user_card_path(cfg, card_path)
    if not resolved.ok:
        return ApprovalExecutionResult(
            error=ApprovalServiceError(
                "card_not_found",
                _format_card_path_resolution_error(cfg, resolved),
                exit_code=2,
            )
        )
    assert resolved.path is not None
    try:
        effect = approve_card(resolved.path, cfg=cfg)
        archive_effect = (
            archive_source_for_approved_card(cfg, resolved.path)
            if effect.kind == "approved"
            else None
        )
        return ApprovalExecutionResult(effect=effect, source_archive=archive_effect)
    except ApprovalError as exc:
        return ApprovalExecutionResult(
            error=ApprovalServiceError(
                "approval_failed",
                str(exc),
                exit_code=exc.exit_code,
                prev_status=exc.prev_status,
            )
        )


def resolve_user_card_path(cfg: MindForgeConfig, card_path: Path) -> ResolvedCardPath:
    """解析用户传入的 card path；不读文件内容、不执行 approve。

    解析顺序：
    1. absolute path：直接使用；
    2. existing cwd-relative path：当前 shell 下存在就使用；
    3. vault-relative path：当前目录不存在时，尝试 ``vault.root / path``。

    这里刻意不把 ``cards_dir`` 再拼一次，因为 approve list/show 暴露的是
    vault-relative ``20-Knowledge-Cards/...``；如果用户只传 track/file，
    需要先回到 ``approve list/show`` 获取明确路径，避免多重猜测带来歧义。
    """

    expanded = card_path.expanduser()
    if expanded.is_absolute():
        return ResolvedCardPath(
            original=card_path,
            path=expanded if expanded.is_file() else None,
            attempts=(("absolute", expanded),),
        )

    cwd_candidate = expanded
    attempts: list[tuple[str, Path]] = [("cwd-relative", cwd_candidate)]
    if cwd_candidate.is_file():
        return ResolvedCardPath(original=card_path, path=cwd_candidate, attempts=tuple(attempts))

    vault_candidate = cfg.vault.root / expanded
    attempts.append(("vault-relative", vault_candidate))
    if vault_candidate.is_file():
        return ResolvedCardPath(original=card_path, path=vault_candidate, attempts=tuple(attempts))

    return ResolvedCardPath(original=card_path, path=None, attempts=tuple(attempts))


def _format_card_path_resolution_error(cfg: MindForgeConfig, resolved: ResolvedCardPath) -> str:
    attempted = "\n".join(f"  - {label}: {path}" for label, path in resolved.attempts)
    return (
        f"card path could not be resolved: {resolved.original}\n"
        f"Attempted paths:\n{attempted}\n"
        f"vault.root: {cfg.vault.root}\n"
        f"cards_dir: {cfg.vault.cards_dir}\n"
        "If you passed a vault-relative path, check vault.root. "
        "You can run `mindforge approve list` or `mindforge approve show --card <path>` "
        "to copy a complete card path."
    )


__all__ = [
    "APPROVAL_PREVIEW_FIELDS",
    "ApprovalCardLookupResult",
    "ApprovalExecutionResult",
    "ApprovalListQuery",
    "ApprovalListResult",
    "ApprovalPreviewResult",
    "ApprovalServiceError",
    "approve_explicit_card",
    "build_bulk_approval_plan",
    "list_approval_candidates",
    "preview_approval_card",
    "resolve_candidate_by_card_id",
    "resolve_card_path_by_source_id",
]
