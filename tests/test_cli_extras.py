"""CLI 扩展功能测试：--profile / --dry-run / llm ping。

不调用任何真实网络；llm ping 不发 HTTP；--dry-run 不写卡片。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.cli import app
from mindforge import env_loader as el

runner = CliRunner()


def test_root_help_documents_cwd_first_vault_resolution() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0, result.output
    assert "优先级：explicit --vault" in result.output
    assert "cwd/ancestor vault > project root" in result.output
    assert "configs/mindforge.yaml 的 vault.root" in result.output
    assert "configured/bundled fallback" in result.output

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
TEMPLATE_PATH = REPO_ROOT / "templates" / "knowledge_card.md.j2"
TRACKS_PATH = REPO_ROOT / "configs" / "learning_tracks.yaml"


@pytest.fixture(autouse=True)
def _reset_dotenv() -> None:
    el.reset_for_tests()


def _build_minimal_cfg(tmp_path: Path) -> tuple[Path, Path]:
    """构造一个含 fake + anthropic 双 profile 的最小可用配置。"""
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)
    src = vault / "00-Inbox" / "ManualNotes" / "n1.md"
    src.write_text("---\ntitle: hello\n---\n\nbody about agent runtime\n", encoding="utf-8")

    cfg = {
        "version": 0.1,
        "vault": {
            "root": str(vault),
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
            "workdir": str(tmp_path / ".mindforge"),
            "state_file": "state.json",
            "runs_dir": "runs",
            "index_file": "index.jsonl",
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {
                "fake": {
                    "triage": "f",
                    "distill": "f",
                    "link_suggestion": "f",
                    "review_questions": "f",
                    "action_extraction": "f",
                },
                "anthropic_coding_plan": {
                    "triage": "a",
                    "distill": "a",
                    "link_suggestion": "a",
                    "review_questions": "a",
                    "action_extraction": "a",
                },
            },
            "models": {
                "f": {"provider": "fake", "type": "fake", "model": "fake-x"},
                "a": {
                    "provider": "dashscope_coding_plan",
                    "type": "anthropic_compatible",
                    "base_url_env": "MINDFORGE_LLM_BASE_URL",
                    "api_key_env": "MINDFORGE_LLM_API_KEY",
                    "version_env": "MINDFORGE_LLM_VERSION",
                    "model_env": "MINDFORGE_LLM_MODEL_STRONG",
                    "model": "qwen3-coder-plus",
                },
            },
        },
        "prompts": {
            "triage_version": "v1",
            "distill_version": "v1",
            "link_suggestion_version": "v1",
            "review_questions_version": "v1",
            "action_extraction_version": "v1",
        },
        "logging": {"level": "INFO", "file": str(tmp_path / "mf.log")},
    }
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return cfg_path, vault


# ---------------------------------------------------------------------------
# --profile
# ---------------------------------------------------------------------------


def test_process_profile_override_unknown_fails(tmp_path: Path) -> None:
    cfg_path, _ = _build_minimal_cfg(tmp_path)
    r = runner.invoke(
        app,
        [
            "process", "--config", str(cfg_path),
            "--prompts-dir", str(PROMPTS_DIR),
            "--tracks", str(TRACKS_PATH),
            "--template", str(TEMPLATE_PATH),
            "--profile", "ghost",
        ],
    )
    assert r.exit_code == 2
    assert "ghost" in r.output


def test_process_profile_override_works(tmp_path: Path) -> None:
    cfg_path, _ = _build_minimal_cfg(tmp_path)
    # 兼容旧 fixture 输入，但用户可见输出必须落在真实模型配置语义上。
    r = runner.invoke(
        app,
        [
            "process", "--config", str(cfg_path),
            "--prompts-dir", str(PROMPTS_DIR),
            "--tracks", str(TRACKS_PATH),
            "--template", str(TEMPLATE_PATH),
            "--profile", "fake",
        ],
    )
    assert r.exit_code == 0, r.output
    assert "model setup =" in r.output
    assert "active_profile" not in r.output


# ---------------------------------------------------------------------------
# --dry-run
# ---------------------------------------------------------------------------


def test_process_dry_run_does_not_write(tmp_path: Path) -> None:
    cfg_path, vault = _build_minimal_cfg(tmp_path)
    r = runner.invoke(
        app,
        [
            "process", "--config", str(cfg_path),
            "--prompts-dir", str(PROMPTS_DIR),
            "--tracks", str(TRACKS_PATH),
            "--template", str(TEMPLATE_PATH),
            "--dry-run",
        ],
    )
    assert r.exit_code == 0, r.output
    # 卡片目录无文件
    assert list((vault / "20-Knowledge-Cards").rglob("*.md")) == []
    # state.json 不写
    assert not (tmp_path / ".mindforge" / "state.json").exists()
    # 但 runs jsonl 仍记录了 pipeline 事件
    runs = list((tmp_path / ".mindforge" / "runs").glob("*.jsonl"))
    assert len(runs) == 1


# ---------------------------------------------------------------------------
# llm ping — 不发 HTTP
# ---------------------------------------------------------------------------


def test_llm_ping_fake_profile_always_ok(tmp_path: Path) -> None:
    cfg_path, _ = _build_minimal_cfg(tmp_path)
    r = runner.invoke(app, ["llm", "ping", "--config", str(cfg_path)])
    assert r.exit_code == 0, r.output
    assert "active_profile = fake" in r.output


def test_llm_ping_missing_required_env_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _ = _build_minimal_cfg(tmp_path)
    # 切到 tmp_path 避免 cwd 的 .env 被加载（项目根可能有真实 .env）
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MINDFORGE_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("MINDFORGE_LLM_API_KEY", raising=False)
    r = runner.invoke(
        app,
        ["llm", "ping", "--config", str(cfg_path), "--profile", "anthropic_coding_plan"],
    )
    assert r.exit_code == 1
    assert "MISSING" in r.output


def test_llm_ping_with_envs_set_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _ = _build_minimal_cfg(tmp_path)
    monkeypatch.setenv("MINDFORGE_LLM_BASE_URL", "https://fake.example.com")
    monkeypatch.setenv("MINDFORGE_LLM_API_KEY", "fake-key-PLACEHOLDER")
    r = runner.invoke(
        app,
        ["llm", "ping", "--config", str(cfg_path), "--profile", "anthropic_coding_plan"],
    )
    assert r.exit_code == 0, r.output
    # 关键安全：不能把 api_key 值打印出来
    assert "fake-key-PLACEHOLDER" not in r.output


def test_llm_ping_does_not_send_http(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """证明 ping 不触发 HTTP：把 httpx.Client.post 替换成会爆炸的 mock。"""
    cfg_path, _ = _build_minimal_cfg(tmp_path)
    monkeypatch.setenv("MINDFORGE_LLM_BASE_URL", "https://fake.example.com")
    monkeypatch.setenv("MINDFORGE_LLM_API_KEY", "fake-key-PLACEHOLDER")

    import httpx

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("llm ping 不应触发任何 HTTP 调用")

    monkeypatch.setattr(httpx.Client, "post", boom)
    r = runner.invoke(
        app,
        ["llm", "ping", "--config", str(cfg_path), "--profile", "anthropic_coding_plan"],
    )
    assert r.exit_code == 0, r.output


# ---------------------------------------------------------------------------
# model_env 覆盖：LLMClient.resolve_model_for_stage 应反映 env 值
# ---------------------------------------------------------------------------


def test_model_env_overrides_yaml_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path, _ = _build_minimal_cfg(tmp_path)
    monkeypatch.setenv("MINDFORGE_LLM_BASE_URL", "https://fake.example.com")
    monkeypatch.setenv("MINDFORGE_LLM_API_KEY", "fake-key")
    monkeypatch.setenv("MINDFORGE_LLM_MODEL_STRONG", "glm-5")

    from mindforge.config import load_mindforge_config
    from dataclasses import replace as _replace
    cfg = load_mindforge_config(cfg_path)
    cfg = _replace(cfg, llm=_replace(cfg.llm, active_profile="anthropic_coding_plan"))
    from mindforge.llm import LLMClient, build_providers
    providers = build_providers(cfg.llm)
    client = LLMClient(llm_config=cfg.llm, providers=providers)
    resolved = client.resolve_model_for_stage("distill")
    assert resolved.actual_model == "glm-5"  # env 覆盖了 yaml 的 qwen3-coder-plus
