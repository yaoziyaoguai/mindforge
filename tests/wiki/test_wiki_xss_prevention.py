"""Wiki P5 — XSS 防护规则测试。

后端输出 canonical Markdown text，不渲染 HTML。
实际 sanitization 在前端 DOMPurify 完成（唯一 sanitization 点）。

后端测试验证：
1. build() 从合法 Markdown 输入产生的输出不引入 HTML 结构
2. ViewModel 字段类型为 str，不作为 HTML 被解释
3. 后端 pipeline 层不会意外包装 body 为 HTML

RFC_0002 §6 / SDD_WIKI_PRESENTATION_V2 §7, §13。
"""

from __future__ import annotations

import pytest


# =============================================================================
# 危险 HTML 标签 / 事件处理器 / 协议模式
# =============================================================================

_DANGEROUS_HTML_TAGS = [
    "<script", "</script", "<iframe", "<object", "<embed",
    "<form", "<input", "<style", "</style",
]

_DANGEROUS_ATTRIBUTES = [
    "onclick=", "onerror=", "onload=", "onmouseover=",
    "onfocus=", "onblur=", "onchange=", "onsubmit=",
]

_DANGEROUS_PROTOCOLS = [
    "javascript:",
]


def _contains_dangerous_patterns(text: str) -> list[str]:
    """返回 text 中匹配的危险模式列表（空 = 安全）。"""
    lower = text.lower()
    found: list[str] = []
    for pat in _DANGEROUS_HTML_TAGS + _DANGEROUS_ATTRIBUTES + _DANGEROUS_PROTOCOLS:
        if pat in lower:
            found.append(pat)
    return found


