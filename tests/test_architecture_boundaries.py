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
            "web_facade.py": {
                "mindforge.relations.community",
                "mindforge.relations.discovery_context",
                "mindforge.relations.graph_builder",
                "mindforge.relations.graph_models",
                "mindforge.relations.local_graph",
                "mindforge.relations.related_cards",
                "mindforge.relations.sensemaking",
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
