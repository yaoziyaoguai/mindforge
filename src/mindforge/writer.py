"""writer — 渲染 Knowledge Card 模板并落盘。

硬约束（来自 docs/MINDFORGE_PROTOCOL.md §5）
============================================

- 卡片只写到 ``<vault>/<cards_dir>/<track>/<YYYYMMDD>--<slug>.md``。
- **不**覆盖已存在的卡片（若 hash 不同则写 ``<filename>.conflict.md``）。
- ``status: ai_draft``（由模板硬编码）。
- 原始 source 文件不被触碰（writer 只 read template + write card path）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


@dataclass(frozen=True)
class WriteResult:
    path: Path
    conflict: bool         # True = 写到了 .conflict.md，未覆盖正本


class CardWriter:
    def __init__(self, *, vault_root: Path, cards_dir: str, template_path: Path) -> None:
        self.vault_root = vault_root
        self.cards_dir = cards_dir
        self.template_path = template_path
        self._env = Environment(
            loader=FileSystemLoader(str(template_path.parent)),
            autoescape=select_autoescape(disabled_extensions=("md", "j2")),
            keep_trailing_newline=True,
        )

    def write(
        self,
        *,
        card_payload: dict[str, Any],
        source: dict[str, Any],
        run: dict[str, Any],
        now: datetime | None = None,
    ) -> WriteResult:
        now = now or datetime.now()
        track = str(card_payload["card"]["track"])
        slug = str(card_payload["card"]["id"])
        date_prefix = now.strftime("%Y%m%d")
        filename = f"{date_prefix}--{slug}.md"

        out_dir = self.vault_root / self.cards_dir / track
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename

        template = self._env.get_template(self.template_path.name)
        rendered = template.render(
            card=card_payload["card"],
            source=source,
            run=run,
        )

        # 不覆盖：如果文件已存在且内容不同，写到 .conflict.md
        conflict = False
        if out_path.exists():
            existing = out_path.read_text("utf-8")
            if existing == rendered:
                # 完全一样：当作幂等成功
                return WriteResult(path=out_path, conflict=False)
            out_path = out_path.with_suffix(".conflict.md")
            conflict = True

        out_path.write_text(rendered, encoding="utf-8")
        return WriteResult(path=out_path, conflict=conflict)


__all__ = ["CardWriter", "WriteResult"]
