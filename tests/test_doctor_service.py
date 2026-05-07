"""Doctor service 与 presenter 的契约测试 / TDD characterization。

中文学习型说明：
- ``services/doctor.py`` 是 ``mindforge doctor`` 的 *纯逻辑层*：不打印任何
  Rich markup、不依赖 Typer / cli.py、不发起任何网络。它只接收
  ``MindForgeConfig`` 和 cwd 之类的最小事实，返回结构化数据。
- ``presenters/doctor.py`` 接管 Rich icon / 颜色等用户可见格式化，承担"用户
  能看到什么"的展示职责。
- 这两个模块联合替代历史上塞在 ``cli.py`` 内的 doctor 巨石。本测试保证：
    1. 纯逻辑层可以独立调用、可单测；
    2. presenter 帮助函数对所有合法状态都返回字符串、不会 KeyError；
    3. CLI 的 ``mindforge doctor`` 用户输出关键片段不被破坏。
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from typer.testing import CliRunner

from mindforge.cli import app
from mindforge.assets_runtime import bundled_asset_path_for_process
from mindforge.config import MindForgeConfig, load_mindforge_config
from mindforge.presenters.doctor import doctor_icon, ok_dir
from mindforge.services.doctor import (
    compute_doctor_hints,
    config_doctor_rows,
    dir_state,
    doctor_paths,
    doctor_recovery_checks,
)


def _make_cfg(tmp_path: Path) -> MindForgeConfig:
    """复用包内默认 mindforge.yaml，只把 vault.root 与 state.workdir 重定向到 tmp。"""

    cfg = load_mindforge_config(bundled_asset_path_for_process("configs", "mindforge.yaml"))
    missing_vault = tmp_path / "vault"
    new_vault = replace(cfg.vault, root=missing_vault)
    new_state = replace(cfg.state, workdir=tmp_path / ".mindforge")
    return replace(cfg, vault=new_vault, state=new_state)


def test_config_doctor_rows_is_pure_and_returns_quadruples(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    rows = config_doctor_rows(cfg)
    assert rows, "config doctor 至少应有 vault.root 一行"
    for row in rows:
        assert len(row) == 4, row
        state, label, detail, hint = row
        assert state in {"ok", "warn", "error", "info"}, state
        assert isinstance(label, str) and label
        assert isinstance(detail, str)
        assert isinstance(hint, str)


def test_doctor_recovery_checks_returns_rows_and_actions(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    payload = doctor_recovery_checks(cfg)
    assert set(payload.keys()) == {"rows", "actions"}
    for row in payload["rows"]:
        assert len(row) == 3
    for action in payload["actions"]:
        assert len(action) == 2
        priority, _msg = action
        assert priority in {"try_first", "critical", "recommended", "info"}, priority


def test_doctor_recovery_actions_include_try_first_demo_hint_when_cards_missing(
    tmp_path: Path,
) -> None:
    """vault 缺失时 doctor 必须把 demo 作为 try_first 第一推荐。

    这条边界由 UX completion pack 引入，搬到 services 后必须保持。
    """

    cfg = _make_cfg(tmp_path)
    payload = doctor_recovery_checks(cfg)
    actions = payload["actions"]
    assert any(p == "try_first" and "mindforge demo" in m for p, m in actions), actions


def test_compute_doctor_hints_handles_empty_vault(tmp_path: Path) -> None:
    """无卡片时 compute_doctor_hints 不应抛出，应只返回 recovery actions 或附加普通建议。"""

    cfg = _make_cfg(tmp_path)
    recovery_actions = doctor_recovery_checks(cfg)["actions"]
    hints = compute_doctor_hints(cfg, recovery_actions)
    assert isinstance(hints, list)
    for entry in hints:
        assert len(entry) == 2
        assert entry[0] in {"try_first", "critical", "recommended", "info"}, entry


def test_doctor_paths_lists_read_write_boundaries(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    rows = doctor_paths(cfg)
    labels = [r[0] for r in rows]
    assert "reads inbox" in labels
    assert "writes state" in labels
    assert any("never writes" == lbl for lbl in labels)


def test_dir_state_returns_ok_or_error(tmp_path: Path) -> None:
    assert dir_state(tmp_path) == "ok"
    assert dir_state(tmp_path / "missing") == "error"


def test_doctor_icon_known_states_have_markup() -> None:
    for state in ("ok", "warn", "error", "info"):
        s = doctor_icon(state)
        assert isinstance(s, str) and "[" in s and "]" in s
    # 未知 state 必须 fallback，不能 KeyError
    assert isinstance(doctor_icon("totally-unknown"), str)


def test_ok_dir_returns_human_readable_state(tmp_path: Path) -> None:
    assert "ok" in ok_dir(tmp_path)
    assert "missing" in ok_dir(tmp_path / "nope").lower()


def test_doctor_command_still_renders_known_sections(tmp_path: Path) -> None:
    """CLI 端到端：``mindforge doctor`` 输出必须仍包含主要 section 标题。

    用 repo 默认 ``configs/mindforge.yaml`` + ``--vault`` 临时覆写，避免
    自造一份和生产 schema 漂移的最小 cfg。
    """

    res = CliRunner().invoke(
        app,
        ["doctor", "--config", "configs/mindforge.yaml", "--vault", str(tmp_path / "vault")],
    )
    assert res.exit_code == 0, res.output
    out = res.output
    # CLI thin adapter 仍必须输出这些 section（来自 presenter）
    for marker in ("MindForge doctor", "Runtime", "Vault", "Recovery checks"):
        assert marker in out, f"doctor 输出缺少 section: {marker}\n---\n{out}"
    # 安全 footer：reaffirm doctor 不读 .env / 不发 HTTP
    assert ".env" in out and "HTTP" in out
