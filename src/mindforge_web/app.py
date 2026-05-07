"""FastAPI app factory for MindForge Local Console."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from mindforge_web.routers import approval, config, drafts, health, home, library, prompts, recall, sources, trash
from mindforge_web.services.web_facade import WebFacade


def create_app(
    *,
    config_path: Path = Path("configs/mindforge.yaml"),
    vault_override: Path | None = None,
    host: str = "127.0.0.1",
    static_dir: Path | None = None,
) -> FastAPI:
    """创建 localhost-only Web app。

    中文学习型说明：app factory 只装配 router/static/facade，不读取 secret，
    不启动 provider，不写 vault。这样 TestClient 可以直接覆盖 facade。
    """

    app = FastAPI(title="MindForge Local Console", version="0.1.0")
    app.state.config_path = config_path
    app.state.vault_override = vault_override
    app.state.host = host
    app.state.facade = WebFacade(
        config_path=config_path,
        vault_override=vault_override,
        host=host,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1", "http://localhost"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(home.router)
    app.include_router(config.router)
    app.include_router(sources.router)
    app.include_router(drafts.router)
    app.include_router(approval.router)
    app.include_router(library.router)
    app.include_router(prompts.router)
    app.include_router(trash.router)
    app.include_router(recall.router)
    if static_dir and static_dir.exists():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="web-assets")

        @app.get("/", include_in_schema=False)
        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str = "") -> FileResponse:
            """Serve React for non-API paths.

            中文学习型说明：FastAPI routers 先注册 `/api/*`，最后才注册这个
            fallback。这样 API 仍由 controller 处理，而 `/setup`、`/drafts`
            这类前端路径刷新时返回同一个 Vite index.html。
            """

            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API route not found")
            return FileResponse(static_dir / "index.html")
    return app
