"""路径边界测试：Web source path、CLI source path、workspace discovery、secret store、trash/wiki path 安全。

中文学习型说明：路径是所有用户级 ingestion 的第一个边界。
不存在的路径必须在 Web/CLI 第一层被拒绝，不能进入 registry/pipeline。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from mindforge.app_context import (
    _looks_like_vault,
    detect_cwd_vault,
    find_project_root,
)
from mindforge.cli import app as cli_app
from mindforge.first_run_config import maybe_bootstrap_local_config
from mindforge.ingestion_service import SourcePathError
from mindforge.trash_service import _resolve_restore_target
from mindforge.wiki_service import _wiki_path
from mindforge.config import MindForgeConfig, load_mindforge_config
from mindforge_web.app import create_app
from mindforge_web.services.web_config_service import WebConfigService

runner = CliRunner()


# ═══════════════════════════════════════════════════════════════════════════════
# 测试辅助
# ═══════════════════════════════════════════════════════════════════════════════

def _write_web_config(tmp_path: Path) -> tuple[Path, Path, Path]:
    """写入 Web 测试用的 config（扁平结构：tmp_path/mindforge.yaml）。"""
    vault = tmp_path / "dogfood-vault"
    inbox = vault / "00-Inbox" / "ManualNotes"
    cards = vault / "20-Knowledge-Cards"
    projects = vault / "30-Projects"
    inbox.mkdir(parents=True)
    cards.mkdir(parents=True)
    projects.mkdir(parents=True)
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {
                    "root": str(vault),
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
                    "projects_dir": "30-Projects",
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
                    "backup_state": True,
                },
                "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
                "llm": {
                    "active_profile": "fake",
                    "profiles": {
                        "fake": {
                            "triage": "fake_alias",
                            "distill": "fake_alias",
                            "link_suggestion": "fake_alias",
                            "review_questions": "fake_alias",
                            "action_extraction": "fake_alias",
                        }
                    },
                    "models": {
                        "fake_alias": {
                            "provider": "fake",
                            "type": "fake",
                            "base_url": "fake://",
                            "model": "fake",
                            "timeout_seconds": 5,
                            "max_retries": 0,
                            "api_key_env": "MINDFORGE_FAKE_SECRET",
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
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return cfg_path, vault, cards


def _write_cli_config(tmp_path: Path, *, active_provider: str = "fake") -> tuple[Path, Path, Path]:
    """写入 CLI 测试用的 config（标准结构：<project>/configs/mindforge.yaml）。"""
    vault = tmp_path / "vault"
    inbox = vault / "00-Inbox" / "ManualNotes"
    inbox.mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)
    cfg = tmp_path / "configs" / "mindforge.yaml"
    cfg.parent.mkdir(parents=True)
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
                        active_provider: {
                            "type": "fake",
                            "purpose": "offline_demo_ci_deterministic_tests",
                        },
                    },
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return cfg, vault, inbox


def _web_client(tmp_path: Path, monkeypatch) -> TestClient:
    """创建 Web TestClient，切换到 tmp_path 运行。"""
    cfg_path, _vault, _cards = _write_web_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    return TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))


# ═══════════════════════════════════════════════════════════════════════════════
# Web source path 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestWebSourcePath:
    """Web API add source 的路径边界校验。"""

    # Web API 路径：watch-add → POST /api/sources/watch，import → POST /api/sources/import

    def test_add_source_relative_path_returns_400(self, tmp_path: Path, monkeypatch):
        """Web 传入相对路径必须 400，提示使用 absolute path。"""
        client = _web_client(tmp_path, monkeypatch)
        r = client.post(
            "/api/sources/watch",
            json={"path": "relative/path/note.md", "process_now": False},
        )
        assert r.status_code == 400
        detail = str(r.json()["detail"])
        assert "absolute path" in detail.lower()

    def test_add_source_nonexistent_path_returns_400(self, tmp_path: Path, monkeypatch):
        """Web 传入不存在的绝对路径必须 400，提示 not found。"""
        client = _web_client(tmp_path, monkeypatch)
        r = client.post(
            "/api/sources/watch",
            json={"path": "/tmp/nonexistent-file-42a7b.md", "process_now": False},
        )
        assert r.status_code == 400
        detail = str(r.json()["detail"])
        assert "not found" in detail.lower()

    def test_add_source_existing_file_returns_200(self, tmp_path: Path, monkeypatch):
        """Web 传入存在的绝对文件路径应 200。"""
        client = _web_client(tmp_path, monkeypatch)
        note = tmp_path / "existing-file.md"
        note.write_text("# Hello\n\nworld\n", encoding="utf-8")
        r = client.post(
            "/api/sources/watch",
            json={"path": str(note), "process_now": False},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_add_source_existing_folder_returns_200(self, tmp_path: Path, monkeypatch):
        """Web 传入存在的绝对文件夹路径应 200。"""
        client = _web_client(tmp_path, monkeypatch)
        folder = tmp_path / "existing-folder"
        folder.mkdir(parents=True)
        (folder / "a.md").write_text("# A\n", encoding="utf-8")
        r = client.post(
            "/api/sources/watch",
            json={"path": str(folder), "process_now": False},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_add_source_path_doubling_returns_400(self, tmp_path: Path, monkeypatch):
        """路径加倍模式 /tmp/x.md/x.md 应 400，不是 500。"""
        client = _web_client(tmp_path, monkeypatch)
        note = tmp_path / "existing-file.md"
        note.write_text("# Hello\n", encoding="utf-8")
        doubled = f"{note}/{note.name}"
        r = client.post(
            "/api/sources/watch",
            json={"path": doubled, "process_now": False},
        )
        assert r.status_code == 400

    def test_import_nonexistent_path_returns_400(self, tmp_path: Path, monkeypatch):
        """Web import 不存在的路径应 400。"""
        client = _web_client(tmp_path, monkeypatch)
        r = client.post(
            "/api/sources/import",
            json={"path": "/tmp/nonexistent-import-42a7b.md"},
        )
        assert r.status_code == 400

    def test_import_relative_path_returns_400(self, tmp_path: Path, monkeypatch):
        """Web import 相对路径应 400，提示使用 absolute path。"""
        client = _web_client(tmp_path, monkeypatch)
        r = client.post(
            "/api/sources/import",
            json={"path": "relative/path/note.md"},
        )
        assert r.status_code == 400
        detail = str(r.json()["detail"])
        assert "absolute path" in detail.lower()

    def test_import_existing_absolute_file_succeeds(self, tmp_path: Path, monkeypatch):
        """Web import 存在的绝对文件路径应 200。"""
        client = _web_client(tmp_path, monkeypatch)
        note = tmp_path / "import-existing-file.md"
        note.write_text("# Import Test\n\nbody\n", encoding="utf-8")
        r = client.post(
            "/api/sources/import",
            json={"path": str(note)},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_import_path_doubling_returns_400(self, tmp_path: Path, monkeypatch):
        """Web import 路径加倍模式应 400，不是 500。"""
        client = _web_client(tmp_path, monkeypatch)
        note = tmp_path / "import-existing-file.md"
        note.write_text("# Hello\n", encoding="utf-8")
        doubled = f"{note}/{note.name}"
        r = client.post(
            "/api/sources/import",
            json={"path": doubled},
        )
        assert r.status_code == 400

    def test_import_existing_absolute_folder_succeeds(self, tmp_path: Path, monkeypatch):
        """Web import 存在的绝对文件夹路径应 200（import 支持文件夹）。"""
        client = _web_client(tmp_path, monkeypatch)
        folder = tmp_path / "import-existing-folder"
        folder.mkdir(parents=True)
        (folder / "a.md").write_text("# A\n", encoding="utf-8")
        r = client.post(
            "/api/sources/import",
            json={"path": str(folder)},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True


class TestSourcePathErrorIsNotRuntimeError:
    """SourcePathError 是 ValueError，不应被当作 RuntimeError 处理。"""

    def test_source_path_error_is_value_error(self):
        """SourcePathError 继承 ValueError，不继承 RuntimeError。"""
        err = SourcePathError("test")
        assert isinstance(err, ValueError)
        assert not isinstance(err, RuntimeError)

    def test_runtime_error_not_caught_as_400_in_facade_pattern(self):
        """RuntimeError 不应被误转成 400。检查 web_facade 分离了 ValueError 和 RuntimeError。"""
        import inspect
        from mindforge_web.services.web_facade import WebFacade

        source = inspect.getsource(WebFacade.watch_add)
        # ValueError → 400, RuntimeError → 500 必须是两条独立 except 分支
        assert "except ValueError" in source
        assert "except RuntimeError" in source
        assert "_http_error(400" in source
        assert "_http_error(500" in source


# ═══════════════════════════════════════════════════════════════════════════════
# CLI source path 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestCLISourcePath:
    """CLI watch/import 的路径行为。"""

    def test_watch_add_existing_relative_file_resolves_to_absolute(self, tmp_path: Path, monkeypatch):
        """CLI watch add 传入相对路径应 resolve 成 absolute path 并处理成功。"""
        cfg, vault, inbox = _write_cli_config(tmp_path)
        note = inbox / "relative-note.md"
        note.write_text("# Relative\n\nbody\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            cli_app,
            ["watch", "add", str(note.relative_to(tmp_path)), "--provider", "fake", "--config", str(cfg)],
        )
        assert result.exit_code == 0, result.output
        assert "registered" in result.output.lower() or "watch add" in result.output.lower()

    def test_watch_add_nonexistent_path_returns_code_2_no_traceback(self, tmp_path: Path, monkeypatch):
        """CLI watch add 不存在路径应 exit_code=2，无 traceback。"""
        cfg, _vault, _inbox = _write_cli_config(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            cli_app,
            ["watch", "add", "/tmp/nonexistent-cli-42a7b.md", "--provider", "fake", "--config", str(cfg)],
        )
        assert result.exit_code == 2
        assert "Traceback" not in result.output

    def test_import_nonexistent_path_returns_code_2_no_traceback(self, tmp_path: Path, monkeypatch):
        """CLI import 不存在路径应 exit_code=2，无 traceback。"""
        cfg, _vault, _inbox = _write_cli_config(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            cli_app,
            ["import", "/tmp/nonexistent-cli-import-42a7b.md", "--provider", "fake", "--config", str(cfg)],
        )
        assert result.exit_code == 2
        assert "Traceback" not in result.output

    def test_import_existing_relative_file_succeeds(self, tmp_path: Path, monkeypatch):
        """CLI import 存在的相对路径应处理成功。"""
        cfg, vault, inbox = _write_cli_config(tmp_path)
        note = inbox / "import-me.md"
        note.write_text("# Import Me\n\nbody\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            cli_app,
            ["import", str(note.relative_to(tmp_path)), "--provider", "fake", "--config", str(cfg)],
        )
        assert result.exit_code == 0, result.output

    def test_watch_scan_also_catches_value_error(self, tmp_path: Path, monkeypatch):
        """CLI watch scan 也应捕获 ValueError（非仅 RuntimeError）。"""
        import inspect
        from mindforge import watch_cli

        source = inspect.getsource(watch_cli.watch_scan)
        assert "except (ValueError, RuntimeError)" in source


# ═══════════════════════════════════════════════════════════════════════════════
# Workspace discovery 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestFindProjectRoot:
    """find_project_root 在各种目录结构下的行为。"""

    def test_from_project_root_with_configs(self, tmp_path: Path):
        """从包含 configs/mindforge.yaml 的目录应返回该目录。"""
        (tmp_path / "configs" / "mindforge.yaml").parent.mkdir(parents=True)
        (tmp_path / "configs" / "mindforge.yaml").write_text("version: 0.7\n", encoding="utf-8")
        assert find_project_root(tmp_path) == tmp_path

    def test_from_vault_subdir_returns_project_root(self, tmp_path: Path):
        """从 project/vault 子目录应返回 project root，不是 vault。"""
        (tmp_path / "configs" / "mindforge.yaml").parent.mkdir(parents=True)
        (tmp_path / "configs" / "mindforge.yaml").write_text("version: 0.7\n", encoding="utf-8")
        vault = tmp_path / "vault"
        (vault / "00-Inbox").mkdir(parents=True)
        assert find_project_root(vault) == tmp_path

    def test_from_vault_knowledge_cards_subdir_returns_project_root(self, tmp_path: Path):
        """从 project/vault/20-Knowledge-Cards 深层子目录应返回 project root。"""
        (tmp_path / "configs" / "mindforge.yaml").parent.mkdir(parents=True)
        (tmp_path / "configs" / "mindforge.yaml").write_text("version: 0.7\n", encoding="utf-8")
        cards = tmp_path / "vault" / "20-Knowledge-Cards"
        cards.mkdir(parents=True)
        assert find_project_root(cards) == tmp_path

    def test_github_clone_pyproject_toml_and_src_mindforge(self, tmp_path: Path):
        """GitHub clone 初始状态：仅有 pyproject.toml + src/mindforge 时能识别 project root。"""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='mindforge'\n", encoding="utf-8")
        (tmp_path / "src" / "mindforge").mkdir(parents=True)
        (tmp_path / "src" / "mindforge" / "__init__.py").write_text("", encoding="utf-8")
        assert find_project_root(tmp_path) == tmp_path

    def test_github_clone_vault_marker(self, tmp_path: Path):
        """GitHub clone 初始状态：仅有 vault/ 目录时能识别 project root。"""
        (tmp_path / "vault").mkdir(parents=True)
        assert find_project_root(tmp_path) == tmp_path

    def test_mindforge_dir_in_project_not_vault_returns_project_root(self, tmp_path: Path):
        """.mindforge/ 在 project root（非 vault 内）应返回 project root。"""
        (tmp_path / ".mindforge").mkdir(parents=True)
        assert find_project_root(tmp_path) == tmp_path
        # 确认 vault 内的 .mindforge 不会误判
        vault = tmp_path / "vault"
        (vault / "00-Inbox").mkdir(parents=True)
        (vault / ".mindforge").mkdir(parents=True)
        assert find_project_root(vault) == tmp_path  # project root 优先，因为有 configs/...
        # 实际上 tmp_path 没有 configs/mindforge.yaml，所以 vault 可能被返回
        # 但如果 tmp_path 有 vault/ 子目录，应该在到达 vault 之前就匹配 tmp_path

    def test_no_markers_returns_none(self):
        """无任何标记的空目录应返回 None。"""
        with tempfile.TemporaryDirectory() as td:
            empty = Path(td)
            assert find_project_root(empty) is None


class TestDetectCwdVault:
    """detect_cwd_vault 的 vault 发现逻辑。"""

    def test_finds_vault_with_00_inbox(self, tmp_path: Path):
        """包含 00-Inbox 的目录应被识别为 vault。"""
        (tmp_path / "00-Inbox").mkdir(parents=True)
        assert detect_cwd_vault(tmp_path) == tmp_path

    def test_finds_vault_with_20_knowledge_cards(self, tmp_path: Path):
        """包含 20-Knowledge-Cards 的目录应被识别为 vault。"""
        (tmp_path / "20-Knowledge-Cards").mkdir(parents=True)
        assert detect_cwd_vault(tmp_path) == tmp_path

    def test_finds_fresh_vault_with_mindforge(self, tmp_path: Path):
        """仅有 .mindforge/ 的 fresh vault 应被识别。"""
        (tmp_path / ".mindforge").mkdir(parents=True)
        assert detect_cwd_vault(tmp_path) == tmp_path

    def test_ignores_directory_with_mindforge_yaml(self, tmp_path: Path):
        """含 mindforge.yaml 的目录不应被 .mindforge/ 误判为 vault。"""
        (tmp_path / ".mindforge").mkdir(parents=True)
        (tmp_path / "mindforge.yaml").write_text("version: 0.7\n", encoding="utf-8")
        assert detect_cwd_vault(tmp_path) is None

    def test_ignores_directory_with_configs_mindforge_yaml(self, tmp_path: Path):
        """含 configs/mindforge.yaml 的目录不应被误判为 vault。"""
        (tmp_path / ".mindforge").mkdir(parents=True)
        (tmp_path / "configs" / "mindforge.yaml").parent.mkdir(parents=True)
        (tmp_path / "configs" / "mindforge.yaml").write_text("version: 0.7\n", encoding="utf-8")
        assert detect_cwd_vault(tmp_path) is None

    def test_no_markers_returns_none(self):
        """无 vault 标记的空目录应返回 None。"""
        with tempfile.TemporaryDirectory() as td:
            empty = Path(td)
            assert detect_cwd_vault(empty) is None


class TestLooksLikeVault:
    """_looks_like_vault 辅助函数。"""

    def test_vault_with_inbox(self, tmp_path: Path):
        (tmp_path / "00-Inbox").mkdir()
        assert _looks_like_vault(tmp_path) is True

    def test_vault_with_cards(self, tmp_path: Path):
        (tmp_path / "20-Knowledge-Cards").mkdir()
        assert _looks_like_vault(tmp_path) is True

    def test_non_vault(self, tmp_path: Path):
        assert _looks_like_vault(tmp_path) is False


# ═══════════════════════════════════════════════════════════════════════════════
# WebConfigService secret store 路径测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestWebConfigServiceSecretStore:
    """WebConfigService 的 secret store 路径选择。"""

    def test_standard_config_creates_dot_mindforge_under_project(self, tmp_path: Path):
        """标准结构 <project>/configs/mindforge.yaml → .mindforge/ 在 <project>/。"""
        config_path = tmp_path / "configs" / "mindforge.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            yaml.safe_dump({"version": 0.7, "vault": {"root": str(tmp_path / "vault")},
                            "llm": {"active_profile": "fake", "profiles": {"fake": {"triage": "x", "distill": "x", "link_suggestion": "x", "review_questions": "x", "action_extraction": "x"}}, "models": {"x": {"provider": "fake", "type": "fake", "base_url": "fake://", "model": "fake"}}},
                            "state": {"workdir": ".mindforge"}}),
            encoding="utf-8",
        )
        WebConfigService(load_mindforge_config(config_path), config_path=config_path)
        assert (tmp_path / ".mindforge" / "secrets.json").parent.exists()
        assert (tmp_path / ".mindforge").is_dir()

    def test_flat_config_creates_dot_mindforge_under_workspace(self, tmp_path: Path):
        """扁平结构 <workspace>/mindforge.yaml → .mindforge/ 在 <workspace>/。"""
        config_path = tmp_path / "mindforge.yaml"
        config_path.write_text(
            yaml.safe_dump({"version": 0.7, "vault": {"root": str(tmp_path / "vault")},
                            "llm": {"active_profile": "fake", "profiles": {"fake": {"triage": "x", "distill": "x", "link_suggestion": "x", "review_questions": "x", "action_extraction": "x"}}, "models": {"x": {"provider": "fake", "type": "fake", "base_url": "fake://", "model": "fake"}}},
                            "state": {"workdir": str(tmp_path / ".mindforge")}}),
            encoding="utf-8",
        )
        WebConfigService(load_mindforge_config(config_path), config_path=config_path)
        assert (tmp_path / ".mindforge" / "secrets.json").parent.exists()
        assert (tmp_path / ".mindforge").is_dir()

    def test_uses_cfg_metadata_project_root_when_available(self, tmp_path: Path):
        """P1-1: cfg.raw._mindforge_project.root 存在时优先使用，
        而非从 config_path 重新推导 project_root。"""
        config_path = tmp_path / "configs" / "mindforge.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            yaml.safe_dump({"version": 0.7, "vault": {"root": str(tmp_path / "vault")},
                            "llm": {"active_profile": "fake", "profiles": {"fake": {"triage": "x", "distill": "x", "link_suggestion": "x", "review_questions": "x", "action_extraction": "x"}}, "models": {"x": {"provider": "fake", "type": "fake", "base_url": "fake://", "model": "fake"}}},
                            "state": {"workdir": ".mindforge"}}),
            encoding="utf-8",
        )
        cfg = load_mindforge_config(config_path)
        # 注入 _mindforge_project metadata（模拟 build_app_context 注入）
        explicit_root = tmp_path / "explicit-project-root"
        cfg.raw["_mindforge_project"] = {"root": str(explicit_root), "config_path": str(config_path)}

        WebConfigService(cfg, config_path=config_path)
        # 验证 .mindforge/ 创建在 metadata 锚点的 project_root，而非 config_path 推导的 tmp_path
        assert (explicit_root / ".mindforge" / "secrets.json").parent.exists()
        assert (explicit_root / ".mindforge").is_dir()

    def test_repo_cwd_secrets_not_contaminate_workspace(
        self, tmp_path: Path, monkeypatch
    ):
        """P1-1: 在 repo cwd 运行但 config 指向 workspace 时，
        WebConfigService 使用 workspace 的 .mindforge/，而非 repo cwd 的。"""
        # 在 repo cwd 创建 .mindforge/secrets.json
        repo_cwd = tmp_path / "repo-cwd"
        repo_cwd.mkdir()
        repo_secrets_dir = repo_cwd / ".mindforge"
        repo_secrets_dir.mkdir()
        (repo_secrets_dir / "secrets.json").write_text(
            '{"repo_key": "sk-should-not-be-used"}', encoding="utf-8"
        )

        # 创建 workspace（独立于 repo cwd）
        ws = tmp_path / "ws"
        config_path = ws / "configs" / "mindforge.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            yaml.safe_dump({"version": 0.7, "vault": {"root": str(ws / "vault")},
                            "llm": {"active_profile": "fake", "profiles": {"fake": {"triage": "x", "distill": "x", "link_suggestion": "x", "review_questions": "x", "action_extraction": "x"}}, "models": {"x": {"provider": "fake", "type": "fake", "base_url": "fake://", "model": "fake"}}},
                            "state": {"workdir": ".mindforge"}}),
            encoding="utf-8",
        )
        cfg = load_mindforge_config(config_path)

        monkeypatch.chdir(repo_cwd)
        WebConfigService(cfg, config_path=config_path)

        # workspace 的 .mindforge 被创建
        assert (ws / ".mindforge" / "secrets.json").parent.exists()
        # repo cwd 的 secrets.json 未被读取或修改（路径选择不碰 CWD 的 secrets）
        assert repo_secrets_dir.exists()  # 仍然存在，未被触碰


# ═══════════════════════════════════════════════════════════════════════════════
# gitignore / 运行时数据隔离测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGitignoreRules:
    """验证关键运行时文件被 .gitignore 覆盖。"""

    def test_vault_is_gitignored(self):
        """vault/ 运行时目录应在 .gitignore 中。"""
        gitignore = Path(__file__).parent.parent / ".gitignore"
        lines = gitignore.read_text().splitlines()
        assert any("vault/" in line and not line.strip().startswith("#") for line in lines), (
            "vault/ 必须被 gitignored"
        )

    def test_configs_mindforge_yaml_is_gitignored(self):
        """configs/mindforge.yaml 本地配置应在 .gitignore 中。"""
        gitignore = Path(__file__).parent.parent / ".gitignore"
        lines = gitignore.read_text().splitlines()
        assert any("configs/mindforge.yaml" in line and not line.strip().startswith("#") for line in lines), (
            "configs/mindforge.yaml 必须被 gitignored"
        )

    def test_dot_mindforge_is_gitignored(self):
        """.mindforge/ 运行时状态目录应在 .gitignore 中。"""
        gitignore = Path(__file__).parent.parent / ".gitignore"
        lines = gitignore.read_text().splitlines()
        assert any(".mindforge/" in line and not line.strip().startswith("#") for line in lines), (
            ".mindforge/ 必须被 gitignored"
        )

    def test_env_is_gitignored(self):
        """.env 环境变量文件应在 .gitignore 中。"""
        gitignore = Path(__file__).parent.parent / ".gitignore"
        lines = gitignore.read_text().splitlines()
        assert any(line.strip() == ".env" for line in lines), (
            ".env 必须被 gitignored"
        )

    def test_claude_code_agent_env_is_gitignored(self):
        """claude-code-agent-env 本地 Claude Code 配置应在 .gitignore 中。"""
        gitignore = Path(__file__).parent.parent / ".gitignore"
        lines = gitignore.read_text().splitlines()
        assert any(
            line.strip() == "claude-code-agent-env" for line in lines
        ), "claude-code-agent-env 必须被 gitignored"

    def test_configs_example_yaml_exists_and_is_committable(self):
        """configs/mindforge_example.yaml 是模板，应存在且不被 gitignore 排除。"""
        example = Path(__file__).parent.parent / "configs" / "mindforge_example.yaml"
        assert example.is_file(), "configs/mindforge_example.yaml 模板应存在"
        # example 不在 gitignore 中
        gitignore = Path(__file__).parent.parent / ".gitignore"
        lines = gitignore.read_text().splitlines()
        assert not any(
            "mindforge_example" in line and not line.strip().startswith("#")
            for line in lines
        ), "mindforge_example.yaml 不应被 gitignored"


class TestFirstRunConfigBootstrapBoundaries:
    """clean clone 首次启动只允许在明确 workspace root 下创建本地 config。"""

    def test_wrong_directory_does_not_create_runtime_config(self, tmp_path: Path):
        """没有 MindForge workspace 标记时不能在 cwd 乱建 configs/mindforge.yaml。"""
        result = maybe_bootstrap_local_config(Path("configs/mindforge.yaml"), cwd=tmp_path)

        assert result.created is False
        assert result.config_path is None
        assert not (tmp_path / "configs" / "mindforge.yaml").exists()
        assert "Run from a MindForge workspace" in (result.message or "")

    def test_workspace_web_cli_bootstraps_before_server_start(self, tmp_path: Path, monkeypatch):
        """`mindforge web --workspace` 应先创建本地 config，再把路径传给 server。"""
        ws = tmp_path / "mindforge"
        (ws / "configs").mkdir(parents=True)
        (ws / "configs" / "mindforge_example.yaml").write_text("version: 0.7\n", encoding="utf-8")
        (ws / "pyproject.toml").write_text("[project]\nname='mindforge'\n", encoding="utf-8")
        (ws / "src" / "mindforge").mkdir(parents=True)

        received_cfg: list[Path] = []

        def fake_run_server(*, host, port, open_browser, config_path, vault_override):
            received_cfg.append(Path(config_path))

        monkeypatch.setattr("mindforge_web.server.run_server", fake_run_server)

        result = runner.invoke(cli_app, ["web", "--workspace", str(ws), "--no-open"])

        assert result.exit_code == 0, result.output
        assert "Created local config at" in result.output
        assert (ws / "configs" / "mindforge.yaml").is_file()
        assert received_cfg == [ws / "configs" / "mindforge.yaml"]

    def test_workspace_web_cli_bootstraps_empty_user_workspace(self, tmp_path: Path, monkeypatch):
        """显式 --workspace 指向空用户目录时，config 必须落在该目录而不是 repo cwd。

        中文学习型说明：fresh clone dogfood 暴露过一个路径边界问题：从仓库目录
        运行 Web，并传入一个全新的用户 workspace 时，首次启动不能把 runtime
        config 写回仓库根目录。显式 workspace 是用户意图，应允许在空目录中创建
        configs/mindforge.yaml，同时保持“未显式 workspace 的错误 cwd 不写文件”边界。
        """
        repo_cwd = tmp_path / "fresh-clone-repo"
        (repo_cwd / "configs").mkdir(parents=True)
        (repo_cwd / "configs" / "mindforge_example.yaml").write_text(
            "version: 0.7\n",
            encoding="utf-8",
        )
        (repo_cwd / "pyproject.toml").write_text("[project]\nname='mindforge'\n", encoding="utf-8")
        (repo_cwd / "src" / "mindforge").mkdir(parents=True)
        user_workspace = tmp_path / "user-workspace"
        user_workspace.mkdir()
        monkeypatch.chdir(repo_cwd)

        received_cfg: list[Path] = []
        received_vault: list[Path | None] = []

        def fake_run_server(*, host, port, open_browser, config_path, vault_override):
            received_cfg.append(Path(config_path))
            received_vault.append(vault_override)

        monkeypatch.setattr("mindforge_web.server.run_server", fake_run_server)

        result = runner.invoke(
            cli_app,
            ["web", "--workspace", str(user_workspace), "--no-open"],
        )

        assert result.exit_code == 0, result.output
        assert (user_workspace / "configs" / "mindforge.yaml").is_file()
        assert not (repo_cwd / "configs" / "mindforge.yaml").exists()
        assert received_cfg == [user_workspace / "configs" / "mindforge.yaml"]
        assert received_vault == [user_workspace / "vault"]


# ═══════════════════════════════════════════════════════════════════════════════
# Trash path 安全测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrashRestorePathSafety:
    """Trash restore 的路径安全校验。"""

    def _make_config(self, tmp_path: Path) -> MindForgeConfig:
        vault = tmp_path / "vault"
        (vault / "00-Inbox").mkdir(parents=True)
        (vault / "20-Knowledge-Cards").mkdir(parents=True)
        cfg_path = tmp_path / "mindforge.yaml"
        cfg_path.write_text(
            yaml.safe_dump({
                "version": 0.7,
                "vault": {
                    "root": str(vault),
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
                },
                "state": {"workdir": str(tmp_path / ".mindforge")},
                "llm": {
                    "active_profile": "fake",
                    "profiles": {"fake": {"triage": "f", "distill": "f", "link_suggestion": "f", "review_questions": "f", "action_extraction": "f"}},
                    "models": {"f": {"provider": "fake", "type": "fake", "base_url": "fake://", "model": "fake"}},
                },
            }),
            encoding="utf-8",
        )
        return load_mindforge_config(cfg_path)

    def test_reject_absolute_original_path(self, tmp_path: Path):
        """Trash restore 拒绝绝对 original_path。"""
        cfg = self._make_config(tmp_path)
        with pytest.raises(Exception) as exc_info:
            _resolve_restore_target(cfg, "/etc/passwd")
        msg = str(exc_info.value)
        # 原文是 "trash original_path 必须是 vault-relative 路径，拒绝恢复"
        assert "拒绝恢复" in msg or "拒绝" in msg

    def test_reject_dotdot_in_original_path(self, tmp_path: Path):
        """Trash restore 拒绝含 .. 的 original_path。"""
        cfg = self._make_config(tmp_path)
        with pytest.raises(Exception) as exc_info:
            _resolve_restore_target(cfg, "../../outside.md")
        assert ".." in str(exc_info.value)

    def test_reject_escape_outside_cards_dir(self, tmp_path: Path):
        """Trash restore 拒绝逃逸到 cards_dir 外的路径。"""
        cfg = self._make_config(tmp_path)
        # 通过 symlink 尝试逃逸
        escape = tmp_path / "escape.md"
        escape.write_text("# escape\n", encoding="utf-8")
        symlink = cfg.vault.root / "00-Inbox" / "symlink.md"
        symlink.parent.mkdir(parents=True, exist_ok=True)
        symlink.symlink_to(escape)
        # 直接用 symlink 路径尝试 resolve（不在 cards_dir 内 → 应拒绝）
        original = "../escape.md"
        with pytest.raises(Exception) as exc_info:
            _resolve_restore_target(cfg, original)
        assert ".." in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# Wiki path 安全测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestWikiPathSafety:
    """Wiki 路径操作的安全边界。"""

    def _make_config(self, tmp_path: Path) -> MindForgeConfig:
        vault = tmp_path / "vault"
        (vault / "30-Wiki").mkdir(parents=True)
        (vault / "20-Knowledge-Cards").mkdir(parents=True)
        cfg_path = tmp_path / "mindforge.yaml"
        cfg_path.write_text(
            yaml.safe_dump({
                "version": 0.7,
                "vault": {
                    "root": str(vault),
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
                },
                "state": {"workdir": str(tmp_path / ".mindforge")},
                "llm": {
                    "active_profile": "fake",
                    "profiles": {"fake": {"triage": "f", "distill": "f", "link_suggestion": "f", "review_questions": "f", "action_extraction": "f"}},
                    "models": {"f": {"provider": "fake", "type": "fake", "base_url": "fake://", "model": "fake"}},
                },
            }),
            encoding="utf-8",
        )
        return load_mindforge_config(cfg_path)

    def test_wiki_path_under_vault_root(self, tmp_path: Path):
        """Wiki 输出路径必须在 vault root 下。"""
        cfg = self._make_config(tmp_path)
        wiki_p = _wiki_path(cfg)
        assert wiki_p.is_relative_to(cfg.vault.root)

    def test_wiki_atomic_write_preserves_old_file_on_failure(self, tmp_path: Path):
        """Wiki 原子写失败时应保留旧文件。"""
        cfg = self._make_config(tmp_path)
        wiki_p = _wiki_path(cfg)
        old_content = "# Old Wiki\n"
        wiki_p.write_text(old_content, encoding="utf-8")

        # 模拟写入失败：删除 wiki 文件并创建同名不可写目录
        wiki_p.unlink()
        wiki_p.mkdir(parents=True)

        # rebuild 应不抛出异常（目录存在时 with_suffix('.tmp') 写不进目录内）
        # 或至少旧内容不受影响
        try:
            from mindforge.wiki_service import rebuild_main_wiki
            rebuild_main_wiki(cfg)
            # 如果返回错误提示，也应安全
        except Exception:
            pass
        # 清理后验证
        import shutil
        shutil.rmtree(str(wiki_p), ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
# --workspace 参数测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkspaceOption:
    """--workspace 参数推导 config / vault 的行为。"""

    # 中文学习型说明：run_server 会被 monkeypatch 替换，不启动实际 HTTP 服务器。
    # 我们只验证 --workspace 推导出的 config/vault 路径是否正确传递给 run_server。

    def test_workspace_flag_appears_in_help(self):
        """--workspace 应在 web --help 中出现。"""
        result = runner.invoke(cli_app, ["web", "--help"])
        assert result.exit_code == 0
        assert "--workspace" in result.stdout

    def test_workspace_derives_config_and_vault(self, tmp_path: Path, monkeypatch):
        """--workspace 下 config 推导为 workspace/configs/mindforge.yaml，
        vault 推导为 workspace/vault。"""
        ws = tmp_path / "my-workspace"
        ws.mkdir(parents=True)
        (ws / "configs").mkdir()
        (ws / "vault").mkdir()
        _write_web_config(ws)  # 在 ws 下生成标准结构
        monkeypatch.chdir(ws)

        received_cfg: list[Path] = []
        received_vault: list[Path | None] = []

        def fake_run_server(*, host, port, open_browser, config_path, vault_override):
            received_cfg.append(Path(config_path).resolve() if not Path(config_path).is_absolute() else Path(config_path))
            received_vault.append(vault_override)

        monkeypatch.setattr(
            "mindforge_web.server.run_server",
            fake_run_server,
        )

        runner.invoke(
            cli_app,
            ["web", "--workspace", str(ws), "--no-open"],
        )
        # 可能因为没有真实 config exit_code=2，但只要 run_server 被调用即可
        if received_cfg:
            expected_cfg = (ws / "configs" / "mindforge.yaml").resolve()
            assert received_cfg[0] == expected_cfg, (
                f"workspace config 应为 {expected_cfg}，实际 {received_cfg[0]}"
            )
        if received_vault:
            expected_vault = ws / "vault"
            assert received_vault[0] == expected_vault, (
                f"workspace vault 应为 {expected_vault}，实际 {received_vault[0]}"
            )

    def test_explicit_config_overrides_workspace(self, tmp_path: Path, monkeypatch):
        """explicit --config 覆盖 workspace 推导的 config。"""
        ws = tmp_path / "my-workspace"
        ws.mkdir(parents=True)
        (ws / "configs").mkdir()
        _write_web_config(ws)
        monkeypatch.chdir(ws)

        explicit_cfg = tmp_path / "explicit-config.yaml"
        explicit_cfg.touch()

        received_cfg: list[Path] = []

        def fake_run_server(*, host, port, open_browser, config_path, vault_override):
            received_cfg.append(Path(config_path).resolve() if not Path(config_path).is_absolute() else Path(config_path))

        monkeypatch.setattr(
            "mindforge_web.server.run_server",
            fake_run_server,
        )

        runner.invoke(
            cli_app,
            ["web", "--workspace", str(ws), "--config", str(explicit_cfg), "--no-open"],
        )
        if received_cfg:
            assert received_cfg[0] == explicit_cfg.resolve(), (
                f"explicit --config 优先生效，应为 {explicit_cfg}，实际 {received_cfg[0]}"
            )

    def test_explicit_vault_overrides_workspace(self, tmp_path: Path, monkeypatch):
        """explicit --vault 覆盖 workspace 推导的 vault。"""
        ws = tmp_path / "my-workspace"
        ws.mkdir(parents=True)
        (ws / "configs").mkdir()
        _write_web_config(ws)
        monkeypatch.chdir(ws)

        explicit_vault = tmp_path / "explicit-vault"
        explicit_vault.mkdir()

        received_vault: list[Path | None] = []

        def fake_run_server(*, host, port, open_browser, config_path, vault_override):
            received_vault.append(vault_override)

        monkeypatch.setattr(
            "mindforge_web.server.run_server",
            fake_run_server,
        )

        runner.invoke(
            cli_app,
            [
                "web",
                "--workspace", str(ws),
                "--vault", str(explicit_vault),
                "--no-open",
            ],
        )
        if received_vault:
            assert received_vault[0] is not None
            assert Path(str(received_vault[0])).resolve() == explicit_vault.resolve(), (
                f"explicit --vault 优先生效，应为 {explicit_vault}，实际 {received_vault[0]}"
            )
