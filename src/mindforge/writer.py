"""writer — 渲染 Knowledge Card 模板并落盘。

硬约束（来自 README.md 的 Card 写入边界）
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

from jinja2 import DictLoader, Environment, FileSystemLoader, select_autoescape

from .card_envelope import normalize_card_payload_for_writer


@dataclass(frozen=True)
class WriteResult:
    path: Path
    conflict: bool         # True = 写到了 .conflict.md，未覆盖正本


class CardWriter:
    def __init__(
        self,
        *,
        vault_root: Path,
        cards_dir: str,
        template_path: Path | None = None,
        template_text: str | None = None,
        template_name: str = "knowledge_card.md.j2",
    ) -> None:
        """Create a writer from either a user template path or bundled text.

        中文学习型说明：packaged install 场景下默认模板来自 package
        resources，不一定有稳定的 repo-root ``templates/`` 路径；但用户显式
        传入 ``--template`` 时仍必须优先使用用户文件。这里保留两种入口，
        不改变 Knowledge Card 写入协议。
        """
        if template_path is None and template_text is None:
            raise ValueError("template_path 或 template_text 必须提供一个")
        self.vault_root = vault_root
        self.cards_dir = cards_dir
        self.template_path = template_path
        self.template_name = template_path.name if template_path is not None else template_name
        loader = (
            FileSystemLoader(str(template_path.parent))
            if template_path is not None
            else DictLoader({self.template_name: template_text or ""})
        )
        self._env = Environment(
            loader=loader,
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
        quality: dict[str, Any] | None = None,
    ) -> WriteResult:
        now = now or datetime.now()
        # v0.10 Slice 5：所有 strategy 输出统一公共 envelope，writer 通过
        # ``structured_payload.card`` 读取写入路径与模板字段。writer 不
        # 理解 strategy-specific keys，也不分发 strategy_id —— 这条边
        # 界由 ``test_card_writer_does_not_read_envelope_top_level_strategy_keys``
        # 守护，防止 writer 演化为多策略巨石。
        normalized_payload = normalize_card_payload_for_writer(card_payload)
        try:
            structured = normalized_payload["structured_payload"]
            card = structured["card"]
        except (KeyError, TypeError) as exc:
            raise KeyError(
                "CardWriter 期望公共 envelope 形态 "
                "(structured_payload.card)；收到的 card_payload 不符合契约"
            ) from exc
        track = str(card["track"])
        slug = str(card["id"])
        date_prefix = now.strftime("%Y%m%d")
        filename = f"{date_prefix}--{slug}.md"

        out_dir = self.vault_root / self.cards_dir / track
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename

        template = self._env.get_template(self.template_name)
        rendered = template.render(
            card=card,
            source=source,
            run=run,
            quality=quality,
        )

        # 不覆盖：如果文件已存在且内容不同，写到 .conflict.md
        conflict = False
        if out_path.exists():
            existing = out_path.read_text("utf-8")
            if existing == rendered:
                # 完全一样：当作幂等成功
                return WriteResult(path=out_path, conflict=False)
            out_path = _next_conflict_path(out_path)
            conflict = True

        out_path.write_text(rendered, encoding="utf-8")
        return WriteResult(path=out_path, conflict=conflict)


def _next_conflict_path(path: Path) -> Path:
    """为同一 source 的多次内容变化保留每个 draft 版本。

    中文学习型说明：watch 是 additive by default。源文件变更可以生成新
    ai_draft，但不能覆盖旧 draft 或已批准知识；删除/归并知识必须人工完成。
    """

    candidate = path.with_suffix(".conflict.md")
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}.conflict-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


__all__ = ["CardWriter", "WriteResult"]
