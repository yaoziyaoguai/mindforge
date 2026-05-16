"""Wiki P5 — Secret Exposure 防护测试。

确保 WikiPageViewModel / WikiSectionView / WikiReferenceView 的序列化输出
不包含 API Key、Token、环境变量等敏感信息。

后端 ViewModel 字段有限且定义明确（dataclass），不可能意外携带 secret。
但需要显式测试防止未来字段扩展引入泄露。

RFC_0002 §6 / SDD_WIKI_PRESENTATION_V2 §13。
"""

from __future__ import annotations

import json
from dataclasses import asdict

import pytest


# =============================================================================
# API Key / Secret Patterns（不应出现在任何 ViewModel 输出中）
# =============================================================================

_SECRET_PATTERNS = [
    "sk-",                    # OpenAI / Anthropic API key prefix
    "api_key",
    "apiKey",
    "apikey",
    "api-key",
    "secret",
    "password",
    "token",
    "credential",
    "private_key",
    "privateKey",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
]


def _check_no_secrets(data: dict, path: str = "root") -> None:
    """递归检查 dict 中不包含 secret pattern。"""
    for key, value in data.items():
        current_path = f"{path}.{key}"
        if isinstance(value, str):
            lower_val = value.lower()
            for pattern in _SECRET_PATTERNS:
                assert pattern.lower() not in lower_val, (
                    f"Secret pattern '{pattern}' found in {current_path}"
                )
        elif isinstance(value, dict):
            _check_no_secrets(value, current_path)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    _check_no_secrets(item, f"{current_path}[{i}]")
                elif isinstance(item, str):
                    lower_val = item.lower()
                    for pattern in _SECRET_PATTERNS:
                        assert pattern.lower() not in lower_val, (
                            f"Secret pattern '{pattern}' found in {current_path}[{i}]"
                        )


class TestWikiSectionViewNoSecretExposure:
    """WikiSectionView 不应泄露敏感信息。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiSectionView, WikiReferenceView

        self.WikiSectionView = WikiSectionView
        self.WikiReferenceView = WikiReferenceView

    def test_section_serialization_no_secrets(self) -> None:
        sec = self.WikiSectionView(
            id="s1",
            title="Section Title",
            body="## Safe Content\n\nNormal markdown text.",
            level=2,
            card_refs=[],
            anchor="#section-title",
        )
        d = asdict(sec)
        _check_no_secrets(d)

    def test_section_with_card_refs_no_secrets(self) -> None:
        ref = self.WikiReferenceView(
            card_id="card-001",
            card_title="Test Card",
            source_title="source.pdf",
            source_type="pdf",
        )
        sec = self.WikiSectionView(
            id="s1",
            title="Section",
            body="Content.",
            level=2,
            card_refs=[ref],
            anchor="#section",
        )
        d = asdict(sec)
        _check_no_secrets(d)

    def test_section_json_serializable(self) -> None:
        """section 序列化为 JSON 不应失败（所有字段可序列化）。"""
        sec = self.WikiSectionView(
            id="s1",
            title="Section",
            body="Content.",
            level=2,
            card_refs=[],
            anchor="#section",
        )
        json_str = json.dumps(asdict(sec))
        assert isinstance(json_str, str)
        assert len(json_str) > 0


class TestWikiReferenceViewNoSecretExposure:
    """WikiReferenceView 只包含 provenance 元数据，不泄露 card body。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiReferenceView

        self.WikiReferenceView = WikiReferenceView

    def test_reference_has_no_body_field(self) -> None:
        ref = self.WikiReferenceView(
            card_id="card-001",
            card_title="Test Card",
            source_title="source.pdf",
            source_type="pdf",
        )
        assert "body" not in ref.__dict__
        assert "content" not in ref.__dict__
        assert "raw_text" not in ref.__dict__

    def test_reference_fields_are_metadata_only(self) -> None:
        """WikiReferenceView 只包含 card 元数据字段。"""
        allowed = {
            "card_id", "card_title", "source_title", "source_type",
            "source_path", "track", "tags", "value_score",
            "approved_at", "card_rel_path",
        }
        ref = self.WikiReferenceView(
            card_id="card-001",
            card_title="Test Card",
        )
        for field_name in ref.__dict__:
            assert field_name in allowed, f"Unexpected field: {field_name}"

    def test_reference_serialization_no_secrets(self) -> None:
        ref = self.WikiReferenceView(
            card_id="card-001",
            card_title="Test Card",
            source_title="source.pdf",
            source_type="pdf",
        )
        d = asdict(ref)
        _check_no_secrets(d)

    def test_reference_json_serializable(self) -> None:
        ref = self.WikiReferenceView(
            card_id="card-001",
            card_title="Test Card",
        )
        json_str = json.dumps(asdict(ref))
        assert isinstance(json_str, str)


