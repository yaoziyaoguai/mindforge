"""Prompt asset visibility CLI.

中文学习型说明：本模块只把 package 内置 prompt asset 以只读方式展示给
用户。它不编辑 prompt、不读取 ``.env``、不构造 provider，也不执行任何
strategy；prompt visibility 和 LLM execution 保持完全分离。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import typer
import yaml

from .assets_runtime import asset_root
from .cli_runtime import console

PROMPT_STAGES: tuple[str, ...] = (
    "triage",
    "distill",
    "link_suggestion",
    "review_questions",
    "action_extraction",
)

prompts_app = typer.Typer(
    add_completion=False,
    help="查看内置 prompt assets（只读；不编辑、不调用 LLM）。",
)


@dataclass(frozen=True)
class PromptAsset:
    stage: str
    version: str
    description: str
    input_variables: tuple[str, ...]
    notes: str


@prompts_app.command("list")
def prompts_list() -> None:
    """列出内置 prompt 的 stage / version / manifest 摘要。"""

    for asset in _iter_prompt_assets():
        console.print(f"[bold]{asset.stage}[/bold]@{asset.version}")
        console.print(f"  description: {_one_line(asset.description)}")
        if asset.input_variables:
            console.print(f"  input_variables: {', '.join(asset.input_variables)}")


@prompts_app.command("show")
def prompts_show(
    ref: str = typer.Argument(..., help="prompt stage 或 stage@version，例如 triage@v1。"),
) -> None:
    """展示单个内置 prompt 的 manifest 信息与 prompt 内容。"""

    stage, version = _parse_prompt_ref(ref)
    try:
        asset = _load_prompt_asset(stage, version)
        body = _prompt_text(stage, version)
    except ValueError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(code=2) from None
    console.print(f"stage: {asset.stage}")
    console.print(f"version: {asset.version}")
    console.print(f"description: {asset.description.rstrip()}")
    if asset.input_variables:
        console.print("input_variables:")
        for name in asset.input_variables:
            console.print(f"  - {name}")
    if asset.notes:
        console.print(f"notes: {asset.notes.rstrip()}")
    console.print("\n--- prompt content ---")
    console.print(body, markup=False)


def _iter_prompt_assets() -> tuple[PromptAsset, ...]:
    return tuple(_load_prompt_asset(stage, "v1") for stage in PROMPT_STAGES)


def _load_prompt_asset(stage: str, version: str) -> PromptAsset:
    if stage not in PROMPT_STAGES:
        raise ValueError(
            f"unknown prompt stage: {stage!r}; available: {PROMPT_STAGES}; "
            "run `mindforge prompts list`."
        )
    manifest_resource = asset_root().joinpath("prompts", stage, "manifest.yaml")
    if not manifest_resource.is_file():
        raise ValueError(f"prompt manifest not found for stage {stage!r}")
    manifest = yaml.safe_load(manifest_resource.read_text(encoding="utf-8")) or {}
    if not isinstance(manifest, dict):
        raise ValueError(f"prompt manifest for stage {stage!r} must be a mapping")
    actual_version = str(manifest.get("version") or "")
    if actual_version != version:
        raise ValueError(
            f"prompt {stage}@{version} not found; available version: {actual_version or '(unknown)'}"
        )
    return PromptAsset(
        stage=str(manifest.get("stage") or stage),
        version=actual_version,
        description=str(manifest.get("description") or "").strip(),
        input_variables=_string_tuple(manifest.get("input_variables")),
        notes=str(manifest.get("notes") or "").strip(),
    )


def _prompt_text(stage: str, version: str) -> str:
    resource = asset_root().joinpath("prompts", stage, f"{version}.md")
    if not resource.is_file():
        raise ValueError(f"prompt body not found: {stage}@{version}")
    return resource.read_text(encoding="utf-8")


def _parse_prompt_ref(ref: str) -> tuple[str, str]:
    text = ref.strip()
    if not text:
        raise ValueError("prompt ref must not be empty")
    if "@" not in text:
        return text, "v1"
    stage, version = text.split("@", 1)
    return stage.strip(), version.strip() or "v1"


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def _one_line(text: str) -> str:
    return " ".join(text.split())


__all__ = ["prompts_app"]
