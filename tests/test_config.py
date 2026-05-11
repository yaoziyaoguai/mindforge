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
from typer.testing import CliRunner

from mindforge.assets_runtime import bundled_asset_path_for_process
from mindforge.cli import app
from mindforge.config import (
    ConfigError,
    LLMConfig,
    ModelConfig,
    REQUIRED_STAGES,
    load_learning_tracks,
    load_mindforge_config,
)
from mindforge.init_cmd import build_plan, execute_plan
from mindforge.first_run_config import maybe_bootstrap_local_config

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "configs"
runner = CliRunner()


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
    # v0.2.4 起 webclip_markdown / chat_export 默认启用；本 milestone 增加
    # common_document 作为通用本地文档入口，不把 Cubox 当核心配置项。
    assert active == {
        "cubox_markdown",
        "plain_markdown",
        "webclip_markdown",
        "chat_export",
        "common_document",
    }
    # llm：package defaults 也必须使用用户可见的新 models/default_model/routing。
    assert cfg.llm.active_profile == "__model_routing__"
    assert cfg.llm.default_model == "main"
    assert cfg.llm.routing == {stage: "main" for stage in REQUIRED_STAGES}
    for stage in REQUIRED_STAGES:
        m = cfg.llm.resolve_stage(stage)
        assert m.alias in cfg.llm.models
        assert m.type == "openai_compatible"
    # 真实路径模型一律不允许把 secret 写进 yaml
    main = cfg.llm.models["main"]
    assert main.type == "openai_compatible"
    # API key 不进 YAML；通过 Web Setup 保存到 local secret store
    assert main.api_key_env is None
    assert main.model == "your-model-name"
    assert main.base_url == "https://your-router.example.com/v1"  # endpoint 不是 secret
    # prompts
    assert cfg.prompts.for_stage("triage") == "v1"
    assert cfg.prompts.for_stage("link_suggestion") == "v1"


def test_init_generates_minimal_user_override_config(tmp_path: Path) -> None:
    """init 输出的是用户 override，而不是 internal full config dump。

    中文学习型说明：运行时仍需要 sources/state/search/prompts 等系统默认值，
    但这些属于 MindForge 内置 defaults。新用户第一天看到的 YAML 只应该承载
    workspace、model setup 占位和 telemetry 这类用户决策；provider key 通过
    Web Setup / local secret store 完成，不创建 env 模板来分叉 first-run 主路径。
    """

    project_root = tmp_path / "project"
    vault = tmp_path / "vault"
    plan = build_plan(
        vault,
        project_root=project_root,
        repo_root=bundled_asset_path_for_process(),
    )
    execute_plan(plan)

    generated = project_root / "configs" / "mindforge.yaml"
    text = generated.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)

    assert sorted(p.relative_to(project_root).as_posix() for p in project_root.rglob("*") if p.is_file()) == [
        "configs/mindforge.yaml",
    ]
    assert set(parsed) == {"version", "vault", "llm", "telemetry"}
    assert parsed["vault"]["root"] == str(vault)
    assert load_mindforge_config(generated).vault.root == vault.resolve()
    assert parsed["llm"]["default_model"] == "main"
    assert "active_profile" not in parsed["llm"]
    assert "profiles" not in parsed["llm"]
    assert "active" not in parsed["llm"]
    assert "providers" not in parsed["llm"]
    assert parsed["llm"]["models"]["main"]["type"] == "openai_compatible"
    # api_key_env 不再是 init 默认内容；API key 通过 Web Setup 填写
    assert parsed["llm"]["models"]["main"]["base_url"] == "https://your-router.example.com/v1"
    assert parsed["llm"]["models"]["main"]["model"] == "your-model-name"
    assert parsed["telemetry"]["local_only"] is True

    forbidden = (
        "sources:",
        "registry:",
        "state:",
        "runs_dir",
        "index_file",
        "obsidian:",
        "include_dirs",
        "exclude_dirs",
        "search:",
        "bm25:",
        "hybrid:",
        "prompts:",
        "record_prompts",
        "record_outputs",
        "cheap-model",
        "strong-model",
        "qwen_coder_fast",
        "qwen_coder_strong",
        "fake_fast",
        "fake_strong",
        "fake://",
    )
    for marker in forbidden:
        assert marker not in text


