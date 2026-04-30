"""Obsidian dogfooding workflow / next-action service。

中文学习型说明：本模块只计算 `mindforge obsidian next` 需要展示的结构化
状态与下一步建议。它不依赖 Typer / Rich，不读取 `.env`，不调用 LLM，不做
RAG/embedding，也不会创建目录或写正式 Obsidian notes。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .safety_policy import OBSIDIAN_WORKFLOW_BOUNDARY_LINE, OBSIDIAN_WORKFLOW_SAFETY_LINE


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
    safe_mode_line: str
    manual_inspection_steps: tuple[str, ...]


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
    hint = source_hint or (_first_markdown_hint(root) if root.exists() else "<note.md>")
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
        safety_line=OBSIDIAN_WORKFLOW_SAFETY_LINE,
        boundary_line=OBSIDIAN_WORKFLOW_BOUNDARY_LINE,
        safe_mode_line="dry-run/staged-export/preflight only",
        manual_inspection_steps=(
            "Inspect staged markdown and manifest by hand.",
            "Confirm backup expectations before any future write gate.",
            "Record unclear output in docs/templates/OBSIDIAN_DOGFOODING_CHECKLIST.md.",
        ),
    )


def _first_markdown_hint(vault_root: Path) -> str:
    """返回可用于 dry-run 示例的第一个 Markdown note；不读取正文。"""
    for path in sorted(vault_root.rglob("*.md")):
        if path.is_file():
            rel = _safe_relative_to(path, vault_root)
            return rel or str(path)
    return "<note.md>"


def _safe_relative_to(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
