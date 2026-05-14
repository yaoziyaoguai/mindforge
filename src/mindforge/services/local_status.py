"""Real-data local status service for CLI adapters.

中文学习型说明：
- 本模块是 CLI/Web 之间可共享的本地状态 use-case 层；它复用 config、
  cards、checkpoint、model setup readiness 等 core 能力。
- 它不依赖 Typer/Rich/React/FastAPI，不读取 secret value，不调用 LLM 或外部 API，
  也不写 vault。CLI 只负责参数和展示，避免 `cli.py` 变成新巨石。
- first-run status 只展示 model setup / local secret store 的产品语义，不把
  legacy provider 诊断字段重新暴露成普通用户主路径。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..app_context import AppContext, build_app_context
from ..cards import iter_cards
from ..checkpoint import Checkpoint, CheckpointError
from ..config import MindForgeConfig
from ..lexical_index import default_index_path
from ..model_setup_readiness import model_setup_readiness
from mindforge_web.services.processing_run_service import list_processing_runs


@dataclass(frozen=True)
class FriendlyError:
    """给普通用户看的分层错误；CLI presenter 决定颜色和 exit code。"""

    what_happened: str
    why_it_matters: str
    how_to_fix: str
    safe_next_command: str


@dataclass(frozen=True)
class LocalStatusSnapshot:
    """MindForge 本地真实数据状态快照；只包含 secret-safe metadata。"""

    config_path: str
    vault: dict[str, Any]
    workspace: dict[str, Any]
    provider: dict[str, Any]
    cubox: dict[str, Any]
    env_keys: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    cards: dict[str, Any]
    recall: dict[str, Any]
    safety: dict[str, Any]
    next_actions: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "vault": self.vault,
            "workspace": self.workspace,
            "provider": self.provider,
            "cubox": self.cubox,
            "sources": self.sources,
            "cards": self.cards,
            "recall": self.recall,
            "safety": self.safety,
            "next_actions": self.next_actions,
            "warnings": self.warnings,
        }


def build_local_status_snapshot(
    config_path: Path,
    *,
    vault_override: Path | None = None,
    cwd: Path | None = None,
) -> LocalStatusSnapshot:
    """构建 CLI 可消费的本地状态快照；只读、不联网、不写入。

    架构边界：这里可以编排多个 core service，但不渲染 Rich、不处理 Typer
    exit code，也不把 Web schema 引入 CLI。Web first slice 的 Safety Bar
    思路在这里沉淀为 terminal-friendly snapshot。
    """

    cwd = cwd or Path.cwd()
    context = build_app_context(config_path, vault_override=vault_override, cwd=cwd)
    cfg = context.config
    cards_scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    card_counts: dict[str, int] = {}
    for card in cards_scan.cards:
        card_counts[card.status] = card_counts.get(card.status, 0) + 1
    model_readiness = model_setup_readiness(cfg)
    vault = _vault_status(cfg)
    workspace = _workspace_status(context)
    recall = _recall_status(cfg, approved_count=card_counts.get("human_approved", 0))
    safety = _safety_summary(
        cfg,
        model_readiness=model_readiness,
        pending_drafts=card_counts.get("ai_draft", 0),
    )
    sources = _source_statuses(cfg)
    processing = _processing_status(cfg)
    warnings = _warnings(vault=vault, safety=safety)
    return LocalStatusSnapshot(
        config_path=str(config_path),
        vault=vault,
        workspace=workspace,
        provider=_provider_status(model_readiness),
        cubox={},
        env_keys=[],
        sources=sources,
        cards={
            "total": len(cards_scan.cards),
            "by_status": card_counts,
            "scan_error_count": len(cards_scan.errors),
        },
        recall=recall,
        safety=safety,
        next_actions=_next_actions(
            vault=vault,
            sources=sources,
            card_counts=card_counts,
            processing=processing,
            model_ready=model_readiness.ready,
        ),
        warnings=warnings,
    )


def friendly_config_error(config_path: Path, message: str) -> FriendlyError:
    """把 config/path 错误转成人能看懂的四段式解释。

    中文学习型说明：错误提示只涉及 workspace path、config path，不含 API key、
    token 或 secret。workspace 概念是用户唯一需要理解的产品概念。
    """

    return FriendlyError(
        what_happened=f"MindForge 无法加载配置文件：{config_path}。{message}",
        why_it_matters=(
            "真实数据 CLI 需要先知道 vault、state 和 provider 配置在哪里；"
            "在配置未确认前继续执行容易误读或误写错误 workspace。"
        ),
        how_to_fix=(
            "1. 创建新 workspace：mindforge init\n"
            "2. 切换到已有 workspace：mindforge workspace use /path/to/workspace\n"
            "3. 临时指定 workspace：mindforge status --workspace /path/to/workspace\n"
            "4. 高级方式指定配置：mindforge status --config /path/to/configs/mindforge.yaml"
        ),
        safe_next_command="mindforge init --interactive",
    )


def _vault_status(cfg: MindForgeConfig) -> dict[str, Any]:
    root = cfg.vault.root
    active_meta = (
        cfg.raw.get("_mindforge_active_vault", {})
        if isinstance(cfg.raw, dict)
        else {}
    )
    required = {
        "inbox": cfg.vault.inbox_path,
        "cards": cfg.vault.cards_path,
        "projects": cfg.vault.projects_path,
    }
    return {
        "path": str(root),
        "exists": root.exists(),
        "readable": root.exists(),
        "looks_like_mindforge": all(path.exists() and path.is_dir() for path in required.values()),
        "paths": {name: str(path) for name, path in required.items()},
        "path_states": {
            name: {
                "exists": path.exists(),
                "is_dir": path.is_dir(),
                "readable": path.exists(),
            }
            for name, path in required.items()
        },
        "is_real_environment": _is_real_environment(root),
        "resolution": {
            "active_root": active_meta.get("root") if isinstance(active_meta, dict) else str(root),
            "reason": active_meta.get("reason") if isinstance(active_meta, dict) else None,
            "configured_root": (
                active_meta.get("configured_root") if isinstance(active_meta, dict) else None
            ),
            "configured_differs": bool(active_meta.get("configured_differs"))
            if isinstance(active_meta, dict)
            else False,
        },
    }


def _workspace_status(context: AppContext) -> dict[str, Any]:
    cfg = context.config
    state_exists = cfg.state.state_path.exists()
    state_error: str | None = None
    state_item_count = 0
    state_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    if state_exists:
        try:
            checkpoint = Checkpoint.load(cfg.state.state_path, backup=False)
            state_item_count = len(list(checkpoint.all_items()))
            state_counts = checkpoint.count_by_status()
            source_counts = checkpoint.count_by_source_type()
        except CheckpointError as exc:
            state_error = f"{type(exc).__name__}: {exc}"
    return {
        "state_path": str(cfg.state.state_path),
        "state_exists": state_exists,
        "state_item_count": state_item_count,
        "state_counts": state_counts,
        "source_counts": source_counts,
        "state_error": state_error,
        "runs_path": str(cfg.state.runs_path),
        "workdir": str(cfg.state.workdir),
    }


def _provider_status(model_readiness) -> dict[str, Any]:
    """返回 first-run 可见的 model setup 状态。

    中文学习型说明：status/start/doctor 必须共用 ``model_setup_readiness``。
    这里刻意不返回 legacy provider 兼容字段或 source-adapter 诊断字段，
    避免 JSON 消费者再把它们渲染回用户主路径。
    """

    return {
        "model_setup_status": model_readiness.status,
        "model_setup_label": model_readiness.label,
        "missing_model_ids": list(model_readiness.missing_model_ids),
        "network_called": False,
    }


def _source_statuses(cfg: MindForgeConfig) -> list[dict[str, Any]]:
    """只按 glob 统计 source 文件，不解析 source 正文。"""

    rows: list[dict[str, Any]] = []
    for entry in cfg.sources.active_entries():
        path = cfg.vault.inbox_path / entry.inbox_subdir
        files = [item for item in path.rglob(entry.file_glob) if item.is_file()] if path.exists() else []
        rows.append(
            {
                "source_type": entry.source_type,
                "adapter": entry.adapter,
                "path": str(path),
                "exists": path.exists(),
                "file_glob": entry.file_glob,
                "file_count": len(files),
                "enabled": entry.enabled,
            }
        )
    return rows


def _recall_status(cfg: MindForgeConfig, *, approved_count: int) -> dict[str, Any]:
    index_path = default_index_path(cfg.state.workdir)
    return {
        "mode": "local lexical recall",
        "not_rag": True,
        "not_embedding": True,
        "index_path": str(index_path),
        "index_exists": index_path.exists(),
        "approved_card_count": approved_count,
        "available": True,
    }


def _safety_summary(
    cfg: MindForgeConfig,
    *,
    model_readiness,
    pending_drafts: int,
) -> dict[str, Any]:
    return {
        "local_only": True,
        "vault_path": str(cfg.vault.root),
        "model_setup": model_readiness.status,
        "write_mode": "explicit_approval_required",
        "pending_drafts": pending_drafts,
        "real_provider_calls": False,
        "real_cubox_calls": False,
    }


def _warnings(
    *,
    vault: dict[str, Any],
    safety: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if vault["is_real_environment"]:
        warnings.append("Real-looking vault is active; writes require explicit user action.")
    if safety["model_setup"] != "ready":
        warnings.append("Model setup needs attention; status checks still do not call LLM.")
    if safety["pending_drafts"]:
        warnings.append("ai_draft cards are pending review; approval requires explicit confirmation.")
    return warnings


def _next_actions(
    *,
    vault: dict[str, Any],
    sources: list[dict[str, Any]],
    card_counts: dict[str, int],
    processing: dict[str, Any],
    model_ready: bool,
) -> list[str]:
    actions: list[str] = []
    if not vault["exists"]:
        actions.append("mindforge init --interactive")
        return actions
    if not model_ready:
        actions.append("mindforge web  # complete model setup with a provider key")
    if not sources or not any(int(item.get("file_count", 0)) > 0 for item in sources):
        actions.append("mindforge watch add <file-or-folder> or mindforge import <file-or-folder>")
    if processing.get("failed_or_blocked"):
        actions.append("mindforge runs list, then mindforge runs show <run_id>")
        actions.append("retry processing after model setup or source issues are fixed")
    if card_counts.get("ai_draft", 0):
        actions.append("mindforge approve list")
    if not card_counts.get("ai_draft", 0) and not card_counts.get("human_approved", 0):
        if processing.get("count", 0) > 0:
            actions.append("mindforge runs list")
        else:
            actions.append("mindforge watch add <file-or-folder> or mindforge import <file-or-folder>")
    if not actions:
        actions.append("mindforge recall --query <keyword>")
    return list(dict.fromkeys(actions))


def _processing_status(cfg: MindForgeConfig) -> dict[str, Any]:
    """只读 processing run 摘要；不创建 run，也不修复 abandoned 状态到磁盘。"""

    records = list_processing_runs(cfg)
    return {
        "count": len(records),
        "failed_or_blocked": any(record.status in {"failed", "partial_failed"} for record in records),
    }


def _is_real_environment(root: Path) -> bool:
    resolved = root.expanduser().resolve()
    text = str(resolved)
    return (
        "demo-vault" not in text
        and "dogfood-vault" not in text
        and "fictional-vault" not in text
        and "tmp" not in resolved.parts
        and resolved.exists()
    )
