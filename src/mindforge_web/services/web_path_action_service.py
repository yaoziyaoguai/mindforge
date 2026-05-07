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

    def copy_path(self, path: Path) -> PathActionResponse:
        resolved = self._validated_path(path)
        return PathActionResponse(
            ok=True,
            action="copy",
            path=str(resolved),
            path_type=_path_type(resolved),
            message="Copied",
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
