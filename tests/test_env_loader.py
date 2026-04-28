"""env_loader 单测：静默、不覆盖已存在 env、容错。

不依赖外部库；不打印任何 value。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mindforge import env_loader as el


@pytest.fixture(autouse=True)
def _reset() -> None:
    el.reset_for_tests()


def _write_env(p: Path, body: str) -> None:
    p.write_text(body, encoding="utf-8")


def test_loads_simple_kv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MF_TEST_A", raising=False)
    monkeypatch.delenv("MF_TEST_B", raising=False)
    _write_env(tmp_path / ".env", "MF_TEST_A=alpha\nMF_TEST_B=beta\n")
    n = el.load_dotenv_silently(tmp_path)
    assert n == 2
    assert os.environ["MF_TEST_A"] == "alpha"
    assert os.environ["MF_TEST_B"] == "beta"


def test_does_not_override_existing_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MF_TEST_A", "from-shell")
    _write_env(tmp_path / ".env", 'MF_TEST_A="from-dotenv"\n')
    el.load_dotenv_silently(tmp_path)
    # env > dotfile：shell 已设置的值不会被 .env 覆盖
    assert os.environ["MF_TEST_A"] == "from-shell"


def test_quoted_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MF_DQ", raising=False)
    monkeypatch.delenv("MF_SQ", raising=False)
    _write_env(tmp_path / ".env", 'MF_DQ="hello world"\nMF_SQ=\'single quoted\'\n')
    el.load_dotenv_silently(tmp_path)
    assert os.environ["MF_DQ"] == "hello world"
    assert os.environ["MF_SQ"] == "single quoted"


def test_comments_and_blank(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MF_X", raising=False)
    _write_env(tmp_path / ".env", "# 这是注释\n\nMF_X=ok\n# end\n")
    el.load_dotenv_silently(tmp_path)
    assert os.environ["MF_X"] == "ok"


def test_invalid_lines_are_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MF_OK", raising=False)
    _write_env(tmp_path / ".env", "no equal sign here\n123BAD=ignored\nMF_OK=yes\n")
    el.load_dotenv_silently(tmp_path)
    assert os.environ["MF_OK"] == "yes"
    assert "123BAD" not in os.environ


def test_finds_dotenv_in_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MF_PARENT", raising=False)
    sub = tmp_path / "a" / "b" / "c"
    sub.mkdir(parents=True)
    _write_env(tmp_path / ".env", "MF_PARENT=found\n")
    el.load_dotenv_silently(sub)
    assert os.environ["MF_PARENT"] == "found"


def test_no_dotenv_returns_zero(tmp_path: Path) -> None:
    assert el.load_dotenv_silently(tmp_path) == 0


def test_once_only_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MF_ONCE", raising=False)
    _write_env(tmp_path / ".env", "MF_ONCE=first\n")
    el.load_dotenv_silently(tmp_path)
    # 第二次：哪怕 .env 改了，guard 也不会重新加载
    _write_env(tmp_path / ".env", "MF_ONCE=second\n")
    n2 = el.load_dotenv_silently(tmp_path)
    assert n2 == 0
    assert os.environ["MF_ONCE"] == "first"


def test_does_not_print_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("MF_SECRET", raising=False)
    secret = "VERY-SENSITIVE-VALUE-DO-NOT-PRINT"
    _write_env(tmp_path / ".env", f"MF_SECRET={secret}\n")
    el.load_dotenv_silently(tmp_path)
    out = capsys.readouterr()
    # 关键不变量：loader 不能输出任何 value 到 stdout / stderr
    assert secret not in out.out
    assert secret not in out.err
