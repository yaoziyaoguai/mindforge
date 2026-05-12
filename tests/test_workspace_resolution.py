"""统一 workspace resolution 测试。

中文学习型说明：测试覆盖 config resolution 优先级链、active workspace
生命周期、错误提示质量。所有测试不读取 API key/token/secret，不使用
真实 LLM 调用，不启动 Web server。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from mindforge.workspace_resolver import (
    WorkspaceResolutionError,
    clear_active_workspace,
    get_active_workspace,
    set_active_workspace,
    global_workspace_override,
    resolve_workspace_config,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_workspace(root: Path) -> None:
    """在 root 下创建最小 workspace，包含合法 configs/mindforge.yaml。"""
    configs = root / "configs"
    configs.mkdir(parents=True, exist_ok=True)
    cfg = {
        "version": 0.7,
        "vault": {"root": str(root / "vault")},
        "llm": {"default_model": "main", "models": {"main": {"type": "anthropic_compatible", "base_url": "https://example.com", "model": "test"}}},
        "telemetry": {"enabled": False, "local_only": True},
    }
    (configs / "mindforge.yaml").write_text(
        yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8"
    )
    (root / "vault").mkdir(parents=True, exist_ok=True)


def _cleanup_active_workspace():
    """确保测试后清除全局 active workspace。"""
    clear_active_workspace()


# ---------------------------------------------------------------------------
# 1. set_active_workspace / get_active_workspace / clear_active_workspace
# ---------------------------------------------------------------------------


def test_set_and_get_active_workspace(tmp_path):
    """init 后写入 active workspace 指针。"""
    _make_workspace(tmp_path)
    active = set_active_workspace(tmp_path)
    assert active.workspace_path == tmp_path.resolve()
    assert active.config_path == (tmp_path / "configs" / "mindforge.yaml").resolve()
    assert active.exists

    loaded = get_active_workspace()
    assert loaded is not None
    assert loaded.workspace_path == tmp_path.resolve()
    assert loaded.exists

    clear_active_workspace()
    assert get_active_workspace() is None


def test_set_active_workspace_rejects_invalid(tmp_path):
    """workspace use <path> 拒绝不含 config 的路径。"""
    with pytest.raises(WorkspaceResolutionError, match="不是有效的 MindForge workspace"):
        set_active_workspace(tmp_path)


def test_clear_does_not_delete_data(tmp_path):
    """workspace clear 清除 active workspace 指针，不删除数据。"""
    _make_workspace(tmp_path)
    set_active_workspace(tmp_path)
    clear_active_workspace()
    assert get_active_workspace() is None
    # workspace 数据完整保留
    assert (tmp_path / "configs" / "mindforge.yaml").is_file()
    assert (tmp_path / "vault").is_dir()


# ---------------------------------------------------------------------------
# 2. resolve_workspace_config 优先级
# ---------------------------------------------------------------------------


def test_priority_1_explicit_config(tmp_path):
    """显式 --config 最高优先级。"""
    _make_workspace(tmp_path)
    config_path = tmp_path / "configs" / "mindforge.yaml"
    resolved = resolve_workspace_config(config_path, cwd=Path("/tmp"))
    assert resolved == config_path.resolve()


def test_priority_2_explicit_workspace(tmp_path):
    """显式 --workspace 覆盖 cwd 和 active workspace。"""
    _make_workspace(tmp_path)
    resolved = resolve_workspace_config(
        Path("configs/mindforge.yaml"),
        workspace_override=tmp_path,
        cwd=Path("/tmp"),
    )
    assert resolved == (tmp_path / "configs" / "mindforge.yaml").resolve()


def test_priority_2_explicit_workspace_rejects_invalid(tmp_path):
    """显式 --workspace 指向非法目录时报错。"""
    with pytest.raises(WorkspaceResolutionError, match="指定的 workspace 中未找到配置"):
        resolve_workspace_config(
            Path("configs/mindforge.yaml"),
            workspace_override=tmp_path,
            cwd=Path("/tmp"),
        )


def test_priority_3_upward_search(tmp_path):
    """cwd 向上查找 configs/mindforge.yaml。"""
    _make_workspace(tmp_path)
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    resolved = resolve_workspace_config(
        Path("configs/mindforge.yaml"),
        cwd=deep,
    )
    assert resolved == (tmp_path / "configs" / "mindforge.yaml").resolve()


def test_priority_4_active_workspace_fallback(tmp_path):
    """在非 workspace 目录执行命令，通过 active workspace 成功读取配置。"""
    _make_workspace(tmp_path)
    set_active_workspace(tmp_path)
    try:
        resolved = resolve_workspace_config(
            Path("configs/mindforge.yaml"),
            cwd=Path("/tmp"),
        )
        assert resolved == (tmp_path / "configs" / "mindforge.yaml").resolve()
    finally:
        clear_active_workspace()


def test_priority_4_stale_workspace(tmp_path):
    """active workspace 路径失效时提示友好。"""
    stale = tmp_path / "stale"
    stale.mkdir()
    _make_workspace(stale)
    set_active_workspace(stale)
    # 删除 workspace
    import shutil
    shutil.rmtree(stale)
    try:
        with pytest.raises(WorkspaceResolutionError, match="不再可用"):
            resolve_workspace_config(
                Path("configs/mindforge.yaml"),
                cwd=Path("/tmp"),
            )
    finally:
        clear_active_workspace()


def test_priority_5_no_workspace():
    """找不到任何 workspace 时错误提示包含 init / workspace use / --workspace / --config。"""
    # 确保没有 active workspace，且 /tmp 不是 workspace
    clear_active_workspace()
    with pytest.raises(WorkspaceResolutionError) as exc_info:
        resolve_workspace_config(
            Path("configs/mindforge.yaml"),
            cwd=Path("/tmp"),
        )
    msg = str(exc_info.value)
    assert exc_info.value.kind == "no_workspace"
    assert "mindforge init" in msg
    assert "mindforge workspace use" in msg
    assert "--workspace" in msg
    assert "--config" in msg


def test_explicit_workspace_overrides_active_workspace(tmp_path):
    """--workspace 覆盖 active workspace。"""
    _make_workspace(tmp_path)
    other = tmp_path / "other_ws"
    _make_workspace(other)
    set_active_workspace(other)
    try:
        resolved = resolve_workspace_config(
            Path("configs/mindforge.yaml"),
            workspace_override=tmp_path,
            cwd=Path("/tmp"),
        )
        assert resolved == (tmp_path / "configs" / "mindforge.yaml").resolve()
    finally:
        clear_active_workspace()


def test_explicit_config_overrides_active_workspace(tmp_path):
    """--config 覆盖 active workspace。"""
    _make_workspace(tmp_path)
    other = tmp_path / "other_ws"
    _make_workspace(other)
    set_active_workspace(other)
    try:
        config_path = tmp_path / "configs" / "mindforge.yaml"
        resolved = resolve_workspace_config(config_path, cwd=Path("/tmp"))
        assert resolved == config_path.resolve()
    finally:
        clear_active_workspace()


# ---------------------------------------------------------------------------
# 3. 不静默创建 config 目录
# ---------------------------------------------------------------------------


def test_no_silent_config_creation(tmp_path):
    """不在错误目录静默创建 configs/mindforge.yaml。"""
    clear_active_workspace()
    with pytest.raises(WorkspaceResolutionError):
        resolve_workspace_config(
            Path("configs/mindforge.yaml"),
            cwd=tmp_path,
        )
    # 确认没有创建 configs/mindforge.yaml
    assert not (tmp_path / "configs" / "mindforge.yaml").exists()


# ---------------------------------------------------------------------------
# 4. global active workspace 不包含 secret
# ---------------------------------------------------------------------------


def test_active_workspace_file_no_secrets(tmp_path):
    """全局 current_workspace.json 不包含 API key/token/secret。"""
    _make_workspace(tmp_path)
    active = set_active_workspace(tmp_path)
    data = active.to_dict()
    assert "api_key" not in data
    assert "token" not in data
    assert "secret" not in data
    assert "api" not in data
    assert "key" not in data
    assert set(data.keys()) == {"workspace_path", "config_path", "updated_at"}

    # 读回文件验证
    ws_file = Path.home() / ".mindforge" / "current_workspace.json"
    raw = json.loads(ws_file.read_text(encoding="utf-8"))
    assert set(raw.keys()) == {"workspace_path", "config_path", "updated_at"}

    clear_active_workspace()


# ---------------------------------------------------------------------------
# 5. global_workspace_override
# ---------------------------------------------------------------------------


def test_global_workspace_override_from_env(tmp_path):
    """--workspace 通过 MINDFORGE_WORKSPACE_OVERRIDE env var 传递。"""
    _make_workspace(tmp_path)
    os.environ["MINDFORGE_WORKSPACE_OVERRIDE"] = str(tmp_path)
    try:
        override = global_workspace_override()
        assert override == tmp_path
    finally:
        del os.environ["MINDFORGE_WORKSPACE_OVERRIDE"]


def test_global_workspace_override_none():
    """没有 --workspace 时返回 None。"""
    os.environ.pop("MINDFORGE_WORKSPACE_OVERRIDE", None)
    assert global_workspace_override() is None


# ---------------------------------------------------------------------------
# 6. workspace_current 不显示 secret
# ---------------------------------------------------------------------------

def test_workspace_current_no_secret(tmp_path):
    """workspace current 显示 workspace 路径/config 路径/vault，不泄漏 secret。"""
    _make_workspace(tmp_path)
    active = set_active_workspace(tmp_path)
    try:
        # 验证 active 对象不包含 secret
        info = active.to_dict()
        for key in info:
            assert "secret" not in key.lower()
            assert "api" not in key.lower()
            assert "key" not in key.lower()
            assert "token" not in key.lower()
        # 验证 active 对象的 to_dict 不包含任何 secret 相关字段
        assert "workspace_path" in json.dumps(info)  # 正常包含路径信息
    finally:
        clear_active_workspace()
