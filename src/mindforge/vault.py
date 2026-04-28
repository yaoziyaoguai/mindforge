"""M5.5 — Obsidian 友好度（vault index + link candidates）。

为什么是"安全可见层"，不是自动改写：
==================================
Obsidian 的核心价值是双链与导航，但"AI 自动给卡片正文插入 [[...]]"会引入
两类风险：

1. 误链接：基于关键词的链接很容易把"agent runtime"和"my first agent"这种
   不同语义的笔记错连，污染知识图谱；
2. 不可逆：一旦写入正文，就脏了用户的 vault；想撤回需要 diff/rollback。

v0.1 的解法是**只做候选层**：
- ``mindforge vault index``：在每个目录生成 ``_index.md``，纯导航，幂等覆盖
  整个文件（带 marker 标识"由 MindForge 维护"）；
- ``mindforge vault links``：把候选写到独立的 ``_link_candidates.md``，
  **不**触碰已有 Knowledge Card 的正文。

这样用户可以一眼看到"哪些卡片可能相关"，但点进去后仍然由人决定要不要
真的加双链。这是 v0.1 "human-in-the-loop" 原则的延伸。

候选规则只用安全字段：
- learning_track（精确相等）
- projects（集合交集）
- tags（集合交集，>=1）
- source_type（精确相等，弱信号）
- title keyword（按英文词 + 中文 2-gram 取交集）

绝不使用：
- LLM；
- embedding / 向量相似度；
- raw source 全文；
- 卡片正文（仅 frontmatter + title）。
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .cards import CardSummary, iter_cards

# 自动生成文件头部的 marker，标识这个文件由 MindForge 维护、可被覆盖。
INDEX_MARKER = "<!-- MINDFORGE:VAULT_INDEX (auto-generated; do not edit by hand) -->"
LINKS_MARKER = "<!-- MINDFORGE:LINK_CANDIDATES (auto-generated; do not edit by hand) -->"

INDEX_FILENAME = "_index.md"
LINKS_FILENAME = "_link_candidates.md"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndexEntry:
    title: str
    rel_path: str
    status: str
    tracks: tuple[str, ...]
    projects: tuple[str, ...]
    review_after: str | None  # ISO 日期或 None；不要 datetime 以方便序列化


@dataclass(frozen=True)
class LinkCandidate:
    other_title: str
    other_rel_path: str
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CardCandidates:
    title: str
    rel_path: str
    candidates: tuple[LinkCandidate, ...]


# ---------------------------------------------------------------------------
# vault index
# ---------------------------------------------------------------------------


def build_index_entries(cards: Iterable[CardSummary]) -> list[IndexEntry]:
    out: list[IndexEntry] = []
    for c in cards:
        out.append(
            IndexEntry(
                title=c.title or Path(c.rel_path).stem,
                rel_path=c.rel_path,
                status=c.status or "(unknown)",
                tracks=(c.track,) if c.track else (),
                projects=c.projects,
                review_after=c.review_after.date().isoformat()
                if c.review_after
                else None,
            )
        )
    out.sort(key=lambda e: (e.status, e.title.lower()))
    return out


def render_index_markdown(
    title: str,
    entries: list[IndexEntry],
    *,
    note: str | None = None,
) -> str:
    lines = [INDEX_MARKER, "", f"# {title}", ""]
    if note:
        lines += [note, ""]
    if not entries:
        lines += ["_(no cards yet)_", ""]
        return "\n".join(lines).rstrip() + "\n"

    # 按 status 分组渲染
    by_status: dict[str, list[IndexEntry]] = {}
    for e in entries:
        by_status.setdefault(e.status, []).append(e)
    for status in sorted(by_status.keys()):
        bucket = by_status[status]
        lines.append(f"## {status} ({len(bucket)})")
        lines.append("")
        for e in bucket:
            tracks = ", ".join(e.tracks) if e.tracks else "—"
            projects = ", ".join(e.projects) if e.projects else "—"
            review = e.review_after or "—"
            # 用 markdown 链接（Obsidian 兼容）— 显示标题，路径用相对 vault 的 posix
            lines.append(
                f"- [{_escape(e.title)}]({_md_link_path(e.rel_path)})  "
                f"`status:{status}`  `tracks:{tracks}`  `projects:{projects}`  "
                f"`review_after:{review}`"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_index(
    target_dir: Path,
    title: str,
    entries: list[IndexEntry],
    *,
    note: str | None = None,
    dry_run: bool = False,
) -> tuple[Path, str]:
    """幂等写入 ``<target_dir>/_index.md``。返回 (path, content)。"""
    target_dir.mkdir(parents=True, exist_ok=True)
    p = target_dir / INDEX_FILENAME
    content = render_index_markdown(title, entries, note=note)
    if not dry_run:
        # 如果存在但不是 MindForge 管理的（首行没有 marker），写到 sibling，避免覆盖人手内容
        if p.exists():
            existing = p.read_text(encoding="utf-8")
            if not existing.lstrip().startswith(INDEX_MARKER):
                p = target_dir / "_index.mindforge.md"
        p.write_text(content, encoding="utf-8")
    return p, content


# ---------------------------------------------------------------------------
# link candidates
# ---------------------------------------------------------------------------


_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def _title_tokens(title: str | None) -> set[str]:
    """从 title 提取 token 集合（英文小写词 + 中文 2-gram）。"""
    if not title:
        return set()
    tokens: set[str] = set()
    # 英文 / 数字
    for m in _WORD_RE.findall(title.lower()):
        if len(m) >= 3:  # 过滤太短的噪声
            tokens.add(m)
    # 中文 2-gram
    cjk = re.findall(r"[\u4e00-\u9fff]+", title)
    for run in cjk:
        for i in range(len(run) - 1):
            tokens.add(run[i : i + 2])
    return tokens


def _candidate_score(a: CardSummary, b: CardSummary) -> tuple[int, list[str]]:
    """返回 (score, reasons)；分数越高越相关。"""
    if a.rel_path == b.rel_path:
        return 0, []
    score = 0
    reasons: list[str] = []
    # learning_track 精确相等：强信号
    if a.track and b.track and a.track == b.track:
        score += 4
        reasons.append(f"track:{a.track}")
    # projects 集合交集
    pa, pb = set(a.projects or ()), set(b.projects or ())
    common_projects = pa & pb
    if common_projects:
        score += 3 * len(common_projects)
        reasons.append("projects:" + ",".join(sorted(common_projects)))
    # tags 集合交集
    ta, tb = set(a.tags or ()), set(b.tags or ())
    common_tags = ta & tb
    if common_tags:
        score += 2 * min(len(common_tags), 3)  # 封顶，避免 tag spam
        reasons.append("tags:" + ",".join(sorted(common_tags)[:3]))
    # source_type 弱信号
    if a.source_type and b.source_type and a.source_type == b.source_type:
        score += 1
        reasons.append(f"source_type:{a.source_type}")
    # title token 交集
    common_tokens = _title_tokens(a.title) & _title_tokens(b.title)
    if common_tokens:
        score += min(len(common_tokens), 3)
        reasons.append("title:" + ",".join(sorted(common_tokens)[:3]))
    return score, reasons


def build_link_candidates(
    cards: Iterable[CardSummary],
    *,
    top_k: int = 5,
    min_score: int = 3,
) -> list[CardCandidates]:
    cards_list = list(cards)
    out: list[CardCandidates] = []
    for a in cards_list:
        scored: list[LinkCandidate] = []
        for b in cards_list:
            score, reasons = _candidate_score(a, b)
            if score >= min_score:
                scored.append(
                    LinkCandidate(
                        other_title=b.title or Path(b.rel_path).stem,
                        other_rel_path=b.rel_path,
                        score=score,
                        reasons=tuple(reasons),
                    )
                )
        scored.sort(key=lambda lc: (-lc.score, lc.other_title.lower()))
        out.append(
            CardCandidates(
                title=a.title or Path(a.rel_path).stem,
                rel_path=a.rel_path,
                candidates=tuple(scored[:top_k]),
            )
        )
    out.sort(key=lambda cc: cc.title.lower())
    return out


def render_link_candidates_markdown(
    cards_with_candidates: list[CardCandidates],
) -> str:
    lines = [LINKS_MARKER, "", "# Link Candidates", ""]
    lines.append(
        "> 这些是 MindForge 基于安全字段（learning_track / projects / tags / "
        "source_type / title token）规则匹配出的相关卡片候选；**不**调用 LLM、"
        "**不**做向量检索、**不**自动写入正文。请人工挑选后再决定是否在卡片"
        "里加 `[[...]]`。"
    )
    lines.append("")
    if not cards_with_candidates:
        lines += ["_(no cards yet)_", ""]
        return "\n".join(lines).rstrip() + "\n"
    for cc in cards_with_candidates:
        lines.append(f"## {_escape(cc.title)}")
        lines.append(f"- source: [{_escape(cc.rel_path)}]({_md_link_path(cc.rel_path)})")
        if not cc.candidates:
            lines.append("- _(no candidates above threshold)_")
        else:
            for lc in cc.candidates:
                reasons = "; ".join(lc.reasons) if lc.reasons else "—"
                lines.append(
                    f"- score={lc.score}  "
                    f"[{_escape(lc.other_title)}]({_md_link_path(lc.other_rel_path)})  "
                    f"_({reasons})_"
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_link_candidates(
    cards_dir: Path,
    cards_with_candidates: list[CardCandidates],
    *,
    dry_run: bool = False,
) -> tuple[Path, str]:
    cards_dir.mkdir(parents=True, exist_ok=True)
    p = cards_dir / LINKS_FILENAME
    content = render_link_candidates_markdown(cards_with_candidates)
    if not dry_run:
        if p.exists():
            existing = p.read_text(encoding="utf-8")
            if not existing.lstrip().startswith(LINKS_MARKER):
                p = cards_dir / "_link_candidates.mindforge.md"
        p.write_text(content, encoding="utf-8")
    return p, content


# ---------------------------------------------------------------------------
# 高层入口：扫卡片 + 写文件（供 CLI 直接调用）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndexResult:
    written: list[Path]
    skipped: list[Path]


def refresh_indexes(
    vault_root: Path,
    cards_dir_rel: str,
    projects_dir_rel: str,
    reviews_dir_rel: str | None,
    *,
    dry_run: bool = False,
) -> IndexResult:
    """为 cards / projects / reviews 三处生成 _index.md。"""
    written: list[Path] = []
    res = iter_cards(vault_root, cards_dir_rel)
    cards_dir = vault_root / cards_dir_rel
    entries = build_index_entries(res.cards)
    p, _ = write_index(
        cards_dir,
        title="Knowledge Cards Index",
        entries=entries,
        note=f"Total cards: {len(entries)}",
        dry_run=dry_run,
    )
    written.append(p)

    # 30-Projects/_index.md：只列 .md 文件，不解析 frontmatter（避免误读用户笔记）
    projects_dir = vault_root / projects_dir_rel
    if projects_dir.exists():
        proj_lines = [INDEX_MARKER, "", "# Projects Index", ""]
        proj_files = sorted(
            [f for f in projects_dir.glob("*.md") if f.name != INDEX_FILENAME]
        )
        if not proj_files:
            proj_lines.append("_(no project notes)_")
        for f in proj_files:
            rel = f"{projects_dir_rel}/{f.name}"
            proj_lines.append(f"- [{_escape(f.stem)}]({_md_link_path(rel)})")
        proj_lines.append("")
        target = projects_dir / INDEX_FILENAME
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if not existing.lstrip().startswith(INDEX_MARKER):
                target = projects_dir / "_index.mindforge.md"
        if not dry_run:
            target.write_text("\n".join(proj_lines).rstrip() + "\n", encoding="utf-8")
        written.append(target)

    # reviews 目录可选
    if reviews_dir_rel:
        reviews_dir = vault_root / reviews_dir_rel
        if reviews_dir.exists():
            r_entries = [e for e in entries if e.review_after]
            r_entries.sort(key=lambda e: e.review_after or "")
            r_lines = [
                INDEX_MARKER,
                "",
                "# Reviews Index",
                "",
                "> 列出所有有 `review_after` 的卡片（不论 status）；按到期日升序。",
                "",
            ]
            for e in r_entries:
                r_lines.append(
                    f"- {e.review_after or '—'}  "
                    f"[{_escape(e.title)}]({_md_link_path(e.rel_path)})  "
                    f"`status:{e.status}`"
                )
            if not r_entries:
                r_lines.append("_(no review-due cards)_")
            target = reviews_dir / INDEX_FILENAME
            if target.exists():
                existing = target.read_text(encoding="utf-8")
                if not existing.lstrip().startswith(INDEX_MARKER):
                    target = reviews_dir / "_index.mindforge.md"
            if not dry_run:
                target.write_text(
                    "\n".join(r_lines).rstrip() + "\n", encoding="utf-8"
                )
            written.append(target)

    return IndexResult(written=written, skipped=[])


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _escape(s: str) -> str:
    # 仅做最小 markdown 转义：避免 ``[`` 把链接断掉
    return s.replace("[", "\\[").replace("]", "\\]")


def _md_link_path(rel_path: str) -> str:
    # 对 spaces 做 URL 转义；其它保留。Obsidian 也接受不转义但更稳。
    return rel_path.replace(" ", "%20")


__all__ = [
    "INDEX_MARKER",
    "LINKS_MARKER",
    "INDEX_FILENAME",
    "LINKS_FILENAME",
    "IndexEntry",
    "LinkCandidate",
    "CardCandidates",
    "IndexResult",
    "build_index_entries",
    "build_link_candidates",
    "render_index_markdown",
    "render_link_candidates_markdown",
    "write_index",
    "write_link_candidates",
    "refresh_indexes",
]
