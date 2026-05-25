"""v3.2 — 检索质量评估指标。

设计原则：
- 纯 deterministic 计算，不调用 LLM
- 不依赖 embedding / vector DB
- 输入为 retrieved relations + ground truth relations
- 输出结构化 EvalReport

中文学习型说明：
借鉴信息检索的 precision/recall 框架，但不做 semantic similarity /
embedding-based ranking。所有指标基于确定性关系匹配计算。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelationPair:
    """一条检索到的关系（由 retrieval/graph engine 返回）。"""

    source_id: str
    target_id: str
    relation_type: str
    has_evidence: bool = True  # evidence/reason 字段非空


@dataclass(frozen=True)
class EvalReport:
    """检索质量评估报告。"""

    # 基础统计
    total_ground_truth: int
    total_retrieved: int
    total_correct: int  # 检索到且在 ground truth 中的关系数

    # 核心指标
    precision: float  # correct / retrieved
    recall: float  # correct / ground_truth
    f1: float  # 2 * precision * recall / (precision + recall)

    # 质量指标
    explainability_coverage: float  # 有 evidence 的关系数 / 总检索关系数
    provenance_coverage: float  # 有 source_id 的卡片数 / 总卡片数

    # 安全性指标
    false_positive_count: int  # 检索到但不在 ground truth 中的关系数
    false_positive_rate: float  # false_positive / retrieved（越低越好）
    negative_pair_violations: int  # 负例卡片对中错误检出的关系数

    # 摘要
    summary: str = ""


def _normalize_pair(source: str, target: str) -> tuple[str, str]:
    """将关系对规范化为无序对（无向图语义）。"""
    return (source, target) if source < target else (target, source)


def evaluate(
    retrieved: list[RelationPair],
    ground_truth: list[tuple[str, str, str]],  # (source, target, relation_type)
    *,
    negative_pairs: list[tuple[str, str]] | None = None,
    total_cards: int = 0,
    cards_with_provenance: int = 0,
) -> EvalReport:
    """运行检索质量评估。

    Args:
        retrieved: 检索/graph engine 返回的关系列表
        ground_truth: 已知 ground truth 关系 (source_id, target_id, relation_type)
        negative_pairs: 预期无关系的卡片对（负例），用于检测 hallucinated relations
        total_cards: benchmark 总卡片数
        cards_with_provenance: 有 source_id 的卡片数
    """
    # 规范化
    gt_pairs: set[tuple[str, str]] = set()
    for s, t, _ in ground_truth:
        gt_pairs.add(_normalize_pair(s, t))

    retrieved_pairs: set[tuple[str, str]] = set()
    for r in retrieved:
        retrieved_pairs.add(_normalize_pair(r.source_id, r.target_id))

    # 交集
    correct_pairs = gt_pairs & retrieved_pairs

    total_gt = len(gt_pairs)
    total_ret = len(retrieved_pairs)
    total_correct = len(correct_pairs)

    # 核心指标
    precision = total_correct / total_ret if total_ret > 0 else 0.0
    recall = total_correct / total_gt if total_gt > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # 可解释性：有 evidence 的关系比例
    with_evidence = sum(1 for r in retrieved if r.has_evidence)
    explainability = with_evidence / total_ret if total_ret > 0 else 0.0

    # 溯源覆盖
    provenance_cov = cards_with_provenance / total_cards if total_cards > 0 else 0.0

    # 假阳性
    false_pos = total_ret - total_correct
    fp_rate = false_pos / total_ret if total_ret > 0 else 0.0

    # 负例违规
    neg_violations = 0
    if negative_pairs:
        for s, t in negative_pairs:
            if _normalize_pair(s, t) in retrieved_pairs:
                neg_violations += 1

    # 摘要
    summary = (
        f"Precision={precision:.2%} Recall={recall:.2%} F1={f1:.2%} | "
        f"Explainability={explainability:.0%} Provenance={provenance_cov:.0%} | "
        f"FalsePos={false_pos} NegViolations={neg_violations}"
    )

    return EvalReport(
        total_ground_truth=total_gt,
        total_retrieved=total_ret,
        total_correct=total_correct,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        explainability_coverage=round(explainability, 4),
        provenance_coverage=round(provenance_cov, 4),
        false_positive_count=false_pos,
        false_positive_rate=round(fp_rate, 4),
        negative_pair_violations=neg_violations,
        summary=summary,
    )
