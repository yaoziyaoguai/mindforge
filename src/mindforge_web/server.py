"""Uvicorn server entry for `mindforge web`."""

from __future__ import annotations

import socket
import webbrowser
from pathlib import Path


def run_server(
    *,
    host: str,
    port: int,
    open_browser: bool,
    config_path: Path,
    vault_override: Path | None,
    static_dir: Path | None = None,
) -> None:
    """启动本地 Web server；默认只绑定 127.0.0.1。

    ``static_dir`` 允许调用方覆盖前端 build 产物目录（仅测试/CI 使用）。
    为 ``None`` 时自动推导为仓库根 ``web/dist``；如果 ``web/dist/index.html``
    不存在则 fail fast，避免静默启动一个只有 API route、前端 404 的 Web。
    """

    try:
        import uvicorn
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on env
        raise RuntimeError(
            "Web dependencies are missing. Install with: pip install -e '.[web]' "
            "or install fastapi and uvicorn."
        ) from exc

    from mindforge_web.app import create_app

    _ensure_port_available(host=host, port=port)

    if static_dir is None:
        # 中文学习型说明：fresh clone / pip install 后 web/dist 不存在。
        # 此时直接启动会导致 /setup 等前端路由 404，用户按 README 操作
        # 会撞到一个只有 API 的误导性 Web。这里 fail fast 并给出构建指引。
        static_dir = Path(__file__).resolve().parents[2] / "web" / "dist"

    if not (static_dir / "index.html").exists():
        raise RuntimeError(
            "Web frontend is not built.\n"
            "Web 前端尚未构建，缺少 web/dist/index.html。\n\n"
            "请先构建 Web 前端：\n"
            "  cd web\n"
            "  npm install\n"
            "  npm run build\n"
            "  cd ..\n\n"
            "然后重新启动：\n"
            "  mindforge web --open\n\n"
            "说明：/setup 等 Web 页面需要已构建的前端 assets；"
            "单独的 API routes 不足以完成 Web Setup。"
        )

    app = create_app(
        config_path=config_path,
        vault_override=vault_override,
        host=host,
        static_dir=static_dir,
    )
    url = f"http://{host}:{port}"
    if open_browser:
        webbrowser.open(url)
    uvicorn.run(app, host=host, port=port, log_level="info")


def _ensure_port_available(*, host: str, port: int) -> None:
    """在打开浏览器前确认端口可用，避免用户落到旧 workspace 的 Web server。

    Web Setup 保存模型配置时必须写入当前 workspace。如果端口已被旧 server
    占用却先打开浏览器，用户可能在旧页面完成保存，当前 CLI/status 仍然
    needs setup。这里先做一次短生命周期 bind，只验证端口边界，不读取配置或
    secret。
    """

    try:
        with socket.create_server((host, port)):
            return
    except OSError as exc:
        fallback_port = port + 1 if port < 65535 else 8766
        raise RuntimeError(
            "MindForge Web could not start because "
            f"http://{host}:{port} is already in use. "
            "Stop the existing server or run: "
            f"mindforge web --port {fallback_port}"
        ) from exc
