"""Prompt read-only API —— 返回当前 workflow 实际使用的 prompt 内容。

中文学习型说明：本 endpoint 只读 prompt asset，不返回 secret、不调 LLM、
不修改任何文件。prompt 内容从 packages assets 或用户 prompts 目录加载。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from mindforge.config import REQUIRED_STAGES
from mindforge.assets_runtime import asset_root
from mindforge.prompts_runtime import load_prompt

from mindforge_web.deps import get_facade
from mindforge_web.services.web_facade import WebFacade

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("/{stage}")
def get_prompt(
    stage: str,
    version: str | None = Query(None, description="Prompt version; defaults to current config version"),
    facade: WebFacade = Depends(get_facade),
) -> dict:
    """返回指定 workflow step 当前使用的 prompt 内容（只读）。"""
    # 验证 stage 是合法 workflow step
    if stage not in REQUIRED_STAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown workflow step: {stage!r}. Known steps: {list(REQUIRED_STAGES)}",
        )

    # 解析 version：优先 query param，fallback config 中的版本
    if version is None:
        try:
            version = facade.cfg.prompts.for_stage(stage)
        except Exception:
            version = "v1"

    # 加载 prompt
    try:
        prompts_dir = _resolve_prompts_dir()
        text = load_prompt(prompts_dir, stage, version)
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt not found: {stage}@{version} ({exc})",
        ) from exc

    # 尝试读 manifest
    manifest: dict | None = None
    try:
        import yaml
        manifest_path = Path(str(prompts_dir)) / stage / "manifest.yaml" if isinstance(prompts_dir, Path) else None
        if manifest_path and manifest_path.exists():
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    return {
        "stage": stage,
        "version": version,
        "content": text,
        "manifest": manifest,
    }


def _resolve_prompts_dir():
    """解析 prompts 目录：优先用户目录，fallback package assets。"""
    # 尝试项目根目录下的 prompts/
    user_prompts = Path("prompts")
    if user_prompts.exists() and (user_prompts / "triage" / "v1.md").exists():
        return user_prompts
    # fallback: package assets
    return asset_root().joinpath("prompts")
