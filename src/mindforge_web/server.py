"""Uvicorn server entry for `mindforge web`."""

from __future__ import annotations

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
