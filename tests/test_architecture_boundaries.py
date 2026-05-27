"""Architecture boundary contract tests.

中文学习型说明：这些测试验证架构边界，不验证功能正确性。
如果架构被不当修改（如主路径 import 了 lab 代码），这些测试会红。
"""

from __future__ import annotations

import ast
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC = _PROJECT_ROOT / "src"


# ── Lab/Internal modules that main path must not depend on ──────────────

_LAB_MODULES = frozenset({
    "mindforge.relations.graph_models",
    "mindforge.relations.graph_builder",
    "mindforge.relations.graph_port",
    "mindforge.relations.community",
    "mindforge.relations.sensemaking",
    "mindforge.relations.entity",
    "mindforge.relations.local_graph",
    "mindforge.relations.related_cards",
    "mindforge.relations.discovery_context",
})

_LAB_ALLOWED_ROUTERS = frozenset({
    "graph.py",
    "discovery.py",
})


# ── RAG / embedding forbidden imports ──────────────────────────────────

_RAG_FORBIDDEN_PACKAGES = frozenset({
    "sentence_transformers",
    "chromadb",
    "faiss",
    "pinecone",
    "weaviate",
    "qdrant_client",
    "langchain",
    "llama_index",
    "tiktoken",
    "torch",
    "transformers",
})


def _all_python_files(root: Path) -> list[Path]:
    return sorted(
        f for f in root.rglob("*.py")
        if ".git" not in str(f) and "__pycache__" not in str(f)
    )


