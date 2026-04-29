"""Obsidian staged export 的纯 service helper。

本模块刻意不依赖 Typer / Rich / CLI app，只负责 staged export 的路径规划、
manifest payload 与安全边界判断。CLI 可以调用这里的结构化结果再决定如何
展示；这里不能写正式 Obsidian notes，也不能读取 `.env` 或调用 LLM。
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import MindForgeConfig


@dataclass(frozen=True)
class StagedExportPlan:
    """一次 staged export 的结构化计划。

    中文学习型说明：plan 只描述"写到人工检查目录的候选文件和 manifest"，
    不代表可以写回正式 vault。把这层从 CLI 抽出，是为了让未来 write gate
    只能消费明确的证据链，而不是散落在 Rich 输出里的隐含约定。
    """

    export_dir: Path
    proposed_path: Path
    target_path: Path
    manifest_path: Path
    proposed_target: Path
    backup_path: Path
    action: str
    output_policy: str
    formal_conflicts: tuple[Path, ...]


@dataclass(frozen=True)
class DiffPreviewPlan:
    """staged-only diff preview 的结构化结果。

    中文学习型说明：这里可以读取 staged 目录里的旧候选文件来生成 diff lines，
    但不能读取或修改正式 vault notes。CLI 只负责把这些行渲染成 Rich 输出。
    """

    existing_path: Path
    exists: bool
    has_changes: bool
    diff_lines: tuple[str, ...]
    truncated_count: int
    manual_inspection_hint: str


@dataclass(frozen=True)
class PreflightDisplayPlan:
    """preflight 结果的展示决策。

    中文学习型说明：PASS/BLOCKED/WARNING 的聚合已经由 preflight service 完成；
    这里仅把结构化状态映射为下一步建议和 no-write 边界，避免 CLI 命令里散落
    判断分支。它不执行 write gate，也不读取 `.env` 或调用 LLM。
    """

    status: str
    outcome_message: str
    next_action: str
    future_gate: str
    no_write_boundary: str
    exit_code: int


@dataclass(frozen=True)
class ObsidianDogfoodCommand:
    command: str
    note: str


@dataclass(frozen=True)
class ObsidianNextPlan:
    """Obsidian dogfooding next-action 的结构化状态。

    中文学习型说明：`obsidian next` 是导航，不是 runner。service 只计算当前
    staged export/manifest 状态和推荐下一步，CLI 负责输出；这里不会创建目录、
    不写 vault，也不会把 preflight 误当成 apply。
    """

    vault_root: Path
    output_dir: Path
    source_hint: str
    vault_exists: bool
    staged_export_count: int
    manifest_count: int
    latest_manifest: Path | None
    recommended_next: str
    commands: tuple[ObsidianDogfoodCommand, ...]
    safety_line: str
    boundary_line: str


def safe_relative_to(path: Path, root: Path) -> str | None:
    """返回 path 相对 root 的 posix 路径，越界时返回 None。

    中文学习型说明：Obsidian 集成大量处理用户手输路径。service 层用这个
    helper 明确表达"路径是否在 vault 内"，避免 CLI 直接拼字符串时误把外部
    文件当成 vault note。这里不读取文件内容，也不写任何路径。
    """
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def first_markdown_hint(vault_root: Path) -> str:
    """返回可用于 dry-run 示例的第一个 Markdown note；不读取正文。"""
    for path in sorted(vault_root.rglob("*.md")):
        if path.is_file():
            rel = safe_relative_to(path, vault_root)
            return rel or str(path)
    return "<note.md>"


def resolve_obsidian_source_for_preview(source: Path, vault_root: Path) -> Path:
    """解析 stage source，兼容 cwd 路径和 vault 内相对路径。

    中文学习型说明：这是 stage/dry-run 的输入路径规范化，不代表允许处理
    vault 外部文件；调用方仍要用 ``safe_relative_to`` 做 vault 边界判断。
    """
    raw = source.expanduser()
    if raw.is_absolute():
        return raw.resolve()
    cwd_candidate = raw.resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (vault_root / raw).resolve()


def obsidian_export_filename(doc: Any) -> str:
    """生成 staged export 文件名；仅用于人工检查目录，不是正式 note 路径。"""
    title = doc.title or Path(doc.source_path).stem
    slug = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", title).strip("-")
    return (slug or "obsidian-candidate") + ".md"


def unique_export_path(path: Path) -> Path:
    """返回不会覆盖已有 staged 文件的路径。

    中文学习型说明：staged export 是人工检查目录，不是正式 vault 写入通道。
    遇到同名文件时生成唯一文件名，而不是覆盖或自动合并，避免把人的检查
    结果变成机器状态。
    """
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for idx in range(2, 10_000):
        candidate = path.with_name(f"{stem}-{idx}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"无法生成唯一 staged export 文件名：{path}")


def staged_export_dir(cfg: MindForgeConfig, output_dir: Path | None) -> Path:
    """解析 staged export 目录；用户显式路径优先，否则走本地 state workdir。"""
    if output_dir is not None:
        return output_dir.expanduser().resolve()
    return (cfg.state.workdir / "staged" / "obsidian").expanduser().resolve()


def formal_note_conflict_paths(vault_root: Path, filename: str) -> tuple[Path, ...]:
    """报告正式 vault 中可能冲突的同名 note，不覆盖、不迁移、不 apply。"""
    conflicts: list[Path] = []
    for path in vault_root.rglob(filename):
        if not path.is_file():
            continue
        rel = safe_relative_to(path, vault_root)
        if rel is None:
            continue
        if rel.startswith(".mindforge/") or rel.startswith("90-System/MindForge/"):
            continue
        conflicts.append(path)
    return tuple(sorted(conflicts))


def plan_staged_export(
    *,
    cfg: MindForgeConfig,
    vault_root: Path,
    doc: Any,
    output_dir: Path | None,
) -> StagedExportPlan:
    """生成 staged export 写入计划，但不创建目录、不写文件。

    中文学习型说明：这个 helper 是 CLI/service 边界的核心切片。它把"候选
    输出路径、manifest 路径、未来 proposed target、backup path、冲突提示"
    这些业务事实集中起来；CLI 仍然负责真正写 staged 文件和渲染提示。
    """
    export_dir = staged_export_dir(cfg, output_dir)
    filename = obsidian_export_filename(doc)
    proposed = export_dir / filename
    target = unique_export_path(proposed)
    proposed_target = (vault_root / cfg.obsidian.review_dir / target.name).resolve()
    backup_path = (cfg.state.workdir / "backups" / "obsidian" / target.name).expanduser().resolve()
    return StagedExportPlan(
        export_dir=export_dir,
        proposed_path=proposed,
        target_path=target,
        manifest_path=target.with_suffix(".manifest.json"),
        proposed_target=proposed_target,
        backup_path=backup_path,
        action="staged-export-create" if target == proposed else "staged-export-create-unique",
        output_policy="explicit-output-dir" if output_dir is not None else "default-state-workdir",
        formal_conflicts=formal_note_conflict_paths(vault_root, target.name),
    )


def build_staged_diff_preview_plan(
    existing: Path,
    proposed_content: str,
    *,
    max_lines: int = 80,
) -> DiffPreviewPlan:
    """生成 staged-only diff plan，不写正式 notes。

    中文学习型说明：diff preview 是人工检查 staged export 的辅助材料，不是
    apply/write。这里最多读取 staged 目录的旧候选文件，用统一 diff 描述差异；
    CLI 再决定如何打印。
    """
    path = existing.expanduser().resolve()
    if not path.exists():
        return DiffPreviewPlan(
            existing_path=path,
            exists=False,
            has_changes=True,
            diff_lines=(),
            truncated_count=0,
            manual_inspection_hint="manual inspection: after export, open the staged markdown and manifest before preflight.",
        )
    old_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = proposed_content.splitlines(keepends=True)
    diff = tuple(
        line.rstrip("\n")
        for line in difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=str(path),
            tofile="proposed",
            n=3,
        )
    )
    return DiffPreviewPlan(
        existing_path=path,
        exists=True,
        has_changes=bool(diff),
        diff_lines=diff[:max_lines],
        truncated_count=max(0, len(diff) - max_lines),
        manual_inspection_hint="manual inspection: review this staged-only diff, then run obsidian preflight on the manifest.",
    )


def build_preflight_display_plan(result: Any) -> PreflightDisplayPlan:
    """把 preflight 结构化状态转换成 CLI 可渲染的 next-action 数据。"""
    future_gate = "staged export -> diff preview -> backup -> explicit confirmation"
    next_action = "Next: manually inspect the staged markdown and diff; future write requires explicit confirmation."
    no_write = "说明：本版本不会写正式 Obsidian notes，不会读取 .env，不会调用真实 LLM。"
    status = str(result.status)
    if status == "PASS":
        message = "PASS: staged export is ready for manual inspection."
        exit_code = 0
    elif status == "WARNING":
        message = "WARNING: inspect conflicts manually before any future confirmation."
        exit_code = 0
    else:
        message = "BLOCKED: staged export is not ready for any future write gate."
        exit_code = 2
    return PreflightDisplayPlan(
        status=status,
        outcome_message=message,
        next_action=next_action,
        future_gate=future_gate,
        no_write_boundary=no_write,
        exit_code=exit_code,
    )


def obsidian_dogfood_command_snippets(
    vault: Path,
    source_hint: str,
    output_dir: Path,
) -> tuple[ObsidianDogfoodCommand, ...]:
    """集中维护 Obsidian dogfooding 命令，防止 CLI 与 docs/checklist 漂移。

    中文学习型说明：这些 snippets 是人工 dogfooding 导航，不是自动 runner。
    它们刻意停在 preflight/manual inspection，避免把未来 write gate 误写成
    当前已实现的正式 Obsidian note 写入能力。
    """
    v = str(vault)
    source = source_hint
    out = str(output_dir)
    manifest = str(output_dir / "<export>.manifest.json")
    return (
        ObsidianDogfoodCommand(f"mindforge obsidian doctor --vault {v}", "检查 vault 边界和 staged export 状态"),
        ObsidianDogfoodCommand(f"mindforge obsidian scan --vault {v} --limit 20", "只读扫描 Markdown 安全摘要"),
        ObsidianDogfoodCommand(f"mindforge obsidian links --vault {v}", "只读解析 [[wikilinks]]，不建 graph/RAG"),
        ObsidianDogfoodCommand(f"mindforge obsidian stage --vault {v} --source {source} --dry-run", "预览候选，不写任何文件"),
        ObsidianDogfoodCommand(
            f"mindforge obsidian stage --vault {v} --source {source} --staged-export "
            f"--output-dir {out} --diff --write --confirm",
            "写 staged export + manifest；仍不写正式 notes",
        ),
        ObsidianDogfoodCommand(
            f"mindforge obsidian preflight --vault {v} --manifest {manifest}",
            "检查未来 write-gate 证据链；BLOCKED/WARNING/PASS 后仍需人工检查",
        ),
    )


def build_obsidian_next_plan(
    *,
    vault_root: Path,
    output_dir: Path,
    source_hint: str | None = None,
) -> ObsidianNextPlan:
    """计算 `obsidian next` 的当前状态与推荐下一步，不执行任何命令。"""
    root = vault_root.expanduser().resolve()
    resolved_output = output_dir.expanduser()
    hint = source_hint or (first_markdown_hint(root) if root.exists() else "<note.md>")
    staged_files = sorted(resolved_output.glob("*.md")) if resolved_output.exists() else []
    manifests = sorted(resolved_output.glob("*.manifest.json")) if resolved_output.exists() else []
    latest_manifest = manifests[-1] if manifests else None
    if latest_manifest is not None:
        recommended = f"mindforge obsidian preflight --vault {root} --manifest {latest_manifest}"
    else:
        recommended = "run stage --dry-run, then staged-export --diff --write --confirm"
    return ObsidianNextPlan(
        vault_root=root,
        output_dir=output_dir,
        source_hint=hint,
        vault_exists=root.exists(),
        staged_export_count=len(staged_files),
        manifest_count=len(manifests),
        latest_manifest=latest_manifest,
        recommended_next=recommended,
        commands=obsidian_dogfood_command_snippets(root, hint, output_dir),
        safety_line="Safety: disposable non-sensitive vault copy only; no .env, no real LLM, no formal note writes.",
        boundary_line="Boundary: dry-run/staged-export/diff/preflight/manual inspection only; no apply command in this version.",
    )


def build_staged_manifest_payload(
    *,
    plan: StagedExportPlan,
    source_path: Path,
    doc: Any,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """构建 staged export manifest；payload 声明 no-write / no-env / no-LLM 边界。"""
    ts = timestamp or datetime.now(timezone.utc)
    return {
        "version": 1,
        "source_note": doc.source_path,
        "source_file": str(source_path),
        "staged_markdown": str(plan.target_path),
        "proposed_file": str(plan.target_path),
        "action": plan.action,
        "timestamp": ts.isoformat(),
        "mode": "staged_export",
        "dry_run": False,
        "staged_export_dir": str(plan.export_dir),
        "staged_output_policy": plan.output_policy,
        "safety": {
            "no_formal_obsidian_note_write": True,
            "no_real_llm": True,
            "no_env_read": True,
            "no_telemetry_upload": True,
            "no_runtime_logs_or_index_in_export": True,
        },
        "write_gate": {
            "proposed_target": str(plan.proposed_target),
            "backup_path": str(plan.backup_path),
            "recovery_plan": "restore backup_path, keep staged_markdown unchanged, then rerun preflight",
            "explicit_confirmation_required": True,
            "diff_preview_required": True,
            "writes_formal_notes_now": False,
        },
    }
