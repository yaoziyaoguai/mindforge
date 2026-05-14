"""`mindforge web` server startup boundary tests.

中文学习型说明：Web Setup 是模型配置主入口。server 启动失败时不能先打开
浏览器，否则用户可能在旧 server / 旧 workspace 上保存，最后 CLI status
仍然显示当前 workspace needs setup。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mindforge_web.server import run_server


def test_run_server_does_not_open_browser_when_port_is_in_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """端口占用必须在打开浏览器前失败，避免用户误操作旧 Web server。"""

    opened_urls: list[str] = []
    monkeypatch.setattr("webbrowser.open", opened_urls.append)
    monkeypatch.setattr(
        "socket.create_server",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError(48, "Address already in use")),
    )

    with pytest.raises(RuntimeError, match="already in use"):
        run_server(
            host="127.0.0.1",
            port=8765,
            open_browser=True,
            config_path=tmp_path / "configs" / "mindforge.yaml",
            vault_override=None,
        )

    assert opened_urls == []
