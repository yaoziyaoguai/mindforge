"""`mindforge web` server startup boundary tests.

中文学习型说明：
- Web Setup 是模型配置主入口。server 启动失败时不能先打开浏览器，
  否则用户可能在旧 server / 旧 workspace 上保存，最后 CLI status
  仍然显示当前 workspace needs setup。
- 根因修复 (2026-05)：fresh clone 后 web/dist 不存在时，``run_server``
  必须 fail fast 并给出清晰构建指引，避免静默启动一个只有 API route、
  /setup 404 的误导性 Web。
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

from mindforge_web.server import run_server


@contextmanager
def _fake_bind(address, **kwargs):
    """模拟端口可用：成功 bind 后立即释放。"""
    yield


def _write_minimal_config(tmp_path: Path) -> None:
    """在 tmp_path 下创建 create_app 可正确解析的 minimal config。"""
    config_dir = tmp_path / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "mindforge.yaml").write_text(
        f"version: 0.1\nvault:\n  root: {vault_dir}\n"
    )


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


def test_run_server_fails_fast_when_frontend_dist_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """web/dist/index.html 缺失时必须 fail fast，不能静默启动 API-only。

    中文学习型说明：这是 Quickstart 根因修复的回归测试。
    模拟 web/dist 不存在的场景，验证 run_server 抛出清晰错误信息，
    包含 npm install / npm run build 构建指引。
    """

    # 确保端口检查通过
    monkeypatch.setattr("socket.create_server", _fake_bind)

    # 创建 minimal config，避免 create_app 解析 config 时失败
    _write_minimal_config(tmp_path)

    # 用一个确定不包含 index.html 的临时目录作为 static_dir
    empty_dir = tmp_path / "empty_dist"
    empty_dir.mkdir()

    with pytest.raises(RuntimeError, match="Web frontend is not built"):
        run_server(
            host="127.0.0.1",
            port=8765,
            open_browser=False,
            config_path=tmp_path / "configs" / "mindforge.yaml",
            vault_override=None,
            static_dir=empty_dir,
        )


def test_run_server_starts_normally_when_frontend_dist_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """web/dist/index.html 存在时应正常启动，SPA fallback 可用。

    中文学习型说明：确保修复没有阻断正常路径。
    """

    # 确保端口检查通过
    monkeypatch.setattr("socket.create_server", _fake_bind)

    # 创建 minimal config
    _write_minimal_config(tmp_path)

    # 创建包含 index.html 的临时 static_dir
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<!DOCTYPE html><html></html>")

    # 拦截 uvicorn.run，避免实际启动 HTTP server
    uvicorn_calls: list[dict] = []
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: uvicorn_calls.append(kwargs))

    run_server(
        host="127.0.0.1",
        port=8765,
        open_browser=False,
        config_path=tmp_path / "configs" / "mindforge.yaml",
        vault_override=None,
        static_dir=dist_dir,
    )

    assert len(uvicorn_calls) == 1
    assert uvicorn_calls[0]["host"] == "127.0.0.1"
    assert uvicorn_calls[0]["port"] == 8765
