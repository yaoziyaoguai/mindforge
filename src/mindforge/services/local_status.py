"""Real-data local status service for CLI adapters.

中文学习型说明：
- 本模块是 CLI/Web 之间可共享的本地状态 use-case 层；它复用 config、
  provider_readiness、cubox_readiness、cards、checkpoint 等 core 能力。
- 它不依赖 Typer/Rich/React/FastAPI，不读取 secret value，不调用 LLM/Cubox
  API，也不写 vault。CLI 只负责参数和展示，避免 `cli.py` 变成新巨石。
- `.env` 只做 key presence 解析：返回 key name 与来源，不返回等号右侧内容。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..app_context import AppContext, build_app_context
from ..cards import iter_cards
from ..checkpoint import Checkpoint, CheckpointError
from ..config import MindForgeConfig
from ..cubox_readiness import classify_cubox_real_opt_in, inspect_cubox_config
from ..lexical_index import default_index_path
from ..provider_readiness import build_readiness_report


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
            "env_keys": self.env_keys,
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
    env_keys = _env_key_statuses(cfg, cwd=cwd)
    provider_report = build_readiness_report(cfg.llm)
    cubox_report = inspect_cubox_config()
    cubox_classification = classify_cubox_real_opt_in(cubox_report, allow_real=False)
    vault = _vault_status(cfg)
    workspace = _workspace_status(context)
    recall = _recall_status(cfg, approved_count=card_counts.get("human_approved", 0))
    safety = _safety_summary(
        cfg,
        provider_report=provider_report,
        env_keys=env_keys,
        pending_drafts=card_counts.get("ai_draft", 0),
    )
    warnings = _warnings(vault=vault, safety=safety, provider_report=provider_report)
    return LocalStatusSnapshot(
        config_path=str(config_path),
        vault=vault,
        workspace=workspace,
        provider=_provider_status(provider_report),
        cubox={
            "token_env_var": cubox_report.get("token_env_var"),
            "token_present": bool(cubox_report.get("token_present", False)),
            "opt_in_state": cubox_classification.get("opt_in_state"),
            "next_action": cubox_classification.get("next_action"),
            "network_called": False,
        },
        env_keys=env_keys,
        sources=_source_statuses(cfg),
        cards={
            "total": len(cards_scan.cards),
            "by_status": card_counts,
            "scan_error_count": len(cards_scan.errors),
        },
        recall=recall,
        safety=safety,
        next_actions=_next_actions(vault=vault, card_counts=card_counts, recall=recall),
        warnings=warnings,
    )


def friendly_config_error(config_path: Path, message: str) -> FriendlyError:
    """把 config/path 错误转成人能看懂的四段式解释。"""

    return FriendlyError(
        what_happened=f"MindForge 无法加载配置文件：{config_path}。{message}",
        why_it_matters=(
            "真实数据 CLI 需要先知道 vault、state 和 provider 配置在哪里；"
            "在配置未确认前继续执行容易误读或误写错误 workspace。"
        ),
        how_to_fix="检查 --config 路径，或用安全模板生成一份本地配置。",
        safe_next_command="mindforge config init --output configs/mindforge.yaml --vault <vault>",
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
        "readable": os.access(root, os.R_OK) if root.exists() else False,
        "looks_like_mindforge": all(path.exists() and path.is_dir() for path in required.values()),
        "paths": {name: str(path) for name, path in required.items()},
        "path_states": {
            name: {
                "exists": path.exists(),
                "is_dir": path.is_dir(),
                "readable": os.access(path, os.R_OK) if path.exists() else False,
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


def _provider_status(report: dict[str, Any]) -> dict[str, Any]:
    provider = report["provider"]
    opt_in = report["opt_in"]
    return {
        "active_profile": provider["active_profile"],
        "opt_in_state": opt_in["opt_in_state"],
        "can_run_real_smoke": opt_in["can_run_real_smoke"],
        "blockers": list(opt_in["blockers"]),
        "aliases": [
            {
                "alias": alias["alias"],
                "type": alias["type"],
                "in_active_profile": alias["in_active_profile"],
                "api_key_env": alias.get("api_key_env"),
                "api_key_present": bool(alias.get("api_key_present")),
                "base_url_env_present": bool(alias.get("base_url_env_present")),
            }
            for alias in provider["aliases"]
        ],
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
    provider_report: dict[str, Any],
    env_keys: list[dict[str, Any]],
    pending_drafts: int,
) -> dict[str, Any]:
    return {
        "local_only": True,
        "vault_path": str(cfg.vault.root),
        "provider_state": provider_report["opt_in"]["opt_in_state"],
        "env_status": "configured" if any(item["configured"] for item in env_keys) else "missing",
        "write_mode": "explicit_approval_required",
        "pending_drafts": pending_drafts,
        "real_provider_calls": False,
        "real_cubox_calls": False,
    }


def _warnings(
    *,
    vault: dict[str, Any],
    safety: dict[str, Any],
    provider_report: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if vault["is_real_environment"]:
        warnings.append("Real-looking vault is active; writes require explicit user action.")
    if provider_report["opt_in"]["opt_in_state"] not in {"fake_default", "env_only"}:
        warnings.append("Real provider profile may be active; status checks still do not call LLM.")
    if safety["pending_drafts"]:
        warnings.append("ai_draft cards are pending review; approval requires explicit confirmation.")
    return warnings


def _next_actions(
    *,
    vault: dict[str, Any],
    card_counts: dict[str, int],
    recall: dict[str, Any],
) -> list[str]:
    actions: list[str] = []
    if not vault["exists"]:
        actions.append("mindforge init --interactive")
    if card_counts.get("ai_draft", 0):
        actions.append("mindforge approve list")
    if recall["approved_card_count"] == 0:
        actions.append("mindforge approve show --card <draft> --show-content")
    if not actions:
        actions.append("mindforge recall --query <keyword>")
    return actions


def _env_key_statuses(cfg: MindForgeConfig, *, cwd: Path) -> list[dict[str, Any]]:
    dotenv = _read_dotenv_keys(cwd)
    names = sorted(_interesting_env_names(cfg))
    rows: list[dict[str, Any]] = []
    for name in names:
        sources: list[str] = []
        if name in os.environ:
            sources.append("process")
        if name in dotenv:
            sources.append(".env")
        rows.append({"name": name, "configured": bool(sources), "sources": sources})
    return rows


def _interesting_env_names(cfg: MindForgeConfig) -> set[str]:
    names = {"MINDFORGE_CUBOX_TOKEN"}
    for model in cfg.llm.models.values():
        for value in (model.api_key_env, model.base_url_env, model.version_env, model.model_env):
            if value:
                names.add(value)
    return names


def _read_dotenv_keys(start: Path) -> frozenset[str]:
    path = _find_dotenv(start)
    if path is None:
        return frozenset()
    keys: set[str] = set()
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                key = _parse_env_key_presence_only(line)
                if key:
                    keys.add(key)
    except OSError:
        return frozenset()
    return frozenset(keys)


def _find_dotenv(start: Path) -> Path | None:
    cur = start.resolve()
    for path in (cur, *cur.parents):
        candidate = path / ".env"
        if candidate.is_file():
            return candidate
    return None


def _parse_env_key_presence_only(line: str) -> str | None:
    """只解析等号左侧 key；调用方不得保存或展示 RHS secret value。"""

    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key = stripped.split("=", 1)[0].removeprefix("export ").strip()
    return key if key.isidentifier() else None


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
