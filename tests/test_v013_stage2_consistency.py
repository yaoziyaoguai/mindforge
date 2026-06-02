"""Product boundary and safety tests.

中文学习型说明：
在 public docs reset 之后，大量 agent-internal 的过程记录（如 ROADMAP_COMPLETION_LEDGER
和 v0.13/v0.14 特定阶段的 check 文档）被移除，以保持仓库面向公众的清晰度。
因此，我们不能继续依赖那些已删除的内部文档来进行断言。

但是，产品的核心安全边界（如 ai_draft vs human_approved, fake provider 默认,
显式 opt-in, 不直接写真实 Obsidian vault）绝不能丢失。
本测试被重写，现在的目标是验证 `docs/developer/product-boundaries.md` 这个
稳定的、面向公众的边界契约，确保这些安全底线持续被保护。
"""

from pathlib import Path

def test_product_boundaries_exist_and_enforce_safety():
    """验证产品边界文档存在且包含关键的安全约束。"""
    doc = Path("docs/developer/product-boundaries.md")
    assert doc.exists(), "必须提供稳定的产品边界文档"

    text = doc.read_text(encoding="utf-8").lower()

    # 核心安全边界必须存在
    required_boundaries = [
        "ai_draft",
        "human_approved",
        "explicit approval required",
        "fake provider default",
        "real llm opt-in",
        "source adapter vs provider",
        "no real obsidian write",
        "no rag",
        "lab / internal features"
    ]

    for b in required_boundaries:
        assert b.lower() in text, f"边界文档缺失关键约束: {b}"