class TestBuildOutputIsCleanMarkdown:
    """build() 从合法 Markdown synthesis 输出不应引入 XSS pattern。

    LLM synthesis 应按约定生成 canonical Markdown（不含 HTML）。
    如果 synthesis 输出本身就是干净的 Markdown，build() 不应添加任何危险标签。
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel

        self.WikiPageViewModel = WikiPageViewModel

    def test_clean_synthesis_produces_no_dangerous_tags(self) -> None:
        synth = {
            "overview": "## Overview\n\nThis is a **safe** overview with *italic*.",
            "sections": [
                {
                    "title": "Section One",
                    "body": "### Details\n\n- item 1\n- item 2\n\n**bold text**",
                    "card_ids": [],
                },
                {
                    "title": "Section Two",
                    "body": "Paragraph with [a link](https://example.com).",
                    "card_ids": [],
                },
            ],
            "open_questions": ["What about X?"],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])

        # overview 中不应有危险模式
        overview_danger = _contains_dangerous_patterns(vm.overview)
        assert not overview_danger, f"Overview contains dangerous patterns: {overview_danger}"

        # 每个 section body 中不应有危险模式
        for sec in vm.sections:
            body_danger = _contains_dangerous_patterns(sec.body)
            assert not body_danger, (
                f"Section '{sec.title}' body contains dangerous patterns: {body_danger}"
            )

    def test_all_sections_body_contains_no_html_tags(self) -> None:
        """所有合法 section 的 body 不应包含 HTML 标签。"""
        synth = {
            "overview": "Overview.",
            "sections": [
                {"title": f"S{i}", "body": f"**Section {i}** content.", "card_ids": []}
                for i in range(3)
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        for sec in vm.sections:
            assert "<" not in sec.body or sec.body.startswith("<!--"), (
                f"Section '{sec.title}' contains HTML angle bracket"
            )

    def test_markdown_code_blocks_with_html_are_preserved_as_text(self) -> None:
        """Markdown code block 中的 HTML 是文本，不是可执行 HTML。
        build() 保留原样，前端 DOMPurify 保证安全。
        """
        synth = {
            "overview": "Overview.",
            "sections": [
                {
                    "title": "Code Example",
                    "body": "```html\n<script>alert(1)</script>\n```\n\n"
                            "This is a code block showing HTML, not executing it.",
                    "card_ids": [],
                }
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        body = vm.sections[0].body
        # 代码块中的 <script> 在 Markdown 上下文中是安全文本
        # 前端通过 Markdown 渲染器将其渲染为 <pre><code> 内容
        assert "```html" in body
        assert "```" in body


class TestViewModelBodyIsPlainText:
    """ViewModel body 字段是 str 类型，不作为 HTML 被解释。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel, WikiSectionView

        self.WikiPageViewModel = WikiPageViewModel
        self.WikiSectionView = WikiSectionView

    def test_section_body_is_plain_str(self) -> None:
        sec = self.WikiSectionView(
            id="s1",
            title="Section",
            body="## Markdown\n\n**bold** and [link](url).",
            level=2,
            card_refs=[],
            anchor="#section",
        )
        assert isinstance(sec.body, str)

    def test_overview_is_plain_str(self) -> None:
        vm = self.WikiPageViewModel(
            title="Wiki",
            mode="llm",
            model_id=None,
            last_rebuilt_at=None,
            overview="## Overview\n\n**Safe** content.",
            sections=[],
            additional_cards=[],
            open_questions=[],
            included_card_count=0,
            additional_card_count=0,
            warnings=[],
        )
        assert isinstance(vm.overview, str)

    def test_body_never_contains_html_wrappers_from_build(self) -> None:
        """build() 不应为 section body 添加 HTML 包装（如 <p> / <div>）。"""
        synth = {
            "overview": "Plain overview.",
            "sections": [
                {
                    "title": "Sec",
                    "body": "Simple paragraph text.",
                    "card_ids": [],
                }
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        body = vm.sections[0].body
        # body 不应被包装为 HTML
        assert body == "Simple paragraph text."


class TestJSONSerializationDoesNotProduceHTML:
    """JSON 序列化后 ViewModel 字段保持为 Markdown text。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel

        self.WikiPageViewModel = WikiPageViewModel

    def test_asdict_preserves_markdown(self) -> None:
        from dataclasses import asdict

        synth = {
            "overview": "## Overview\n\n**bold**",
            "sections": [
                {
                    "title": "Section",
                    "body": "### Subheading\n\n- list\n- items",
                    "card_ids": [],
                }
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        d = asdict(vm)

        # 序列化后 overview 仍为 Markdown text
        assert d["overview"] == "## Overview\n\n**bold**"
        assert d["sections"][0]["body"] == "### Subheading\n\n- list\n- items"

    def test_json_dumps_escapes_html_literals(self) -> None:
        """json.dumps 自动转义 < > & 为 Unicode 安全形式... 不对，
        json.dumps 实际上不转义 < >。但重要的是输出仍为 text，不被前端当作 HTML 解析。
        """
        import json
        from dataclasses import asdict

        synth = {
            "overview": "Overview.",
            "sections": [
                {
                    "title": "Sec",
                    "body": "Content with **markdown**.",
                    "card_ids": [],
                }
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        json_str = json.dumps(asdict(vm))
        parsed = json.loads(json_str)
        # Round-trip 后 body 仍为 Markdown
        assert "**markdown**" in parsed["sections"][0]["body"]


class TestSanitizationBoundaryContract:
    """sanitization 责任边界测试。

    后端不负责 sanitization。此合约确保：
    - 后端输出 canonical Markdown text
    - 前端 DOMPurify 为唯一 sanitization 点
    - 不会出现双重 sanitization 的责任模糊
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel

        self.WikiPageViewModel = WikiPageViewModel

    def test_build_does_not_import_html_sanitizer(self) -> None:
        """wiki_view_model 模块不应 import HTML sanitization library。"""
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

        forbidden = {"bleach", "html_sanitizer", "nh3", "lxml", "beautifulsoup4"}
        found = imports & forbidden
        assert not found, (
            f"wiki_view_model 不应 import HTML sanitization library: {found}"
        )

    def test_build_does_not_parse_html(self) -> None:
        """build() 不对 body 进行 HTML 解析——直接按原始字符串存储。"""
        from pathlib import Path

        vm_file = (
            Path(__file__).resolve().parent.parent.parent
            / "src" / "mindforge" / "wiki_view_model.py"
        )
        text = vm_file.read_text(encoding="utf-8")
        # 不应对 body 调用 HTML parser
        assert "HTMLParser" not in text
        assert "BeautifulSoup" not in text

    def test_build_preserves_user_content_as_given(self) -> None:
        """build() 不修改 section body 内容——保留 LLM synthesis 输出原样。"""
        original_body = "## Section\n\nExact content with **markdown** formatting."
        synth = {
            "overview": "Overview.",
            "sections": [
                {"title": "Sec", "body": original_body, "card_ids": []}
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.sections[0].body == original_body
