"""CuboxApiAdapter contract tests — Phase 1 Real Cubox opt-in 骨架。

只覆盖**离线 + opt-in 边界**：
- 解析 fixture JSON export → SourceDocument shape；
- 多 item 拆分；
- highlights / metadata / content_hash 与 markdown adapter 同形态；
- ``fetch_inbox`` 显式 ``NotImplementedError``（绝不静默联网）；
- ``CuboxApiCredential.from_env`` 不读取默认变量名（必须显式指定）；
- adapter 注册到 registry 但默认 config 不启用；
- processor / pipeline 不感知 ``cubox_api`` 字段细节（boundary）。
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from mindforge.sources.base import SourceDocument
from mindforge.sources.cubox_api import (
    CuboxApiAdapter,
    CuboxApiCredential,
    CuboxApiNotConfigured,
)
from mindforge.sources.registry import _BUILTIN_ADAPTERS

FIXTURE = Path(__file__).parent / "fixtures" / "sample_cubox_api_export.json"


# ---------------------------------------------------------------------------
# Parse contract
# ---------------------------------------------------------------------------


def test_parse_export_returns_one_doc_per_item() -> None:
    adapter = CuboxApiAdapter()
    docs = adapter.parse_export(FIXTURE)
    assert len(docs) == 2
    assert all(isinstance(d, SourceDocument) for d in docs)
    assert {d.title for d in docs} == {
        "Designing Token Budgets for Long-Context Agents",
        "Approval Outcomes as First-Class Domain Objects",
    }


def test_parse_export_preserves_highlights_with_notes() -> None:
    adapter = CuboxApiAdapter()
    docs = adapter.parse_export(FIXTURE)
    first = docs[0]
    assert len(first.highlights) == 3
    annotated = [h for h in first.highlights if h.note]
    assert len(annotated) == 1
    assert "ReAct" in annotated[0].note


def test_parse_export_sets_source_type_and_metadata() -> None:
    adapter = CuboxApiAdapter()
    docs = adapter.parse_export(FIXTURE)
    for d in docs:
        assert d.source_type == "cubox_api"
        assert d.source_id.startswith("cubox_api:")
        assert d.metadata.get("cubox_item_id")
        assert d.content_hash  # 非空


def test_load_returns_first_item_for_single_doc_contract() -> None:
    adapter = CuboxApiAdapter()
    doc = adapter.load(str(FIXTURE))
    assert doc.title == "Designing Token Budgets for Long-Context Agents"


def test_can_handle_only_json() -> None:
    adapter = CuboxApiAdapter()
    assert adapter.can_handle("/tmp/x.json") is True
    assert adapter.can_handle("/tmp/x.md") is False


def test_parse_export_rejects_non_array_top_level(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"items": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="顶层必须是 array"):
        CuboxApiAdapter().parse_export(bad)


def test_missing_file_raises_filenotfound(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        CuboxApiAdapter().parse_export(tmp_path / "nope.json")


# ---------------------------------------------------------------------------
# Opt-in safety boundary
# ---------------------------------------------------------------------------


def test_fetch_inbox_explicitly_not_implemented() -> None:
    """真实 HTTP 路径必须显式爆炸，绝不静默联网。"""
    adapter = CuboxApiAdapter()
    with pytest.raises(NotImplementedError, match="opt-in"):
        adapter.fetch_inbox()


def test_credential_from_env_does_not_read_default_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """from_env 必须显式传变量名；MINDFORGE_CUBOX_TOKEN 不会被自动读取。"""
    monkeypatch.setenv("MINDFORGE_CUBOX_TOKEN", "should-not-be-picked-up")
    with pytest.raises(TypeError):
        # 故意不传参数 —— from_env 必须要求显式 var_name
        CuboxApiCredential.from_env()  # type: ignore[call-arg]


def test_credential_from_env_requires_nonempty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CUSTOM_TOKEN_VAR", raising=False)
    with pytest.raises(CuboxApiNotConfigured):
        CuboxApiCredential.from_env("CUSTOM_TOKEN_VAR")


def test_credential_default_unconfigured() -> None:
    cred = CuboxApiCredential()
    assert cred.is_configured() is False
    assert cred.token is None


# ---------------------------------------------------------------------------
# Registry & boundary
# ---------------------------------------------------------------------------


def test_adapter_registered_in_builtin_registry() -> None:
    assert "CuboxApiAdapter" in _BUILTIN_ADAPTERS
    assert _BUILTIN_ADAPTERS["CuboxApiAdapter"] is CuboxApiAdapter


def test_default_config_does_not_enable_cubox_api() -> None:
    """默认 configs/mindforge.yaml 不能启用 cubox_api（必须用户显式 opt-in）。"""
    cfg = Path(__file__).resolve().parent.parent / "configs" / "mindforge.yaml"
    text = cfg.read_text(encoding="utf-8")
    # 允许以 source_type 字符串出现在注释 / 文档中，但不允许在 enabled 列表中
    # 简化判断：默认配置不包含 cubox_api 这个字符串即可
    assert "cubox_api" not in text, (
        "默认 configs/mindforge.yaml 不应包含 cubox_api；"
        "Real Cubox API adapter 是 opt-in，由用户在自己的 config override 中启用。"
    )


# ---------------------------------------------------------------------------
# Credential redaction & data-leak boundary
# ---------------------------------------------------------------------------


def test_credential_repr_does_not_leak_token() -> None:
    """repr / str 都必须只暴露 credential_present，不暴露 token 明文。"""
    cred = CuboxApiCredential(token="FAKE_TOKEN_DO_NOT_LEAK_ABC123")
    assert "FAKE_TOKEN_DO_NOT_LEAK_ABC123" not in repr(cred)
    assert "FAKE_TOKEN_DO_NOT_LEAK_ABC123" not in str(cred)
    assert "FAKE_TOKEN_DO_NOT_LEAK_ABC123" not in f"{cred}"
    assert "credential_present=True" in repr(cred)


def test_credential_repr_when_unconfigured() -> None:
    cred = CuboxApiCredential()
    assert "credential_present=False" in repr(cred)


def test_missing_id_error_does_not_leak_item_body() -> None:
    """缺 id 报错只能暴露 keys，不能暴露正文 / url / author。"""
    bad_item = {
        "title": "PRIVATE_TITLE_DO_NOT_LEAK",
        "url": "https://private.example.com/secret",
        "author": "PRIVATE_AUTHOR_DO_NOT_LEAK",
        "content": "PRIVATE_BODY_DO_NOT_LEAK_XYZ",
    }
    adapter = CuboxApiAdapter()
    with pytest.raises(ValueError) as exc_info:
        adapter._item_to_source_document(bad_item, "/tmp/x.json")
    msg = str(exc_info.value)
    assert "PRIVATE_TITLE_DO_NOT_LEAK" not in msg
    assert "PRIVATE_BODY_DO_NOT_LEAK_XYZ" not in msg
    assert "PRIVATE_AUTHOR_DO_NOT_LEAK" not in msg
    assert "private.example.com" not in msg
    # 只允许 keys 出现
    assert "keys=" in msg


def test_source_document_metadata_does_not_carry_credential() -> None:
    """SourceDocument.metadata 必须不包含任何 credential 痕迹。"""
    adapter = CuboxApiAdapter(
        credential=CuboxApiCredential(token="FAKE_TOKEN_DO_NOT_LEAK_DEF456"),
    )
    docs = adapter.parse_export(FIXTURE)
    for d in docs:
        meta_str = repr(d.metadata)
        assert "FAKE_TOKEN_DO_NOT_LEAK_DEF456" not in meta_str
        assert "token" not in d.metadata
        assert "credential" not in d.metadata


def test_fixture_contains_no_credential_artifacts() -> None:
    """fixture 文件本身不能含 token / api_link / credential 字段或 Bearer 头。

    检查方式：
    - JSON 顶层 / item 层不能出现 credential 类 key；
    - 文本不能出现 Bearer / Authorization 头形态（这些只会出现在真实 HTTP）。
    """
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    forbidden_keys = {
        "token",
        "api_token",
        "access_token",
        "api_key",
        "apikey",
        "credential",
        "authorization",
        "bearer",
        "secret",
    }
    for item in raw:
        item_keys = {k.lower() for k in item.keys()}
        leaked = item_keys & forbidden_keys
        assert not leaked, f"fixture item 含 credential-like key: {leaked}"

    text = FIXTURE.read_text(encoding="utf-8")
    assert "Bearer " not in text
    assert "Authorization:" not in text


def test_processor_does_not_import_cubox_api() -> None:

    """boundary：核心 processor / pipeline 不能直接 import cubox_api。"""
    forbidden_modules = [
        Path(__file__).resolve().parent.parent / "src" / "mindforge" / "processor.py",
        Path(__file__).resolve().parent.parent / "src" / "mindforge" / "pipeline.py",
    ]
    for mod_path in forbidden_modules:
        if not mod_path.exists():
            continue
        tree = ast.parse(mod_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "cubox_api" not in node.module, (
                    f"{mod_path.name} 不应 import cubox_api；"
                    f"adapter 应通过 SourceAdapter 抽象注入。"
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "cubox_api" not in alias.name, (
                        f"{mod_path.name} 不应 import cubox_api"
                    )
