"""Obsidian staged-export manifest 校验策略。

中文学习边界：
- 本模块只承担"manifest 证据是否完整、是否合法"这一类纯策略检查。
- 不读 ``.env``、不读 manifest 之外的文件、不写文件、不调 LLM、不发 HTTP。
- 不知道 Typer / Rich / CLI 的存在，也不知道 RunLogger / Checkpoint 的存在。
- 公共入口（``obsidian_preflight``）保留在 ``mindforge.obsidian`` 作为 facade，
  这里只导出 helper 函数；外部测试和调用方应继续从 ``mindforge.obsidian``
  导入 ``obsidian_preflight`` / ``ObsidianPreflightResult``。
- 抽出来的目的：把"安全 manifest 必须包含哪些证据/边界"这一组语义集中到一
  处，避免它们与 vault scanning / load issue / slug 等无关职责互相耦合。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .safety_policy import OBSIDIAN_MANIFEST_SAFETY_LABELS, forbidden_derived_parts


def manifest_path_value(payload: dict[str, Any], *keys: str) -> Path | None:
    """按顺序在 manifest 顶层取第一个非空字符串字段并 resolve 成绝对路径。"""

    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return Path(value).expanduser().resolve()
    return None


def manifest_write_gate_path(payload: dict[str, Any], key: str) -> Path | None:
    """从 manifest.write_gate 子结构中取一个绝对路径。"""

    write_gate = payload.get("write_gate")
    if not isinstance(write_gate, dict):
        return None
    value = write_gate.get(key)
    if isinstance(value, str) and value.strip():
        return Path(value).expanduser().resolve()
    return None


def require_manifest_value(
    payload: dict[str, Any],
    keys: tuple[str, ...],
    label: str,
    blocked: list[str],
) -> None:
    """断言 manifest 顶层至少有一个 key 提供了非空证据，否则记入 ``blocked``。"""

    if not any(
        key in payload and payload.get(key) not in (None, "", {}) for key in keys
    ):
        blocked.append(f"manifest 缺少 {label}")


def _is_within(path: Path, parent: Path) -> bool:
    """5 行的 path-within 判断。

    与 ``mindforge.obsidian._is_relative_to`` 行为一致：故意不反向 import
    ``mindforge.obsidian``，避免 facade ↔ policy 的循环依赖。
    """

    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def check_staged_output_policy(
    *,
    payload: dict[str, Any],
    staged_markdown: Path,
    manifest: Path,
    default_staged_root: Path,
    blocked: list[str],
) -> None:
    """根据 manifest 声明的 staged_output_policy 校验 staged markdown 落点。"""

    policy = str(payload.get("staged_output_policy") or "")
    if policy == "explicit-output-dir":
        if staged_markdown.parent != manifest.parent:
            blocked.append(
                "explicit output-dir 下 manifest 与 staged markdown 必须在同一目录"
            )
        return
    if policy != "default-state-workdir":
        blocked.append("manifest 缺少 staged_output_policy")
        return
    manifest_root = manifest_path_value(payload, "staged_export_dir") or default_staged_root
    if not _is_within(staged_markdown, manifest_root):
        blocked.append(f"default staged output 必须位于 {manifest_root}")


def check_safety_boundary(payload: dict[str, Any], blocked: list[str]) -> None:
    """校验 manifest.safety 完整声明所有受保护边界。"""

    safety = payload.get("safety")
    if not isinstance(safety, dict):
        blocked.append("manifest.safety 必须是 object")
        return
    for key, label in OBSIDIAN_MANIFEST_SAFETY_LABELS.items():
        if safety.get(key) is not True:
            blocked.append(f"manifest.safety 必须声明 {label}")


def check_no_forbidden_machine_parts(
    path: Path, label: str, blocked: list[str]
) -> None:
    """禁止 staged/proposed 路径触及机器派生层（cache/index/vector 等）。"""

    bad = forbidden_derived_parts(path)
    if bad:
        blocked.append(f"{label} 包含禁止的机器派生层路径：{', '.join(bad)}")


__all__ = [
    "check_no_forbidden_machine_parts",
    "check_safety_boundary",
    "check_staged_output_policy",
    "manifest_path_value",
    "manifest_write_gate_path",
    "require_manifest_value",
]
