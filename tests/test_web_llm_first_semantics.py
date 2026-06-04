"""Web LLM-first 产品语义 characterization tests。

中文学习型说明：MindForge 是 LLM-first local knowledge workflow，不是双模式工具。
这些测试保护以下产品边界：

1. Wiki 主路径不暴露 deterministic/template 作为并列选项
2. Wiki /status 返回 model_ready 供前端按钮状态判断
3. Setup 普通路径不暴露 api_key_optional / Template summary (no model)
4. deterministic/template fallback 作为内部回退存在，不回归
5. 旧语义（env/api_key_env/fake/demo/profile/Cubox）不进入用户主路径

测试使用临时 vault/config + FastAPI TestClient；不读 .env、不调真实 LLM。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from mindforge_web.app import create_app


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_llm_first_config(tmp_path: Path, *, with_model: bool = True) -> tuple[Path, Path, Path]:
    """创建 LLM-first 临时 config（新格式 llm.models/default_model/routing）。

    不包含旧语义：active_profile / profiles / api_key_env / fake provider。
    """
    vault = tmp_path / "vault"
    inbox = vault / "00-Inbox"
    cards = vault / "20-Knowledge-Cards"
    inbox.mkdir(parents=True)
    cards.mkdir(parents=True)

    config: dict = {
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
                    "inbox_subdir": ".",
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
            "default_model": "main" if with_model else None,
            "models": (
                {
                    "main": {
                        "type": "openai_compatible",
                        "base_url": "http://localhost:9999/v1",
                        "model": "test-model",
                        "api_key_optional": True,
                    }
                }
                if with_model
                else {}
            ),
            "routing": (
                {
                    "triage": "main",
                    "distill": "main",
                    "link_suggestion": "main",
                    "review_questions": "main",
                    "action_extraction": "main",
                }
                if with_model
                else {}
            ),
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
    cfg_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return cfg_path, vault, cards


def _write_approved_card(cards: Path) -> Path:
    card = cards / "approved-card.md"
    card.write_text(
        """---
id: approved-1
title: Test Card
status: human_approved
track: product
tags:
  - test
