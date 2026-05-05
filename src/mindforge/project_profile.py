"""M5.3 — Project profile loader（**只读 frontmatter**）。

读取 ``<vault.root>/<vault.projects_dir>/<project_name>.md`` 的 frontmatter，
为 ``project context`` 命令提供项目级稳定上下文。

设计契约（详见 docs/IMPLEMENTATION.md 的 project context 说明）：

1. **只读 frontmatter**：永不读取项目笔记正文，避免误把个人草稿 / secret
   带进 context pack；
2. **缺失即降级**：文件不存在 → ``ProjectProfile(found=False)``，调用方
   自动走 cards-only 路径，不报错；
3. **零 LLM / 零 .env / 零网络**；
4. **路径安全**：拒绝 project_name 中含 ``/`` / ``..`` / 绝对路径，避免
   ``mindforge project context ../../etc/passwd`` 类穿越；
5. **frontmatter 解析失败**：归类为 ``found=False`` + ``error_message``，
   绝不把异常文本含正文片段打到 stdout / 日志。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VALID_TARGETS: frozenset[str] = frozenset(
    {"claude-code", "copilot", "codex", "generic"}
)


@dataclass(frozen=True)
class ProjectProfile:
    """项目级稳定上下文（来自 30-Projects/<name>.md frontmatter）。"""

    project_name: str
    found: bool
    rel_path: str | None
    description: str | None = None
    default_target: str | None = None
    principles: tuple[str, ...] = field(default_factory=tuple)
    known_risks: tuple[str, ...] = field(default_factory=tuple)
    preferred_workflow: tuple[str, ...] = field(default_factory=tuple)
    error_message: str | None = None


class ProjectProfileError(ValueError):
    """非降级类错误（如 project_name 不安全）。"""


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def load_project_profile(
    vault_root: Path,
    projects_dir: str,
    project_name: str,
) -> ProjectProfile:
    """加载项目 profile；找不到/解析失败 → found=False（不抛）。"""
    _validate_project_name(project_name)

    rel_path = f"{projects_dir.rstrip('/')}/{project_name}.md"
    file_path = (vault_root / projects_dir / f"{project_name}.md").resolve()

    # 路径越界二次防御：解析后必须仍在 projects_dir 之内
    projects_root = (vault_root / projects_dir).resolve()
    try:
        file_path.relative_to(projects_root)
    except ValueError as e:
        raise ProjectProfileError(
            f"project_name {project_name!r} 解析后跳出 projects_dir"
        ) from e

    if not file_path.exists() or not file_path.is_file():
        return ProjectProfile(
            project_name=project_name, found=False, rel_path=None
        )

    try:
        text = file_path.read_text(encoding="utf-8")
        fm_dict = _parse_frontmatter(text)
    except Exception as e:
        return ProjectProfile(
            project_name=project_name,
            found=False,
            rel_path=rel_path,
            error_message=f"frontmatter 解析失败：{type(e).__name__}",
        )

    default_target = _str_or_none(fm_dict.get("default_target"))
    if default_target is not None and default_target not in VALID_TARGETS:
        # 不在合法集合内 → 当作未配置；但不丢 profile 其余字段
        default_target = None

    return ProjectProfile(
        project_name=project_name,
        found=True,
        rel_path=rel_path,
        description=_str_or_none(fm_dict.get("description")),
        default_target=default_target,
        principles=_str_tuple(fm_dict.get("principles")),
        known_risks=_str_tuple(fm_dict.get("known_risks")),
        preferred_workflow=_str_tuple(fm_dict.get("preferred_workflow")),
    )


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _validate_project_name(name: str) -> None:
    if not name or not isinstance(name, str):
        raise ProjectProfileError("project_name 不能为空")
    if "/" in name or "\\" in name or ".." in name:
        raise ProjectProfileError(
            f"project_name {name!r} 含非法字符（/ \\ ..）"
        )
    if Path(name).is_absolute():
        raise ProjectProfileError(f"project_name {name!r} 不能是绝对路径")


def _parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        # 没有 frontmatter → 视为"profile 文件存在但未配置任何字段"
        return {}
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        if rest.endswith("\n---"):
            fm_text = rest[:-4]
        else:
            return {}
    else:
        fm_text = rest[:end]
    data = yaml.safe_load(fm_text)
    if not isinstance(data, dict):
        return {}
    return data


def _str_or_none(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return s or None
    return str(v)


def _str_tuple(v: Any) -> tuple[str, ...]:
    if v is None:
        return ()
    if isinstance(v, (list, tuple)):
        return tuple(str(x).strip() for x in v if x is not None and str(x).strip())
    s = str(v).strip()
    return (s,) if s else ()


__all__ = [
    "ProjectProfile",
    "ProjectProfileError",
    "VALID_TARGETS",
    "load_project_profile",
]
