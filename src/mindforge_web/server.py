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
) -> None:
    """启动本地 Web server；默认只绑定 127.0.0.1。"""

    try:
        import uvicorn
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on env
        raise RuntimeError(
            "Web dependencies are missing. Install with: pip install -e '.[web]' "
            "or install fastapi and uvicorn."
        ) from exc

    from mindforge_web.app import create_app

    _ensure_port_available(host=host, port=port)

    web_dist = Path(__file__).resolve().parents[2] / "web" / "dist"
    app = create_app(
        config_path=config_path,
        vault_override=vault_override,
        host=host,
        static_dir=web_dist if web_dist.exists() else None,
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
