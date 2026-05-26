"""Import/Export API schemas.

中文学习型说明：这是主路径 Import/Export 的 Web API 契约。从 schemas/__init__.py
提取到独立模块，减少单文件巨石，提高 import/export 相关改动的可发现性。
Schema 定义本身不变，backend-compatible re-export 确保所有现有 import 路径继续工作。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExportCardsRequest(BaseModel):
    card_ids: list[str]
    format: str = "markdown"  # "markdown" | "json" | "opml"


class ExportCardsResponse(BaseModel):
    markdown: str = ""
    json_data: str = Field(default="", alias="json")
    opml: str = ""
    format: str = "markdown"
    card_count: int = 0


class ImportCardRequest(BaseModel):
    title: str
    body: str
    source_name: str = ""


class _PotentialDuplicateResponse(BaseModel):
    """疑似重复卡片引用 — v2.4 U2。"""
    card_id: str
    title: str
    rel_path: str
    similarity: float  # 0.0-1.0，1.0 = exact hash match
    match_type: str  # "exact_hash" | "title_fuzzy"


class ImportCardResponse(BaseModel):
    id: str
    title: str
    rel_path: str
    status: str
    created_at: str
    # v 2.4 U2
    potential_duplicates: list[_PotentialDuplicateResponse] = Field(default_factory=list)


# ── v2.4 U3 Batch Paste Import ──────────────────────


class BatchImportCardItem(BaseModel):
    """批量导入中的单篇内容。"""
    title: str
    body: str


class BatchImportCardRequest(BaseModel):
    """批量粘贴导入请求 — v2.4 U3。"""
    items: list[BatchImportCardItem]
    source_name: str = ""


class BatchImportCardResponse(BaseModel):
    results: list[ImportCardResponse]
    created_count: int


# ── v2.4 U1 Folder Import ──────────────────────


class FolderImportPreviewRequest(BaseModel):
    """扫描指定文件夹，dry-run 预览可导入的 .md 文件。"""
    folder_path: str


class _FolderImportPreviewFile(BaseModel):
    """单个 .md 文件的预览信息。"""
    index: int
    filename: str
    title: str
    body_preview: str  # 前 200 字符预览
    size_bytes: int
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None  # 非空表示该文件无法导入
    potential_duplicates: list[_PotentialDuplicateResponse] = Field(default_factory=list)


class FolderImportPreviewResponse(BaseModel):
    folder_path: str
    total_files: int
    importable_count: int
    files: list[_FolderImportPreviewFile]
    folder_warning: str | None = None


class FolderImportRequest(BaseModel):
    """确认批量导入文件夹中的指定文件。"""
    folder_path: str
    indices: list[int]  # 选择导入的文件索引（来自 preview）


class _FolderImportResultItem(BaseModel):
    """单个文件导入结果。"""
    index: int
    filename: str
    status: str  # "created" | "skipped" | "failed"
    card_id: str | None = None
    title: str | None = None
    error: str | None = None


class FolderImportResponse(BaseModel):
    folder_path: str
    results: list[_FolderImportResultItem]
    created_count: int
    skipped_count: int
    failed_count: int
