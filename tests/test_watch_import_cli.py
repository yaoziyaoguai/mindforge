"""CLI e2e tests for simple watch/import ingestion.

这些测试用 offline LLM test double 与临时 vault 验证用户级 ingestion 入口：
watch = 注册并立即处理，import = 一次性处理且不注册。两者都只能生成
ai_draft，不能自动 approve。
"""

from __future__ import annotations

from pathlib import Path
import time

import yaml
from typer.testing import CliRunner

from mindforge.approval_service import approve_explicit_card
from mindforge.cards import read_card_frontmatter
from mindforge.cli import app
from mindforge.cli_runtime import load_cfg
from mindforge.config import load_mindforge_config
from mindforge_web.services.processing_run_service import get_processing_run
from mindforge.watch_registry import WatchRegistry, add_watch_source, registry_path_for_vault

runner = CliRunner()


def _write_config(tmp_path: Path, *, active_provider: str = "fake") -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    cfg = tmp_path / "mindforge.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
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
                    "workdir": ".mindforge",
                    "state_file": "state.json",
                    "runs_dir": "runs",
                    "index_file": "index.jsonl",
                    "backup_state": True,
                },
                "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
                "llm": {
                    "active": active_provider,
                    "providers": {
                        "fake": {
                            "type": "fake",
                            "purpose": "offline_demo_ci_deterministic_tests",
                        },
                        "openai_compatible": {
                            "type": "openai_compatible",
                            "api_key_env": "MINDFORGE_OPENAI_API_KEY",
                            "default_base_url": "https://example.invalid/v1",
                            "default_model": "gpt-4o-mini",
                        },
                        "anthropic": {
                            "type": "anthropic",
                            "api_key_env": "MINDFORGE_ANTHROPIC_API_KEY",
                            "base_url_env": "MINDFORGE_ANTHROPIC_BASE_URL",
                            "model_env": "MINDFORGE_ANTHROPIC_MODEL",
                            "default_base_url": "https://api.anthropic.com",
                            "default_model": "claude-3-5-haiku-latest",
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
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return cfg, vault


def _write_project_config(project_root: Path, *, active_provider: str = "fake") -> tuple[Path, Path]:
    """写入接近 init 产物的 project config，验证 CLI 默认路径解析。

    中文学习型说明：这里刻意把 ``vault.root`` 写成相对路径 ``vault``，测试
    loader 是否按 project root 解析，而不是按当前 shell cwd 解析。
    """

    vault = project_root / "vault"
    (vault / "00-Inbox" / "ManualNotes").mkdir(parents=True)
    cfg = project_root / "configs" / "mindforge.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {"root": "vault"},
                "llm": {
                    "active": active_provider,
                    "providers": {
                        "fake": {
                            "type": "fake",
                            "purpose": "offline_demo_ci_deterministic_tests",
                        },
                        "openai_compatible": {
                            "type": "openai_compatible",
                            "api_key_env": "MINDFORGE_OPENAI_API_KEY",
                            "base_url_env": "MINDFORGE_OPENAI_BASE_URL",
                            "model_env": "MINDFORGE_OPENAI_MODEL",
                            "default_base_url": "https://example.invalid/v1",
                            "default_model": "gpt-4o-mini",
                        },
                        "anthropic": {
                            "type": "anthropic",
                            "api_key_env": "MINDFORGE_ANTHROPIC_API_KEY",
                            "base_url_env": "MINDFORGE_ANTHROPIC_BASE_URL",
                            "model_env": "MINDFORGE_ANTHROPIC_MODEL",
                            "default_base_url": "https://api.anthropic.com",
                            "default_model": "claude-3-5-haiku-latest",
                        },
                    },
                },
                "telemetry": {"enabled": True, "local_only": True},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return cfg, vault


def _card_paths(vault: Path) -> list[Path]:
    return sorted((vault / "20-Knowledge-Cards").rglob("*.md"))


def _run_id_from_output(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("run_id: "):
            return line.split("run_id: ", 1)[1].strip()
    for line in output.splitlines():
        if "run_id=" in line:
            return line.split("run_id=", 1)[1].strip()
    raise AssertionError(f"missing run_id in output:\n{output}")


def _latest_run_status(cfg: Path, run_id: str):
    """测试观察 CLI async run 的只读边界。

    中文学习型说明：watch/import 命令只负责启动后台 processing；测试不能再
    从命令输出断言 pipeline counts，而要通过 durable ProcessingRun 观察最终
    状态。这和用户用 ``mindforge runs show`` 查看进度是同一产品模型。
    """

    return get_processing_run(load_cfg(cfg, read_env=False), run_id)


def _wait_for_cli_run(cfg: Path, output: str, *, timeout: float = 10.0):
    run_id = _run_id_from_output(output)
    deadline = time.monotonic() + timeout
    latest = None
    while time.monotonic() < deadline:
        latest = _latest_run_status(cfg, run_id)
        if latest is not None and latest.status not in {"queued", "running"}:
            return latest
        time.sleep(0.05)
    raise AssertionError(f"processing run did not finish: {run_id}, latest={latest}")


def _assert_run_counts(run, *, processed: int, skipped: int, failed: int, seen: int) -> None:
    assert run.summary.get("processed", 0) == processed
    assert run.summary.get("skipped", 0) == skipped
    assert run.summary.get("errors", 0) == failed
    assert run.summary.get("discovered", 0) == seen


def _set_triage_threshold(cfg: Path, threshold: int) -> None:
    raw = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    raw.setdefault("triage", {})["value_score_threshold"] = threshold
    cfg.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_watch_list_shows_default_inbox(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)

    result = runner.invoke(app, ["watch", "list", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "default-inbox" in result.output
    assert "00-Inbox" in result.output
    assert "default" in result.output


def test_watch_add_file_registers_and_generates_ai_draft_once(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source = tmp_path / "external-file.md"
    source.write_text("# External File\n\nbody\n", encoding="utf-8")

    first = runner.invoke(app, ["watch", "add", str(source), "--config", str(cfg)])
    second = runner.invoke(app, ["watch", "add", str(source), "--config", str(cfg)])

    assert first.exit_code == 0, first.output
    assert "registered" in first.output
    first_run = _wait_for_cli_run(cfg, first.output)
    _assert_run_counts(first_run, processed=1, skipped=0, failed=0, seen=1)
    assert second.exit_code == 0, second.output
    assert "already registered" in second.output
    assert "run_id: " in second.output
    cards = _card_paths(vault)
    assert len(cards) == 1
    assert read_card_frontmatter(cards[0])["status"] == "ai_draft"
    assert read_card_frontmatter(cards[0])["source_path"] == str(source.resolve())
    assert WatchRegistry.load(vault / ".mindforge" / "watched_sources.json").sources[0].path == source.resolve()
    assert source.exists()


def test_watch_add_output_explains_background_lifecycle_review_and_retry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """CLI watch add 必须进入后台 processing 产品心智。"""

    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source = tmp_path / "cli-lifecycle.md"
    source.write_text("# CLI Lifecycle\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["watch", "add", str(source), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "Background processing started." in result.output
    assert "run_id: " in result.output
    assert "You can continue using MindForge." in result.output
    assert "Check progress: mindforge runs show" in result.output
    assert "Drafts appear in: mindforge approve list after processing succeeds." in result.output
    assert "Processing completed in this command." not in result.output
    run = _latest_run_status(cfg, _run_id_from_output(result.output))
    assert run is not None
    assert run.status in {"queued", "running", "succeeded", "skipped", "failed", "partial_failed"}


def test_import_output_explains_background_lifecycle_review_and_retry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source = tmp_path / "import-lifecycle.md"
    source.write_text("# Import Lifecycle\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["import", str(source), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert "Background processing started." in result.output
    assert "run_id: " in result.output
    assert "You can continue using MindForge." in result.output
    assert "Check progress: mindforge runs show" in result.output
    assert "Processing completed in this command." not in result.output


def test_watch_and_import_help_describe_background_processing() -> None:
    """CLI help 必须教授异步主路径，而不是旧的同步生成 draft 心智。"""

    watch_help = runner.invoke(app, ["watch", "--help"])
    watch_add_help = runner.invoke(app, ["watch", "add", "--help"])
    import_help = runner.invoke(app, ["import", "--help"])

    for result in (watch_help, watch_add_help, import_help):
        assert result.exit_code == 0, result.output
        assert "background" in result.output.lower() or "后台" in result.output
        assert "立即生成 ai_draft" not in result.output
        assert "立即处理当前内容" not in result.output


def test_root_version_flag_is_available() -> None:
    """根级 --version 是普通 CLI 约定；保留 mindforge version 之外也要支持。"""

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert "MindForge v" in result.output


def test_status_does_not_create_run_logger_entry(tmp_path: Path, monkeypatch) -> None:
    """status 是 read/query path，不得创建 runs/*.jsonl 污染最近一次 run。

    中文学习型说明：processing/run state 应只由 command path 推进。status /
    watch status / runs show 只能读取已有状态，否则用户会看到
    ``cmd=status`` 取代真正的 processing run。
    """

    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    runs_dir = vault / ".mindforge" / "runs"

    result = runner.invoke(app, ["status", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert not list(runs_dir.glob("*.jsonl"))


def test_missing_model_key_error_uses_setup_language_without_env_words(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="anthropic")
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    source = tmp_path / "missing-key.md"
    source.write_text("# Missing Key\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["import", str(source), "--config", str(cfg)])
    run = _wait_for_cli_run(cfg, result.output)
    show = runner.invoke(app, ["runs", "show", run.run_id, "--config", str(cfg)])
    combined = f"{run.error_message} {run.message} {show.output}"

    assert result.exit_code == 0, result.output
    assert show.exit_code == 0, show.output
    assert "Model setup is incomplete" in combined
    for token in ("env", "environment variable", "<api_key_env>", "fake", "demo", "profile fake"):
        assert token not in combined.lower()


def test_watch_add_openai_compatible_missing_key_fails_without_fake_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """真实 provider 缺 key 时必须友好失败，不能偷偷落回 fake。

    中文学习型说明：watch/import 是真实 dogfood 主入口，但自动化边界仍然只到
    ``ai_draft``。缺少真实 provider secret 时，正确行为是明确告诉用户如何设置
    env，而不是用 fake 内容冒充真实模型产物。
    """

    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.watch_cli.load_dotenv_silently", lambda *_a, **_k: 0)
    source = tmp_path / "real-provider-note.md"
    source.write_text("# Real Provider Note\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["watch", "add", str(source), "--profile", "openai_compatible", "--config", str(cfg)],
    )

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=0, skipped=0, failed=1, seen=1)
    # 缺 key 时必须友好失败，不能偷偷落回 fake
    assert "Model setup is incomplete" in (run.error_message or run.message)
    assert _card_paths(vault) == []


def test_watch_add_anthropic_missing_key_fails_without_fake_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.watch_cli.load_dotenv_silently", lambda *_a, **_k: 0)
    source = tmp_path / "anthropic-note.md"
    source.write_text("# Anthropic Note\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["watch", "add", str(source), "--profile", "anthropic", "--config", str(cfg)],
    )

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=0, skipped=0, failed=1, seen=1)
    # 缺 key 时必须友好失败，不能偷偷落回 fake
    assert "Model setup is incomplete" in (run.error_message or run.message)
    assert _card_paths(vault) == []


def test_watch_add_uses_llm_active_without_cli_provider(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="openai_compatible")
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.watch_cli.load_dotenv_silently", lambda *_a, **_k: 0)
    source = tmp_path / "active-openai.md"
    source.write_text("# Active OpenAI\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["watch", "add", str(source), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=0, skipped=0, failed=1, seen=1)
    assert "Model setup is incomplete" in (run.error_message or run.message)
    assert _card_paths(vault) == []


def test_watch_add_provider_override_wins_over_active(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="anthropic")
    monkeypatch.chdir(vault)
    source = tmp_path / "override-fake.md"
    source.write_text("# Override Fake\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["watch", "add", str(source), "--provider", "fake", "--config", str(cfg)],
    )

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=1, skipped=0, failed=0, seen=1)
    assert len(_card_paths(vault)) == 1


def test_watch_add_unknown_provider_override_is_friendly(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source = tmp_path / "unknown-provider.md"
    source.write_text("# Unknown Provider\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["watch", "add", str(source), "--provider", "ghost", "--config", str(cfg)],
    )

    assert result.exit_code == 2, result.output
    assert "--provider 'ghost'" in result.output
    assert "llm.providers" in result.output


def test_watch_add_folder_and_delete_preserves_source_and_cards(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    folder = tmp_path / "folder"
    source = folder / "folder-note.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Folder Note\n\nbody\n", encoding="utf-8")

    added = runner.invoke(app, ["watch", "add", str(folder), "--config", str(cfg)])
    assert added.exit_code == 0, added.output
    run = _wait_for_cli_run(cfg, added.output)
    _assert_run_counts(run, processed=1, skipped=0, failed=0, seen=1)
    registry = WatchRegistry.load(vault / ".mindforge" / "watched_sources.json")
    deleted = runner.invoke(app, ["watch", "delete", registry.sources[0].id, "--config", str(cfg)])

    assert deleted.exit_code == 0, deleted.output
    assert "deleted" in deleted.output
    assert source.exists()
    assert len(_card_paths(vault)) == 1
    assert WatchRegistry.load(vault / ".mindforge" / "watched_sources.json").sources == ()


def test_watch_add_folder_recursively_processes_nested_supported_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    folder = tmp_path / "folder"
    nested = folder / "nested" / "folder-note.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# Folder Recursive\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["watch", "add", str(folder), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=1, skipped=0, failed=0, seen=1)
    assert len(_card_paths(vault)) == 1


def test_import_file_and_folder_do_not_register_watch(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    one = tmp_path / "import-one.md"
    folder = tmp_path / "import-folder"
    two = folder / "import-two.md"
    one.write_text("# Import One\n\nbody\n", encoding="utf-8")
    two.parent.mkdir(parents=True)
    two.write_text("# Import Two\n\nbody\n", encoding="utf-8")

    imported_file = runner.invoke(app, ["import", str(one), "--config", str(cfg)])
    imported_folder = runner.invoke(app, ["import", str(folder), "--config", str(cfg)])

    assert imported_file.exit_code == 0, imported_file.output
    file_run = _wait_for_cli_run(cfg, imported_file.output)
    assert imported_folder.exit_code == 0, imported_folder.output
    folder_run = _wait_for_cli_run(cfg, imported_folder.output)
    assert "Source import registered" in imported_file.output
    assert "Source import registered" in imported_folder.output
    _assert_run_counts(file_run, processed=1, skipped=0, failed=0, seen=1)
    _assert_run_counts(folder_run, processed=1, skipped=0, failed=0, seen=1)
    assert len(_card_paths(vault)) == 2
    assert not (vault / ".mindforge" / "watched_sources.json").exists()


def test_import_folder_uses_recursive_scan_policy_without_registering_watch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    folder = tmp_path / "import-folder"
    nested = folder / "nested" / "import-recursive.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# Import Recursive\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["import", str(folder), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=1, skipped=0, failed=0, seen=1)
    assert len(_card_paths(vault)) == 1
    assert not (vault / ".mindforge" / "watched_sources.json").exists()


def test_fresh_new_file_import_with_fake_is_processed_and_pending(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """fresh source identity 必须精确到具体文档，不能在 provider 前被误跳过。"""

    project = tmp_path / "project"
    cfg, vault = _write_project_config(project)
    source = vault / "00-Inbox" / "ManualNotes" / "fresh-new.md"
    source.write_text("# Fresh New\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(project)

    imported = runner.invoke(app, ["import", "vault/00-Inbox/ManualNotes/fresh-new.md", "--provider", "fake"])

    assert imported.exit_code == 0, imported.output
    _assert_run_counts(
        _wait_for_cli_run(project / "configs" / "mindforge.yaml", imported.output),
        processed=1,
        skipped=0,
        failed=0,
        seen=1,
    )
    pending = runner.invoke(app, ["approve", "list"])
    assert pending.exit_code == 0, pending.output
    assert "[1]" in pending.output
    assert "Fresh New" in pending.output or "fresh-new" in pending.output


def test_import_uses_active_fake_without_provider_override(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    _cfg, vault = _write_project_config(project, active_provider="fake")
    source = vault / "00-Inbox" / "ManualNotes" / "active-fake.md"
    source.write_text("# Active Fake\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(project)

    result = runner.invoke(app, ["import", "vault/00-Inbox/ManualNotes/active-fake.md"])

    assert result.exit_code == 0, result.output
    _assert_run_counts(
        _wait_for_cli_run(project / "configs" / "mindforge.yaml", result.output),
        processed=1,
        skipped=0,
        failed=0,
        seen=1,
    )


def test_high_value_explicit_import_defaults_to_processed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="fake")
    monkeypatch.chdir(vault)
    source = vault / "00-Inbox" / "ManualNotes" / "high-value.md"
    source.write_text(
        "# Agent Runtime Lessons\n\n"
        "背景：我们在真实 ingestion pipeline 中发现 state checkpoint 会影响重复处理。\n\n"
        "经验教训：source identity 必须包含 normalized source path，不能只依赖 content hash。\n\n"
        "可复习 insight：自动化只能生成 ai_draft，human_approved 必须由用户显式 approve。\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["import", str(source), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    _assert_run_counts(
        _wait_for_cli_run(cfg, result.output),
        processed=1,
        skipped=0,
        failed=0,
        seen=1,
    )


def test_low_value_explicit_import_defaults_to_triage_skip_with_hint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """explicit import 默认尊重 triage，避免低价值资料污染知识库。

    中文学习型说明：fake triage 固定给 value_score=7。这里把阈值提高到 10，
    稳定复现低价值路径；CLI 必须告诉用户分数、阈值和 --force 覆盖方式，
    而不是静默 skipped。
    """

    cfg, vault = _write_config(tmp_path)
    _set_triage_threshold(cfg, 10)
    monkeypatch.chdir(vault)
    source = vault / "00-Inbox" / "ManualNotes" / "explicit-low.md"
    source.write_text("# Explicit Low\n\nsmall note\n", encoding="utf-8")

    result = runner.invoke(app, ["import", str(source), "--provider", "fake", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=0, skipped=1, failed=0, seen=1)
    assert any("value_score=7 threshold=10" in reason for reason in run.skip_reasons)
    assert _card_paths(vault) == []


def test_low_value_explicit_import_force_overrides_triage_with_fake_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="fake")
    _set_triage_threshold(cfg, 10)
    monkeypatch.chdir(vault)
    source = vault / "00-Inbox" / "ManualNotes" / "active-low.md"
    source.write_text("# Active Low\n\nsmall note\n", encoding="utf-8")

    result = runner.invoke(app, ["import", str(source), "--force", "--config", str(cfg)])
    assert result.exit_code == 0, result.output
    _assert_run_counts(
        _wait_for_cli_run(cfg, result.output),
        processed=1,
        skipped=0,
        failed=0,
        seen=1,
    )
    pending = runner.invoke(app, ["approve", "list", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert pending.exit_code == 0, pending.output
    assert "[1]" in pending.output
    assert "Active Low" in pending.output or "active-low" in pending.output


def test_low_value_explicit_import_real_missing_key_fails_before_triage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """provider 配置错误优先报告，不能被 triage 或 force 吞掉。"""

    cfg, vault = _write_config(tmp_path, active_provider="anthropic")
    _set_triage_threshold(cfg, 10)
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    source = vault / "00-Inbox" / "ManualNotes" / "real-low.md"
    source.write_text("# Real Low\n\nsmall note\n", encoding="utf-8")

    default = runner.invoke(app, ["import", str(source), "--config", str(cfg)])
    forced = runner.invoke(app, ["import", str(source), "--force", "--config", str(cfg)])

    assert default.exit_code == 0, default.output
    default_run = _wait_for_cli_run(cfg, default.output)
    _assert_run_counts(default_run, processed=0, skipped=0, failed=1, seen=1)
    assert "Model setup is incomplete" in (default_run.error_message or default_run.message)
    assert forced.exit_code == 0, forced.output
    forced_run = _wait_for_cli_run(cfg, forced.output)
    _assert_run_counts(forced_run, processed=0, skipped=0, failed=1, seen=1)
    assert "Model setup is incomplete" in (forced_run.error_message or forced_run.message)
    assert _card_paths(vault) == []


def test_process_still_respects_low_value_triage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """自动 process 保留 triage 过滤，和 explicit import 语义分开。"""

    cfg, vault = _write_config(tmp_path, active_provider="fake")
    _set_triage_threshold(cfg, 10)
    monkeypatch.chdir(vault)
    source = vault / "00-Inbox" / "ManualNotes" / "auto-low.md"
    source.write_text("# Auto Low\n\nsmall note\n", encoding="utf-8")

    result = runner.invoke(app, ["process", "--config", str(cfg), "--limit", "1"])

    assert result.exit_code == 0, result.output
    assert "seen=1 processed=0 skipped=1 failed=0" in result.output
    assert "triage value_score=7 threshold=10 should_process=True" in result.output
    assert _card_paths(vault) == []


def test_process_output_explains_sync_lifecycle_review_and_retry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="fake")
    monkeypatch.chdir(vault)
    source = vault / "00-Inbox" / "ManualNotes" / "process-lifecycle.md"
    source.write_text("# Process Lifecycle\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["process", "--config", str(cfg), "--limit", "1"])

    assert result.exit_code == 0, result.output
    assert "Processing completed in this command." in result.output
    assert "Check drafts with: mindforge approve list" in result.output
    assert "If processing failed, fix the error above and retry this command." in result.output


def test_active_anthropic_missing_key_fails_not_skips(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """真实 provider 缺 key 是 failed，不是 already_processed/approved skipped。"""

    project = tmp_path / "project"
    _cfg, vault = _write_project_config(project, active_provider="anthropic")
    source = vault / "00-Inbox" / "ManualNotes" / "active-anthropic.md"
    source.write_text("# Active Anthropic\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(project)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)

    result = runner.invoke(app, ["import", "vault/00-Inbox/ManualNotes/active-anthropic.md"])

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(project / "configs" / "mindforge.yaml", result.output)
    _assert_run_counts(run, processed=0, skipped=0, failed=1, seen=1)
    assert "Model setup is incomplete" in (run.error_message or run.message)
    assert _card_paths(vault) == []


def test_two_different_new_files_with_same_content_skip_duplicate_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """content_hash 已生成过知识时，不因路径不同重复生成 draft。"""

    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    first = vault / "00-Inbox" / "ManualNotes" / "same-a.md"
    second = vault / "00-Inbox" / "ManualNotes" / "same-b.md"
    body = "---\ntitle: Same Content\n---\n\nidentical body\n"
    first.write_text(body, encoding="utf-8")
    second.write_text(body, encoding="utf-8")

    imported_first = runner.invoke(app, ["import", str(first), "--provider", "fake", "--config", str(cfg)])
    assert imported_first.exit_code == 0, imported_first.output
    _assert_run_counts(_wait_for_cli_run(cfg, imported_first.output), processed=1, skipped=0, failed=0, seen=1)
    imported_second = runner.invoke(app, ["import", str(second), "--provider", "fake", "--config", str(cfg)])
    assert imported_second.exit_code == 0, imported_second.output
    second_run = _wait_for_cli_run(cfg, imported_second.output)
    _assert_run_counts(second_run, processed=0, skipped=1, failed=0, seen=1)
    assert any("duplicate_content_hash" in reason for reason in second_run.skip_reasons)
    assert len(_card_paths(vault)) == 1


def test_folder_import_keeps_same_content_different_files_in_same_batch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """同批次 duplicate content_hash 只生成一张 draft，并解释 skipped 原因。

    中文学习型说明：folder watch/import 的扫描边界仍然是文件，但同一次
    ingestion 内如果 parser 产出相同 content_hash，下游知识卡会重复。
    因此 batch 内按 content_hash 去重，重复项以 duplicate_content_hash
    进入 skipped diagnostics。
    """

    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    folder = vault / "00-Inbox" / "ManualNotes" / "same-folder"
    folder.mkdir()
    body = "---\ntitle: Same Batch\n---\n\nidentical body\n"
    (folder / "same-1.md").write_text(body, encoding="utf-8")
    (folder / "same-2.md").write_text(body, encoding="utf-8")

    result = runner.invoke(app, ["import", str(folder), "--provider", "fake", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=1, skipped=1, failed=0, seen=2)
    assert any("duplicate_content_hash" in reason for reason in run.skip_reasons)
    assert len(_card_paths(vault)) == 1


def test_repeated_import_reports_precise_already_processed_skip(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source = vault / "00-Inbox" / "ManualNotes" / "repeat.md"
    source.write_text("# Repeat\n\nbody\n", encoding="utf-8")

    first = runner.invoke(app, ["import", str(source), "--provider", "fake", "--config", str(cfg)])
    assert first.exit_code == 0, first.output
    _assert_run_counts(_wait_for_cli_run(cfg, first.output), processed=1, skipped=0, failed=0, seen=1)
    second = runner.invoke(app, ["import", str(source), "--provider", "fake", "--config", str(cfg)])
    assert second.exit_code == 0, second.output
    second_run = _wait_for_cli_run(cfg, second.output)
    _assert_run_counts(second_run, processed=0, skipped=1, failed=0, seen=1)
    assert second_run.skip_reasons
    assert any("already_processed" in reason for reason in second_run.skip_reasons)
    assert second_run.source_path == str(source.resolve())
    assert second_run.skip_reasons
    assert second_run.skip_reasons
    assert second_run.skip_reasons


def test_same_file_different_path_forms_share_precise_source_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """同一文件的不同路径表达应归一到同一个 source identity。

    中文学习型说明：用户可以从 project root、vault root 或任意位置传绝对路径。
    这些表达最终都必须落到同一 normalized source path；重复导入可以跳过，
    但跳过原因要指向同一个具体文档，而不是目录或 content_hash。
    """

    project = tmp_path / "project"
    cfg, vault = _write_project_config(project)
    note = vault / "00-Inbox" / "ManualNotes" / "identity.md"
    note.write_text("# Identity\n\nbody\n", encoding="utf-8")

    monkeypatch.chdir(project)
    first = runner.invoke(
        app,
        ["import", "vault/00-Inbox/ManualNotes/identity.md", "--provider", "fake"],
    )
    monkeypatch.chdir(vault)
    second = runner.invoke(
        app,
        ["import", "00-Inbox/ManualNotes/identity.md", "--provider", "fake"],
    )
    third = runner.invoke(app, ["import", str(note.resolve()), "--provider", "fake"])

    assert first.exit_code == 0, first.output
    _assert_run_counts(_wait_for_cli_run(cfg, first.output), processed=1, skipped=0, failed=0, seen=1)
    second = runner.invoke(
        app,
        ["import", "00-Inbox/ManualNotes/identity.md", "--provider", "fake"],
    )
    assert second.exit_code == 0, second.output
    second_run = _wait_for_cli_run(cfg, second.output)
    _assert_run_counts(second_run, processed=0, skipped=1, failed=0, seen=1)
    third = runner.invoke(app, ["import", str(note.resolve()), "--provider", "fake"])
    assert third.exit_code == 0, third.output
    third_run = _wait_for_cli_run(cfg, third.output)
    _assert_run_counts(third_run, processed=0, skipped=1, failed=0, seen=1)
    assert any("already_processed" in reason for reason in second_run.skip_reasons)
    assert any("already_processed" in reason for reason in third_run.skip_reasons)
    assert len(_card_paths(vault)) == 1


def test_approved_source_a_does_not_skip_different_source_b(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    first = vault / "00-Inbox" / "ManualNotes" / "approved-a.md"
    second = vault / "00-Inbox" / "ManualNotes" / "new-b.md"
    first.write_text("# Approved A\n\nbody A\n", encoding="utf-8")
    second.write_text("# New B\n\nbody B\n", encoding="utf-8")

    imported_first = runner.invoke(app, ["import", str(first), "--provider", "fake", "--config", str(cfg)])
    _assert_run_counts(_wait_for_cli_run(cfg, imported_first.output), processed=1, skipped=0, failed=0, seen=1)
    card = _card_paths(vault)[0]
    approved = approve_explicit_card(load_mindforge_config(cfg), card)
    imported_second = runner.invoke(app, ["import", str(second), "--provider", "fake", "--config", str(cfg)])

    assert imported_first.exit_code == 0, imported_first.output
    assert approved.error is None
    assert imported_second.exit_code == 0, imported_second.output
    _assert_run_counts(_wait_for_cli_run(cfg, imported_second.output), processed=1, skipped=0, failed=0, seen=1)


def test_import_missing_file_fails_and_does_not_poison_future_processing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """missing import 是输入错误，不能写 processed/fingerprint 状态。

    真实 smoke 暴露过：先 import 不存在文件得到 seen=0，之后创建同名文件再
    import 会被 skipped。这个回归测试证明空跑不会污染后续处理。
    """

    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    missing = vault / "00-Inbox" / "ManualNotes" / "later-note.md"

    failed = runner.invoke(app, ["import", str(missing), "--provider", "fake", "--config", str(cfg)])

    assert failed.exit_code == 2, failed.output
    assert "File not found" in failed.output
    assert "cwd:" in failed.output
    assert "project root:" in failed.output
    assert "active vault:" in failed.output
    assert "tried" in failed.output
    assert "candidates" in failed.output
    assert _card_paths(vault) == []

    missing.write_text("# Later Note\n\nbody\n", encoding="utf-8")
    imported = runner.invoke(app, ["import", str(missing), "--provider", "fake", "--config", str(cfg)])
    assert imported.exit_code == 0, imported.output
    _assert_run_counts(_wait_for_cli_run(cfg, imported.output), processed=1, skipped=0, failed=0, seen=1)
    pending = runner.invoke(app, ["approve", "list", "--config", str(cfg)])
    assert pending.exit_code == 0, pending.output
    assert "[1]" in pending.output
    assert "Later Note" in pending.output or "later-note" in pending.output


def test_import_resolves_project_root_relative_path(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    cfg, vault = _write_project_config(project)
    note = vault / "00-Inbox" / "ManualNotes" / "project-relative.md"
    note.write_text("# Project Relative\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(project)

    result = runner.invoke(
        app,
        ["import", "vault/00-Inbox/ManualNotes/project-relative.md", "--provider", "fake"],
    )

    assert result.exit_code == 0, result.output
    _assert_run_counts(_wait_for_cli_run(cfg, result.output), processed=1, skipped=0, failed=0, seen=1)
    assert "project root:" in result.output
    assert len(_card_paths(vault)) == 1


def test_import_resolves_vault_relative_path_from_vault_root(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    cfg, vault = _write_project_config(project)
    note = vault / "00-Inbox" / "ManualNotes" / "vault-relative.md"
    note.write_text("# Vault Relative\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    result = runner.invoke(app, ["import", "00-Inbox/ManualNotes/vault-relative.md", "--provider", "fake"])

    assert result.exit_code == 0, result.output
    _assert_run_counts(_wait_for_cli_run(cfg, result.output), processed=1, skipped=0, failed=0, seen=1)
    assert f"active vault: {vault.resolve()}" in result.output
    assert len(_card_paths(vault)) == 1


def test_import_resolves_cwd_relative_path_from_project_child(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    cfg, vault = _write_project_config(project)
    child = project / "workspace" / "notes"
    child.mkdir(parents=True)
    note = child / "cwd-relative.md"
    note.write_text("# Cwd Relative\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(child)

    result = runner.invoke(app, ["import", "./cwd-relative.md", "--provider", "fake"])

    assert result.exit_code == 0, result.output
    _assert_run_counts(_wait_for_cli_run(cfg, result.output), processed=1, skipped=0, failed=0, seen=1)
    assert len(_card_paths(vault)) == 1


def test_import_resolves_absolute_path(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    cfg, vault = _write_project_config(project)
    note = tmp_path / "absolute-note.md"
    note.write_text("# Absolute Note\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(project / "vault")

    result = runner.invoke(app, ["import", str(note), "--provider", "fake"])

    assert result.exit_code == 0, result.output
    _assert_run_counts(_wait_for_cli_run(cfg, result.output), processed=1, skipped=0, failed=0, seen=1)
    assert len(_card_paths(vault)) == 1


def test_watch_add_resolves_project_root_relative_path(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    cfg, vault = _write_project_config(project)
    note = vault / "00-Inbox" / "ManualNotes" / "watch-project-relative.md"
    note.write_text("# Watch Project Relative\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(project)

    result = runner.invoke(
        app,
        ["watch", "add", "vault/00-Inbox/ManualNotes/watch-project-relative.md", "--provider", "fake"],
    )

    assert result.exit_code == 0, result.output
    _assert_run_counts(_wait_for_cli_run(cfg, result.output), processed=1, skipped=0, failed=0, seen=1)
    registry = WatchRegistry.load(vault / ".mindforge" / "watched_sources.json")
    assert registry.sources[0].path == note.resolve()


def test_watch_add_missing_file_fails_before_registry_write(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    missing = vault / "00-Inbox" / "ManualNotes" / "missing-watch.md"

    result = runner.invoke(app, ["watch", "add", str(missing), "--provider", "fake", "--config", str(cfg)])

    assert result.exit_code == 2, result.output
    assert "File not found" in result.output
    assert not (vault / ".mindforge" / "watched_sources.json").exists()
    assert _card_paths(vault) == []


def test_import_openai_compatible_missing_key_fails_without_fake_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_OPENAI_API_KEY", raising=False)
    source = tmp_path / "real-import-note.md"
    source.write_text("# Real Import Note\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["import", str(source), "--profile", "openai_compatible", "--config", str(cfg)],
    )

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=0, skipped=0, failed=1, seen=1)
    assert "Model setup is incomplete" in (run.error_message or run.message)
    assert _card_paths(vault) == []


def test_import_anthropic_missing_key_fails_without_fake_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    source = tmp_path / "anthropic-import.md"
    source.write_text("# Anthropic Import\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["import", str(source), "--profile", "anthropic", "--config", str(cfg)],
    )

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=0, skipped=0, failed=1, seen=1)
    assert "Model setup is incomplete" in (run.error_message or run.message)
    assert _card_paths(vault) == []


def test_import_uses_llm_active_without_cli_provider(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="anthropic")
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    source = tmp_path / "active-anthropic-import.md"
    source.write_text("# Active Anthropic Import\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["import", str(source), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=0, skipped=0, failed=1, seen=1)
    assert "Model setup is incomplete" in (run.error_message or run.message)
    assert _card_paths(vault) == []


def test_import_invalid_active_provider_fails_with_available_providers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = tmp_path / "project"
    cfg, vault = _write_project_config(project, active_provider="fake")
    raw = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    raw["llm"]["active"] = "missing_provider"
    cfg.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    source = vault / "00-Inbox" / "ManualNotes" / "invalid-active.md"
    source.write_text("# Invalid Active\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(project)

    result = runner.invoke(app, ["import", "vault/00-Inbox/ManualNotes/invalid-active.md"])

    assert result.exit_code == 2, result.output
    assert "llm.active='missing_provider'" in result.output
    assert "openai_compatible" in result.output
    assert "anthropic" in result.output
    assert "fake" in result.output


def test_import_without_model_config_reports_setup_action(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    raw = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    raw["llm"] = {"default_model": None, "models": {}, "routing": {}}
    cfg.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    source = tmp_path / "import-no-model.md"
    source.write_text("# Import No Model\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    result = runner.invoke(app, ["import", str(source), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    assert run.status == "failed"
    assert "No model configured for stage 'triage'" in (run.error_message or run.message)
    assert "Add a model in Web Setup" in (run.error_message or run.message)


def test_process_without_model_config_reports_setup_action(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path)
    raw = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    raw["llm"] = {"default_model": None, "models": {}, "routing": {}}
    cfg.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    monkeypatch.chdir(vault)

    result = runner.invoke(app, ["process", "--config", str(cfg), "--limit", "1"])

    assert result.exit_code == 2, result.output
    assert "No model configured for stage 'triage'" in result.output
    assert "Add a model in Web Setup" in result.output
    assert "Traceback" not in result.output


def test_import_missing_model_setup_run_has_friendly_next_actions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """缺 model setup 是后台 run 的可观察状态，不是 import 命令的同步失败。

    中文学习型说明：CLI import 主路径只负责创建 durable run 并返回 run_id。
    worker 失败后，用户通过 runs show 看到 Web Setup / local secret store 的
    下一步，而不是 env/fake/profile 之类历史诊断。
    """

    cfg, vault = _write_config(tmp_path)
    raw = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    raw["llm"] = {"default_model": None, "models": {}, "routing": {}}
    cfg.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    source = tmp_path / "import-no-model-friendly.md"
    source.write_text("# Import No Model Friendly\n\nbody\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    result = runner.invoke(app, ["import", str(source), "--config", str(cfg)])
    run = _wait_for_cli_run(cfg, result.output)
    shown = runner.invoke(app, ["runs", "show", run.run_id, "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert run.status in {"failed", "needs_model_setup"}
    assert "Model setup is incomplete" in shown.output or "Add a model in Web Setup" in shown.output
    assert "retry after setup" in shown.output or "Retry after completing model setup" in shown.output
    for token in ("fake", ".env", " env", "demo", "profile", "api_key_env"):
        assert token not in shown.output


def test_watch_scan_without_model_config_reports_setup_action(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """无 model setup 时，watch scan 应创建 background run 并 failed，而非同步崩溃。

    中文学习型说明：watch scan 现在使用 process_changes=False 做只读 scan，
    然后为有变更的 source 创建 background ProcessingRun。model setup 错误应
    出现在 background run 中（通过 runs show 观察），而不是 watch scan 命令
    同步返回错误码。
    """
    cfg, vault = _write_config(tmp_path)
    raw = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    raw["llm"] = {"default_model": None, "models": {}, "routing": {}}
    cfg.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    source = tmp_path / "watch-scan-no-model.md"
    source.write_text("# Watch Scan No Model\n\nbody\n", encoding="utf-8")
    registry_path = registry_path_for_vault(vault)
    add_watch_source(vault, registry_path, source, frequency="manual")
    watch_id = WatchRegistry.load(registry_path).sources[0].id
    monkeypatch.chdir(vault)

    result = runner.invoke(app, ["watch", "scan", watch_id, "--config", str(cfg)])

    # scan 本身成功（只做文件扫描和 diff）
    assert result.exit_code == 0, result.output
    assert "scanned=1" in result.output

    # background run 应该 fail with model setup error
    run = _wait_for_cli_run(cfg, result.output)
    assert run.status in {"failed", "needs_model_setup"}
    assert "No model configured" in (run.error_message or run.message) or \
           "model setup" in (run.error_message or run.message).lower()
    assert "traceback" not in (run.error_message or run.message).lower()


def test_process_missing_real_provider_key_reports_selected_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """process 的 provider 失败也必须透明，但不能读取或打印 secret。"""

    cfg, vault = _write_config(tmp_path, active_provider="anthropic")
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("mindforge.process_cli.load_dotenv_silently", lambda *_a, **_k: 0)
    source = vault / "00-Inbox" / "ManualNotes" / "process-real.md"
    source.write_text("# Process Real\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["process", "--config", str(cfg), "--limit", "1"])

    assert result.exit_code == 2, result.output
    assert "Provider failure" in result.output
    assert "selected provider: anthropic" in result.output
    assert "provider type: anthropic" in result.output
    assert "selection source: llm.active" in result.output
    assert "Model setup is incomplete" in result.output
    assert "env" not in result.output.lower()
    assert _card_paths(vault) == []


def test_import_provider_override_wins_over_legacy_profile(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="fake")
    monkeypatch.chdir(vault)
    monkeypatch.delenv("MINDFORGE_ANTHROPIC_API_KEY", raising=False)
    source = tmp_path / "provider-wins.md"
    source.write_text("# Provider Wins\n\nbody\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "import",
            str(source),
            "--provider",
            "anthropic",
            "--profile",
            "fake",
            "--config",
            str(cfg),
        ],
    )

    assert result.exit_code == 0, result.output
    run = _wait_for_cli_run(cfg, result.output)
    _assert_run_counts(run, processed=0, skipped=0, failed=1, seen=1)
    assert "Model setup is incomplete" in (run.error_message or run.message)
    assert _card_paths(vault) == []


def test_force_does_not_bypass_already_processed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="fake")
    _set_triage_threshold(cfg, 10)
    monkeypatch.chdir(vault)
    source = vault / "00-Inbox" / "ManualNotes" / "force-duplicate.md"
    source.write_text("# Force Duplicate\n\nsmall note\n", encoding="utf-8")

    first = runner.invoke(app, ["import", str(source), "--force", "--config", str(cfg)])
    assert first.exit_code == 0, first.output
    _assert_run_counts(_wait_for_cli_run(cfg, first.output), processed=1, skipped=0, failed=0, seen=1)
    second = runner.invoke(app, ["import", str(source), "--force", "--config", str(cfg)])
    assert second.exit_code == 0, second.output
    second_run = _wait_for_cli_run(cfg, second.output)
    _assert_run_counts(second_run, processed=0, skipped=1, failed=0, seen=1)
    assert any("already_processed" in reason for reason in second_run.skip_reasons)
    assert len(_card_paths(vault)) == 1


def test_no_triage_alias_overrides_triage_gate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg, vault = _write_config(tmp_path, active_provider="fake")
    _set_triage_threshold(cfg, 10)
    monkeypatch.chdir(vault)
    source = vault / "00-Inbox" / "ManualNotes" / "no-triage.md"
    source.write_text("# No Triage\n\nsmall note\n", encoding="utf-8")

    result = runner.invoke(app, ["import", str(source), "--no-triage", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    _assert_run_counts(_wait_for_cli_run(cfg, result.output), processed=1, skipped=0, failed=0, seen=1)


def test_watch_delete_default_and_approve_boundary(tmp_path: Path, monkeypatch) -> None:
    cfg, vault = _write_config(tmp_path)
    monkeypatch.chdir(vault)
    source = tmp_path / "approval-boundary.md"
    source.write_text("# Approval Boundary\n\nbody\n", encoding="utf-8")

    add = runner.invoke(app, ["watch", "add", str(source), "--config", str(cfg)])
    assert add.exit_code == 0, add.output
    _assert_run_counts(_wait_for_cli_run(cfg, add.output), processed=1, skipped=0, failed=0, seen=1)
    stop_default = runner.invoke(app, ["watch", "delete", "default-inbox", "--config", str(cfg)])
    cfg_obj = load_mindforge_config(cfg)
    card = _card_paths(vault)[0]

    assert stop_default.exit_code == 0, stop_default.output
    assert "only stops future monitoring" in stop_default.output
    assert "source files, or knowledge cards" in stop_default.output
    assert (vault / "00-Inbox").exists()
    assert read_card_frontmatter(card)["status"] == "ai_draft"
    approve = approve_explicit_card(cfg_obj, card)
    assert approve.error is None
    assert read_card_frontmatter(card)["status"] == "human_approved"
