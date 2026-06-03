"""FastAPI app factory for MindForge Local Console."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from mindforge.first_run_config import maybe_bootstrap_local_config
from mindforge_web.routers import (
    approval, config, discovery, dogfood, drafts, graph, health, home,
    library, lifecycle, processing, prompts, provider_readiness, provenance,
    quality, recall, sources, trash, usage, wiki,
)
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

    bootstrap = maybe_bootstrap_local_config(config_path)
    if bootstrap.config_path is not None:
        config_path = bootstrap.config_path

    app = FastAPI(title="MindForge Local Console", version="0.1.0")

    # 中文学习型说明：Pydantic 的 RequestValidationError 默认在 error detail
    # 中 echo 客户端发送的 raw input（包括 extra forbidden fields 的值）。
    # 这个 handler 在返回 422 前 strip 掉所有 `input` 字段，防止 raw path
    # 等不可信输入通过 validation error 回显。
    from fastapi.exceptions import RequestValidationError
    from fastapi.requests import Request
    from fastapi.responses import JSONResponse

    async def _safe_validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        safe_errors: list[dict] = []
        for err in errors:
            safe = {k: v for k, v in err.items() if k != "input"}
            # model_validator ValueError 会在 ctx.error 中带入 Exception
            # 对象，JSON 无法序列化，统一转为字符串。
            ctx = safe.get("ctx")
            if isinstance(ctx, dict):
                safe["ctx"] = {
                    ck: str(cv) if isinstance(cv, Exception) else cv
                    for ck, cv in ctx.items()
                }
            safe_errors.append(safe)
        return JSONResponse(
            status_code=422,
            content={"detail": safe_errors},
        )

    app.add_exception_handler(RequestValidationError, _safe_validation_handler)

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
    app.include_router(processing.router)
    app.include_router(drafts.router)
    app.include_router(approval.router)
    app.include_router(library.router)
    app.include_router(prompts.router)
    app.include_router(trash.router)
    app.include_router(wiki.router)
    app.include_router(quality.router)
    app.include_router(provenance.router)
    app.include_router(recall.router)
    app.include_router(graph.router)
    app.include_router(discovery.router)
    app.include_router(dogfood.router)
    app.include_router(provider_readiness.router)
    app.include_router(usage.router)
    app.include_router(lifecycle.router)
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
