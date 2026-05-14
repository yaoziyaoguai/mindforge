"""Secret handling boundary for Web Setup model configuration.

中文学习型说明：Web Setup 会保存 / 删除 / 展示脱敏 API key，但不能让
``WebConfigService`` 同时承担 secret store 细节和 config view/write 细节。
本模块只封装 secret path、presence、mask、save/delete，不读取或返回 raw key。
"""

from __future__ import annotations

import os
from pathlib import Path

from mindforge.secret_store import SecretStore


class WebConfigSecretManager:
    """Web Setup 的 secret store 适配层；只返回 secret-safe metadata。"""

    def __init__(self, secrets_path: Path) -> None:
        self._store = SecretStore(secrets_path)

    @property
    def path(self) -> Path:
        return self._store.path

    def remove(self, model_id: str) -> None:
        self._store.remove(model_id)

    def apply_api_key_patch(self, model_id: str, model_patch) -> None:
        """根据 api_key_action 写入、清除或保留 local secret store。"""

        action = model_patch.api_key_action or "keep"
        if action == "clear":
            self._store.remove(model_id)
        elif action == "update" and model_patch.api_key:
            self._store.set(model_id, model_patch.api_key)

    def api_key_source(
        self,
        model_id: str,
        model_type: str,
        api_key_env: str | None,
    ) -> str:
        """判断 key 来源；不读取 local secret 明文。"""

        if model_type == "fake":
            return "demo"
        if self._store.present(model_id):
            return "local_secret"
        if api_key_env and os.environ.get(api_key_env):
            return "env"
        return "missing"

    def masked_api_key_value(
        self,
        model_id: str,
        api_key_env: str | None,
        api_key_source: str,
    ) -> str | None:
        """返回脱敏展示值，绝不返回 raw secret。"""

        if api_key_source == "local_secret":
            return self._store.masked(model_id)
        if api_key_source == "env" and api_key_env:
            raw = os.environ.get(api_key_env, "")
            return mask_secret(raw) if raw else None
        return None


def mask_secret(value: str) -> str:
    suffix = value[-4:] if len(value) >= 4 else value
    prefix = "sk-" if value.startswith("sk-") else ""
    return f"{prefix}****{suffix}"


__all__ = ["WebConfigSecretManager", "mask_secret"]
