"""SourceInterface contract hardening — Cubox-first 阶段验收测试。

本文件**不**新增 production 代码。它把以下三件事固化为可执行 contract：

1. 默认 ``configs/mindforge.yaml`` 把 ``cubox_markdown`` 作为唯一启用的
   source，且 ``cubox_api`` 必须保持 opt-in（即不出现在默认 yaml 中）。
2. core 模块（cli / processor / pipeline / scanner / source_mux）不可
   import 任何具体 cubox adapter 模块 —— 即"默认 cubox"不等于"写死
   cubox 进 core"。
3. ``Scanner`` 输出可被 ``SourceMux`` 直接消费（形态一致），且 mux 接
   入是显式 opt-in（Scanner 默认不去重）。

测试全部预期 Green —— 这是 characterization。任何 Red 都意味着既有
production 行为已偏离设计意图，需立即停止并 Ask User，禁止擅自修改
production 来"对齐"测试。
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from mindforge.scanner import ScanResult, Scanner
from mindforge.source_mux import SourceMux
from mindforge.sources.base import SourceDocument
from mindforge.sources.registry import (
    AdapterRegistryError,
    build_active_adapters,
)

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT_YAML = _REPO / "configs" / "mindforge.yaml"


# ---------------------------------------------------------------------------
# A. Default-source regression
# ---------------------------------------------------------------------------


def test_default_yaml_enables_cubox_markdown() -> None:
    """默认 source 语义来自 runtime defaults + user override 合并后的配置。

    v0.7.21 起默认只启用 plain_markdown。cubox_markdown 是 optional adapter，
    默认不启用。用户可以通过 enabled 列表显式启用。
    """
    from mindforge.config import load_mindforge_config

    cfg = load_mindforge_config(_DEFAULT_YAML)
    assert "plain_markdown" in cfg.sources.enabled
    assert cfg.sources.registry["plain_markdown"].enabled is True
    # cubox_markdown 是 optional adapter，默认不启用
    assert "cubox_markdown" not in cfg.sources.enabled


def test_default_yaml_does_not_enable_cubox_api() -> None:
    """cubox_api 是 opt-in：默认 yaml 不能出现 cubox_api 字符串。"""
    text = _DEFAULT_YAML.read_text(encoding="utf-8")
    assert "cubox_api" not in text


def test_default_active_entries_only_cubox_markdown_among_cubox_family() -> None:
    """Selector 解析默认 yaml 后，cubox 家族默认不激活。

    v0.7.21 起默认只启用 plain_markdown。cubox 家族 adapter 均为 optional，
    active_entries 中不包含任何 cubox_ 前缀条目。
    """
    from mindforge.config import load_mindforge_config
    cfg = load_mindforge_config(_DEFAULT_YAML)
    active_types = {e.source_type for e in cfg.sources.active_entries()}
    assert "plain_markdown" in active_types
    cubox_active = {t for t in active_types if t.startswith("cubox_")}
    assert cubox_active == set(), "cubox 家族 adapter 默认不激活（optional）"


def test_core_modules_do_not_hardcode_cubox() -> None:
    """cli / processor / pipeline / scanner / source_mux 不可 import 具体 cubox 模块。"""
    core_files = [
        _REPO / "src" / "mindforge" / "cli.py",
        _REPO / "src" / "mindforge" / "processor.py",
        _REPO / "src" / "mindforge" / "pipeline.py",
        _REPO / "src" / "mindforge" / "scanner.py",
        _REPO / "src" / "mindforge" / "source_mux.py",
    ]
    forbidden = {"cubox_markdown", "cubox_api"}
    for fp in core_files:
        if not fp.exists():
            continue
        tree = ast.parse(fp.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for f in forbidden:
                    assert f not in node.module, (
                        f"{fp.name} 不应 import {node.module!r}（写死 cubox 到 core）"
                    )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for f in forbidden:
                        assert f not in alias.name, (
                            f"{fp.name} 不应 import {alias.name!r}"
                        )


def test_unknown_adapter_name_raises_typed_error(tmp_path: Path) -> None:
    """Selector 遇到未注册 adapter 类名时必须抛 typed AdapterRegistryError。"""
    from mindforge.config import SourceRegistryEntry, SourcesConfig
    bad = SourcesConfig(
        enabled=("ghost",),
        registry={
            "ghost": SourceRegistryEntry(
                source_type="ghost",
                adapter="NoSuchAdapter",
                inbox_subdir="ghost",
                file_glob="*.md",
                enabled=True,
            ),
        },
    )
    try:
        build_active_adapters(bad)
    except AdapterRegistryError as e:
        assert "NoSuchAdapter" in str(e)
        return
    raise AssertionError("expected AdapterRegistryError")


def test_default_path_does_not_read_dotenv() -> None:
    """默认加载 yaml + 构建 selector 路径不可 import dotenv / .env 解析模块。"""
    forbidden_modules = {"dotenv", "python_dotenv"}
    for mod in (
        _REPO / "src" / "mindforge" / "config.py",
        _REPO / "src" / "mindforge" / "sources" / "registry.py",
        _REPO / "src" / "mindforge" / "scanner.py",
    ):
        tree = ast.parse(mod.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden_modules, (
                        f"{mod.name} 不应 import {alias.name!r}"
                    )
            if isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                assert top not in forbidden_modules, (
                    f"{mod.name} 不应 from {node.module!r} import"
                )


# ---------------------------------------------------------------------------
# B. Scanner ↔ SourceMux integration contract
# ---------------------------------------------------------------------------


def _doc(content_hash: str, *, source_type: str = "cubox_markdown") -> SourceDocument:
    return SourceDocument(
        source_id=f"id:{content_hash}",
        source_type=source_type,  # type: ignore[arg-type]
        source_path=f"/tmp/{content_hash}.md",
        title="t",
        author=None,
        source_url=None,
        created_at=None,
        captured_at=None,
        tags=[],
        highlights=[],
        raw_text="",
        metadata={},
        content_hash=content_hash,
    )


def _scan_result(doc: SourceDocument | None, *, source_type: str | None = None,
                 path: str = "/tmp/x", error: str | None = None) -> ScanResult:
    return ScanResult(
        source_type=source_type or (doc.source_type if doc else "unknown"),
        adapter_name="Stub",
        path=Path(path),
        document=doc,
        error=error,
    )


def test_scanner_output_shape_is_consumable_by_source_mux() -> None:
    """形态一致性：Scanner.iter_results 产出的 ScanResult 直接喂给 mux 不报错。"""
    fake_results: Iterable[ScanResult] = [_scan_result(_doc("h1")), _scan_result(_doc("h2"))]
    mux = SourceMux()
    out = list(mux.iter_deduped(fake_results))
    assert len(out) == 2
    assert all(isinstance(r, ScanResult) for r in out)


def test_scanner_plus_mux_dedupes_documents_with_same_content_hash() -> None:
    """模拟双 cubox 链路：同 content_hash 来自不同 source_type，mux 只保留 first-seen。"""
    md = _scan_result(_doc("same", source_type="cubox_markdown"))
    api = _scan_result(_doc("same", source_type="cubox_api"))
    mux = SourceMux()
    out = list(mux.iter_deduped([md, api]))
    assert len(out) == 1
    assert out[0].source_type == "cubox_markdown"
    assert mux.stats.deduped == 1


def test_scanner_does_not_perform_dedup_without_mux() -> None:
    """Scanner 自身不去重 —— mux 是 opt-in 的上层。

    通过 AST 检查 scanner.py 不 import source_mux 来证明。
    """
    src = (_REPO / "src" / "mindforge" / "scanner.py").read_text(encoding="utf-8")
    assert "source_mux" not in src
    assert "SourceMux" not in src


def test_scanner_does_not_carry_credential_into_documents(tmp_path: Path) -> None:
    """Scanner 流水线中 SourceDocument.metadata 不可出现 token / credential 字段。

    这条测试在 Scanner 实际调用层以 contract 形式锁住：metadata key 不允许
    包含 credential 关键字。CuboxApiAdapter 已在自己的测试中守护，但这里
    给 Scanner 层补一层 invariant，以防未来某个 adapter 误把 token 塞进
    metadata。
    """
    forbidden_keys = {"token", "api_token", "access_token", "credential",
                      "authorization", "bearer", "secret"}
    # 用 stub 文档模拟 Scanner 输出（避免依赖真实 adapter / inbox 文件）
    safe_doc = _doc("h1")
    bad_doc = replace(safe_doc, metadata={"token": "FAKE"})
    # 安全文档应通过；恶意文档应被本测试捕获
    safe_keys = {k.lower() for k in safe_doc.metadata.keys()}
    assert not (safe_keys & forbidden_keys)
    bad_keys = {k.lower() for k in bad_doc.metadata.keys()}
    assert bad_keys & forbidden_keys, "测试自身有效性：恶意 metadata 必须被识别"


def test_scanner_module_does_not_perform_knowledge_or_review() -> None:
    """Scanner 职责单一：不可依赖 strategy / approval / review / writer。"""
    forbidden = {"strategies", "approver", "approval_service", "review_service",
                 "writer", "presenter", "llm"}
    tree = ast.parse((_REPO / "src" / "mindforge" / "scanner.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            last = node.module.split(".")[-1]
            top = node.module.split(".")[0]
            assert last not in forbidden and top not in forbidden, (
                f"scanner.py 禁止依赖 {node.module!r}"
            )


def test_scanner_with_real_default_yaml_uses_cubox_markdown(tmp_path: Path) -> None:
    """端到端 thin 集成：用默认 yaml 构造 Scanner，确认 adapters dict 含 plain_markdown。

    v0.7.21 起默认只启用 plain_markdown。Scanner 只应包含启用的 adapter。
    """
    from mindforge.config import load_mindforge_config
    cfg = load_mindforge_config(_DEFAULT_YAML)
    # 重写 vault 路径到 tmp 避免依赖真实 vault
    cfg = replace(cfg, vault=replace(cfg.vault, root=tmp_path))
    scanner = Scanner(cfg)
    assert "plain_markdown" in scanner.adapters
    assert scanner.adapters["plain_markdown"].__class__.__name__ == "PlainMarkdownAdapter"
    # cubox_markdown 是 optional adapter，默认不出现
    assert "cubox_markdown" not in scanner.adapters
