"""v0.7.16 — Safety policy 边界测试。

学习要点：safety_policy 只表达 MindForge 的本地安全边界和少量纯判断。
它不能依赖 CLI/presenter，也不能读取 `.env`、调用 LLM、写文件或改变状态。
"""

from __future__ import annotations

import socket
from pathlib import Path

from mindforge.safety_policy import (
    LEXICAL_RECALL_BOUNDARY_LINE,
    LOCAL_FIRST_BOUNDARIES,
    OBSIDIAN_MANIFEST_SAFETY_LABELS,
    OBSIDIAN_WORKFLOW_BOUNDARY_LINE,
    OBSIDIAN_WORKFLOW_SAFETY_LINE,
    boundary_statement,
    forbidden_derived_parts,
    obsidian_manifest_safety_flags,
)


def _policy_text() -> str:
    return "\n".join(f"{item.key} {item.label} {item.statement}" for item in LOCAL_FIRST_BOUNDARIES)


def test_safety_policy_lists_core_boundaries() -> None:
    """核心边界必须集中可见，避免散落文案互相漂移。"""
    text = _policy_text()

    assert "no_formal_obsidian_note_write" in text
    assert "no .env" in text
    assert "no real LLM" in text
    assert "never uploaded" in text
    assert "no RAG" in text
    assert "embeddings" in text
    assert "no Obsidian plugin" in text
    assert "no Web UI" in text
    assert "fake provider" in text
    assert "human_approved requires explicit user approval" in text


def test_safety_policy_manifest_flags_match_preflight_requirements() -> None:
    """manifest safety flags 是 preflight 可消费的 policy 数据，不是 CLI 文案。"""
    flags = obsidian_manifest_safety_flags()

    assert flags == {key: True for key in OBSIDIAN_MANIFEST_SAFETY_LABELS}
    assert flags["no_formal_obsidian_note_write"] is True
    assert flags["no_real_llm"] is True
    assert flags["no_env_read"] is True
    assert flags["no_telemetry_upload"] is True
    assert flags["no_runtime_logs_or_index_in_export"] is True


def test_safety_policy_forbidden_derived_paths() -> None:
    """runtime/cache/index/logs/sqlite/vector/graph 等机器派生层不能进入 write gate。"""
    assert forbidden_derived_parts(Path("90-System/MindForge/Runtime/note.md")) == ("runtime",)
    assert forbidden_derived_parts(Path("vault/cache/vector/Graph.md")) == ("cache", "vector")
    assert forbidden_derived_parts(Path("02-Knowledge/human-note.md")) == ()


def test_safety_policy_boundary_lines_are_reusable() -> None:
    """recall/workflow 可以复用稳定边界句，但 policy 不负责 Rich 渲染。"""
    assert "local lexical recall only" in LEXICAL_RECALL_BOUNDARY_LINE
    assert "no RAG" in LEXICAL_RECALL_BOUNDARY_LINE
    assert "no formal note writes" in OBSIDIAN_WORKFLOW_SAFETY_LINE
    assert "no apply command" in OBSIDIAN_WORKFLOW_BOUNDARY_LINE
    assert "single-machine local data" in boundary_statement("local_first")


def test_safety_policy_no_cli_env_llm_file_or_state_dependency(tmp_path: Path, monkeypatch) -> None:
    """policy 模块无副作用：不读 `.env`、不联网、不写文件、不依赖 Typer/Rich。"""
    (tmp_path / ".env").write_text("SECRET=value\n", encoding="utf-8")

    def _blocked(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("safety_policy 不应触发外部边界")

    monkeypatch.setattr("mindforge.env_loader.load_dotenv_silently", _blocked)
    monkeypatch.setattr("mindforge.llm.build_providers", _blocked)
    monkeypatch.setattr(socket, "socket", _blocked)

    assert obsidian_manifest_safety_flags()["no_env_read"] is True
    source = Path("src/mindforge/safety_policy.py").read_text(encoding="utf-8")

    assert "import typer" not in source
    assert "from rich" not in source
    assert "load_dotenv" not in source
    assert "build_providers" not in source
    assert "write_text" not in source
    assert "read_text" not in source
    assert not (tmp_path / ".mindforge").exists()
