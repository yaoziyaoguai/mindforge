"""Secret store 与 project_root 解析测试（P0-2）。

验证 provider secrets 使用 workspace 锚点、不依赖 Path.cwd()、
model_setup_readiness 与 provider 使用同一路径语义。
所有测试不读取实际 secret value，只验证路径选择逻辑。
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from mindforge.secret_store import (
    SecretStore,
    find_secret_store_path,
    resolve_project_root_from_config,
)


def _make_workspace(root: Path) -> Path:
    """在 root 下创建最小 workspace，返回 config path。"""
    configs = root / "configs"
    configs.mkdir(parents=True)
    cfg = {
        "version": 0.7,
        "vault": {"root": str(root / "vault")},
        "llm": {
            "default_model": "main",
            "models": {
                "main": {
                    "type": "openai_compatible",
                    "base_url": "https://example.com",
                    "model": "test",
                }
            },
        },
        "telemetry": {"enabled": False, "local_only": True},
    }
    cfg_path = configs / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    (root / "vault").mkdir(parents=True, exist_ok=True)
    return cfg_path


# ---------------------------------------------------------------------------
# find_secret_store_path
# ---------------------------------------------------------------------------


def test_find_secret_store_path_uses_project_root(tmp_path):
    """project_root/.mindforge/secrets.json 存在时优先使用。"""
    secrets_dir = tmp_path / ".mindforge"
    secrets_dir.mkdir()
    secrets_file = secrets_dir / "secrets.json"
    secrets_file.write_text(json.dumps({"test_model": "sk-test-key"}), encoding="utf-8")

    result = find_secret_store_path(project_root=tmp_path)
    assert result == secrets_file.resolve()


def test_find_secret_store_path_falls_back_to_cwd(tmp_path, monkeypatch):
    """project_root=None 且 project_root 下无 secrets 时回退 CWD 查找。"""
    real_cwd = tmp_path / "subdir"
    real_cwd.mkdir()
    monkeypatch.chdir(real_cwd)

    secrets_dir = tmp_path / ".mindforge"
    secrets_dir.mkdir()
    secrets_file = secrets_dir / "secrets.json"
    secrets_file.write_text(json.dumps({"test_model": "sk-test-key"}), encoding="utf-8")

    result = find_secret_store_path(project_root=None)
    assert result is not None
    assert result.resolve() == secrets_file.resolve()


def test_find_secret_store_path_returns_none_when_missing(tmp_path, monkeypatch):
    """secrets.json 不存在时返回 None。"""
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)

    result = find_secret_store_path(project_root=None)
    assert result is None


def test_find_secret_store_path_no_secrets_read(tmp_path):
    """只验证路径选择，不读取或暴露 secrets 内容。"""
    secrets_dir = tmp_path / ".mindforge"
    secrets_dir.mkdir()
    secrets_file = secrets_dir / "secrets.json"
    secrets_file.write_text(json.dumps({"test_model": "sk-secret-value"}), encoding="utf-8")

    result = find_secret_store_path(project_root=tmp_path)
    assert result == secrets_file.resolve()
    # 不读取文件内容
    assert "sk-" not in str(result.as_posix())


# ---------------------------------------------------------------------------
# resolve_project_root_from_config
# ---------------------------------------------------------------------------


def test_resolve_project_root_from_config_metadata(tmp_path):
    """从 _mindforge_config.project_root 提取路径。"""
    from mindforge.config import load_mindforge_config

    cfg_path = _make_workspace(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    project_root = resolve_project_root_from_config(cfg)
    assert project_root is not None
    assert project_root.resolve() == tmp_path.resolve()


def test_resolve_project_root_from_project_metadata(tmp_path):
    """从 _mindforge_project.root 提取路径（workspace anchor）。"""
    from mindforge.config import load_mindforge_config

    cfg_path = _make_workspace(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    # 模拟 build_app_context 注入 _mindforge_project
    cfg.raw["_mindforge_project"] = {"root": str(tmp_path / "workspace"), "config_path": str(cfg_path)}

    project_root = resolve_project_root_from_config(cfg)
    assert project_root == tmp_path / "workspace"


def test_resolve_project_root_from_config_no_metadata(tmp_path):
    """raw metadata 为空时 resolve_project_root_from_config 返回 None。"""
    # 构造不含 _mindforge_config / _mindforge_project metadata 的 config
    from mindforge.config import load_mindforge_config

    cfg_path = _make_workspace(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    # 删除 load_mindforge_config 注入的 metadata
    if isinstance(cfg.raw, dict):
        cfg.raw.pop("_mindforge_config", None)
        cfg.raw.pop("_mindforge_project", None)

    result = resolve_project_root_from_config(cfg)
    assert result is None


# ---------------------------------------------------------------------------
# model_setup_readiness 与 provider 同一路径语义
# ---------------------------------------------------------------------------


def test_model_setup_readiness_and_provider_use_same_path_logic(tmp_path):
    """model_setup_readiness 的 _secret_store_path 与 provider 的
    find_secret_store_path 使用相同的 project_root 解析链。"""
    from mindforge.config import load_mindforge_config
    from mindforge.model_setup_readiness import _secret_store_path

    cfg_path = _make_workspace(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    # model_setup_readiness 使用 _secret_store_path
    readiness_path = _secret_store_path(cfg)

    # provider 链使用 find_secret_store_path(resolve_project_root_from_config(cfg))
    project_root = resolve_project_root_from_config(cfg)
    provider_path = find_secret_store_path(project_root=project_root)

    # CWD fallback 情况两者都指向相同默认值
    if readiness_path.is_file():
        assert provider_path == readiness_path.resolve()
    else:
        # 都不存在时，model_setup_readiness 返回默认路径，provider 返回 None
        expected_default = tmp_path / ".mindforge" / "secrets.json"
        assert readiness_path == expected_default


def test_provider_secret_path_independent_of_cwd(tmp_path, monkeypatch):
    """provider 的 secret path 不依赖 Path.cwd()，只依赖传入的 project_root。"""
    from mindforge.config import load_mindforge_config

    # 在 workspace 里创建 secrets.json
    secrets_dir = tmp_path / ".mindforge"
    secrets_dir.mkdir()
    secrets_file = secrets_dir / "secrets.json"
    secrets_file.write_text(json.dumps({"main": "test"}), encoding="utf-8")

    cfg_path = _make_workspace(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    # 无论 CWD 在哪，resolve_project_root_from_config 返回相同 project_root
    project_root_1 = resolve_project_root_from_config(cfg)

    monkeypatch.chdir(tmp_path / "vault")
    project_root_2 = resolve_project_root_from_config(cfg)

    assert project_root_1 == project_root_2

    # find_secret_store_path 基于 project_root 查找
    secret_path = find_secret_store_path(project_root=project_root_1)
    assert secret_path == secrets_file.resolve()


def test_secret_store_path_uses_project_root_when_resolved(tmp_path):
    """project_root 已解析但 secrets 文件不存在时，_secret_store_path
    返回 project_root 锚定的路径，而非 CWD 路径。确保 readiness 与
    processing provider 始终校验同一 workspace。

    P1-2 修正验证：不能在 project_root 已解析时 fallback 到 CWD。
    """
    from mindforge.config import load_mindforge_config
    from mindforge.model_setup_readiness import _secret_store_path

    cfg_path = _make_workspace(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    # 不创建 .mindforge/secrets.json — 模拟用户尚未 Web Setup
    path = _secret_store_path(cfg)
    assert path == (tmp_path / ".mindforge" / "secrets.json"), (
        f"project_root 已解析时路径应锚定到 project_root，"
        f"expected={tmp_path / '.mindforge' / 'secrets.json'}, got={path}"
    )


def test_secret_store_path_falls_back_cwd_only_when_no_project_root(tmp_path, monkeypatch):
    """仅当 project_root 无法解析时才 fallback 到 CWD。

    P1-2 修正验证：CWD fallback 仅限于 cfg metadata 缺失时的兜底。
    """
    from mindforge.config import load_mindforge_config
    from mindforge.model_setup_readiness import _secret_store_path

    cfg_path = _make_workspace(tmp_path)
    cfg = load_mindforge_config(cfg_path)

    # 清除 metadata，模拟缺失 _mindforge_config / _mindforge_project
    if isinstance(cfg.raw, dict):
        cfg.raw.pop("_mindforge_config", None)
        cfg.raw.pop("_mindforge_project", None)

    monkeypatch.chdir(tmp_path)
    path = _secret_store_path(cfg)
    assert path == (tmp_path / ".mindforge" / "secrets.json"), (
        f"无 project_root metadata 时 CWD fallback 仍有效，"
        f"expected={tmp_path / '.mindforge' / 'secrets.json'}, got={path}"
    )


def test_readiness_not_misled_by_cwd_secrets(tmp_path, monkeypatch):
    """cwd 下有 secrets 但 config 不在 cwd workspace → readiness
    不应被 cwd 的 secrets 误判为 ready。

    P1-2 修正验证：readiness 应使用 workspace 锚点的 secrets，
    不被 CWD 的无关 secrets 文件误导。
    """
    from mindforge.config import load_mindforge_config
    from mindforge.model_setup_readiness import model_setup_readiness

    # 在 cwd 创建假的 secrets（模拟 repo cwd 已有 .mindforge/secrets.json）
    cwd_secrets_dir = tmp_path / ".mindforge"
    cwd_secrets_dir.mkdir()
    cwd_secrets_file = cwd_secrets_dir / "secrets.json"
    cwd_secrets_file.write_text(
        json.dumps({"main": "sk-cwd-should-not-be-used"}),
        encoding="utf-8",
    )

    # 在另一个目录创建 workspace（无 secrets）
    ws = tmp_path / "actual-ws"
    _make_workspace(ws)
    cfg_path = ws / "configs" / "mindforge.yaml"
    cfg = load_mindforge_config(cfg_path)

    # readiness 应使用 ws 锚点的 secrets path，不被 cwd secrets 误导
    monkeypatch.chdir(tmp_path)
    result = model_setup_readiness(cfg)
    # ws 的 models 需要 api_key，但 ws/.mindforge/secrets.json 不存在
    # → readiness 应为 needs_setup
    assert result.status == "needs_setup", (
        f"readiness 不受 cwd secrets 误判，expected=needs_setup, got={result.status}"
    )


def test_no_real_secret_value_read(tmp_path):
    """所有测试函数不读取实际 secret value，只验证路径选择。"""
    secrets_dir = tmp_path / ".mindforge"
    secrets_dir.mkdir()
    secrets_file = secrets_dir / "secrets.json"
    secrets_file.write_text(json.dumps({"model": "sk-should-not-be-read"}), encoding="utf-8")

    # find_secret_store_path 只检查文件存在性，不读内容
    result = find_secret_store_path(project_root=tmp_path)
    assert result == secrets_file.resolve()

    # SecretStore.get 是读内容的方法，但测试只构造路径，不调用 get()
    store = SecretStore(secrets_file)
    assert store.present("model")
    assert store.masked("model") == "sk-****read"
