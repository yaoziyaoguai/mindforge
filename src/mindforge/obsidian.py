"""只读 Obsidian Binding 服务层。

这里放 CLI 可复用的纯本地逻辑。它不读取 `.env`、不联网、不调用 LLM，也不把
runtime state 写进 Obsidian notes。写入能力仅限 staging/review，并需要显式确认。
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

from .config import ObsidianConfig
from .safety_policy import OBSIDIAN_MANIFEST_SAFETY_LABELS, forbidden_derived_parts
from .sources.base import SourceDocument
from .sources.obsidian_vault import ObsidianVaultSourceAdapter

_RUNTIME_DIR_NAMES = {".mindforge", "runs", "state", "telemetry", "index"}
_DEFAULT_EXCLUDE_DIRS = (".obsidian", ".git", ".mindforge", "node_modules")


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


@dataclass(frozen=True)
class ObsidianPreflightResult:
    """Obsidian future write-gate 的只读检查结果。

    中文学习型说明：preflight 只判断 staged export 是否具备"未来可进入写入闸门"
    的证据链。它不会创建、修改、删除任何 Obsidian note，也不会把 staged 文件
    应用回 vault；真正写入仍必须等后续版本加入显式确认、备份与恢复路径。
    """

    status: str
    blocked: list[str]
    warnings: list[str]
    manifest_path: Path
    staged_markdown: Path | None
    proposed_target: Path | None
    backup_path: Path | None
    recovery_plan: str


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

    files: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        if not path.is_file():
            continue
        in_scope, _reason = obsidian_path_in_scope(path, options)
        if in_scope:
            files.append(path)
    return files


def obsidian_path_in_scope(path: Path, options: ObsidianScanOptions) -> tuple[bool, str]:
    """判断单个 note 是否落在 Obsidian include/exclude 范围内。

    中文学习型说明：scan 与 stage 共用同一套 scope 规则，避免出现"scan 看不到，
    stage 却能写出候选"的安全错觉。这里只做路径判断，不读取正文、不写文件。
    """
    root = options.vault_root.expanduser().resolve()
    try:
        path.resolve().relative_to(root)
    except ValueError:
        return False, "source 不在 Obsidian vault 内"
    if _is_excluded(path, root, options.exclude_dirs):
        return False, "被 exclude rules 排除"
    if options.include_dirs and not any(_matches_scope(path, root, item) for item in options.include_dirs):
        return False, "不匹配 include rules"
    return True, ""


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
    rows.append(("ok", "formal note writes", "no"))
    rows.append(("ok", "include rules", ", ".join(cfg_obsidian.include_dirs) or "<all markdown>"))
    rows.append(("ok", "exclude rules", ", ".join(_effective_excludes(cfg_obsidian.exclude_dirs))))
    if root.exists() and root.is_dir():
        markdown_files = list(root.rglob("*.md"))
        non_markdown = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() != ".md"]
        large_md = [p for p in markdown_files if p.stat().st_size > 1_000_000]
        rows.append(("ok" if markdown_files else "warn", "markdown files", str(len(markdown_files))))
        rows.append(("warn" if large_md else "ok", "large markdown", str(len(large_md))))
        rows.append(("warn" if non_markdown else "ok", "non markdown files", str(len(non_markdown))))
        rows.append(("warn" if _duplicate_note_titles(root) else "ok", "duplicate titles", ", ".join(_duplicate_note_titles(root)[:5]) or "none"))
    return rows


def obsidian_preflight(
    *,
    vault_root: Path,
    manifest_path: Path,
    default_staged_root: Path,
) -> ObsidianPreflightResult:
    """只读校验 staged export manifest，为未来 write gate 做准备。

    中文学习型说明：这里检查的是"证据是否完整"，不是"执行写入"。因此函数
    只读取 manifest 和 staged markdown 的存在性，不读取 `.env`、不调用 LLM、
    不上传 telemetry，也不写正式 Obsidian notes。把这层做成纯函数风格，可以
    防止未来 apply/write 命令绕过 staged export → diff → confirmation 边界。
    """
    root = vault_root.expanduser().resolve()
    manifest = manifest_path.expanduser().resolve()
    staged_root = default_staged_root.expanduser().resolve()
    blocked: list[str] = []
    warnings: list[str] = []
    payload: dict[str, Any] = {}

    if not manifest.exists():
        blocked.append(f"staged manifest 不存在：{manifest}")
    elif not manifest.is_file():
        blocked.append(f"staged manifest 不是文件：{manifest}")
    else:
        try:
            loaded = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            blocked.append(f"staged manifest 不是合法 JSON：{e.msg}")
        else:
            if not isinstance(loaded, dict):
                blocked.append("staged manifest 必须是 JSON object")
            else:
                payload = loaded

    staged_markdown = _manifest_path_value(payload, "staged_markdown", "proposed_file")
    proposed_target = _manifest_write_gate_path(payload, "proposed_target")
    backup_path = _manifest_write_gate_path(payload, "backup_path")
    recovery_plan = str((payload.get("write_gate") or {}).get("recovery_plan") or "")

    _require_manifest_value(payload, ("source_note", "source"), "source", blocked)
    _require_manifest_value(payload, ("action",), "action", blocked)
    _require_manifest_value(payload, ("timestamp",), "timestamp", blocked)
    _require_manifest_value(payload, ("safety",), "safety boundary", blocked)

    if staged_markdown is None:
        blocked.append("manifest 缺少 staged_markdown/proposed_file")
    else:
        if not staged_markdown.exists():
            blocked.append(f"staged markdown 不存在：{staged_markdown}")
        elif staged_markdown.suffix.lower() != ".md":
            blocked.append(f"staged markdown 不是 .md 文件：{staged_markdown}")
        _check_staged_output_policy(
            payload=payload,
            staged_markdown=staged_markdown,
            manifest=manifest,
            default_staged_root=staged_root,
            blocked=blocked,
        )
        _check_no_forbidden_machine_parts(staged_markdown, "staged markdown", blocked)

    if proposed_target is None:
        blocked.append("manifest.write_gate 缺少 proposed_target")
    else:
        if not _is_relative_to(proposed_target, root):
            blocked.append(f"proposed target 不在 Obsidian vault 内：{proposed_target}")
        if proposed_target.exists():
            warnings.append(f"proposed target 已存在；preflight 不会覆盖：{proposed_target}")
        _check_no_forbidden_machine_parts(proposed_target, "proposed target", blocked)

    if backup_path is None:
        blocked.append("manifest.write_gate 缺少 backup_path")
    if not recovery_plan:
        blocked.append("manifest.write_gate 缺少 rollback/recovery plan")

    _check_safety_boundary(payload, blocked)
    if payload.get("mode") not in {"staged_export", "human_approved"}:
        blocked.append("manifest.mode 必须来自 staged_export 或 explicit human-approved")
    if (payload.get("write_gate") or {}).get("writes_formal_notes_now") is not False:
        blocked.append("manifest 必须声明 writes_formal_notes_now=false")

    status = "BLOCKED" if blocked else "WARNING" if warnings else "PASS"
    return ObsidianPreflightResult(
        status=status,
        blocked=blocked,
        warnings=warnings,
        manifest_path=manifest,
        staged_markdown=staged_markdown,
        proposed_target=proposed_target,
        backup_path=backup_path,
        recovery_plan=recovery_plan,
    )


def _manifest_path_value(payload: dict[str, Any], *keys: str) -> Path | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return Path(value).expanduser().resolve()
    return None


def _manifest_write_gate_path(payload: dict[str, Any], key: str) -> Path | None:
    write_gate = payload.get("write_gate")
    if not isinstance(write_gate, dict):
        return None
    value = write_gate.get(key)
    if isinstance(value, str) and value.strip():
        return Path(value).expanduser().resolve()
    return None


def _require_manifest_value(
    payload: dict[str, Any],
    keys: tuple[str, ...],
    label: str,
    blocked: list[str],
) -> None:
    if not any(key in payload and payload.get(key) not in (None, "", {}) for key in keys):
        blocked.append(f"manifest 缺少 {label}")


def _check_staged_output_policy(
    *,
    payload: dict[str, Any],
    staged_markdown: Path,
    manifest: Path,
    default_staged_root: Path,
    blocked: list[str],
) -> None:
    policy = str(payload.get("staged_output_policy") or "")
    if policy == "explicit-output-dir":
        if staged_markdown.parent != manifest.parent:
            blocked.append("explicit output-dir 下 manifest 与 staged markdown 必须在同一目录")
        return
    if policy != "default-state-workdir":
        blocked.append("manifest 缺少 staged_output_policy")
        return
    manifest_root = _manifest_path_value(payload, "staged_export_dir") or default_staged_root
    if not _is_relative_to(staged_markdown, manifest_root):
        blocked.append(f"default staged output 必须位于 {manifest_root}")


def _check_safety_boundary(payload: dict[str, Any], blocked: list[str]) -> None:
    safety = payload.get("safety")
    if not isinstance(safety, dict):
        blocked.append("manifest.safety 必须是 object")
        return
    for key, label in OBSIDIAN_MANIFEST_SAFETY_LABELS.items():
        if safety.get(key) is not True:
            blocked.append(f"manifest.safety 必须声明 {label}")


def _check_no_forbidden_machine_parts(path: Path, label: str, blocked: list[str]) -> None:
    bad = forbidden_derived_parts(path)
    if bad:
        blocked.append(f"{label} 包含禁止的机器派生层路径：{', '.join(bad)}")


def _is_excluded(path: Path, root: Path, exclude_dirs: tuple[str, ...]) -> bool:
    parts = set(path.resolve().relative_to(root).parts)
    if parts & _RUNTIME_DIR_NAMES:
        return True
    for item in _effective_excludes(exclude_dirs):
        if _matches_scope(path, root, item):
            return True
    return False


def _effective_excludes(exclude_dirs: tuple[str, ...]) -> tuple[str, ...]:
    """默认排除工具/runtime 目录，再叠加配置或 CLI exclude。"""
    seen: set[str] = set()
    merged: list[str] = []
    for item in (*_DEFAULT_EXCLUDE_DIRS, *exclude_dirs):
        clean = item.strip().strip("/")
        if clean and clean not in seen:
            seen.add(clean)
            merged.append(clean)
    return tuple(merged)


def _matches_scope(path: Path, root: Path, pattern: str) -> bool:
    rel = path.resolve().relative_to(root).as_posix()
    clean = pattern.strip().strip("/")
    if not clean:
        return False
    parts = set(path.resolve().relative_to(root).parts)
    if any(ch in clean for ch in "*?[]"):
        return fnmatch(rel, clean) or fnmatch(Path(rel).name, clean)
    return rel == clean or rel.startswith(clean + "/") or clean in parts


def _duplicate_note_titles(root: Path) -> list[str]:
    """轻量查重：只看文件 stem，避免 doctor 为了诊断去解析 note 正文。"""
    seen: dict[str, int] = {}
    for path in root.rglob("*.md"):
        title = path.stem.strip().lower()
        seen[title] = seen.get(title, 0) + 1
    return sorted(title for title, count in seen.items() if count > 1)


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
