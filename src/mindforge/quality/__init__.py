"""M1 Card Quality 模块。

导出 quality metadata 模型、rubric scoring、card type 分类、warnings 检测和 suggestions 生成。

Quality metadata 是只读附属，不修改卡片 body/status（RFC §6 AD-2）。
所有评分基于确定性规则（RFC §6 AD-1）。
"""

from mindforge.quality.models import (
    CardQuality,
    CardType,
    QualityLevel,
    QualityRubricScore,
    QualityWarning,
)
from mindforge.quality.rubric import score_quality
from mindforge.quality.card_type import classify_card_type
from mindforge.quality.warnings import detect_warnings
from mindforge.quality.suggestions import generate_suggestions

__all__ = [
    "CardQuality",
    "CardType",
    "QualityLevel",
    "QualityRubricScore",
    "QualityWarning",
    "score_quality",
    "classify_card_type",
    "detect_warnings",
    "generate_suggestions",
]
