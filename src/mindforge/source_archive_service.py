"""Processed source archive service.

中文学习型说明：Source 是原始证据，Card 是加工结果。本服务只在显式 approve
成功后运行，把仍位于待处理 Inbox 的 source 移入
``00-Inbox/_processed/<adapter-subdir>/`` 并写回 card provenance。

边界：
- process / ai_draft 阶段不调用这里；
- 不删除 source，不覆盖已有 archive；
- vault 外部 source 不移动，只记录 external；
- 不读取 source 正文，只做路径与 frontmatter metadata 操作。
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .approver import ApprovalError
from .config import MindForgeConfig


@dataclass(frozen=True)
class SourceArchiveEffect:
    kind: str
    source_path: Path | None
    archive_path: Path | None
    message: str

    @property
    def archived(self) -> bool:
        return self.kind == "archived"


def archive_source_for_approved_card(
    cfg: MindForgeConfig,
    card_path: Path,
) -> SourceArchiveEffect:
    """为已批准 card 归档原始 source，并写回 provenance frontmatter。"""
    raw = card_path.read_text(encoding="utf-8")
    fm_text, body = _split_frontmatter(raw)
    data = _load_frontmatter(fm_text)
    source_raw = _str_or_empty(data.get("source_path"))
    source_type = _str_or_empty(data.get("source_type"))
    if not source_raw:
        data["source_missing"] = True
        _write_frontmatter(card_path, data, body)
        return SourceArchiveEffect("missing", None, None, "card 没有 source_path")

    source_path = _resolve_source_path(cfg, source_raw)
    if not source_path.exists():
        data["source_missing"] = True
        data["source_archive_path"] = ""
        _write_frontmatter(card_path, data, body)
        return SourceArchiveEffect("missing", source_path, None, "source 文件不存在")

    inbox_root = cfg.vault.inbox_path.resolve()
    try:
        rel_to_inbox = source_path.resolve().relative_to(inbox_root)
    except ValueError:
        data["source_external"] = True
        data["source_missing"] = False
        data.setdefault("source_archive_path", "")
        _write_frontmatter(card_path, data, body)
        return SourceArchiveEffect("external", source_path, None, "vault 外部 source 不移动")

    if rel_to_inbox.parts and rel_to_inbox.parts[0] == "_processed":
        data["source_missing"] = False
        data["source_archive_path"] = source_path.relative_to(cfg.vault.root).as_posix()
        _write_frontmatter(card_path, data, body)
        return SourceArchiveEffect("already_archived", source_path, source_path, "source 已在 _processed")

    bucket = _archive_bucket(cfg, source_type, rel_to_inbox)
    suffix_inside_bucket = (
        Path(*rel_to_inbox.parts[1:]) if len(rel_to_inbox.parts) > 1 else Path(source_path.name)
    )
    target = cfg.vault.inbox_path / "_processed" / bucket / suffix_inside_bucket
    target = _conflict_safe_target(target, source_path=source_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(source_path, target)

    data["source_missing"] = False
    data["source_external"] = False
    data["source_archive_path"] = target.relative_to(cfg.vault.root).as_posix()
    _write_frontmatter(card_path, data, body)
    return SourceArchiveEffect("archived", source_path, target, "source 已移动到 _processed")


def _archive_bucket(cfg: MindForgeConfig, source_type: str, rel_to_inbox: Path) -> str:
    entry = cfg.sources.registry.get(source_type)
    if entry is not None and entry.inbox_subdir:
        return entry.inbox_subdir
    if rel_to_inbox.parts:
        return rel_to_inbox.parts[0]
    return source_type or "Unknown"


def _resolve_source_path(cfg: MindForgeConfig, raw: str) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return cfg.vault.root / path


def _conflict_safe_target(target: Path, *, source_path: Path) -> Path:
    if not target.exists():
        return target
    digest = hashlib.sha1(str(source_path.resolve()).encode("utf-8")).hexdigest()[:8]
    candidate = target.with_name(f"{target.stem}--{digest}{target.suffix}")
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        fallback = target.with_name(f"{target.stem}--{digest}-{counter}{target.suffix}")
        if not fallback.exists():
            return fallback
        counter += 1


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ApprovalError("卡片缺少 frontmatter（未以 '---' 开头）", exit_code=3)
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        raise ApprovalError("卡片 frontmatter 未闭合（缺第二个 '---'）", exit_code=3)
    return rest[:end], rest[end + len("\n---\n") :]


def _load_frontmatter(fm_text: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        raise ApprovalError(f"frontmatter YAML 解析失败：{exc}", exit_code=3) from exc
    if not isinstance(data, dict):
        raise ApprovalError("frontmatter 必须是 YAML 对象", exit_code=3)
    return data


def _write_frontmatter(card_path: Path, data: dict[str, Any], body: str) -> None:
    fm_text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    tmp = card_path.with_suffix(card_path.suffix + ".tmp")
    tmp.write_text(f"---\n{fm_text}---\n{body}", encoding="utf-8")
    os.replace(tmp, card_path)


def _str_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""


__all__ = ["SourceArchiveEffect", "archive_source_for_approved_card"]
