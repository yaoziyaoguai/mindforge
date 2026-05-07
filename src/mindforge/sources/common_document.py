"""CommonDocumentAdapter — 通用本地文档 parser registry。

中文学习型说明：本 adapter 是“常见文档格式 → SourceDocument”的轻量注册表，
不承担 folder traversal，也不触发 LLM/网络/写文件。scanner 只负责发现文件；
这里按 extension 选择 parser；ingestion pipeline 再负责 dedupe 和生成
``ai_draft``。重依赖格式保留为 optional/future，不伪装成功。
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frontmatter

from .base import SourceAdapter, SourceDocument, compute_content_hash
from .pdf import OptionalDependencyError


Parser = Callable[[Path], tuple[str, str | None, dict[str, Any]]]

_SUPPORTED_SUFFIXES = frozenset(
    {
        ".md",
        ".markdown",
        ".txt",
        ".html",
        ".htm",
        ".json",
        ".csv",
        ".tsv",
        ".xml",
        ".url",
        ".webloc",
    }
)

_MISSING_OPTIONAL_SUFFIXES = frozenset({".xlsx", ".pptx", ".rtf", ".epub"})


@dataclass(frozen=True)
class ParserChoice:
    parser: Parser | None
    skip_reason: str | None = None


class CommonDocumentAdapter(SourceAdapter):
    name = "CommonDocumentAdapter"
    source_type = "common_document"  # type: ignore[assignment]

    def can_handle(self, path: str) -> bool:
        suffix = Path(path).suffix.lower()
        return suffix in _SUPPORTED_SUFFIXES or suffix in _MISSING_OPTIONAL_SUFFIXES

    def skip_reason(self, path: str) -> str | None:
        """给 scanner 提供 parser 层 skip reason，但不泄漏解析实现。

        中文学习型说明：scanner 只问“这个文件是否应跳过以及原因”，不自己理解
        xlsx/pptx/epub 等格式。是否缺 optional dependency 是 parser registry
        的知识，保持架构边界清晰。
        """

        suffix = Path(path).suffix.lower()
        if suffix in _MISSING_OPTIONAL_SUFFIXES:
            return "missing_optional_dependency"
        return None

    def load(self, path: str) -> SourceDocument:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Document 文件不存在：{p}。请检查 source 路径。")
        choice = _parser_for_path(p)
        if choice.skip_reason == "missing_optional_dependency":
            raise OptionalDependencyError(
                f"{p.suffix.lower()} parsing requires an optional dependency; "
                "ordinary scan will mark it as missing_optional_dependency."
            )
        if choice.parser is None:
            raise ValueError(f"Unsupported document extension: {p.suffix.lower()}")

        body, title, metadata = choice.parser(p)
        title = title or p.stem
        source_id = "sha1:" + hashlib.sha1(str(p.resolve()).encode("utf-8")).hexdigest()
        key_meta = {"title": title, "extension": p.suffix.lower()}
        return SourceDocument(
            source_id=source_id,
            source_type=self.source_type,
            source_path=str(p.resolve()),
            title=title,
            raw_text=body,
            metadata={"parser": metadata, "extension": p.suffix.lower()},
            content_hash=compute_content_hash(body, key_meta),
        )


def _parser_for_path(path: Path) -> ParserChoice:
    suffix = path.suffix.lower()
    if suffix in _MISSING_OPTIONAL_SUFFIXES:
        return ParserChoice(parser=None, skip_reason="missing_optional_dependency")
    parsers: dict[str, Parser] = {
        ".md": _parse_markdown,
        ".markdown": _parse_markdown,
        ".txt": _parse_text,
        ".html": _parse_html,
        ".htm": _parse_html,
        ".json": _parse_json,
        ".csv": _parse_csv,
        ".tsv": _parse_tsv,
        ".xml": _parse_xml,
        ".url": _parse_url_shortcut,
        ".webloc": _parse_webloc,
    }
    return ParserChoice(parser=parsers.get(suffix))


def _parse_markdown(path: Path) -> tuple[str, str | None, dict[str, Any]]:
    post = frontmatter.load(str(path))
    meta = dict(post.metadata or {})
    return post.content or "", _coerce_str(meta.get("title")) or _heading(post.content), {"frontmatter": meta}


def _parse_text(path: Path) -> tuple[str, str | None, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    return text, _first_non_empty_line(text), {"format": "text"}


def _parse_html(path: Path) -> tuple[str, str | None, dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.I | re.S)
    title = _clean_html_text(title_match.group(1)) if title_match else None
    body = _clean_html_text(raw)
    return body, title or _first_non_empty_line(body), {"format": "html"}


def _parse_json(path: Path) -> tuple[str, str | None, dict[str, Any]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    title = _json_title(obj)
    body = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    return body, title, {"format": "json"}


def _parse_csv(path: Path) -> tuple[str, str | None, dict[str, Any]]:
    return _parse_delimited(path, delimiter=",")


def _parse_tsv(path: Path) -> tuple[str, str | None, dict[str, Any]]:
    return _parse_delimited(path, delimiter="\t")


def _parse_delimited(path: Path, *, delimiter: str) -> tuple[str, str | None, dict[str, Any]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            rows.append({str(k): str(v) for k, v in row.items() if k is not None and v is not None})
    body = json.dumps(rows, ensure_ascii=False, indent=2)
    title = rows[0].get("title") if rows else None
    return body, title, {"format": "tsv" if delimiter == "\t" else "csv", "row_count": len(rows)}


def _parse_xml(path: Path) -> tuple[str, str | None, dict[str, Any]]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    parts = [text.strip() for text in root.itertext() if text and text.strip()]
    body = "\n".join(parts)
    title = None
    for child in root.iter():
        if child.tag.lower().endswith("title") and child.text and child.text.strip():
            title = child.text.strip()
            break
    return body, title or _first_non_empty_line(body), {"format": "xml", "root_tag": root.tag}


def _parse_url_shortcut(path: Path) -> tuple[str, str | None, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    url = None
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip().lower() == "url":
            url = value.strip()
            break
    body = f"URL: {url or ''}".strip()
    return body, path.stem, {"format": "url", "url": url, "network_fetch": "explicit_opt_in_required"}


def _parse_webloc(path: Path) -> tuple[str, str | None, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"<key>URL</key>\s*<string>(.*?)</string>", text, flags=re.I | re.S)
    url = html.unescape(match.group(1).strip()) if match else None
    body = f"URL: {url or ''}".strip()
    return body, path.stem, {"format": "webloc", "url": url, "network_fetch": "explicit_opt_in_required"}


def _heading(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"^\s*#\s+(.+?)\s*$", text, flags=re.M)
    return match.group(1).strip() if match else None


def _first_non_empty_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return None


def _clean_html_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return re.sub(r"\s+", " ", raw).strip()


def _json_title(obj: Any) -> str | None:
    if isinstance(obj, dict):
        for key in ("title", "name", "headline"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = ["CommonDocumentAdapter"]
