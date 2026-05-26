"""Shared schema types used across multiple domain modules.

中文学习型说明：这些基础类型被 schemas/__init__.py 中多个 domain schema 以及
services/ 层广泛引用。将它们提取到独立模块可以打破循环 import 障碍，
为后续 Review/Approval 等 domain extraction 铺路。

本模块只依赖 Python 标准库和 pydantic，不引用任何 schemas/ 子模块或 services/。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


StatusLevel = Literal["ok", "info", "warn", "error"]


class NextAction(BaseModel):
    label: str
    description: str
    command: str | None = None
    href: str | None = None
    action_key: str | None = None  # 稳定展示映射键，前端据此做本地化。可选，缺省时前端 fallback 到 label
    description_key: str | None = None  # action.description 本地化键，与 action_key 同模式。可选，缺省时前端 fallback 到原始 description


class StatusItem(BaseModel):
    key: str
    label: str
    status: StatusLevel
    value: str
    detail: str | None = None
    next_action: NextAction | None = None


class SourcePathViewModel(BaseModel):
    """后端生成的 source path 安全视图 —— 前端只展示，不做安全决策。

    中文学习型说明：path_kind 由后端根据 allowlisted roots 计算，
    前端根据 can_copy_full_path / can_reveal_in_finder 禁用按钮。
    outside_allowed_roots 时不展示完整 absolute path。
    """

    display_source_name: str | None = None
    """展示用的 source 名称（basename 或脱敏路径）。"""

    display_path: str | None = None
    """展示路径。outside 时仅显示 basename，不暴露完整路径。"""

    path_kind: Literal[
        "workspace",
        "registered_source",
        "outside_allowed_roots",
        "not_available",
        "unknown",
    ] = "unknown"
    """路径分类：workspace / registered_source / outside_allowed_roots /
    not_available / unknown。"""

    full_path_available: bool = False
    """完整 absolute path 是否对用户可见。"""

    can_copy_full_path: bool = False
    """是否允许 Copy full absolute path。"""

    can_copy_display_path: bool = False
    """是否允许 Copy display path（always true if display_path 存在）。"""

    can_reveal_in_finder: bool = False
    """是否允许 Reveal in Finder。"""

    safety_label: str | None = None
    """安全标签（如 \"Workspace\" / \"Registered Source\" / \"External\"）。"""

    warning: str | None = None
    """安全警告文案。outside 时说明路径不在 workspace 或已注册 source root 内。"""
