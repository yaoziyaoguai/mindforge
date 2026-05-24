"""模块边界契约测试：验证核心模块的 public API 表面不泄露内部实现。

中文学习型说明：
- 这些测试不验证功能正确性（那是其他测试的职责）。
- 它们只验证模块边界的契约：重要公开符号是否可 import、是否保持稳定。
- 如果有模块重构导致 public API 变化，这个测试会红，提醒更新 architecture-map.md。
"""

from __future__ import annotations


class TestCoreModulePublicAPI:
    """验证核心模块的关键公开符号可以正常 import。"""

    def test_cards_public_api(self) -> None:
        from mindforge.cards import CardSummary, iter_cards, read_card_body, read_card_frontmatter

        assert CardSummary is not None
        assert iter_cards is not None
        assert read_card_body is not None
        assert read_card_frontmatter is not None

    def test_config_public_api(self) -> None:
        from mindforge.config import MindForgeConfig, VaultConfig

        assert MindForgeConfig is not None
        assert VaultConfig is not None

    def test_safety_policy_public_api(self) -> None:
        from mindforge.safety_policy import (
            LOCAL_FIRST_BOUNDARIES,
            OBSIDIAN_WORKFLOW_SAFETY_LINE,
            SafetyBoundary,
        )

        assert SafetyBoundary is not None
        assert len(LOCAL_FIRST_BOUNDARIES) > 0
        assert isinstance(OBSIDIAN_WORKFLOW_SAFETY_LINE, str)

    def test_relations_public_api(self) -> None:
        from mindforge.relations.graph_models import Graph, GraphEdge, GraphNode
        from mindforge.relations.graph_port import GraphPort
        from mindforge.relations.community import detect_communities, KnowledgeCommunity

        assert Graph is not None
        assert GraphEdge is not None
        assert GraphNode is not None
        assert GraphPort is not None
        assert detect_communities is not None
        assert KnowledgeCommunity is not None

    def test_lexical_index_public_api(self) -> None:
        from mindforge.lexical_index import BM25Index, build_index, default_index_path, rebuild_index_for_config, search

        assert BM25Index is not None
        assert build_index is not None
        assert default_index_path is not None
        assert rebuild_index_for_config is not None
        assert search is not None

    def test_provider_readiness_public_api(self) -> None:
        from mindforge.provider_readiness import inspect_provider_config

        assert inspect_provider_config is not None

    def test_fake_provider_public_api(self) -> None:
        from mindforge.llm.fake import FakeProvider

        assert FakeProvider is not None

    def test_web_schemas_public_api(self) -> None:
        from mindforge_web.schemas import (
            ExportCardsRequest,
            ExportCardsResponse,
            ImportCardRequest,
            ImportCardResponse,
            LibraryCardDetailResponse,
            LibraryCardsResponse,
        )

        assert ExportCardsRequest is not None
        assert ExportCardsResponse is not None
        assert ImportCardRequest is not None
        assert ImportCardResponse is not None
        assert LibraryCardDetailResponse is not None
        assert LibraryCardsResponse is not None


class TestModuleIsolation:
    """验证模块间的隔离边界不泄露内部实现细节。"""

    def test_schemas_do_not_import_core_services(self) -> None:
        """schemas.py 只定义数据形状，不得 import 业务 service。"""
        import ast
        from pathlib import Path

        schemas_path = Path(__file__).resolve().parents[1] / "src" / "mindforge_web" / "schemas.py"
        tree = ast.parse(schemas_path.read_text(encoding="utf-8"))

        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(module)

        # schemas 只允许 import mindforge 核心（类型引用），不得 import mindforge_web services
        service_imports = [m for m in imports if "mindforge_web.services" in m or "mindforge_web.routers" in m]
        assert not service_imports, f"schemas.py 不应 import Web service/router：{service_imports}"

    def test_card_workspace_does_not_import_config_directly(self) -> None:
        """card_workspace_service 通过 MindForgeConfig 参数接收配置，不自行加载。"""
        import ast
        from pathlib import Path

        svc_path = (
            Path(__file__).resolve().parents[1]
            / "src" / "mindforge" / "card_workspace_service.py"
        )
        tree = ast.parse(svc_path.read_text(encoding="utf-8"))

        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(f"from {module}")

        # 不应有 load_mindforge_config（那是 app_context 的职责）
        load_imports = [i for i in imports if "load_mindforge_config" in i]
        assert not load_imports, f"card_workspace_service 不应自行加载 config：{load_imports}"
