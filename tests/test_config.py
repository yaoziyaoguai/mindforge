"""配置加载与校验单测。

覆盖：
- 加载真实的 ``configs/mindforge.yaml`` / ``learning_tracks.yaml``（确保 M0 文件可被代码消费）；
- 各种校验路径：active_profile 不存在、stage 缺失、source_type 未知、alias 不存在等。

不依赖任何外部网络 / LLM。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mindforge.assets_runtime import bundled_asset_path_for_process
from mindforge.config import (
    ConfigError,
    REQUIRED_STAGES,
    load_learning_tracks,
    load_mindforge_config,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "configs"


# ---------------------------------------------------------------------------
# 真实配置文件可被加载
# ---------------------------------------------------------------------------


def test_real_mindforge_yaml_loads() -> None:
    cfg = load_mindforge_config(bundled_asset_path_for_process("configs", "mindforge.yaml"))
    # vault
    assert cfg.vault.inbox_root == "00-Inbox"
    # sources
    assert "cubox_markdown" in cfg.sources.enabled
    assert "plain_markdown" in cfg.sources.enabled
    active = {e.source_type for e in cfg.sources.active_entries()}
    # v0.2.4 起 webclip_markdown / chat_export 默认启用（真实 adapter 已落地）
    assert active == {
        "cubox_markdown",
        "plain_markdown",
        "webclip_markdown",
        "chat_export",
    }
    # llm
    # 真实 dogfood 阶段：新用户主配置默认指向 openai_compatible；缺 key 时
    # watch/import/process 会友好失败，不会 fallback 到 fake。
    assert cfg.llm.active_profile == "openai_compatible"
    assert "anthropic_coding_plan" in cfg.llm.profiles
    assert "anthropic" in cfg.llm.profiles
    assert "openai_compatible" in cfg.llm.profiles
    for stage in REQUIRED_STAGES:
        m = cfg.llm.resolve_stage(stage)
        assert m.alias in cfg.llm.models
        assert m.type == "openai_compatible"
    # 真实路径模型一律不允许把 secret 写进 yaml
    openai = cfg.llm.models["openai_strong"]
    assert openai.type == "openai_compatible"
    assert openai.base_url_env == "MINDFORGE_OPENAI_BASE_URL"
    assert openai.api_key_env == "MINDFORGE_OPENAI_API_KEY"
    assert openai.model_env == "MINDFORGE_OPENAI_MODEL"
    assert openai.model == "gpt-4o-mini"
    assert openai.base_url == "https://api.openai.com/v1"  # endpoint 不是 secret
    anthropic = cfg.llm.models["anthropic_strong"]
    assert anthropic.type == "anthropic_compatible"
    assert anthropic.provider == "anthropic"
    assert anthropic.base_url_env == "MINDFORGE_ANTHROPIC_BASE_URL"
    assert anthropic.api_key_env == "MINDFORGE_ANTHROPIC_API_KEY"
    assert anthropic.model_env == "MINDFORGE_ANTHROPIC_MODEL"
    assert anthropic.model == "claude-3-5-haiku-latest"
    # prompts
    assert cfg.prompts.for_stage("triage") == "v1"
    assert cfg.prompts.for_stage("link_suggestion") == "v1"


def test_real_learning_tracks_yaml_loads() -> None:
    lt = load_learning_tracks(CONFIG_DIR / "learning_tracks.yaml")
    ids = {t.id for t in lt.tracks}
    assert "agent-runtime" in ids
    assert "unrouted" in ids
    assert lt.by_id("agent-runtime") is not None
    assert lt.by_id("nonexistent") is None


# ---------------------------------------------------------------------------
# 校验失败路径（用临时 yaml 文件构造各种坏配置）
# ---------------------------------------------------------------------------


def _write_yaml(tmp_path: Path, data: dict) -> Path:
    # 构造 configs/ 目录结构以便 base_dir 推断
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir()
    p = cfg_dir / "mindforge.yaml"
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return p


def _minimal_valid_config() -> dict:
    return {
        "version": 0.1,
        "vault": {
            "root": "/tmp/vault",
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {
            "enabled": ["plain_markdown"],
            "registry": {
                "plain_markdown": {
                    "adapter": "PlainMarkdownAdapter",
                    "inbox_subdir": "ManualNotes",
                    "file_glob": "*.md",
                    "enabled": True,
                }
            },
        },
        "state": {
            "workdir": ".mindforge",
            "state_file": "state.json",
            "runs_dir": "runs",
            "index_file": "index.jsonl",
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "default",
            "profiles": {
                "default": {
                    "triage": "m1",
                    "distill": "m1",
                    "link_suggestion": "m1",
                    "review_questions": "m1",
                    "action_extraction": "m1",
                }
            },
            "models": {
                "m1": {
                    "provider": "p",
                    "type": "openai_compatible",
                    "base_url": "http://x",
                    "model": "m",
                    "timeout_seconds": 60,
                    "max_retries": 1,
                }
            },
        },
        "prompts": {
            "triage_version": "v1",
            "distill_version": "v1",
            "link_suggestion_version": "v1",
            "review_questions_version": "v1",
            "action_extraction_version": "v1",
        },
        "logging": {"level": "INFO", "file": ".mindforge/x.log"},
    }


def test_minimal_valid_config(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path, _minimal_valid_config())
    cfg = load_mindforge_config(p)
    assert cfg.llm.active_profile == "default"


def test_relative_workdir_resolves_against_cwd_not_config_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.5.2: copied configs must not make runtime state depend on repo layout.

    Packaged users may keep `mindforge.yaml` anywhere. A relative `.mindforge`
    should mean "under the directory I run MindForge from", not "two levels above
    wherever the config file happens to live".
    """
    data = _minimal_valid_config()
    data["state"]["workdir"] = ".mindforge"
    cfg_dir = tmp_path / "deeply" / "nested"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    run_dir = tmp_path / "run-from-here"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)

    cfg = load_mindforge_config(cfg_path)
    assert cfg.state.workdir == run_dir / ".mindforge"


