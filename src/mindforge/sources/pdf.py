"""PdfAdapter — 文本型 PDF 的最小文本抽取（M5.1 v0.2.5）。

边界（硬性）：
- **不做 OCR**：扫描件 / 图片 PDF 一律抛 ``PdfNoTextError``，不要试图猜；
- **不做表格 / 多栏版式还原**：按页拼接 ``page.extract_text()`` 的输出；
- **不解析图片 / 注释 / 表单 / JavaScript**；
- **lazy import**：未安装 ``pypdf`` 时只在调用 ``load()`` 时报错，
  ``mindforge`` 的其他命令仍然可用。

为什么不做 OCR？当前 source adapter 边界见 ``docs/IMPLEMENTATION.md``。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .base import SourceAdapter, SourceDocument, compute_content_hash


class OptionalDependencyError(RuntimeError):
    """提示用户用 ``pip install mindforge[pdf]`` 等命令安装可选依赖。"""


class PdfNoTextError(RuntimeError):
    """PDF 没有可抽取的文本层（很可能是扫描件）；MindForge 不做 OCR。"""


class PdfAdapter(SourceAdapter):
    name = "PdfAdapter"
    source_type = "pdf"  # type: ignore[assignment]

    def can_handle(self, path: str) -> bool:
        return path.lower().endswith(".pdf")

    def load(self, path: str) -> SourceDocument:
        try:
            import pypdf  # type: ignore[import-not-found]
        except ImportError as e:
            raise OptionalDependencyError(
                "PdfAdapter 需要 'pypdf'（可选依赖）。请运行：\n"
                "    pip install 'mindforge[pdf]'\n"
                "或:\n"
                "    pip install pypdf\n"
                "详见 docs/IMPLEMENTATION.md 的 source adapter 说明。"
            ) from e

        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"PDF 文件不存在：{p}。请检查 inbox 路径。")

        # 用 pypdf 最小读取；不传 password、不解 encrypted 文件。
        try:
            reader = pypdf.PdfReader(str(p))
        except Exception as e:  # pypdf 自己的异常体系不稳，统一收敛
            raise OptionalDependencyError(
                f"PDF 解析失败（pypdf/{type(e).__name__}）：{e}。"
                "请确认文件不是加密 PDF，或先用外部工具导出文本。"
            ) from e

        pages_text: list[str] = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:  # noqa: BLE001 — 单页失败降级为空，不影响整文档
                t = ""
            pages_text.append(t)
        body = "\n\n".join(s.strip() for s in pages_text if s.strip())

        if not body.strip():
            # 文本层为空 → 很可能是扫描件；不静默成功，避免下游产出空卡片
            raise PdfNoTextError(
                f"未能从 PDF {p.name} 抽取任何文本（很可能是扫描件）。"
                "MindForge v0.x 不做 OCR；请用其他工具先 OCR 后再放回 inbox，"
                "或直接归档。详见 docs/IMPLEMENTATION.md 的 source adapter 说明。"
            )

        title = _pick_title(reader, p)
        author = _pick_author(reader)

        source_id = "sha1:" + hashlib.sha1(path.encode("utf-8")).hexdigest()
        key_meta = {"title": title, "page_count": len(reader.pages)}
        content_hash = compute_content_hash(body, key_meta)

        return SourceDocument(
            source_id=source_id,
            source_type=self.source_type,
            source_path=path,
            title=title,
            author=author,
            source_url=None,
            created_at=None,
            captured_at=None,
            tags=[],
            highlights=[],
            raw_text=body,
            metadata={"page_count": len(reader.pages)},
            content_hash=content_hash,
        )


def _pick_title(reader: object, p: Path) -> str:
    try:
        meta = getattr(reader, "metadata", None)
        if meta:
            t = getattr(meta, "title", None) or meta.get("/Title")  # type: ignore[union-attr]
            if t:
                return str(t).strip()
    except Exception:  # noqa: BLE001
        pass
    return p.stem


def _pick_author(reader: object) -> str | None:
    try:
        meta = getattr(reader, "metadata", None)
        if meta:
            a = getattr(meta, "author", None) or meta.get("/Author")  # type: ignore[union-attr]
            if a:
                return str(a).strip()
    except Exception:  # noqa: BLE001
        pass
    return None


__all__ = ["PdfAdapter", "OptionalDependencyError", "PdfNoTextError"]
