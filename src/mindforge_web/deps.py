"""FastAPI dependencies for MindForge Web."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request

from mindforge_web.services.web_facade import WebFacade


def get_facade(request: Request) -> WebFacade:
    facade = getattr(request.app.state, "facade", None)
    if not isinstance(facade, WebFacade):
        config_path = getattr(request.app.state, "config_path", Path("configs/mindforge.yaml"))
        vault_override = getattr(request.app.state, "vault_override", None)
        host = getattr(request.app.state, "host", "127.0.0.1")
        facade = WebFacade(config_path=config_path, vault_override=vault_override, host=host)
        request.app.state.facade = facade
    return facade