def test_absolute_workdir_is_unchanged(tmp_path: Path) -> None:
    """绝对 workdir 是用户显式选择，不能被 cwd 或 package asset 规则覆盖。"""
    data = _minimal_valid_config()
    abs_dir = tmp_path / "runtime" / ".mindforge"
    data["state"]["workdir"] = str(abs_dir)
    p = _write_yaml(tmp_path, data)
    cfg = load_mindforge_config(p)
    assert cfg.state.workdir == abs_dir


def test_active_profile_missing(tmp_path: Path) -> None:
    data = _minimal_valid_config()
    data["llm"]["active_profile"] = "ghost"
    p = _write_yaml(tmp_path, data)
    with pytest.raises(ConfigError, match="active_profile"):
        load_mindforge_config(p)


def test_profile_missing_stage(tmp_path: Path) -> None:
    data = _minimal_valid_config()
    data["llm"]["profiles"]["default"].pop("distill")
    p = _write_yaml(tmp_path, data)
    with pytest.raises(ConfigError, match="distill"):
        load_mindforge_config(p)


def test_profile_alias_unknown(tmp_path: Path) -> None:
    data = _minimal_valid_config()
    data["llm"]["profiles"]["default"]["distill"] = "ghost"
    p = _write_yaml(tmp_path, data)
    with pytest.raises(ConfigError, match="ghost"):
        load_mindforge_config(p)


def test_source_type_unknown(tmp_path: Path) -> None:
    data = _minimal_valid_config()
    data["sources"]["registry"]["unknown_type"] = {
        "adapter": "X",
        "inbox_subdir": "X",
        "file_glob": "*.x",
    }
    p = _write_yaml(tmp_path, data)
    with pytest.raises(ConfigError, match="unknown_type"):
        load_mindforge_config(p)


def test_enabled_not_in_registry(tmp_path: Path) -> None:
    data = _minimal_valid_config()
    data["sources"]["enabled"].append("pdf")
    p = _write_yaml(tmp_path, data)
    with pytest.raises(ConfigError, match="pdf"):
        load_mindforge_config(p)


def test_missing_required_top_field(tmp_path: Path) -> None:
    data = _minimal_valid_config()
    data.pop("triage")
    p = _write_yaml(tmp_path, data)
    with pytest.raises(ConfigError, match="triage"):
        load_mindforge_config(p)
