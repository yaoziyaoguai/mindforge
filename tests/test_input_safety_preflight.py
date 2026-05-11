"""Input safety preflight tests for source-centric MindForge workflows.

覆盖 ``input_safety`` 模块的关键安全契约:

- synthetic 路径 → allowed;
- non-existent / private / Obsidian / home 路径 → refused;
- declared_non_sensitive 不能绕过更高优先级拒绝;
- preflight 永远不读取 input 目录内容 (静态分类);
- 输出 contract 永远 ``human_approved=False`` / ``writes_vault=False``;
- 不依赖真实 secret, 不发起任何网络调用。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mindforge.config import LLMConfig, with_fake_llm_profile
from mindforge.input_safety import (
    CLASS_HOME_SCAN_FORBIDDEN,
    CLASS_NON_SENSITIVE_LOCAL,
    CLASS_OBSIDIAN_VAULT_FORBIDDEN,
    CLASS_PATH_DOES_NOT_EXIST,
    CLASS_PRIVATE_REAL_DATA_FORBIDDEN,
    CLASS_SYNTHETIC,
    build_preflight_report,
    classify_input_path,
    input_readiness_report,
    render_input_readiness_report,
    render_preflight_report,
)


@pytest.fixture
def fake_llm_config() -> LLMConfig:
    """测试专用 fake profile 只在内存注入，不要求用户默认配置暴露 fake。"""
    from mindforge.app_context import load_app_config

    repo_root = Path(__file__).resolve().parents[1]
    return with_fake_llm_profile(load_app_config(repo_root / "configs" / "mindforge.yaml").llm)


def test_synthetic_examples_path_classified_as_synthetic(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    synthetic = repo_root / "examples" / "fixture-vault"
    assert classify_input_path(synthetic) == CLASS_SYNTHETIC


def test_obsidian_vault_path_is_forbidden(tmp_path):
    """带 .obsidian 目录的路径必须被拒绝, 即使声明 non-sensitive。"""
    vault = tmp_path / "myvault"
    (vault / ".obsidian").mkdir(parents=True)
    note = vault / "note.md"
    note.write_text("hi", encoding="utf-8")
    # 路径在 .obsidian 标记的 vault 内 → 拒绝
    assert (
        classify_input_path(note, declared_non_sensitive=True)
        == CLASS_OBSIDIAN_VAULT_FORBIDDEN
    )


def test_tmp_disposable_obsidian_vault_can_be_declared_non_sensitive(tmp_path):
    """临时 disposable vault 副本应能通过 readiness。

    中文学习：这里允许的前提很窄：必须是临时目录下、必须显式声明
    non-sensitive；home 下真实个人 vault 仍由下一条测试拒绝。
    """
    vault = Path("/tmp") / f"mindforge-test-{tmp_path.name}"
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    try:
        assert (
            classify_input_path(vault, declared_non_sensitive=True)
            == CLASS_NON_SENSITIVE_LOCAL
        )
    finally:
        for child in (vault / ".obsidian").glob("*"):
            child.unlink()
        (vault / ".obsidian").rmdir()
        vault.rmdir()


def test_home_path_outside_cwd_is_forbidden(tmp_path, monkeypatch):
    """模拟用户把家目录的子路径作为 input — 必须拒绝。"""
    fake_home = tmp_path / "home"
    fake_cwd = tmp_path / "work"
    target = fake_home / "private" / "doc.md"
    target.parent.mkdir(parents=True)
    target.write_text("x", encoding="utf-8")
    fake_cwd.mkdir()
    assert (
        classify_input_path(
            target,
            declared_non_sensitive=True,
            home=fake_home,
            cwd=fake_cwd,
        )
        == CLASS_HOME_SCAN_FORBIDDEN
    )


def test_nonexistent_path_is_refused(tmp_path):
    assert (
        classify_input_path(tmp_path / "does_not_exist.md")
        == CLASS_PATH_DOES_NOT_EXIST
    )


def test_local_path_without_declaration_is_forbidden(tmp_path):
    """普通本地路径未声明 non-sensitive → 默认按 private 拒绝。"""
    f = tmp_path / "doc.md"
    f.write_text("x", encoding="utf-8")
    assert (
        classify_input_path(f, declared_non_sensitive=False, home=tmp_path / "h")
        == CLASS_PRIVATE_REAL_DATA_FORBIDDEN
    )


def test_local_path_with_declaration_becomes_non_sensitive(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("x", encoding="utf-8")
    cls = classify_input_path(
        f,
        declared_non_sensitive=True,
        home=tmp_path / "h",
        cwd=tmp_path,
    )
    assert cls == CLASS_NON_SENSITIVE_LOCAL


def test_classify_does_not_read_file_contents(tmp_path, monkeypatch):
    """关键安全断言: classify_input_path 不应触发 ``open`` / ``read_*``。"""
    f = tmp_path / "doc.md"
    f.write_text("SECRET-CONTENT-MUST-NOT-BE-READ", encoding="utf-8")

    real_open = open

    def _fail_open(*args, **kwargs):
        # 测试自身在 fixture 阶段已经写过文件; 在 classify 阶段如果再
        # 调到 open() 就会直接失败。
        raise AssertionError(f"classify_input_path opened a file: {args}")

    monkeypatch.setattr("builtins.open", _fail_open)
    try:
        classify_input_path(f, declared_non_sensitive=True, home=tmp_path / "h", cwd=tmp_path)
    finally:
        monkeypatch.setattr("builtins.open", real_open)


def test_preflight_report_synthetic_path_allowed(fake_llm_config):
    repo_root = Path(__file__).resolve().parents[1]
    report = build_preflight_report(
        repo_root / "examples" / "fixture-vault",
        declared_non_sensitive=False,
        allow_real=False,
        llm_config=fake_llm_config,
    )
    assert report["decision"]["allowed"] is True
    assert report["decision"]["blockers"] == []
    assert report["input"]["classification"] == CLASS_SYNTHETIC
    # 永久 contract: 即使 allowed, 也不能产生 human_approved / 写 vault
    assert report["output_contract"]["human_approved"] is False
    assert report["output_contract"]["writes_vault"] is False
    assert report["output_contract"]["approves"] is False


def test_preflight_report_refuses_obsidian(tmp_path, fake_llm_config):
    vault = tmp_path / "v"
    (vault / ".obsidian").mkdir(parents=True)
    note = vault / "n.md"
    note.write_text("x", encoding="utf-8")
    report = build_preflight_report(
        note,
        declared_non_sensitive=True,
        allow_real=False,
        llm_config=fake_llm_config,
    )
    assert report["decision"]["allowed"] is False
    assert any("obsidian_vault_forbidden" in b for b in report["decision"]["blockers"])
    assert report["output_contract"]["human_approved"] is False


def test_preflight_allow_real_blocked_when_fake_default(fake_llm_config):
    repo_root = Path(__file__).resolve().parents[1]
    report = build_preflight_report(
        repo_root / "examples" / "fixture-vault",
        declared_non_sensitive=False,
        allow_real=True,
        llm_config=fake_llm_config,
    )
    # path 是 synthetic, 但 allow_real 命中 fake-default → 加 blocker
    assert any("allow_real" in b for b in report["decision"]["blockers"])
    assert report["decision"]["allowed"] is False
    # 仍然不会写 vault, 不会 human_approved
    assert report["output_contract"]["human_approved"] is False


def test_render_input_preflight_synthetic_is_actionable(fake_llm_config):
    """service smoke: synthetic 路径 → allowed, 输出指向真实主路径。"""
    repo_root = Path(__file__).resolve().parents[1]
    report = build_preflight_report(
        repo_root / "examples" / "fixture-vault",
        declared_non_sensitive=False,
        allow_real=False,
        llm_config=fake_llm_config,
    )
    rendered = render_preflight_report(report)
    assert "synthetic" in rendered
    assert "decision.allowed     : True" in rendered
    assert "mindforge web" in rendered
    assert "mindforge watch add" in rendered
    # 输出绝不能含 human_approved=True / api_key 字面值
    assert "human_approved=True" not in rendered
    assert "api_key" not in rendered.lower()


def test_render_input_preflight_obsidian_is_refused(tmp_path, fake_llm_config):
    vault = tmp_path / "v"
    (vault / ".obsidian").mkdir(parents=True)
    note = vault / "n.md"
    note.write_text("x", encoding="utf-8")
    report = build_preflight_report(
        note,
        declared_non_sensitive=True,
        allow_real=False,
        llm_config=fake_llm_config,
    )
    rendered = render_preflight_report(report)
    assert report["decision"]["allowed"] is False
    assert "obsidian_vault_forbidden" in rendered


def test_input_preflight_does_not_invoke_llm(tmp_path, fake_llm_config, monkeypatch):
    """preflight 必须**不**调用 llm.factory.build_providers / provider.generate。"""
    repo_root = Path(__file__).resolve().parents[1]
    import mindforge.llm.factory as factory_mod

    real_build = factory_mod.build_providers

    def _fail_build(*args, **kwargs):
        raise AssertionError("input preflight must not build any LLM provider")

    monkeypatch.setattr(factory_mod, "build_providers", _fail_build)
    try:
        report = build_preflight_report(
            repo_root / "examples" / "fixture-vault",
            declared_non_sensitive=False,
            allow_real=False,
            llm_config=fake_llm_config,
        )
        assert report["decision"]["allowed"] is True
    finally:
        monkeypatch.setattr(factory_mod, "build_providers", real_build)


def test_input_readiness_summarizes_safe_default_path(fake_llm_config):
    """readiness 是 source 输入前的只读检查点，不读取任何输入内容。"""
    repo_root = Path(__file__).resolve().parents[1]
    report = input_readiness_report(
        vault=repo_root / "examples" / "fixture-vault",
        source_export=None,
        declared_non_sensitive=True,
        llm_config=fake_llm_config,
    )
    assert report["decision"]["ready"] is True
    assert report["model"]["uses_test_double"] is True
    assert report["output_contract"]["reads_env"] is False
    assert report["output_contract"]["calls_real_llm"] is False
    assert report["output_contract"]["calls_external_api"] is False
    assert report["output_contract"]["human_approved"] is False
    rendered = render_input_readiness_report(report)
    assert "MindForge input readiness" in rendered
    assert "mindforge web" in rendered
    assert "mindforge watch add" in rendered
    assert "rollback = delete that copy" in rendered


def test_input_readiness_allows_tmp_disposable_vault(fake_llm_config, tmp_path):
    """readiness 必须承接临时 disposable vault 路径。"""
    vault = Path("/tmp") / f"mindforge-readiness-{tmp_path.name}"
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    try:
        report = input_readiness_report(
            vault=vault,
            source_export=None,
            declared_non_sensitive=True,
            llm_config=fake_llm_config,
        )
        assert report["decision"]["ready"] is True
        assert report["vault"]["classification"] == CLASS_NON_SENSITIVE_LOCAL
    finally:
        (vault / ".obsidian").rmdir()
        vault.rmdir()


def test_input_readiness_blocks_missing_export(fake_llm_config, tmp_path):
    """提供 source export 时只检查存在性；缺失要给 blocker，而不是猜测继续。"""
    repo_root = Path(__file__).resolve().parents[1]
    missing_export = tmp_path / "missing.json"
    report = input_readiness_report(
        vault=repo_root / "examples" / "fixture-vault",
        source_export=missing_export,
        declared_non_sensitive=True,
        llm_config=fake_llm_config,
    )
    assert report["decision"]["ready"] is False
    assert any("source_export" in b for b in report["decision"]["blockers"])
    assert report["source_export"]["will_read_contents"] is False


def test_input_readiness_does_not_read_env_or_export_contents(
    tmp_path, fake_llm_config, monkeypatch
):
    """readiness 不读 `.env`，也不读取 source export 内容。"""
    repo_root = Path(__file__).resolve().parents[1]
    export = tmp_path / "export.json"
    export.write_text("SECRET-CONTENT-MUST-NOT-BE-READ", encoding="utf-8")

    def _blocked_env(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("input readiness 不应读取 .env")

    def _blocked_read_text(self, *args, **kwargs):  # noqa: ANN001
        if self == export:
            raise AssertionError("input readiness 不应读取 source export 内容")
        return real_read_text(self, *args, **kwargs)

    real_read_text = Path.read_text
    monkeypatch.setattr("mindforge.env_loader.load_dotenv_silently", _blocked_env)
    monkeypatch.setattr(Path, "read_text", _blocked_read_text)

    report = input_readiness_report(
        vault=repo_root / "examples" / "fixture-vault",
        source_export=export,
        declared_non_sensitive=True,
        llm_config=fake_llm_config,
    )
    rendered = render_input_readiness_report(report)
    assert "decision.ready          : True" in rendered
    assert "reads_env=False" in rendered
    assert "human_approved=False" in rendered
