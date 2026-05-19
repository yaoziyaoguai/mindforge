"""Secret-safe local path actions for the Web UI.

中文学习型说明：浏览器只能请求“定位已知本地路径”，不能把任意字符串变成
系统命令。这个 service 统一做 resolve、allowlist、existence check，并且
调用系统命令时始终使用参数数组与 ``shell=False``。
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from mindforge.cards import iter_cards
from mindforge.config import MindForgeConfig
from mindforge.ingestion_service import watch_sources_for_display

from mindforge_web.schemas import PathActionResponse


@dataclass(frozen=True)
class PathActionError(ValueError):
    status_code: int
    message: str


class WebPathActionService:
    def __init__(self, cfg: MindForgeConfig, *, config_path: Path) -> None:
        self.cfg = cfg
        self.config_path = config_path

    # ------------------------------------------------------------------
    # 中文学习型说明：build_source_path_view 是后端统一的 path safety 分类
    # 入口。它只接受已知对象引用的 source_path（来自已加载的 card/source），
    # 不接受任意用户输入，不做任意路径查询。
    # ------------------------------------------------------------------

    def build_source_path_view(
        self,
        source_path: str | None,
        *,
        source_title: str | None = None,
    ):
        """为已知 card/source 对象生成 path safety view model。

        Args:
            source_path: card/source 的 source_path（可能为 None）。
            source_title: 展示用的 source 名称。

        Returns:
            SourcePathViewModel with path_kind, can_copy_full_path, can_reveal_in_finder, etc.
        """
        from mindforge_web.schemas import SourcePathViewModel

        if not source_path:
            return SourcePathViewModel(
                path_kind="not_available",
                warning="No source path available.",
            )

        try:
            resolved = Path(source_path).expanduser()
            if not resolved.is_absolute():
                resolved = self.cfg.vault.root / resolved
            resolved = resolved.resolve(strict=False)
        except Exception:
            return SourcePathViewModel(
                display_source_name=source_title,
                display_path=_safe_display_path(source_path),
                path_kind="unknown",
                can_copy_display_path=True,
                safety_label="Unknown",
                warning="Could not resolve source path.",
            )

        # 分类
        if not resolved.exists():
            # 中文学习型说明：missing/not_available 不泄露存在性差异。
            # 对外统一用 not_available。
            return SourcePathViewModel(
                display_source_name=source_title or Path(source_path).name,
                display_path=_safe_display_path(source_path),
                path_kind="not_available",
                full_path_available=False,
                can_copy_display_path=True,
                can_copy_full_path=False,
                can_reveal_in_finder=False,
                safety_label="Unavailable",
                warning="Source path is not accessible.",
            )

        if self._is_allowlisted(resolved):
            # workspace 内还是 registered source？先统一为 workspace
            # —— 两者目前权限相同（允许 copy/reveal）
            return SourcePathViewModel(
                display_source_name=source_title or resolved.name,
                display_path=str(resolved),
                path_kind="workspace",
                full_path_available=True,
                can_copy_full_path=True,
                can_copy_display_path=True,
                can_reveal_in_finder=True,
                safety_label="Workspace",
            )

        # outside_allowed_roots —— 不展示完整 absolute path
        return SourcePathViewModel(
            display_source_name=source_title or resolved.name,
            display_path=resolved.name,  # 只展示 basename
            path_kind="outside_allowed_roots",
            full_path_available=False,
            can_copy_full_path=False,
            can_copy_display_path=True,  # 允许 copy basename
            can_reveal_in_finder=False,
            safety_label="External",
            warning="Path is outside allowed local MindForge roots.",
        )

    def reveal_by_ref(
        self,
        *,
        card_id: str | None = None,
        draft_id: str | None = None,
    ) -> PathActionResponse:
        """安全的 object-reference reveal —— 不接受 raw path。

        中文学习型说明：前端传 card_id 或 draft_id，后端自行查找对象、
        重新构建 source_path_view 判断权限，再执行 reveal。
        这是 source path safety 的唯一 reveal 入口。
        """
        if not card_id and not draft_id:
            raise ValueError("card_id or draft_id is required")

        source_path: str | None = None
        source_title: str | None = None

        # 查找 card
        if card_id:
            scan = iter_cards(self.cfg.vault.root, self.cfg.vault.cards_dir)
            for card in scan.cards:
                if card.id == card_id or card.rel_path == card_id:
                    source_path = card.source_path
                    source_title = card.source_title
                    break
            if source_path is None:
                raise PathActionError(404, "Card not found.")

        # 查找 draft
        if draft_id:
            from mindforge.approval_service import (
                ApprovalListQuery,
                list_approval_candidates,
            )
            result = list_approval_candidates(
                self.cfg, ApprovalListQuery(statuses=("ai_draft",), limit=200),
            )
            for card in result.candidates:
                if card.id == draft_id or card.rel_path == draft_id:
                    source_path = card.source_path
                    source_title = card.source_title
                    break
            if source_path is None:
                raise PathActionError(404, "Draft not found.")

        # 通过 view model 校验权限
        view = self.build_source_path_view(source_path, source_title=source_title)
        if not view.can_reveal_in_finder:
            raise PathActionError(
                403,
                "Reveal is not allowed for this path."
                + (f" ({view.warning})" if view.warning else ""),
            )

        # 执行 reveal
        resolved = Path(source_path).expanduser()  # type: ignore[arg-type]
        if not resolved.is_absolute():
            resolved = self.cfg.vault.root / resolved
        resolved = resolved.resolve(strict=False)

        if sys.platform != "darwin":
            return PathActionResponse(
                ok=False,
                action="reveal",
                path=str(resolved),
                path_type=_path_type(resolved),
                message="Reveal in Finder is available on macOS only.",
                path_kind=view.path_kind,
            )

        command = ["open", str(resolved)] if resolved.is_dir() else ["open", "-R", str(resolved)]
        subprocess.run(command, check=False, shell=False)
        return PathActionResponse(
            ok=True,
            action="reveal",
            path=str(resolved),
            path_type=_path_type(resolved),
            message="Opened",
            command=command,
            path_kind=view.path_kind,
        )

    def copy_path(self, path: Path) -> PathActionResponse:
        resolved = self._validated_path(path)
        return PathActionResponse(
            ok=True,
            action="copy",
            path=str(resolved),
            path_type=_path_type(resolved),
            message="Copied",
            path_kind=_classify_resolved(resolved, self._allowlisted_roots()),
        )

    def reveal_path(self, path: Path) -> PathActionResponse:
        resolved = self._validated_path(path)
        if sys.platform != "darwin":
            return PathActionResponse(
                ok=False,
                action="reveal",
                path=str(resolved),
                path_type=_path_type(resolved),
                message="Reveal in Finder is available on macOS only. Copy path instead.",
                path_kind=_classify_resolved(resolved, self._allowlisted_roots()),
            )

        command = ["open", str(resolved)] if resolved.is_dir() else ["open", "-R", str(resolved)]
        subprocess.run(command, check=False, shell=False)
        return PathActionResponse(
            ok=True,
            action="reveal",
            path=str(resolved),
            path_type=_path_type(resolved),
            message="Opened",
            command=command,
            path_kind=_classify_resolved(resolved, self._allowlisted_roots()),
        )

    def _validated_path(self, path: Path) -> Path:
        candidate = path.expanduser()
        if not candidate.is_absolute():
            candidate = self.cfg.vault.root / candidate
        resolved = candidate.resolve(strict=False)
        if not self._is_allowlisted(resolved):
            raise PathActionError(403, "Path is outside allowed local MindForge roots.")
        if not resolved.exists():
            raise PathActionError(404, "Path does not exist.")
        return resolved

    def _is_allowlisted(self, resolved: Path) -> bool:
        return any(_contains(root, resolved) for root in self._allowlisted_roots())

    def _allowlisted_roots(self) -> list[Path]:
        roots = [
            self.cfg.vault.root,
            self.config_path.parent,
            self.cfg.vault.cards_path,
        ]
        roots.extend(source.path for source in watch_sources_for_display(self.cfg))
        roots.extend(card.path for card in iter_cards(self.cfg.vault.root, self.cfg.vault.cards_dir).cards)
        return [root.expanduser().resolve(strict=False) for root in roots]


def _classify_resolved(resolved: Path, allowlisted_roots: list[Path]) -> str:
    """安全分类已解析路径，返回 path_kind literal。

    中文学习型说明：_validated_path 已验证 allowlist + existence，
    此处仅做最终分类标记，保证 copy/reveal response 携带 path_kind。
    """
    if not resolved.exists():
        return "not_available"
    if any(_contains(root, resolved) for root in allowlisted_roots):
        return "workspace"
    return "outside_allowed_roots"


def _safe_display_path(raw: str) -> str:
    """从原始路径字符串提取安全的展示名（basename）。

    中文学习型说明：outside_allowed_roots 时不暴露完整 absolute path，
    仅返回 basename 供前端展示。
    """
    try:
        return Path(raw).name or raw
    except Exception:
        return raw or "unknown"


def _contains(root: Path, candidate: Path) -> bool:
    if candidate == root:
        return True
    if root.is_file():
        return False
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _path_type(path: Path) -> str:
    return "folder" if path.is_dir() else "file"