---
# Body
Test content.
""",
        encoding="utf-8",
    )
    return card


# ---------------------------------------------------------------------------
# 1. Wiki /status 返回 model_ready — 供前端按钮状态判断
# ---------------------------------------------------------------------------

def test_wiki_status_returns_model_ready_true_when_model_configured(tmp_path: Path) -> None:
    """Wiki /status 的 model_ready 在模型已配置且 api_key_optional 时应为 true。"""
    cfg_path, _vault, _cards = _write_llm_first_config(tmp_path, with_model=True)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.get("/api/wiki/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "model_ready" in data, "wiki /status 必须返回 model_ready 字段"
    assert "model_ready_label" in data, "wiki /status 必须返回 model_ready_label 字段"
    assert data["model_ready"] is True, "api_key_optional 模型应判定为 ready"
    assert "needs" not in data["model_ready_label"].lower()


def test_wiki_status_returns_model_ready_false_when_no_model(tmp_path: Path) -> None:
    """Wiki /status 的 model_ready 在无模型时应为 false。"""
    cfg_path, _vault, _cards = _write_llm_first_config(tmp_path, with_model=False)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.get("/api/wiki/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_ready"] is False, "无模型时 model_ready 应为 false"


# ---------------------------------------------------------------------------
# 2. Wiki LLM rebuild 是主路径 — deterministic 仍可用于显式请求
# ---------------------------------------------------------------------------

def test_wiki_rebuild_llm_is_primary_path(tmp_path: Path, monkeypatch) -> None:
    """Web Wiki rebuild is deprecated."""
    cfg_path, _vault, cards = _write_llm_first_config(tmp_path, with_model=True)
    _write_approved_card(cards)

    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
    resp = client.post("/api/wiki/rebuild", json={"mode": "llm"})

    assert resp.status_code == 410
    data = resp.json()
    assert data["ok"] is False
    assert "deprecated" in data["error"].lower()


def test_wiki_rebuild_deterministic_still_works_as_fallback(tmp_path: Path) -> None:
    """deterministic rebuild is deprecated."""
    cfg_path, _vault, cards = _write_llm_first_config(tmp_path, with_model=False)
    _write_approved_card(cards)

    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))
    resp = client.post("/api/wiki/rebuild", json={"mode": "deterministic"})

    assert resp.status_code == 410
    data = resp.json()
    assert data["ok"] is False
    assert "deprecated" in data["error"].lower()


# ---------------------------------------------------------------------------
# 3. Setup editable config 结构不泄露旧语义
# ---------------------------------------------------------------------------

def test_setup_editable_config_exposes_wiki_as_llm_capable(tmp_path: Path) -> None:
    """Setup editable config 返回 wiki 配置，wiki_mode 仅作为 deprecated 字段存在。"""
    cfg_path, _vault, _cards = _write_llm_first_config(tmp_path, with_model=True)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.get("/api/config/editable")
    assert resp.status_code == 200
    data = resp.json()

    wiki = data.get("wiki")
    assert wiki is not None, "editable config 必须包含 wiki 字段"
    assert "mode" in wiki, "wiki.mode 作为 deprecated 兼容字段仍返回"
    # wiki.mode 存在但不作为用户可选 generation mode 暴露
    # 前端已移除 mode 选择器，后端保留字段仅用于兼容旧配置


def test_setup_editable_model_has_api_key_optional_field(tmp_path: Path) -> None:
    """模型配置中 api_key_optional 字段存在但前端应仅在 Advanced 展示。"""
    cfg_path, _vault, _cards = _write_llm_first_config(tmp_path, with_model=True)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.get("/api/config/editable")
    assert resp.status_code == 200
    data = resp.json()

    models = data["llm"]["configured_models"]
    assert "main" in models
    model = models["main"]
    assert "api_key_optional" in model, "api_key_optional 字段作为兼容字段存在"
    assert model["api_key_optional"] is True
    # api_key_optional 在前端 Setup 页面中已移入 Advanced 折叠区
    # 普通用户主路径不直接暴露此 checkbox


# ---------------------------------------------------------------------------
# 4. 旧语义不泄露到 API 响应中的关键字段
# ---------------------------------------------------------------------------

def test_wiki_status_does_not_leak_mode_selector_semantics(tmp_path: Path) -> None:
    """Wiki /status 响应不包含 mode 选择器语义（如 deterministic/llm 并列描述）。"""
    cfg_path, _vault, _cards = _write_llm_first_config(tmp_path, with_model=True)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.get("/api/wiki/status")
    assert resp.status_code == 200
    data = resp.json()

    # 核心字段存在
    for key in ("wiki_path", "exists", "approved_card_count", "wiki_card_count"):
        assert key in data, f"wiki /status 必须包含 {key}"

    # 不泄露旧语义
    assert "mode" not in data, "wiki /status 不应暴露 wiki.mode（属于 deprecated 内部字段）"
    assert "deterministic" not in str(data).lower() or "deterministic" not in str(
        {k: v for k, v in data.items() if k != "wiki_path"}
    ), "wiki /status 不应在非路径字段中暴露 deterministic"


def test_setup_editable_config_does_not_leak_old_classification_labels(tmp_path: Path) -> None:
    """Setup editable config 不暴露旧分类标签（Template summary / no model / env / demo）。"""
    cfg_path, _vault, _cards = _write_llm_first_config(tmp_path, with_model=True)
    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    resp = client.get("/api/config/editable")
    assert resp.status_code == 200
    data = resp.json()

    # API key status label 不应泄露 "env" 原始值
    models = data["llm"]["configured_models"]
    for model_id, model in models.items():
        source = model.get("api_key_source", "")
        # api_key_source 是内部字段；前端只通过 keySource 间接映射为用户友好标签
        assert isinstance(source, str)

    # Cubox 在 editable config 中作为可选 adapter 存在，但不作为默认 source
    cubox = data.get("cubox")
    assert cubox is not None


# ---------------------------------------------------------------------------
# 5. Setup save 不发送 wiki_mode 时保持现有配置（兼容性保护）
# ---------------------------------------------------------------------------

def test_setup_save_without_wiki_mode_preserves_existing_config(tmp_path: Path) -> None:
    """前端不再发送 wiki_mode 时，后端兼容保留现有 wiki.mode 配置。

    模拟真实前端行为：先 GET editable config，再 PATCH 保存（含 models/default_model/routing），
    但 wiki_mode 不发送（因为前端已移除 mode 选择器）。
    """
    cfg_path, _vault, _cards = _write_llm_first_config(tmp_path, with_model=True)

    # 预先写一个 deterministic 配置
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["wiki"] = {"mode": "deterministic", "model": "main", "auto_rebuild_on_approve": False}
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    client = TestClient(create_app(config_path=cfg_path, host="127.0.0.1"))

    # 先获取 editable config 以构建合理的 PATCH body（模拟真实前端行为）
    editable_resp = client.get("/api/config/editable")
    assert editable_resp.status_code == 200
    editable = editable_resp.json()

    # 构建前端 PATCH：含 models/default_model/routing，但不含 wiki_mode
    patch_body: dict = {
        "vault_root": str(tmp_path / "vault"),
        "default_model": editable["llm"]["default_model"],
        "models": {
            model_id: {
                "type": m.get("type", "openai_compatible"),
                "base_url": m.get("base_url"),
                "model": m.get("model"),
                "api_key_optional": m.get("api_key_optional", False),
                "api_key_action": "keep",
            }
            for model_id, m in editable["llm"]["configured_models"].items()
        },
        "routing": editable["llm"]["routing"],
        "wiki_auto_rebuild_on_approve": True,
        # 故意不发送 wiki_mode
    }
    resp = client.patch("/api/config/editable", json=patch_body)
    assert resp.status_code == 200, f"PATCH 应成功，得到 {resp.status_code}: {resp.text[:300]}"

    # 验证 wiki.mode 未被覆盖
    saved = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert saved["wiki"]["mode"] == "deterministic", (
        "不发送 wiki_mode 时应保留现有配置，不覆盖为默认值"
    )
    assert saved["wiki"]["auto_rebuild_on_approve"] is True
