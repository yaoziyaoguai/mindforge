"""MindForge 本地安全边界 policy。

中文学习型说明：本模块只表达"系统边界是什么"以及少量纯判断，例如机器
派生层路径是否被禁止。它不渲染 UI、不读取 `.env`、不调用 LLM、不写文件、
不改变 approval/review/Obsidian 状态，避免 safety policy 变成新的业务巨石。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SafetyBoundary:
    key: str
    label: str
    statement: str


LOCAL_FIRST_BOUNDARIES: tuple[SafetyBoundary, ...] = (
    SafetyBoundary("local_first", "local-first", "single-machine local data; no cloud runtime by default"),
    SafetyBoundary("fake_provider_default", "fake provider", "fake provider remains the default safe path"),
    SafetyBoundary("no_env_read", "no .env read", "safe dry-run/service paths do not read real .env files"),
    SafetyBoundary("no_real_llm", "no real LLM", "safe dry-run/service paths do not call real LLM providers"),
    SafetyBoundary("no_telemetry_upload", "no telemetry upload", "telemetry is local-only and never uploaded"),
    SafetyBoundary("no_rag", "no RAG", "lexical recall is not RAG and does not call an LLM"),
    SafetyBoundary("no_embedding", "no embedding", "lexical recall does not create embeddings or vectors"),
    SafetyBoundary("no_obsidian_plugin", "no Obsidian plugin", "Obsidian integration is CLI dry-run/staged export only"),
    SafetyBoundary("no_web_ui", "no Web UI", "MindForge remains a CLI-first local product"),
    SafetyBoundary("human_approved_gate", "human approved", "human_approved requires explicit user approval"),
    SafetyBoundary(
        "no_formal_obsidian_note_write",
        "no formal Obsidian note write",
        "current Obsidian flow stops at dry-run/staged-export/preflight/manual inspection",
    ),
)

OBSIDIAN_MANIFEST_SAFETY_LABELS: dict[str, str] = {
    "no_formal_obsidian_note_write": "no formal Obsidian note write",
    "no_real_llm": "no real LLM",
    "no_env_read": "no .env read",
    "no_telemetry_upload": "no telemetry upload",
    "no_runtime_logs_or_index_in_export": "no runtime/cache/index/log export",
}

WRITE_GATE_FORBIDDEN_DERIVED_PARTS: tuple[str, ...] = (
    "runtime",
    "cache",
    "index",
    "logs",
    "sqlite",
    "vector",
    "vectors",
    "graph",
)

LEXICAL_RECALL_BOUNDARY_LINE = "Boundary: local lexical recall only; no RAG, no embedding, no LLM, no .env, no upload."
OBSIDIAN_WORKFLOW_SAFETY_LINE = (
    "Safety: disposable non-sensitive vault copy only; no .env, no real LLM, no formal note writes."
)
OBSIDIAN_WORKFLOW_BOUNDARY_LINE = (
    "Boundary: dry-run/staged-export/diff/preflight/manual inspection only; no apply command in this version."
)


def obsidian_manifest_safety_flags() -> dict[str, bool]:
    """返回 staged export manifest 必须声明的安全旗标。"""
    return dict.fromkeys(OBSIDIAN_MANIFEST_SAFETY_LABELS, True)


def forbidden_derived_parts(path: Path) -> tuple[str, ...]:
    """返回路径中命中的机器派生层片段。

    中文学习型说明：write-gate prep 不能让 runtime/cache/index/logs/sqlite/vector/
    graph 这些机器派生层混入正式 Obsidian note 路径。这里只检查 path.parts，
    不解析 vault、不读文件、不决定 CLI 输出。
    """
    parts = {part.lower() for part in path.parts}
    return tuple(sorted(parts & set(WRITE_GATE_FORBIDDEN_DERIVED_PARTS)))


def boundary_statement(key: str) -> str:
    """按 key 取安全边界说明，便于 tests/docs/CLI 复用稳定 policy 数据。"""
    for boundary in LOCAL_FIRST_BOUNDARIES:
        if boundary.key == key:
            return boundary.statement
    raise KeyError(key)
