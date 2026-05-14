"""Web Setup secret manager boundary tests.

这些测试只使用 tmp_path 下的 synthetic secret store，不读取真实
``.mindforge/secrets.json``。目标是固化 Web Setup 的 secret 边界：
Web 层只能保存、删除、判断 presence、展示 masked 值，不能返回 raw key。
"""

from __future__ import annotations

from types import SimpleNamespace

from mindforge_web.services.web_config_secret_manager import WebConfigSecretManager


def test_secret_manager_updates_keeps_clears_and_masks_tmp_secret(tmp_path, monkeypatch):
    """WebConfigSecretManager 是 Web Setup 的唯一 secret 操作边界。"""

    manager = WebConfigSecretManager(tmp_path / ".mindforge" / "secrets.json")

    assert manager.api_key_source("main", "openai_compatible", None) == "missing"
    assert manager.masked_api_key_value("main", None, "missing") is None

    manager.apply_api_key_patch(
        "main",
        SimpleNamespace(api_key_action="update", api_key="sk-test-value-1234"),
    )
    assert manager.api_key_source("main", "openai_compatible", None) == "local_secret"
    masked = manager.masked_api_key_value("main", None, "local_secret")
    assert masked == "sk-****1234"
    assert "sk-test-value-1234" not in str(masked)

    manager.apply_api_key_patch(
        "main",
        SimpleNamespace(api_key_action="keep", api_key=""),
    )
    assert manager.api_key_source("main", "openai_compatible", None) == "local_secret"

    manager.apply_api_key_patch(
        "main",
        SimpleNamespace(api_key_action="clear", api_key=""),
    )
    assert manager.api_key_source("main", "openai_compatible", None) == "missing"

    monkeypatch.setenv("MINDFORGE_TEST_KEY", "sk-env-value-9999")
    assert manager.api_key_source("env-model", "openai_compatible", "MINDFORGE_TEST_KEY") == "env"
    assert (
        manager.masked_api_key_value("env-model", "MINDFORGE_TEST_KEY", "env")
        == "sk-****9999"
    )
    assert manager.api_key_source("demo", "fake", "MINDFORGE_TEST_KEY") == "demo"