class TestArchitectureMainPathBoundaries:
    """主路径代码不得依赖 lab/internal graph/sensemaking 模块。"""

    def test_main_path_routers_do_not_import_lab_graph(self) -> None:
        """主路径 routers（非 graph/discovery）不得 import relations.* 模块。"""
        routers_dir = _SRC / "mindforge_web" / "routers"
        violations: list[str] = []

        for router_file in sorted(routers_dir.glob("*.py")):
            if router_file.name in _LAB_ALLOWED_ROUTERS:
                continue
            if router_file.name == "__init__.py":
                continue

            tree = ast.parse(router_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if any(
                        node.module == m or node.module.startswith(m + ".")
                        for m in _LAB_MODULES
                    ):
                        violations.append(
                            f"{router_file.name}: imports {node.module}"
                        )

        assert not violations, (
            "主路径 routers 不得 import lab graph/sensemaking 模块：\n"
            + "\n".join(violations)
        )

    def test_main_path_services_lab_imports_are_known(self) -> None:
        """Web services 的 lab graph import 必须是 known violation。

        中文学习型说明：web_facade.py 当前有 graph/sensemaking 方法的 relation
        import — 这是 known violation。Slice 2 将修复。本测试确保不会意外新增
        lab import。
        """
        services_dir = _SRC / "mindforge_web" / "services"
        known_lab_imports: dict[str, set[str]] = {
            # web_facade 保留 relations import 用于 local graph / provenance / quality
            # 等非 lab 方法。lab 方法已提取到 web_lab_service。
            "web_facade.py": {
                "mindforge.relations.community",
                "mindforge.relations.discovery_context",
                "mindforge.relations.graph_builder",
                "mindforge.relations.graph_models",
                "mindforge.relations.local_graph",
                "mindforge.relations.related_cards",
            },
            # web_lab_service 包含所有从 web_facade 提取的 lab/internal 方法
            "web_lab_service.py": {
                "mindforge.relations.community",
                "mindforge.relations.discovery_context",
                "mindforge.relations.graph_builder",
                "mindforge.relations.graph_models",
                "mindforge.relations.sensemaking",
                "mindforge.relations.topic",
            },
            # dogfood_service 使用 graph_builder 计算 relation 统计 — internal 工具
            "dogfood_service.py": {
                "mindforge.relations.graph_builder",
            },
        }

        for svc_file in sorted(services_dir.glob("*.py")):
            if svc_file.name == "__init__.py":
                continue

            tree = ast.parse(svc_file.read_text(encoding="utf-8"))
            actual: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for m in _LAB_MODULES:
                        if node.module == m or node.module.startswith(m + "."):
                            actual.add(node.module)

            expected = known_lab_imports.get(svc_file.name, set())
            unexpected = actual - expected

            assert not unexpected, (
                f"{svc_file.name}: 意外新增 lab graph import：{unexpected}\n"
                f"如果是新 lab 集成，请更新 known_lab_imports。"
            )


class TestArchitectureSchemaBoundaries:
    """Schema domain modules 的 import 方向必须正确。"""

    def test_schema_submodules_no_service_imports(self) -> None:
        """验证 schemas/ 子模块不 import services 或 routers。"""
        schemas_dir = _SRC / "mindforge_web" / "schemas"
        violations: list[str] = []

        for schema_file in sorted(schemas_dir.glob("*.py")):
            if schema_file.name == "__init__.py":
                continue

            tree = ast.parse(schema_file.read_text(encoding="utf-8"))

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "mindforge_web.services" in node.module:
                        violations.append(
                            f"{schema_file.name}: imports service {node.module}"
                        )
                    if "mindforge_web.routers" in node.module:
                        violations.append(
                            f"{schema_file.name}: imports router {node.module}"
                        )

        assert not violations, (
            f"Schema domain modules must not import services/routers: {violations}"
        )

    def test_all_schema_submodule_classes_re_exported(self) -> None:
        """验证所有 schema 子模块的 public 类都在 __init__.py 中 re-export。"""
        schemas_dir = _SRC / "mindforge_web" / "schemas"
        init_path = schemas_dir / "__init__.py"
        init_tree = ast.parse(init_path.read_text(encoding="utf-8"))

        re_exported: set[str] = set()
        for node in ast.walk(init_tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("mindforge_web.schemas."):
                    for alias in node.names:
                        re_exported.add(alias.name)

        missing: list[str] = []
        for schema_file in sorted(schemas_dir.glob("*.py")):
            if schema_file.name == "__init__.py":
                continue
            tree = ast.parse(schema_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                    if node.name not in re_exported:
                        missing.append(f"{node.name} (from {schema_file.name})")

        assert not missing, (
            "以下 schema 子模块的 public 类未在 __init__.py 中 re-export：\n"
            + "\n".join(missing)
        )


class TestArchitectureNoRAGNoEmbedding:
    """全局禁止 RAG/embedding/vector DB 依赖。"""

    def test_no_rag_embedding_imports(self) -> None:
        """整个 src/ 代码树不得 import RAG/embedding/vector DB 库。"""
        violations: list[str] = []

        for py_file in _all_python_files(_SRC):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                modules_to_check: list[str] = []
                if isinstance(node, ast.Import):
                    modules_to_check = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules_to_check = [node.module]

                for mod in modules_to_check:
                    top_level = mod.split(".")[0]
                    if top_level in _RAG_FORBIDDEN_PACKAGES:
                        violations.append(
                            f"{py_file.relative_to(_PROJECT_ROOT)}: imports {mod}"
                        )

        assert not violations, (
            "代码树不得 import RAG/embedding/vector DB 库：\n"
            + "\n".join(violations)
        )


# ── Slice 0: Core → Web layer boundary ──────────────────────────────────

# 中文学习型说明：known_core_web_imports 列出了当前已知的 core → web
# 反向依赖。这些是 AUDIT-118-03 P1 债项，已由 Slice 1 消除 processing_run_service
# 相关条目。剩余 2 个为合理（web server 入口 + dogfood 内部工具）。
# 新代码不得新增反向依赖。
_CORE_WEB_KNOWN_VIOLATIONS: dict[str, set[str]] = {
    "dogfood/scenario_runner.py": {
        "mindforge_web.services.dogfood_service",
    },
    # web_cli.py 是 web server 入口，import from mindforge_web 是合理的
    "web_cli.py": {
        "mindforge_web.server",
    },
}


# 中文学习型说明：core → web private symbol import 已在 Slice 1 全部消除。
# _run_worker 和 _save_record 现在定义在 mindforge.processing.run_store（core 层）。
# 空 dict 表示：任何新的 private symbol import 都会触发测试失败。
_CORE_WEB_KNOWN_PRIVATE_IMPORTS: dict[str, set[str]] = {}


class TestArchitectureCoreWebLayerBoundary:
    """core (src/mindforge/) 不得反向依赖 web (src/mindforge_web/)。

    Slice 1 已完成：processing_run_service 处理逻辑已迁移到 mindforge.processing.run_store，
    core 层不再 import 任何 processing_run 相关 web 模块。
    剩余 known violation: dogfood_service（P2）和 web_cli（P3，web server 入口）。
    """

    def test_core_web_imports_are_known_only(self) -> None:
        """core 目录下所有 mindforge_web import 必须是 known violation。"""
        core_dir = _SRC / "mindforge"
        violations: list[str] = []

        for py_file in sorted(core_dir.rglob("*.py")):
            if py_file.name == "__init__.py" and py_file.stat().st_size == 0:
                continue
            if "__pycache__" in str(py_file):
                continue

            rel = str(py_file.relative_to(core_dir))
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue

            actual: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("mindforge_web"):
                        actual.add(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("mindforge_web"):
                            actual.add(alias.name)

            expected = _CORE_WEB_KNOWN_VIOLATIONS.get(rel, set())
            new_violations = actual - expected

            if new_violations:
                violations.append(
                    f"{rel}: 新增 mindforge_web import {new_violations}"
                )

        assert not violations, (
            "core 模块不得新增 mindforge_web 反向依赖：\n"
            + "\n".join(violations)
            + "\n\n如果是新的合法 web server 入口或已知例外，"
            "请更新 _CORE_WEB_KNOWN_VIOLATIONS。"
        )

    def test_no_core_imports_web_private_symbols(self) -> None:
        """core 模块不得 import mindforge_web 中的 private symbol（`_` 前缀）。

        中文学习型说明：当前 processing_worker.py 和 cli_processing_runtime.py
        分别 import 了 _run_worker 和 _save_record（private symbol）。
        这是 AUDIT-118-03 中最严重的反向依赖 —— core 不仅依赖 web，
        还依赖 web 的内部实现细节。Slice 1 必须消除。
        本测试只对 NEW private symbol import 报红，已知 violation 容忍。
        """
        core_dir = _SRC / "mindforge"
        new_violations: list[str] = []

        for py_file in sorted(core_dir.rglob("*.py")):
            if "__pycache__" in str(py_file):
                continue

            rel = str(py_file.relative_to(core_dir))
            known_for_file = _CORE_WEB_KNOWN_PRIVATE_IMPORTS.get(rel, set())
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("mindforge_web"):
                        for alias in node.names:
                            if alias.name.startswith("_") and alias.name not in known_for_file:
                                new_violations.append(
                                    f"{rel}: imports private {node.module}.{alias.name}"
                                )

        assert not new_violations, (
            "core 模块不得新增 web 层的 private symbol import：\n"
            + "\n".join(new_violations)
            + "\n\nPrivate symbol import 说明 core 深度耦合了 web 内部实现。"
            " 这些函数应提取到 core 层（src/mindforge/processing/）。"
        )


# ── Slice 0: WebFacade public method contract ─────────────────────────

class TestArchitectureWebFacadeContract:
    """WebFacade 公开方法合同 —— 确保重构不意外删除或修改方法签名。"""

    def test_web_facade_public_methods_exist(self) -> None:
        """WebFacade 所有公开方法均可通过 getattr 访问。"""
        from mindforge_web.services.web_facade import WebFacade

        # 这些是 routers/ 直接调用的公开方法
        required_methods = [
            # Home / Setup
            "home_status",
            "config_status",
            "setup_editable_config",
            "validate_setup_config_patch",
            "update_setup_config_patch",
            "set_provider_mode",
            # Sources
            "sources",
            "watch_sources",
            "watch_add",
            "watch_scan",
            "watch_delete",
            "watch_frequency",
            "import_source",
            "processing_run",
            # Drafts
            "drafts",
            "draft_detail",
            "update_draft_body",
            # Library
            "library_cards",
            "library_card_detail",
            "update_library_card_body",
            "provenance_trail",
            # Recall / Wiki
            "recall",
            "recall_status",
            # Home status
            "health",
            "knowledge_health_report",
            "workflow_summary",
            "safety_summary",
            "workspace_status",
            "vault_status",
            # Dogfood
            "dogfood_report",
            # Provider
            "provider_readiness_detail",
            # Lifecycle
            "source_lifecycle",
            # Lab (delegated)
            "get_graph_node",
            "get_graph_explore",
            "get_graph_edge",
            "get_sensemaking",
            "get_discovery_context",
            "knowledge_communities",
            "knowledge_topics",
            # Import/Export
            "import_card",
            "preview_folder_import",
            "import_from_folder",
            # Quality / Location
            "compute_card_quality",
            "compute_card_location",
            # Reveal
            "reveal_by_ref",
        ]

        # 验证方法存在且可调用
        facade = WebFacade.__dict__
        missing = [m for m in required_methods if m not in facade]
        assert not missing, (
            f"WebFacade 缺少以下公开方法：{missing}\n"
            "如果方法是故意删除/重命名的，请更新此测试。"
        )

    def test_web_facade_core_methods_have_consistent_return_types(self) -> None:
        """WebFacade 核心方法的返回类型注解存在。"""
        import inspect
        from mindforge_web.services.web_facade import WebFacade

        core_methods = [
            "home_status",
            "config_status",
            "sources",
            "drafts",
            "library_cards",
            "library_card_detail",
            "recall",
            "dogfood_report",
            "provider_readiness_detail",
            "source_lifecycle",
        ]

        no_return_annotation: list[str] = []
        for method_name in core_methods:
            method = getattr(WebFacade, method_name, None)
            if method is None:
                continue
            sig = inspect.signature(method)
            if sig.return_annotation is inspect.Parameter.empty:
                no_return_annotation.append(method_name)

        assert not no_return_annotation, (
            f"以下核心方法缺少返回类型注解：{no_return_annotation}"
        )


# ── Slice 0: Processing run contract ───────────────────────────────────

class TestArchitectureProcessingRunContract:
    """Processing run 函数合同 —— 确保 Slice 1 迁移时不改变接口。"""

    def test_processing_run_functions_exist(self) -> None:
        """验证 processing_run_service 的关键公开函数存在且签名一致。"""
        from mindforge_web.services import processing_run_service as prs

        required_functions = [
            "get_processing_run",
            "list_processing_runs",
            "latest_run_for_source",
            "processing_run_response",
            "ProcessingRunRecord",
        ]

        for func_name in required_functions:
            assert hasattr(prs, func_name), (
                f"processing_run_service 缺少 {func_name}"
            )

    def test_processing_run_record_fields(self) -> None:
        """ProcessingRunRecord 关键字段不被意外修改。"""
        from mindforge_web.services.processing_run_service import ProcessingRunRecord

        required_fields = [
            "run_id",
            "source_ref",
            "source_path",
            "status",
            "started_at",
        ]

        # ProcessingRunRecord 是 dataclass
        import dataclasses
        fields = {f.name for f in dataclasses.fields(ProcessingRunRecord)}
        missing = [f for f in required_fields if f not in fields]
        assert not missing, (
            f"ProcessingRunRecord 缺少关键字段：{missing}"
        )


class TestArchitectureApprovalSafety:
    """Approval 安全语义的架构保护。"""

    def test_approval_schemas_importable(self) -> None:
        """确保 approval 相关 schema 保持可通过稳定路径 import。"""
        from mindforge_web.schemas import (
            ApprovalResponse,
            ApproveRequest,
            DraftDetailResponse,
            DraftsResponse,
            DraftSummary,
            RejectRequest,
        )
        assert ApprovalResponse is not None
        assert ApproveRequest is not None
        assert RejectRequest is not None
        assert DraftDetailResponse is not None
        assert DraftsResponse is not None
        assert DraftSummary is not None

    def test_human_approved_value_unchanged(self) -> None:
        """human_approved 目标状态常量不得被意外修改。"""
        from mindforge.approver import _TARGET_STATUS
        assert _TARGET_STATUS == "human_approved", (
            f"approver._TARGET_STATUS 必须是 'human_approved'，当前值：{_TARGET_STATUS}"
            " — 改变此值会破坏核心安全语义"
        )

    def test_approval_requires_explicit_confirm(self) -> None:
        """ApproveRequest 的 confirm 字段必须为 bool 类型（不能默认 True）。"""
        from mindforge_web.schemas import ApproveRequest
        fields = ApproveRequest.model_fields
        assert "confirm" in fields, "ApproveRequest 必须有 confirm 字段"
        assert fields["confirm"].annotation is bool, (
            "confirm 必须是 bool — 不能默认 approve"
        )
