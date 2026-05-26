"""Web Import/Export Service — 卡片导入、文件夹导入、去重检测。

中文学习型说明：从 web_facade 提取的 import/export 逻辑。
物理隔离 import 方法，让 web_facade 回归 orchestrator 角色。
所有方法标记主路径功能 — 不涉及 RAG/embedding/real LLM。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from mindforge.cards import iter_cards

if TYPE_CHECKING:
    from mindforge.config import MindForgeConfig
    from mindforge_web.schemas import (
        FolderImportPreviewResponse,
        FolderImportResponse,
        ImportCardResponse,
        _FolderImportPreviewFile,
        _FolderImportResultItem,
        _PotentialDuplicateResponse,
    )


class WebImportExportService:
    """卡片导入/导出服务 — 主路径功能。

    中文学习型说明：处理 Markdown 卡片导入（单卡片 + 批量文件夹导入）、
    去重检测、markdown 解析。不调用 LLM，不依赖外部服务。
    """

    # 安全检查：拒绝导入的文件名模式
    _REJECTED_FILENAME_PATTERNS = [
        lambda n: n.startswith("."),                 # 隐藏文件
        lambda n: n in (".DS_Store", "Thumbs.db", "desktop.ini"),  # 系统文件
        lambda n: not n.lower().endswith(".md"),      # 非 markdown 文件
    ]

    # 单文件最大 1MB
    _MAX_IMPORT_FILE_BYTES = 1_048_576

    def __init__(self, cfg: MindForgeConfig) -> None:
        self._cfg = cfg

    # ── Card Import ────────────────────────────────────────────────────────

    def import_card(self, title: str, body: str, source_name: str = "") -> ImportCardResponse:
        """从 Markdown 内容创建 ai_draft 卡片（fake dogfood 场景）。

        不调用 LLM / provider / external service。
        卡片创建在 cards_dir 下，文件名从标题生成。
        """
        from mindforge_web.schemas import ImportCardResponse

        potential_duplicates = self._find_duplicates(title)

        slug = re.sub(r"[^a-zA-Z0-9一-鿿_-]", "-", title.strip()).strip("-")[:60] or "imported"
        card_id = f"{slug}-{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        filename = f"{card_id}.md"

        cards_dir = self._cfg.vault.cards_path
        cards_dir.mkdir(parents=True, exist_ok=True)

        frontmatter_lines = [
            f"id: {card_id}",
            f"title: {title.strip()}",
            "status: ai_draft",
            "source_type: imported_markdown",
            f"created_at: {now}",
        ]
        if source_name.strip():
            frontmatter_lines.append(f"source_title: {source_name.strip()}")
        frontmatter = "\n".join(frontmatter_lines)

        content = f"---\n{frontmatter}\n---\n{body if body.endswith(chr(10)) else body + chr(10)}"
        card_path = cards_dir / filename
        card_path.write_text(content, encoding="utf-8")

        rel_path = card_path.resolve().relative_to(self._cfg.vault.root.resolve()).as_posix()

        return ImportCardResponse(
            id=card_id,
            title=title.strip(),
            rel_path=rel_path,
            status="ai_draft",
            created_at=now,
            potential_duplicates=potential_duplicates,
        )

    # ── Folder Import ──────────────────────────────────────────────────────

    def preview_folder_import(self, folder_path: str) -> FolderImportPreviewResponse:
        """扫描文件夹中的 .md 文件，dry-run 预览导入内容。

        不写入任何文件，只返回可导入文件的标题、内容预览和警告。
        """
        from mindforge_web.schemas import FolderImportPreviewResponse
        from mindforge_web.schemas.import_export import _FolderImportPreviewFile

        folder = Path(folder_path).resolve()
        if not folder.is_dir():
            return FolderImportPreviewResponse(
                folder_path=folder_path,
                total_files=0,
                importable_count=0,
                files=[],
                folder_warning="文件夹不存在或不是有效目录。",
            )

        # 安全检查：拒绝系统路径
        resolved = str(folder.resolve())
        if resolved in ("/", "/System", "/etc", "/var", "/tmp", "/usr", "/bin", "/sbin"):
            return FolderImportPreviewResponse(
                folder_path=folder_path,
                total_files=0,
                importable_count=0,
                files=[],
                folder_warning="出于安全考虑，拒绝扫描系统路径。",
            )

        # 扫描 .md 文件
        md_files: list[Path] = []
        folder_warning = None
        try:
            for entry in sorted(folder.iterdir()):
                if not entry.is_file():
                    continue
                name = entry.name
                if any(p(name) for p in self._REJECTED_FILENAME_PATTERNS):
                    continue
                md_files.append(entry)
        except OSError as e:
            return FolderImportPreviewResponse(
                folder_path=folder_path,
                total_files=0,
                importable_count=0,
                files=[],
                folder_warning=f"无法读取文件夹: {e}",
            )

        files: list[_FolderImportPreviewFile] = []
        for i, fpath in enumerate(md_files):
            try:
                stat = fpath.stat()
                if stat.st_size > self._MAX_IMPORT_FILE_BYTES:
                    files.append(_FolderImportPreviewFile(
                        index=i, filename=fpath.name, title=fpath.name,
                        body_preview="", size_bytes=stat.st_size,
                        warnings=[], error=f"文件过大 ({stat.st_size} bytes, max {self._MAX_IMPORT_FILE_BYTES})",
                    ))
                    continue

                raw = fpath.read_text(encoding="utf-8")
                title, body = self._parse_markdown_title_body(raw, fpath.name)

                warnings: list[str] = []
                if not body.strip():
                    warnings.append("内容为空，仅含 frontmatter")
                if len(title) > 120:
                    warnings.append("标题过长")

                dups = self._find_duplicates(title)

                files.append(_FolderImportPreviewFile(
                    index=i, filename=fpath.name,
                    title=title,
                    body_preview=body[:200].strip(),
                    size_bytes=stat.st_size,
                    warnings=warnings,
                    error=None,
                    potential_duplicates=dups,
                ))
            except UnicodeDecodeError:
                files.append(_FolderImportPreviewFile(
                    index=i, filename=fpath.name, title=fpath.name,
                    body_preview="", size_bytes=0,
                    warnings=[], error="无法以 UTF-8 编码读取文件",
                ))
            except OSError as e:
                files.append(_FolderImportPreviewFile(
                    index=i, filename=fpath.name, title=fpath.name,
                    body_preview="", size_bytes=0,
                    warnings=[], error=f"读取失败: {e}",
                ))

        importable = sum(1 for f in files if f.error is None)

        return FolderImportPreviewResponse(
            folder_path=folder_path,
            total_files=len(md_files),
            importable_count=importable,
            files=files,
            folder_warning=folder_warning,
        )

    def import_from_folder(
        self, folder_path: str, indices: list[int],
    ) -> FolderImportResponse:
        """批量导入文件夹中指定索引的 .md 文件为 ai_draft 卡片。

        先 dry-run 扫描，再对指定索引执行实际导入。
        """
        from mindforge_web.schemas import FolderImportResponse
        from mindforge_web.schemas.import_export import _FolderImportResultItem

        preview = self.preview_folder_import(folder_path)
        index_map = {f.index: f for f in preview.files}

        results: list[_FolderImportResultItem] = []
        created = skipped = failed = 0

        for idx in indices:
            file_info = index_map.get(idx)
            if file_info is None:
                results.append(_FolderImportResultItem(
                    index=idx, filename=f"index_{idx}",
                    status="failed",
                    error="索引无效：不在预览列表中",
                ))
                failed += 1
                continue

            if file_info.error is not None:
                results.append(_FolderImportResultItem(
                    index=idx, filename=file_info.filename,
                    status="skipped",
                    title=file_info.title,
                    error=file_info.error,
                ))
                skipped += 1
                continue

            filepath = Path(folder_path).resolve() / file_info.filename
            try:
                raw = filepath.read_text(encoding="utf-8")
                title, body = self._parse_markdown_title_body(raw, file_info.filename)

                if not title.strip():
                    results.append(_FolderImportResultItem(
                        index=idx, filename=file_info.filename,
                        status="skipped",
                        error="无法提取标题",
                    ))
                    skipped += 1
                    continue

                imported = self.import_card(title, body, file_info.filename)
                results.append(_FolderImportResultItem(
                    index=idx, filename=file_info.filename,
                    status="created",
                    card_id=imported.id,
                    title=imported.title,
                ))
                created += 1
            except Exception as e:
                results.append(_FolderImportResultItem(
                    index=idx, filename=file_info.filename,
                    status="failed",
                    error=str(e),
                ))
                failed += 1

        return FolderImportResponse(
            folder_path=folder_path,
            results=results,
            created_count=created,
            skipped_count=skipped,
            failed_count=failed,
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_markdown_title_body(raw: str, filename: str) -> tuple[str, str]:
        """从 markdown 文本中提取标题和正文。

        标题提取优先级：YAML frontmatter title → 第一个 # heading → 文件名。
        """
        body = raw
        title = ""

        # 提取 YAML frontmatter 中的 title
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                fm_lines = parts[1].strip().split("\n")
                for line in fm_lines:
                    if line.startswith("title:") or line.startswith("title :"):
                        title = line.split(":", 1)[1].strip().strip("\"'")
                        break
                body = parts[2].strip()

        # 如果 frontmatter 没有 title，从第一个 # heading 提取
        if not title:
            for line in body.split("\n"):
                stripped = line.strip()
                if stripped.startswith("# ") and not stripped.startswith("## "):
                    title = stripped[2:].strip()
                    break

        # 最后 fallback 到文件名
        if not title:
            title = filename.replace(".md", "").replace("_", " ").replace("-", " ")

        return title, body

    def _find_duplicates(
        self, title: str,
    ) -> list[_PotentialDuplicateResponse]:
        """检测与已有卡片的 title 重复（exact match + fuzzy Jaccard）。

        对已有 CardSummary 做 title-level 匹配。
        不读取 body（避免 IO 开销），best-effort，失败不阻塞导入。
        """
        from mindforge_web.schemas.import_export import _PotentialDuplicateResponse

        results: list[_PotentialDuplicateResponse] = []
        title_lower = title.strip().lower()
        if not title_lower:
            return results

        title_words = set(title_lower.split())

        try:
            for card_summary in iter_cards(
                self._cfg.vault,
                _use_cache=True,
            ):
                if card_summary.id is None:
                    continue

                ct = (card_summary.title or "").strip()
                ct_lower = ct.lower()
                if not ct_lower:
                    continue

                # Exact title match → 1.0
                if ct_lower == title_lower:
                    results.append(_PotentialDuplicateResponse(
                        card_id=card_summary.id,
                        title=ct,
                        rel_path=card_summary.rel_path or "",
                        similarity=1.0,
                        match_type="exact_hash",
                    ))
                    continue

                # Fuzzy Jaccard on word sets
                ct_words = set(ct_lower.split())
                if not title_words or not ct_words:
                    continue

                intersection = title_words & ct_words
                union = title_words | ct_words
                jaccard = len(intersection) / len(union) if union else 0.0

                if jaccard >= 0.6:
                    results.append(_PotentialDuplicateResponse(
                        card_id=card_summary.id,
                        title=ct,
                        rel_path=card_summary.rel_path or "",
                        similarity=round(jaccard, 2),
                        match_type="title_fuzzy",
                    ))
        except Exception:
            # 去重是 best-effort，失败不阻塞导入
            pass

        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:5]
