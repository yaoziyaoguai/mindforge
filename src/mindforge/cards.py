"""M4 — Knowledge Card 只读读取层。

设计契约（详见 README.md 的 cards / recall 说明）：

1. **只读**。本模块永远不写卡片、不写 source、不写 state.json。
2. **白名单字段**。CardSummary 仅含 §5.3 安全字段；卡片正文段落由调用方
   按需通过 ``read_card_body`` / ``extract_section`` 取出，不进入摘要结构。
3. **损坏鲁棒**。frontmatter 损坏的卡片 → 返回 ``CardLoadError`` 列表，
   主流程不崩溃；**绝不**把出错卡片正文打印到 stdout / 日志。
4. **零依赖**。不调 LLM、不读 .env、不读 state.json / runs。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass(frozen=True)
class CardSummary:
    """单张 Knowledge Card 的安全摘要（白名单字段）。"""

    id: str | None
    title: str | None
    path: Path                  # 绝对路径
    rel_path: str               # 相对 vault.root 的 posix 字符串
    status: str
    track: str | None
    projects: tuple[str, ...]
    tags: tuple[str, ...]
    source_type: str | None
    wiki_sections: tuple[str, ...] = ()
    source_id: str | None = None
    adapter_name: str | None = None
    source_path: str | None = None
    source_title: str | None = None
    source_url: str | None = None
    source_content_hash: str | None = None
    source_archive_path: str | None = None
    source_missing: bool = False
    value_score: int | None = None
    created_at: datetime | None = None
    # M3 approval 字段（approver 写入 approved_at；旧卡片可能只有 reviewed_at）
    approved_at: datetime | None = None
    # M4 review 字段（缺失按默认值）
    reviewed_at: datetime | None = None
    review_count: int = 0
    last_review_result: str | None = None
    review_after: datetime | None = None
    # M4.1：文件 mtime（仅用作 sort key，不参与 keyword 搜索）
    updated_at: datetime | None = None
    # M5.3：卡片级结构化补充字段（项目 profile 永远优先；这里只做补充）
    principles: tuple[str, ...] = ()
    known_risks: tuple[str, ...] = ()
    profile: str | None = None
    provider: str | None = None
    strategy_id: str | None = None
    strategy_version: str | None = None
    schema_version: str | None = None
    prompt_version: str | None = None
    prompt_versions: dict[str, str] = field(default_factory=dict)
    stage_models: dict[str, Any] = field(default_factory=dict)
    run_id: str | None = None
    source_location_index: int | None = None


@dataclass(frozen=True)
class CardLoadError:
    path: Path
    rel_path: str
    reason: str   # 简短原因；不含正文内容


@dataclass(frozen=True)
class CardScanResult:
    cards: tuple[CardSummary, ...] = field(default_factory=tuple)
    errors: tuple[CardLoadError, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def iter_cards(vault_root: Path, cards_dir_rel: str) -> CardScanResult:
    """扫描 vault_root / cards_dir_rel 下所有 .md 卡片，返回 (CardSummary, errors)。

    - 仅扫 .md 文件；
    - 隐藏文件 / .conflict.md 卡片跳过（不当成正常卡片）；
    - frontmatter 损坏的文件归入 errors，不入 cards。
    """
    cards_root = (vault_root / cards_dir_rel).resolve()
    if not cards_root.exists() or not cards_root.is_dir():
        return CardScanResult()

    summaries: list[CardSummary] = []
    errors: list[CardLoadError] = []
    for md in sorted(cards_root.rglob("*.md")):
        if md.name.startswith("."):
            continue
        if md.name.endswith(".conflict.md"):
            continue
        try:
            summary = _load_summary(md, vault_root)
        except _CardError as e:
            rel = _safe_rel(md, vault_root)
            errors.append(CardLoadError(path=md, rel_path=rel, reason=str(e)))
            continue
        summaries.append(summary)
    return CardScanResult(cards=tuple(summaries), errors=tuple(errors))


def read_card_frontmatter(card_path: Path) -> dict[str, Any]:
    """返回卡片 frontmatter 的 dict；损坏抛 CardLoadValueError。

    与 iter_cards 不同：本函数不吞错误，给写命令（review mark）使用。
    """
    raw = card_path.read_text(encoding="utf-8")
    fm_text, _body = _split_frontmatter(raw)
    try:
        data = yaml.safe_load(fm_text)
    except yaml.YAMLError as e:
        raise CardLoadValueError(f"frontmatter YAML 解析失败：{e}") from e
    if not isinstance(data, dict):
        raise CardLoadValueError("frontmatter 顶层必须是 YAML 对象")
    return data


def read_card_body(card_path: Path) -> str:
    """返回卡片 frontmatter 之后的正文部分。"""
    raw = card_path.read_text(encoding="utf-8")
    _fm, body = _split_frontmatter(raw)
    return body


def extract_section(body: str, section_title: str) -> str | None:
    """从 markdown body 抽取一个二级标题（## ...）下的内容。

    匹配规则：精确匹配 ``## <section_title>`` 一行（不区分大小写、忽略
    首尾空格）。返回该段直到下一个二级标题（或文末）的内容，已 strip。
    若找不到返回 None。
    """
    lines = body.splitlines()
    target = section_title.strip().lower()
    start = -1
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("## "):
            head = s[3:].strip().lower()
            if head == target:
                start = i + 1
                break
    if start == -1:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        s = lines[j].strip()
        if s.startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end]).strip() or None


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


class _CardError(Exception):
    pass


class CardLoadValueError(ValueError):
    """供外部捕获的卡片加载错误（read_card_frontmatter 等公开函数抛出）。"""


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise _CardError("缺少 frontmatter（未以 '---' 开头）")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        if rest.endswith("\n---"):
            return rest[:-4], ""
        raise _CardError("frontmatter 未闭合（缺第二个 '---'）")
    return rest[:end], rest[end + len("\n---\n") :]


def _safe_rel(p: Path, base: Path) -> str:
    try:
        return p.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return p.name


def _load_summary(card_path: Path, vault_root: Path) -> CardSummary:
    raw = card_path.read_text(encoding="utf-8")
    try:
        fm_text, _body = _split_frontmatter(raw)
    except _CardError:
        raise

    try:
        data = yaml.safe_load(fm_text)
    except yaml.YAMLError as e:
        raise _CardError(f"frontmatter YAML 解析失败：{e}") from e
    if not isinstance(data, dict):
        raise _CardError("frontmatter 顶层必须是 YAML 对象")

    status = data.get("status")
    if not isinstance(status, str) or not status:
        raise _CardError("frontmatter 缺 status 字段")

    try:
        mtime = datetime.fromtimestamp(card_path.stat().st_mtime).astimezone()
    except OSError:
        mtime = None

    return CardSummary(
        id=_str_or_none(data.get("id")),
        title=_str_or_none(data.get("title")),
        path=card_path.resolve(),
        rel_path=_safe_rel(card_path, vault_root),
        status=status,
        track=_str_or_none(data.get("track")),
        projects=_str_tuple(data.get("projects")),
        tags=_str_tuple(data.get("tags")),
        wiki_sections=_str_tuple(data.get("wiki_sections")),
        source_id=_str_or_none(data.get("source_id")),
        source_type=_str_or_none(data.get("source_type")),
        adapter_name=_str_or_none(data.get("adapter_name")),
        source_path=_str_or_none(data.get("source_path")),
        source_title=_str_or_none(data.get("source_title")),
        source_url=_str_or_none(data.get("source_url")),
        source_content_hash=_str_or_none(data.get("source_content_hash")),
        source_archive_path=_str_or_none(data.get("source_archive_path")),
        source_missing=_bool_or_false(data.get("source_missing")),
        value_score=_int_or_none(data.get("value_score")),
        created_at=_dt_or_none(data.get("created_at")),
        # 中文学习型说明：approved_at 是显式 approval timestamp，不能用
        # reviewed_at（复习时间）fallback。旧卡片若只有 reviewed_at，仍通过
        # reviewed_at 字段表达，避免把“复习过”误报成“已批准”。
        approved_at=_dt_or_none(data.get("approved_at")),
        reviewed_at=_dt_or_none(data.get("reviewed_at")),
        review_count=_int_or_none(data.get("review_count")) or 0,
        last_review_result=_str_or_none(data.get("last_review_result")),
        review_after=_dt_or_none(data.get("review_after")),
        updated_at=mtime,
        principles=_str_tuple(data.get("principles")),
        known_risks=_str_tuple(data.get("known_risks")),
        profile=_str_or_none(data.get("profile")),
        provider=_provider_from_stage_models(data.get("stage_models")),
        strategy_id=_str_or_none(data.get("strategy_id")),
        strategy_version=_str_or_none(data.get("strategy_version")),
        schema_version=_str_or_none(data.get("schema_version")),
        prompt_version=_str_or_none(data.get("prompt_version")),
        prompt_versions=_str_dict(data.get("prompt_versions")),
        stage_models=_dict_or_empty(data.get("stage_models")),
        run_id=_str_or_none(data.get("run_id")),
        source_location_index=_source_location_index(data),
    )


def _str_or_none(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        return v or None
    return str(v)


def _int_or_none(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _source_location_index(data: dict[str, Any]) -> int | None:
    """把不同 source location 字段归一成可比较序号。

    中文学习型说明：Related Cards 只需要判断“同 source 的相邻位置”，不需要
    重新解析 source 正文。这里仅使用 card frontmatter 已持久化的安全位置字段，
    保持只读、确定性，并避免 OCR / URL crawling / embedding。
    """

    explicit = _int_or_none(data.get("source_location_index"))
    if explicit is not None:
        return explicit
    for key in ("line_start", "page_number", "paragraph_start"):
        value = _int_or_none(data.get(key))
        if value is not None:
            return value
    location = data.get("source_location")
    if isinstance(location, dict):
        for key in ("source_location_index", "line_start", "page_number", "paragraph_start"):
            value = _int_or_none(location.get(key))
            if value is not None:
                return value
    return None


def _str_dict(v: Any) -> dict[str, str]:
    if not isinstance(v, dict):
        return {}
    return {str(k): str(val) for k, val in v.items() if val is not None}


def _dict_or_empty(v: Any) -> dict[str, Any]:
    return dict(v) if isinstance(v, dict) else {}


def _bool_or_false(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _str_tuple(v: Any) -> tuple[str, ...]:
    if v is None:
        return ()
    if isinstance(v, (list, tuple)):
        return tuple(str(x) for x in v if x is not None and str(x))
    return (str(v),)


def _provider_from_stage_models(v: Any) -> str | None:
    if not isinstance(v, dict):
        return None
    providers: list[str] = []
    for meta in v.values():
        if isinstance(meta, dict):
            provider = _str_or_none(meta.get("provider"))
            if provider and provider not in providers:
                providers.append(provider)
    if not providers:
        return None
    return ",".join(providers)


def _dt_or_none(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except ValueError:
            return None
    return None


def filter_cards(
    cards: Iterable[CardSummary],
    *,
    track: str | None = None,
    project: str | None = None,
    tags: Iterable[str] = (),
    source_type: str | None = None,
    status: str | None = "human_approved",   # None / "all" 表示不限
    keyword: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    include_drafts: bool = False,
) -> list[CardSummary]:
    """规则检索过滤器（M4 §5.2 AND 语义）。

    - 默认 status="human_approved"；显式 include_drafts=True 或 status="all"
      时不限状态；
    - keyword 仅搜白名单字段（不搜 body）：title / track / projects /
      tags / source_title + 文件名。大小写不敏感。
    """
    eff_status = None if (include_drafts or status in (None, "all")) else status
    tag_set = {t.lower() for t in tags if t}
    kw = keyword.lower().strip() if keyword else None

    out: list[CardSummary] = []
    for c in cards:
        if eff_status is not None and c.status != eff_status:
            continue
        if track is not None and c.track != track:
            continue
        if project is not None and project not in c.projects:
            continue
        if source_type is not None and c.source_type != source_type:
            continue
        if tag_set:
            card_tags = {t.lower() for t in c.tags}
            if not tag_set.issubset(card_tags):
                continue
        if since is not None and (c.created_at is None or c.created_at < since):
            continue
        if until is not None and (c.created_at is None or c.created_at > until):
            continue
        if kw and not _keyword_match(c, kw):
            continue
        out.append(c)
    return out


def _keyword_match(c: CardSummary, kw: str) -> bool:
    """关键词匹配（M4.1：多 token AND；每个 token 在白名单字段做 ci-contains）。

    安全设计：**绝不**匹配 body / source 原文 / human_note 等敏感字段。仅在
    frontmatter 白名单 + 文件名上做匹配，从而保证 keyword 命中即可对外打印
    安全摘要，而不会暴露未审核内容。
    """
    haystack: list[str] = []
    if c.title:
        haystack.append(c.title)
    if c.track:
        haystack.append(c.track)
    if c.source_title:
        haystack.append(c.source_title)
    haystack.extend(c.projects)
    haystack.extend(c.tags)
    haystack.append(c.path.name)
    blob = "\n".join(haystack).lower()
    tokens = [t for t in kw.lower().split() if t]
    if not tokens:
        return True
    return all(tok in blob for tok in tokens)


__all__ = [
    "CardSummary",
    "CardLoadError",
    "CardLoadValueError",
    "CardScanResult",
    "iter_cards",
    "filter_cards",
    "sort_cards",
    "read_card_frontmatter",
    "read_card_body",
    "extract_section",
]


# ---------------------------------------------------------------------------
# M4.1 — 排序键（recall / project context 共用）
# ---------------------------------------------------------------------------


_SORT_KEYS = ("review_after", "updated_at", "title", "value_score", "default")


def sort_cards(cards: Iterable[CardSummary], by: str = "default") -> list[CardSummary]:
    """稳定排序。``by`` ∈ {default, review_after, updated_at, title, value_score}。

    - default      ：(status_priority, -value_score, title)；human_approved 优先
    - review_after ：升序，None 排最后
    - updated_at   ：降序，None 排最后（最近更新在前）
    - title        ：升序（None 视为空字符串）
    - value_score  ：降序，None 排最后
    """
    items = list(cards)
    if by not in _SORT_KEYS:
        raise ValueError(f"unsupported sort key: {by!r} (valid: {_SORT_KEYS})")
    if by == "default":
        return sorted(
            items,
            key=lambda c: (
                0 if c.status == "human_approved" else 1,
                -(c.value_score or 0),
                (c.title or "").lower(),
                c.path.name,
            ),
        )
    if by == "review_after":
        big = datetime.max.replace(tzinfo=None)
        return sorted(
            items,
            key=lambda c: (
                0 if c.review_after is not None else 1,
                _strip_tz(c.review_after) or big,
                c.path.name,
            ),
        )
    if by == "updated_at":
        return sorted(
            items,
            key=lambda c: (
                0 if c.updated_at is not None else 1,
                # 反向：用负 timestamp 排序使最新在前
                -(c.updated_at.timestamp() if c.updated_at else 0),
                c.path.name,
            ),
        )
    if by == "title":
        return sorted(items, key=lambda c: ((c.title or "").lower(), c.path.name))
    # value_score
    return sorted(
        items,
        key=lambda c: (
            -(c.value_score or 0),
            (c.title or "").lower(),
            c.path.name,
        ),
    )


def _strip_tz(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=None)
