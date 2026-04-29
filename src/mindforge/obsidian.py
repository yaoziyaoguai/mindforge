"""只读 Obsidian Binding 服务层。

这里放 CLI 可复用的纯本地逻辑。它不读取 `.env`、不联网、不调用 LLM，也不把
runtime state 写进 Obsidian notes。写入能力仅限 staging/review，并需要显式确认。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .config import ObsidianConfig
from .sources.base import SourceDocument
from .sources.obsidian_vault import ObsidianVaultSourceAdapter

_RUNTIME_DIR_NAMES = {".mindforge", "runs", "state", "telemetry", "index"}


@dataclass(frozen=True)
class ObsidianScanOptions:
    vault_root: Path
    include_dirs: tuple[str, ...]
    exclude_dirs: tuple[str, ...]


@dataclass(frozen=True)
class ObsidianLoadIssue:
    """单个 note 的只读解析问题。

    中文学习型说明：dogfooding 真实 vault 副本时，用户很可能遇到坏
    frontmatter、非标准 Markdown 或编辑器生成的边界文件。scan/links 应该把
    这些文件标成 skipped，而不是因为一个坏 note 中断整个只读巡检。
    """

    path: Path
    reason: str


def resolve_obsidian_vault(
    cfg_obsidian: ObsidianConfig,
    fallback_vault: Path,
    override: Path | None = None,
) -> Path:
    """解析 Obsidian vault path。

    优先级：命令行覆盖 > obsidian.vault_path > MindForge vault.root。最后一项让
    demo vault 和测试 fixture 可直接试跑，但真实使用应显式配置或传 --vault。
    """
    if override is not None:
        return override.expanduser().resolve()
    if cfg_obsidian.vault_path is not None:
        return cfg_obsidian.vault_path.expanduser().resolve()
    return fallback_vault.expanduser().resolve()


def iter_obsidian_markdown(options: ObsidianScanOptions) -> list[Path]:
    root = options.vault_root.expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Obsidian vault 不存在：{root}。请检查 --vault 或 obsidian.vault_path。")
    if not root.is_dir():
        raise NotADirectoryError(f"Obsidian vault 不是目录：{root}")

    scan_roots: list[Path] = []
    for include in options.include_dirs:
        candidate = root / include
        if candidate.exists() and candidate.is_dir():
            scan_roots.append(candidate)
    if not scan_roots:
        scan_roots = [root]

    files: list[Path] = []
    for scan_root in scan_roots:
        for path in sorted(scan_root.rglob("*.md")):
            if path.is_file() and not _is_excluded(path, root, options.exclude_dirs):
                files.append(path)
    return files


def load_obsidian_documents(options: ObsidianScanOptions, *, limit: int = 0) -> list[SourceDocument]:
    adapter = ObsidianVaultSourceAdapter(options.vault_root)
    docs: list[SourceDocument] = []
    for path in iter_obsidian_markdown(options):
        docs.append(adapter.load(str(path)))
        if limit > 0 and len(docs) >= limit:
            break
    return docs


def load_obsidian_documents_with_issues(
    options: ObsidianScanOptions,
    *,
    limit: int = 0,
) -> tuple[list[SourceDocument], list[ObsidianLoadIssue]]:
    """只读加载 Obsidian notes，并把单文件解析失败降级成 issue。

    这里不吞掉 vault 路径级错误：vault 不存在或不是目录仍然抛给 CLI 处理。
    降级范围只限单个 Markdown 文件，避免真实 dry-run 因一条坏 frontmatter
    卡住，同时不把正文或 secret 打印出来。
    """
    adapter = ObsidianVaultSourceAdapter(options.vault_root)
    docs: list[SourceDocument] = []
    issues: list[ObsidianLoadIssue] = []
    for path in iter_obsidian_markdown(options):
        try:
            docs.append(adapter.load(str(path)))
        except Exception as e:  # noqa: BLE001 - CLI 只展示安全摘要，不泄漏 note 正文
            issues.append(ObsidianLoadIssue(path=path, reason=f"{type(e).__name__}: {e}"))
            continue
        if limit > 0 and len(docs) >= limit:
            break
    return docs, issues


def summarize_doc(doc: SourceDocument) -> dict[str, Any]:
    """返回安全摘要：不含 raw_text / note body。"""
    headings = doc.metadata.get("headings") or []
    wikilinks = doc.metadata.get("wikilinks") or []
    return {
        "title": doc.title,
        "relative_path": doc.source_path,
        "tags": list(doc.tags),
        "wikilink_count": len(wikilinks),
        "heading_count": len(headings),
        "content_hash": doc.content_hash,
        "source_type": doc.source_type,
    }


def build_link_entries(docs: list[SourceDocument]) -> list[dict[str, Any]]:
    outgoing_by_note: dict[str, list[str]] = {
        doc.source_path: list(doc.metadata.get("wikilinks") or [])
        for doc in docs
    }
    incoming_count: dict[str, int] = {}
    title_to_path = {
        (doc.title or Path(doc.source_path).stem): doc.source_path
        for doc in docs
    }
    stem_to_path = {Path(doc.source_path).stem: doc.source_path for doc in docs}
    for outgoing in outgoing_by_note.values():
        for link in outgoing:
            target = title_to_path.get(link) or stem_to_path.get(link) or link
            incoming_count[target] = incoming_count.get(target, 0) + 1
    return [
        {
            "note": note,
            "outgoing_links": outgoing,
            "outgoing_count": len(outgoing),
            "incoming_count": incoming_count.get(note, 0),
        }
        for note, outgoing in sorted(outgoing_by_note.items())
    ]


def build_stage_markdown(doc: SourceDocument) -> str:
    now = datetime.now(timezone.utc).isoformat()
    title = doc.title or Path(doc.source_path).stem
    fm = {
        "title": f"Candidate: {title}",
        "source_type": "obsidian_note",
        "obsidian_relative_path": doc.source_path,
        "obsidian_note_title": title,
        "source_content_hash": doc.content_hash,
        "status": "ai_draft",
        "generated_by": "mindforge",
        "created_at": now,
    }
    body = (
        f"# Candidate: {title}\n\n"
        "## Review Notes\n\n"
        "- This file is a staged MindForge candidate generated without a real LLM.\n"
        "- Review manually before copying anything into formal Obsidian notes.\n\n"
        "## Source Metadata\n\n"
        f"- Source: `{doc.source_path}`\n"
        f"- Tags: {', '.join(doc.tags) or '-'}\n"
        f"- Wikilinks: {', '.join(doc.metadata.get('wikilinks') or []) or '-'}\n"
        f"- Headings: {len(doc.metadata.get('headings') or [])}\n"
    )
    return "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n" + body


def stage_output_path(
    vault_root: Path,
    cfg_obsidian: ObsidianConfig,
    doc: SourceDocument,
    output_dir: str | Path | None,
) -> Path:
    root = vault_root.expanduser().resolve()
    allowed_roots = [
        (root / cfg_obsidian.staging_dir).resolve(),
        (root / cfg_obsidian.review_dir).resolve(),
    ]
    if output_dir is None:
        target_dir = allowed_roots[0]
    else:
        raw = Path(output_dir).expanduser()
        target_dir = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    if not any(_is_relative_to(target_dir, allowed) for allowed in allowed_roots):
        allowed_text = ", ".join(str(p) for p in allowed_roots)
        raise ValueError(f"输出目录必须位于 staging/review 内：{allowed_text}")
    filename = _slugify(doc.title or Path(doc.source_path).stem) + ".md"
    return target_dir / filename


def obsidian_doctor_rows(
    vault_root: Path,
    cfg_obsidian: ObsidianConfig,
) -> list[tuple[str, str, str]]:
    root = vault_root.expanduser().resolve()
    rows: list[tuple[str, str, str]] = []
    rows.append(("ok" if root.exists() and root.is_dir() else "error", "vault path", str(root)))
    rows.append(("ok" if (root / ".obsidian").is_dir() else "warn", ".obsidian", "present" if (root / ".obsidian").is_dir() else "missing"))
    rows.append(("ok" if cfg_obsidian.read_only else "error", "read_only", str(cfg_obsidian.read_only)))

    for label, rel in (("staging_dir", cfg_obsidian.staging_dir), ("review_dir", cfg_obsidian.review_dir)):
        target = (root / rel).resolve()
        state = "ok" if _is_relative_to(target, root) and not _is_formal_runtime_path(target, root) else "error"
        rows.append((state, label, str(target)))

    rows.append(("warn" if (root / ".mindforge").exists() else "ok", ".mindforge in vault", "present" if (root / ".mindforge").exists() else "absent"))
    runtime = root / "90-System" / "MindForge" / "Runtime"
    rows.append(("warn" if runtime.exists() else "ok", "runtime notes risk", "present" if runtime.exists() else "absent"))
    return rows


def _is_excluded(path: Path, root: Path, exclude_dirs: tuple[str, ...]) -> bool:
    rel = path.resolve().relative_to(root).as_posix()
    parts = set(path.resolve().relative_to(root).parts)
    if parts & _RUNTIME_DIR_NAMES:
        return True
    for item in exclude_dirs:
        clean = item.strip().strip("/")
        if not clean:
            continue
        if rel == clean or rel.startswith(clean + "/"):
            return True
        if clean in parts:
            return True
    return False


def _is_formal_runtime_path(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return True
    return rel.startswith(".obsidian/") or rel.startswith(".mindforge/")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff._-]+", "-", text.strip()).strip("-")
    return slug[:80] or "obsidian-note"