def test_init_does_not_create_env_example_on_first_run(tmp_path: Path) -> None:
    """first-run init 不创建 env 模板，避免把 advanced 兼容路径变成用户主路径。"""

    project_root = tmp_path / "project"
    vault = tmp_path / "vault"
    plan = build_plan(
        vault,
        project_root=project_root,
        repo_root=bundled_asset_path_for_process(),
    )
    execute_plan(plan)

    assert not (project_root / ".env.example").exists()
    assert all(item.target.name != ".env.example" for item in plan.items)


def test_init_default_skeleton_uses_local_sources_not_cubox(tmp_path: Path) -> None:
    """first-run 默认骨架只能表达本地文件/文件夹 source 主路径。

    中文学习型说明：Cubox 仍可作为 adapter/test fixture 存在，但不能在
    ``mindforge init`` 的新用户默认目录里出现，避免把第一阶段误解成
    Cubox-first workflow。
    """

    project_root = tmp_path / "project"
    vault = project_root / "vault"
    plan = build_plan(
        vault,
        project_root=project_root,
        repo_root=bundled_asset_path_for_process(),
    )
    execute_plan(plan)

    assert (vault / "00-Inbox" / "ManualNotes").is_dir()
    assert not (vault / "00-Inbox" / "Cubox").exists()


def test_init_help_uses_model_setup_language_not_legacy_env_modes() -> None:
    """init help 是 first-run surface，不能继续把 env/fake/demo/profile 当主路径。"""

    res = runner.invoke(app, ["init", "--help"])

    assert res.exit_code == 0, res.output
    assert "configs/" in res.output
    for token in (".env", "env", "environment variable", "fake", "demo", "profile fake", "Cubox"):
        assert token not in res.output


def test_init_default_vault_root_is_project_relative(tmp_path: Path) -> None:
    """默认 init 在 project root 下创建 ``vault/``，YAML 也写相对 ``vault``。"""

    project_root = tmp_path / "project"
    vault = project_root / "vault"
    plan = build_plan(
        vault,
        project_root=project_root,
        repo_root=bundled_asset_path_for_process(),
    )
    execute_plan(plan)

    generated = project_root / "configs" / "mindforge.yaml"
    parsed = yaml.safe_load(generated.read_text(encoding="utf-8"))

    assert parsed["vault"]["root"] == "vault"
    assert load_mindforge_config(generated).vault.root == vault.resolve()


