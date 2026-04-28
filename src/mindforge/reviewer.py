"""M4 — review mark：把卡片复习结果记录到 frontmatter。

设计契约（详见 docs/M4_RECALL_REVIEW_PROTOCOL.md §4 / §8）

1. ``mindforge review mark`` 是 review 字段的**唯一**写入口（沿用 M3
   "审计入口必须唯一"原则）。
2. 仅修改 4 个字段：``reviewed_at`` / ``review_count`` /
   ``last_review_result`` / ``review_after``。卡片正文与其他 frontmatter
   字段 byte 级不变。
3. **不**改 ``status`` 字段——保护 M3 反 AI 污染闸门。
4. 不调 LLM、不需 .env、不改源文件、不改 state.json。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import yaml

from .config import MindForgeConfig

ReviewResult = Literal["remembered", "partial", "forgotten"]
_VALID_RESULTS: tuple[str, ...] = ("remembered", "partial", "forgotten")


class ReviewError(Exception):
    """review mark 业务错误；CLI 据此映射 exit code。"""

    def __init__(self, message: str, *, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class ReviewOutcome:
    card_path: Path
    result: ReviewResult
    prev_review_count: int
    new_review_count: int
    reviewed_at: datetime
    review_after: datetime


def mark_card_review(
    card_path: Path,
    result: str,
    *,
    cfg: MindForgeConfig,
) -> ReviewOutcome:
    """把一次 review 结果写入卡片 frontmatter，返回 ReviewOutcome。

    失败抛 ReviewError（含 exit_code）。
    """
    if result not in _VALID_RESULTS:
        raise ReviewError(
            f"--result 必须是 {_VALID_RESULTS} 之一，得到 {result!r}",
            exit_code=3,
        )
    if not card_path.exists() or not card_path.is_file():
        raise ReviewError(f"卡片文件不存在：{card_path}", exit_code=2)

    raw = card_path.read_text(encoding="utf-8")
    fm_text, body = _split_frontmatter(raw)

    try:
        data = yaml.safe_load(fm_text)
    except yaml.YAMLError as e:
        raise ReviewError(f"frontmatter YAML 解析失败：{e}", exit_code=3) from e
    if not isinstance(data, dict):
        raise ReviewError("frontmatter 顶层必须是 mapping", exit_code=3)
    # 即便不严格要求 status，但若字段非法（不是字符串）也归类为损坏
    if "status" in data and not isinstance(data["status"], str):
        raise ReviewError(
            f"status 字段类型异常：{type(data['status']).__name__}", exit_code=3
        )

    # 计算新值
    interval_days = _interval_for(cfg, result)
    now = datetime.now(timezone.utc).astimezone()
    review_after = now + timedelta(days=interval_days)
    prev_count = _safe_int(data.get("review_count")) or 0
    new_count = prev_count + 1

    data["reviewed_at"] = now.isoformat(timespec="seconds")
    data["review_count"] = new_count
    data["last_review_result"] = result
    data["review_after"] = review_after.isoformat(timespec="seconds")

    new_fm_text = yaml.safe_dump(
        data, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    _atomic_write(card_path, _join_frontmatter(new_fm_text, body))

    return ReviewOutcome(
        card_path=card_path,
        result=result,  # type: ignore[arg-type]
        prev_review_count=prev_count,
        new_review_count=new_count,
        reviewed_at=now,
        review_after=review_after,
    )


def _interval_for(cfg: MindForgeConfig, result: str) -> int:
    iv = cfg.review.intervals
    return {
        "remembered": iv.remembered,
        "partial": iv.partial,
        "forgotten": iv.forgotten,
    }[result]


def _safe_int(v: object) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    return None


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ReviewError("卡片缺少 frontmatter（未以 '---' 开头）", exit_code=3)
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        if rest.endswith("\n---"):
            return rest[:-4], ""
        raise ReviewError("卡片 frontmatter 未闭合（缺第二个 '---'）", exit_code=3)
    return rest[:end], rest[end + len("\n---\n") :]


def _join_frontmatter(fm_text: str, body: str) -> str:
    if not fm_text.endswith("\n"):
        fm_text = fm_text + "\n"
    return f"---\n{fm_text}---\n{body}"


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


__all__ = ["ReviewError", "ReviewOutcome", "ReviewResult", "mark_card_review"]
