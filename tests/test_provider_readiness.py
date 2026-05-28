"""v2.5 U4 Provider Readiness Center tests — API endpoint + response schema 测试。

中文学习型说明：测试 provider readiness API 结构和基本行为，使用合成配置不调用 LLM。
"""

from __future__ import annotations

import pytest


class TestProviderReadinessResponse:
    """验证 ProviderReadinessResponse schema 结构。"""

    def test_minimal_readiness_structure(self):
        """fake-default 配置返回有效就绪状态。"""
        from mindforge_web.schemas import ProviderReadinessResponse

        resp = ProviderReadinessResponse(
            active_profile="fake",
            opt_in_state="fake_default",
            model_setup="needs_setup",
            model_setup_label="needs setup",
            can_run_real_smoke=False,
            provider_mode="fake",
            aliases=[],
            blockers=[],
            invariants={"fake_is_default": True, "secret_value_not_returned": True},
        )
        assert resp.active_profile == "fake"
        assert resp.opt_in_state == "fake_default"
        assert resp.can_run_real_smoke is False
        assert resp.invariants["fake_is_default"] is True

    def test_readiness_with_aliases_and_blockers(self):
        """带 alias 和 blocker 的就绪状态。"""
        from mindforge_web.schemas import ProviderAliasStatus, ProviderReadinessResponse

        aliases = [
            ProviderAliasStatus(
                alias="main",
                type="anthropic_compatible",
                in_active_profile=True,
                api_key_env="ANTHROPIC_API_KEY",
                api_key_present=False,
                base_url_env_present=False,
            ),
        ]
        resp = ProviderReadinessResponse(
            active_profile="real",
            opt_in_state="profile_only",
            model_setup="needs_setup",
            model_setup_label="needs setup",
            can_run_real_smoke=False,
            provider_mode="fake",
            aliases=aliases,
            blockers=["alias 'main' 缺少 api_key (env 不存在)"],
            invariants={"fake_is_default": True},
        )
        assert len(resp.aliases) == 1
        assert resp.aliases[0].api_key_present is False
        assert len(resp.blockers) == 1


class TestProviderReadinessApiEndpoint:
    """验证 provider readiness API 端点可访问。"""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch: pytest.MonkeyPatch):
        """创建带临时 vault/config 的 TestClient。"""
        import yaml
        from fastapi.testclient import TestClient
        from mindforge_web.app import create_app

        vault = tmp_path / "vault"
        cards_dir = vault / "20-Knowledge-Cards"
        cards_dir.mkdir(parents=True)

        config: dict = {
            "version": 0.7,
            "vault": {
                "root": str(vault),
                "cards_dir": "20-Knowledge-Cards",
            },
            "state": {
                "workdir": str(tmp_path / ".mindforge"),
                "state_file": "state.json",
                "runs_dir": "runs",
                "index_file": "index.jsonl",
                "backup_state": True,
            },
            "sources": {
                "enabled": ["plain_markdown"],
                "registry": {
                    "plain_markdown": {
                        "adapter": "PlainMarkdownAdapter",
                        "inbox_subdir": ".",
                        "file_glob": "*.md",
                        "enabled": True,
                    }
                },
            },
            "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
            "llm": {
                "default_model": None,
                "models": {},
                "routing": {},
            },
        }
        config_path = tmp_path / "mindforge.yaml"
        config_path.write_text(yaml.dump(config))

        app = create_app(config_path=config_path, host="127.0.0.1")
        with TestClient(app) as tc:
            self.client = tc

    def test_provider_readiness_endpoint_returns_200(self):
        """GET /api/provider/readiness 返回 200。"""
        resp = self.client.get("/api/provider/readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_profile" in data
        assert "opt_in_state" in data
        assert "model_setup" in data
        assert "can_run_real_smoke" in data
        assert "provider_mode" in data
        assert "aliases" in data
        assert "blockers" in data
        assert "invariants" in data
        assert isinstance(data["aliases"], list)
        assert isinstance(data["blockers"], list)
        assert isinstance(data["invariants"], dict)

    def test_provider_readiness_no_models(self):
        """未配置任何 model 时返回 blocked 状态（model routing 路径无 fake fallback）。"""
        resp = self.client.get("/api/provider/readiness")
        assert resp.status_code == 200
        data = resp.json()
        # model_routing 路径下 active_profile 为 __model_routing__，无模型时 blocked
        assert data["opt_in_state"] == "blocked"
        assert data["can_run_real_smoke"] is False
        assert data["invariants"]["secret_value_not_returned"] is True
        assert data["aliases"] == []
        assert len(data["blockers"]) > 0

    def test_provider_readiness_with_models_no_secret_leak(self, tmp_path, monkeypatch: pytest.MonkeyPatch):
        """配置了 model + api_key_env 时返回 200，不暴露 secret value（P0 DOGFOOD-001 回归测试）。"""
        import yaml
        from fastapi.testclient import TestClient
        from mindforge_web.app import create_app

        vault = tmp_path / "vault"
        cards_dir = vault / "20-Knowledge-Cards"
        cards_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv("DOGFOOD_TEST_KEY", "sk-test-placeholder-not-real")

        config: dict = {
            "version": 0.7,
            "vault": {"root": str(vault), "cards_dir": "20-Knowledge-Cards"},
            "state": {
                "workdir": str(tmp_path / ".mindforge"),
                "state_file": "state.json",
                "runs_dir": "runs",
                "index_file": "index.jsonl",
                "backup_state": True,
            },
            "sources": {
                "enabled": ["plain_markdown"],
                "registry": {
                    "plain_markdown": {
                        "adapter": "PlainMarkdownAdapter",
                        "inbox_subdir": ".",
                        "file_glob": "*.md",
                        "enabled": True,
                    }
                },
            },
            "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
            "llm": {
                "default_model": "main",
                "models": {
                    "main": {
                        "type": "openai_compatible",
                        "base_url": "https://test.example.com/v1",
                        "model": "test-model",
                        "api_key_env": "DOGFOOD_TEST_KEY",
                    }
                },
                "routing": {
                    "triage": "main",
                    "distill": "main",
                },
            },
        }
        config_path = tmp_path / "mindforge.yaml"
        config_path.write_text(yaml.dump(config))

        app = create_app(config_path=config_path, host="127.0.0.1")
        with TestClient(app) as client:
            resp = client.get("/api/provider/readiness")
            assert resp.status_code == 200, f"P0 regression: expected 200, got {resp.status_code}. Body: {resp.text}"
            data = resp.json()

            # 不暴露 secret value
            assert data["invariants"]["secret_value_not_returned"] is True

            # api_key_present 为 bool，不返回 raw key
            for alias in data["aliases"]:
                assert isinstance(alias["api_key_present"], bool)
                assert "api_key_env" in alias
                raw_placeholder = "sk-test-placeholder-not-real"
                assert raw_placeholder not in str(alias)
                assert raw_placeholder not in str(data)

            # 不应包含任何 raw secret 标记
            response_text = resp.text
            assert "sk-test-placeholder-not-real" not in response_text
