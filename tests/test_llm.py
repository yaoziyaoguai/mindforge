"""LLM 层单元测试（fake provider + factory + client 路由）。"""

from __future__ import annotations

import json

import pytest

from mindforge.llm import (
    FakeProvider,
    LLMClient,
    LLMRequest,
    ProviderError,
    build_provider_for_model,
    build_providers,
)
from mindforge.llm.client import ResolvedModel


class _FakeMC:
    """轻量 ModelConfig 替身，仅供本文件使用。"""

    def __init__(self, alias: str, type_: str = "fake") -> None:
        self.alias = alias
        self.provider = "fake-provider"
        self.type = type_
        self.base_url = "fake://"
        self.model = f"fake-model-{alias}"
        self.timeout_seconds = 5
        self.max_retries = 1
        self.api_key_env = None
        self.api_key_optional = True


class _FakeLLMConfig:
    def __init__(self) -> None:
        self.active_profile = "default"
        self.models = {"a": _FakeMC("a"), "b": _FakeMC("b")}
        self.profiles = {
            "default": {
                "triage": "a",
                "distill": "b",
                "link_suggestion": "a",
                "review_questions": "b",
                "action_extraction": "b",
            }
        }

    def resolve_stage(self, stage: str):
        return self.models[self.profiles[self.active_profile][stage]]


class _FallbackLLMConfig(_FakeLLMConfig):
    """模拟新 routing/default_model 解析层，不暴露 profile[stage]。"""

    def __init__(self) -> None:
        super().__init__()
        self.default_model = "a"
        self.routing = {}
        self.profiles = {"default": {}}

    def resolve_stage(self, stage: str):
        return self.models[self.default_model]


def test_fake_provider_returns_schema_for_each_stage() -> None:
    fp = FakeProvider()
    for stage in [
        "triage",
        "distill",
        "link_suggestion",
        "review_questions",
        "action_extraction",
    ]:
        out = fp.generate(LLMRequest(prompt="title: foo\ntrack: agent-runtime\n", stage=stage, model="x"))
        payload = json.loads(out.text)
        assert isinstance(payload, dict)
        assert out.tokens_in and out.tokens_out
        assert out.latency_ms is not None


def test_fake_provider_unknown_stage_raises() -> None:
    with pytest.raises(ValueError, match="不识别的 stage"):
        FakeProvider().generate(LLMRequest(prompt="x", stage="bogus", model="x"))


def test_build_providers_dispatch() -> None:
    cfg = _FakeLLMConfig()
    providers = build_providers(cfg)
    assert set(providers) == {"a", "b"}
    assert all(isinstance(p, FakeProvider) for p in providers.values())


def test_build_providers_unknown_type_raises() -> None:
    cfg = _FakeLLMConfig()
    cfg.models["a"] = _FakeMC("a", type_="bogus_type")
    with pytest.raises(ProviderError, match="未注册"):
        build_providers(cfg)


def test_build_provider_for_model_does_not_require_stage_routing() -> None:
    """Wiki synthesis 等单模型用途可复用 provider 工厂，但不绑定 processing routing。"""

    provider = build_provider_for_model(_FakeMC("wiki"))

    assert isinstance(provider, FakeProvider)


def test_client_resolve_for_each_stage() -> None:
    cfg = _FakeLLMConfig()
    client = LLMClient(llm_config=cfg, providers=build_providers(cfg))
    r = client.resolve_model_for_stage("triage")
    assert isinstance(r, ResolvedModel)
    assert r.stage == "triage"
    assert r.model_alias == "a"
    assert r.actual_model == "fake-model-a"
    assert r.type == "fake"


def test_client_resolve_uses_resolved_model_alias_without_profile_lookup() -> None:
    """LLMClient 不应在 resolve_stage 后再次读取 profile[stage]。

    中文学习型说明：新格式允许 stage routing 缺省并 fallback 到 default_model。
    如果 client 又走旧 profile 字典取 alias，就会在 dogfood processing 中复现
    KeyError('triage')。
    """

    cfg = _FallbackLLMConfig()
    client = LLMClient(llm_config=cfg, providers=build_providers(cfg))

    resolved = client.resolve_model_for_stage("triage")

    assert resolved.model_alias == "a"
    assert resolved.actual_model == "fake-model-a"


def test_client_generate_returns_result_and_routes_correctly() -> None:
    cfg = _FakeLLMConfig()
    client = LLMClient(llm_config=cfg, providers=build_providers(cfg))
    out = client.generate(stage="distill", prompt="title: hello\n", options=None)
    assert out.resolved.model_alias == "b"
    assert out.resolved.actual_model == "fake-model-b"
    payload = json.loads(out.result.text)
    assert payload["title"] == "hello"
    assert "ai_summary_bullets" in payload


def test_fake_provider_extracts_rendered_prompt_variable_table_title() -> None:
    """v0.5.1: fake smoke 卡片应继承 source title，而不是退化成 Untitled。"""
    prompt = (
        "## Inputs (variables)\n\n"
        "- `为什么 Agent Runtime 需要显式 Checkpoint`           — 素材标题\n"
        "- `agent-runtime`           — Triager 已分流到的 learning_track id\n"
    )
    out = FakeProvider().generate(LLMRequest(prompt=prompt, stage="distill", model="x"))
    payload = json.loads(out.text)
    assert payload["title"] == "为什么 Agent Runtime 需要显式 Checkpoint"
    assert payload["slug"] == "agent-runtime-checkpoint"


class _BoomProvider(FakeProvider):
    """每次都抛 ProviderError，用于测试重试。"""

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        raise ProviderError("boom")


def test_client_retries_then_raises() -> None:
    cfg = _FakeLLMConfig()
    cfg.models["a"].max_retries = 2  # → 3 次尝试
    boom = _BoomProvider()
    client = LLMClient(llm_config=cfg, providers={"a": boom, "b": FakeProvider()})
    with pytest.raises(ProviderError, match="boom"):
        client.generate(stage="triage", prompt="title: x\n")
    assert boom.calls == 3