class TestWikiPageViewModelNoSecretExposure:
    """WikiPageViewModel 序列化后不包含敏感信息。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel

        self.WikiPageViewModel = WikiPageViewModel

    def test_viewmodel_serialization_no_secrets(self) -> None:
        synth = {
            "overview": "Safe overview text.",
            "sections": [
                {
                    "title": "Section",
                    "body": "Content with **bold**.",
                    "card_ids": [],
                }
            ],
            "open_questions": ["Question 1"],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        d = asdict(vm)
        _check_no_secrets(d)

    def test_viewmodel_warnings_no_secrets(self) -> None:
        """即使有 warnings，也不泄露敏感信息。"""
        synth = {"overview": "", "sections": [], "open_questions": []}
        vm = self.WikiPageViewModel.build(
            synthesis_output=synth,
            digests=[],
            warnings=["LLM synthesis timeout", "Model overloaded"],
        )
        d = asdict(vm)
        _check_no_secrets(d)

    def test_viewmodel_json_serializable(self) -> None:
        synth = {
            "overview": "Overview.",
            "sections": [],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        json_str = json.dumps(asdict(vm))
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["title"] == "MindForge Main Wiki"
        assert parsed["mode"] == "llm"

    def test_viewmodel_fields_are_bounded(self) -> None:
        """ViewModel 的字段集合应是已知的有限集合。"""
        synth = {"overview": "", "sections": [], "open_questions": []}
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        d = asdict(vm)
        expected_fields = {
            "title", "mode", "model_id", "last_rebuilt_at",
            "overview", "sections", "additional_cards", "open_questions",
            "included_card_count", "additional_card_count", "warnings",
        }
        assert set(d.keys()) == expected_fields


class TestNoDotEnvOrConfigLeakage:
    """确保 ViewModel 不意外引用 .env 或 config 对象。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import (
            WikiPageViewModel,
            WikiSectionView,
            WikiReferenceView,
            WikiQuestionView,
            WikiRenderOptions,
        )

        self.WikiPageViewModel = WikiPageViewModel
        self.WikiSectionView = WikiSectionView
        self.WikiReferenceView = WikiReferenceView
        self.WikiQuestionView = WikiQuestionView
        self.WikiRenderOptions = WikiRenderOptions

    def test_view_models_do_not_import_env(self) -> None:
        """ViewModel 模块不应 import env_loader 或 os.environ。"""
        import ast
        from pathlib import Path

        vm_file = (
            Path(__file__).resolve().parent.parent.parent
            / "src" / "mindforge" / "wiki_view_model.py"
        )
        tree = ast.parse(vm_file.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.add(a.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        assert "mindforge.env_loader" not in imports
        assert "os" not in imports or "os" not in {
            n.name for n in ast.walk(tree)
            if isinstance(n, ast.Import) and "os" in {a.name for a in n.names}
        }

    def test_wiki_render_options_do_not_expose_secrets(self) -> None:
        """WikiRenderOptions 只包含渲染配置，不含敏感字段。"""
        opts = self.WikiRenderOptions()
        d = asdict(opts)
        _check_no_secrets(d)
        # 所有字段应为 boolean/string 渲染配置
        for k, v in d.items():
            assert isinstance(v, (bool, str)), (
                f"WikiRenderOptions.{k} 类型异常: {type(v)}"
            )