def test_clean_clone_web_bootstrap_creates_safe_local_runtime_config(tmp_path: Path) -> None:
    """clean clone 只有 example 时，Web 首次启动应创建安全本地 runtime config。

    中文学习型说明：`configs/mindforge.yaml` 是本地运行时文件，不能提交到 Git；
    因此 GitHub clone 后的 `mindforge web` 必须能自己生成无 secret、无模型的
    初始配置，让用户进入 Web Setup 再添加真实模型。
    """

    workspace = tmp_path / "mindforge"
    (workspace / "configs").mkdir(parents=True)
    (workspace / "configs" / "mindforge_example.yaml").write_text(
        (REPO_ROOT / "configs" / "mindforge_example.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (workspace / "pyproject.toml").write_text("[project]\nname='mindforge'\n", encoding="utf-8")
    (workspace / "src" / "mindforge").mkdir(parents=True)

    result = maybe_bootstrap_local_config(Path("configs/mindforge.yaml"), cwd=workspace)
    generated = workspace / "configs" / "mindforge.yaml"
    raw_text = generated.read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw_text)

    assert result.created is True
    assert result.config_path == generated
    assert parsed["vault"]["root"] == "vault"
    assert parsed["llm"]["default_model"] is None
    assert parsed["llm"]["models"] == {}
    assert parsed["llm"]["routing"] == {}
    assert parsed["wiki"] == {
        "mode": "deterministic",
        "model": None,
        "auto_rebuild_on_approve": False,
    }
    assert load_mindforge_config(generated).llm.models == {}

    forbidden = (
        "api_key",
        "active_profile",
        "profiles",
        "fake",
        "fake_fast",
        "fake_strong",
        "api_key_env",
        "base_url_env",
        "model_env",
    )
    for token in forbidden:
        assert token not in raw_text


def test_clean_clone_web_bootstrap_does_not_overwrite_existing_config(tmp_path: Path) -> None:
    workspace = tmp_path / "mindforge"
    config_dir = workspace / "configs"
    config_dir.mkdir(parents=True)
    (config_dir / "mindforge_example.yaml").write_text("version: 0.7\n", encoding="utf-8")
    existing = config_dir / "mindforge.yaml"
    existing.write_text("version: 0.7\nvault:\n  root: custom-vault\n", encoding="utf-8")

    result = maybe_bootstrap_local_config(workspace / "configs" / "mindforge.yaml", cwd=workspace)

    assert result.created is False
    assert existing.read_text(encoding="utf-8") == "version: 0.7\nvault:\n  root: custom-vault\n"


def test_clean_clone_web_bootstrap_does_not_modify_example_template(tmp_path: Path) -> None:
    workspace = tmp_path / "mindforge"
    config_dir = workspace / "configs"
    config_dir.mkdir(parents=True)
    example = config_dir / "mindforge_example.yaml"
    original = "version: 0.7\n# example stays immutable\n"
    example.write_text(original, encoding="utf-8")
    (workspace / "pyproject.toml").write_text("[project]\nname='mindforge'\n", encoding="utf-8")
    (workspace / "src" / "mindforge").mkdir(parents=True)

    maybe_bootstrap_local_config(Path("configs/mindforge.yaml"), cwd=workspace)

    assert example.read_text(encoding="utf-8") == original


def test_minimal_user_override_merges_with_internal_defaults(tmp_path: Path) -> None:
    """极简用户 YAML 必须能和 internal defaults 合并成完整运行配置。"""

    cfg_path = tmp_path / "configs" / "mindforge.yaml"
    cfg_path.parent.mkdir()
    vault = tmp_path / "vault"
    cfg_path.write_text(
        """
version: 0.1
vault:
  root: "{vault}"
llm:
  active: fake
  providers:
    fake:
      type: fake
      purpose: offline_demo_ci_deterministic_tests
telemetry:
  enabled: true
  local_only: true
""".format(vault=vault),
        encoding="utf-8",
    )

    cfg = load_mindforge_config(cfg_path)

    assert cfg.vault.root == vault
    assert cfg.vault.inbox_root == "00-Inbox"
    assert cfg.sources.active_entries()
    assert cfg.state.state_file == "state.json"
    assert cfg.prompts.for_stage("distill") == "v1"
    assert cfg.search.bm25.enabled is True
    assert cfg.llm.active_profile == "fake"


def test_new_active_wins_over_legacy_active_profile(tmp_path: Path) -> None:
    """同时存在新旧字段时，产品语义以 ``llm.active`` 为准。"""

    cfg_path = tmp_path / "configs" / "mindforge.yaml"
    cfg_path.parent.mkdir()
    cfg_path.write_text(
        """
version: 0.1
vault:
  root: "/tmp/provider-selection"
llm:
  active: fake
  active_profile: anthropic
  providers:
    fake:
      type: fake
      purpose: offline_demo_ci_deterministic_tests
    anthropic:
      type: anthropic
      api_key_env: MINDFORGE_ANTHROPIC_API_KEY
      default_base_url: "https://api.anthropic.com"
      default_model: "claude-3-5-haiku-latest"
  profiles:
    anthropic:
      provider: anthropic
      api_key_env: MINDFORGE_ANTHROPIC_API_KEY
      default_model: "claude-3-5-haiku-latest"
""",
        encoding="utf-8",
    )

    cfg = load_mindforge_config(cfg_path)

    assert cfg.llm.active_profile == "fake"


def test_llm_active_unknown_provider_fails_fast(tmp_path: Path) -> None:
    cfg_path = tmp_path / "configs" / "mindforge.yaml"
    cfg_path.parent.mkdir()
    cfg_path.write_text(
        """
version: 0.1
vault:
  root: "/tmp/provider-selection"
llm:
  active: missing_provider
  providers:
    fake:
      type: fake
      purpose: offline_demo_ci_deterministic_tests
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="missing_provider"):
        load_mindforge_config(cfg_path)


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


def _minimal_config_with_new_llm(llm: dict) -> dict:
    data = _minimal_valid_config()
    data["llm"] = llm
    return data


def test_single_model_llm_config_uses_default_for_all_workflow_steps(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        _minimal_config_with_new_llm(
            {
                "default_model": "main",
                "models": {
                    "main": {
                        "type": "openai_compatible",
                        "api_key_env": "MINDFORGE_LLM_API_KEY",
                        "base_url": "https://router.example.com/v1",
                        "model": "main-model",
                    }
                },
            }
        ),
    )

    cfg = load_mindforge_config(p)

    assert cfg.llm.default_model == "main"
    assert cfg.llm.routing == {stage: "main" for stage in REQUIRED_STAGES}
    for stage in REQUIRED_STAGES:
        model = cfg.llm.resolve_stage(stage)
        assert model.alias == "main"
        assert model.type == "openai_compatible"
        assert model.model == "main-model"


def test_partial_llm_routing_falls_back_to_default_model(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        _minimal_config_with_new_llm(
            {
                "default_model": "strong",
                "models": {
                    "cheap": {
                        "type": "openai_compatible",
                        "base_url": "https://router.example.com/v1",
                        "model": "cheap-model",
                    },
                    "strong": {
                        "type": "anthropic_compatible",
                        "api_key_env": "MINDFORGE_LLM_API_KEY",
                        "base_url": "https://router.example.com/anthropic",
                        "model": "strong-model",
                    },
                },
                "routing": {
                    "triage": "cheap",
                    "link_suggestion": "cheap",
                },
            }
        ),
    )

    cfg = load_mindforge_config(p)

    assert cfg.llm.routing["triage"] == "cheap"
    assert cfg.llm.routing["link_suggestion"] == "cheap"
    assert cfg.llm.routing["distill"] == "strong"
    assert cfg.llm.routing["review_questions"] == "strong"
    assert cfg.llm.routing["action_extraction"] == "strong"


def _model_config(alias: str) -> ModelConfig:
    return ModelConfig(
        alias=alias,
        provider="test",
        type="fake",
        base_url="fake://",
        model=f"{alias}-model",
        timeout_seconds=5,
        max_retries=0,
    )


def test_resolve_stage_falls_back_to_default_model_when_routing_is_missing() -> None:
    """执行边界也要做 default_model fallback，不能依赖 YAML parse 已经补齐。

    中文学习型说明：clean clone 后 Web Setup 可能产生只有 default_model 的新格式
    配置；pipeline runtime 必须在最后一道解析边界兜住缺失 stage，避免旧
    profile[stage] 语义重新抛出 KeyError。
    """

    llm = LLMConfig(
        active_profile="__model_routing__",
        profiles={"__model_routing__": {}},
        models={"main": _model_config("main")},
        default_model="main",
        routing={},
    )

    assert llm.resolve_stage("triage").alias == "main"


def test_resolve_stage_without_routing_or_default_model_fails_clearly() -> None:
    llm = LLMConfig(
        active_profile="__model_routing__",
        profiles={"__model_routing__": {}},
        models={},
        default_model=None,
        routing={},
    )

    with pytest.raises(ConfigError, match="No model configured for stage 'triage'"):
        llm.resolve_stage("triage")


def test_resolve_stage_bad_model_reference_fails_clearly() -> None:
    llm = LLMConfig(
        active_profile="__model_routing__",
        profiles={"__model_routing__": {"triage": "ghost"}},
        models={"main": _model_config("main")},
        default_model=None,
        routing={"triage": "ghost"},
    )

    with pytest.raises(ConfigError, match="Model 'ghost' referenced by stage 'triage'"):
        llm.resolve_stage("triage")


def test_legacy_profile_missing_stage_does_not_raise_key_error() -> None:
    """旧 profiles 兼容路径也必须收敛成 ConfigError，而不是 KeyError。"""

    llm = LLMConfig(
        active_profile="legacy",
        profiles={"legacy": {"distill": "main"}},
        models={"main": _model_config("main")},
        default_model=None,
        routing={"distill": "main"},
        legacy_config_detected=True,
    )

    with pytest.raises(ConfigError, match="No model configured for stage 'triage'"):
        llm.resolve_stage("triage")


def test_resolve_all_required_stages_use_default_without_key_error() -> None:
    llm = LLMConfig(
        active_profile="__model_routing__",
        profiles={"__model_routing__": {}},
        models={"main": _model_config("main")},
        default_model="main",
        routing={},
    )

    assert {stage: llm.resolve_stage(stage).alias for stage in REQUIRED_STAGES} == {
        stage: "main" for stage in REQUIRED_STAGES
    }


def test_llm_routing_missing_model_fails_clearly(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        _minimal_config_with_new_llm(
            {
                "default_model": "main",
                "models": {
                    "main": {
                        "type": "openai_compatible",
                        "base_url": "https://router.example.com/v1",
                        "model": "main-model",
                    }
                },
                "routing": {"triage": "ghost"},
            }
        ),
    )

    with pytest.raises(ConfigError, match="llm.routing.triage='ghost'.*llm.models"):
        load_mindforge_config(p)


def test_llm_default_model_missing_fails_clearly(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        _minimal_config_with_new_llm(
            {
                "default_model": "ghost",
                "models": {
                    "main": {
                        "type": "openai_compatible",
                        "base_url": "https://router.example.com/v1",
                        "model": "main-model",
                    }
                },
            }
        ),
    )

    with pytest.raises(ConfigError, match="llm.default_model='ghost'.*llm.models"):
        load_mindforge_config(p)


def test_llm_model_type_is_required_and_not_inferred_from_url(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        _minimal_config_with_new_llm(
            {
                "default_model": "main",
                "models": {
                    "main": {
                        "api_key_env": "MINDFORGE_LLM_API_KEY",
                        "base_url": "https://api.anthropic.com",
                        "model": "claude-3-5-haiku-latest",
                    }
                },
            }
        ),
    )

    with pytest.raises(ConfigError, match="llm.models.main.type"):
        load_mindforge_config(p)


def test_llm_supported_types_and_local_openai_compatible_config(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        _minimal_config_with_new_llm(
            {
                "default_model": "local",
                "models": {
                    "anthropic_native": {
                        "type": "anthropic",
                        "api_key_env": "MINDFORGE_ANTHROPIC_API_KEY",
                        "base_url": "https://api.anthropic.com",
                        "model": "claude-3-5-haiku-latest",
                    },
                    "anthropic_router": {
                        "type": "anthropic_compatible",
                        "api_key_env": "MINDFORGE_LLM_API_KEY",
                        "base_url": "https://router.example.com/anthropic",
                        "model": "strong-model",
                    },
                    "local": {
                        "type": "openai_compatible",
                        "api_key_env": "MINDFORGE_LOCAL_API_KEY",
                        "api_key_optional": True,
                        "base_url": "http://localhost:11434/v1",
                        "model": "qwen2.5:14b",
                    },
                    "official_openai": {
                        "type": "openai",
                        "api_key_env": "OPENAI_API_KEY",
                        "model": "gpt-4o-mini",
                    },
                },
                "routing": {
                    "triage": "local",
                    "distill": "anthropic_native",
                    "review_questions": "anthropic_router",
                    "action_extraction": "official_openai",
                },
            }
        ),
    )

    cfg = load_mindforge_config(p)

    assert cfg.llm.models["anthropic_native"].type == "anthropic"
    assert cfg.llm.models["anthropic_router"].type == "anthropic_compatible"
    assert cfg.llm.models["local"].type == "openai_compatible"
    assert cfg.llm.models["official_openai"].type == "openai"
    assert cfg.llm.models["official_openai"].base_url == ""
    assert cfg.llm.models["local"].api_key_optional is True


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
    data["sources"]["enabled"].append("ghost_source")
    p = _write_yaml(tmp_path, data)
    with pytest.raises(ConfigError, match="ghost_source"):
        load_mindforge_config(p)


def test_missing_required_top_field_uses_internal_defaults(tmp_path: Path) -> None:
    """用户 override 可以省略 internal defaults 已覆盖的顶层配置。"""

    data = _minimal_valid_config()
    data.pop("triage")
    p = _write_yaml(tmp_path, data)
    cfg = load_mindforge_config(p)
    assert cfg.triage.default_track == "unrouted"
