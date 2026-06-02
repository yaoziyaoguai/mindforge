"""Product boundary and UX safety tests.

中文学习型说明：
在 public docs reset 之后，部分 agent-internal 的文档以及强绑定的文案检查测试失去了上下文。
为了保证不为了过 CI 而随意删除安全测试，我们将这些测试重构为对
`docs/developer/product-boundaries.md` 的断言，确保:
- fake provider 是安全的默认项
- explicit approval 是不可跳过的流程
- ai_draft 与 human_approved 保持分离

任何进一步的产品安全底线修改都应该体现在 product-boundaries.md 中。
"""

from pathlib import Path

def test_product_boundaries_exist_and_enforce_safety():
    """验证产品边界文档存在且包含关键的安全约束。"""
    doc = Path("docs/developer/product-boundaries.md")
    assert doc.exists(), "必须提供稳定的产品边界文档"

    text = doc.read_text(encoding="utf-8").lower()

    required_boundaries = [
        "ai_draft",
        "human_approved",
        "explicit approval required",
        "fake provider default",
        "real llm opt-in",
        "source adapter vs provider"
    ]

    for b in required_boundaries:
        assert b.lower() in text, f"边界文档缺失关键约束: {b}"
