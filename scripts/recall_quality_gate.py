#!/usr/bin/env python3
"""v4.9 Direction C — Recall Quality Gate Script.

中文学习型说明：独立运行的质量 gate，加载 golden recall fixtures，
对每个 query 执行 BM25 recall，验证 expected_hit_ids 命中率 ≥ 阈值。
不依赖 Web server、不调用 LLM/embedding/vector DB。

用法:
    python scripts/recall_quality_gate.py           # 使用默认阈值 80%
    python scripts/recall_quality_gate.py --threshold 0.7  # 自定义阈值
    python scripts/recall_quality_gate.py --verbose        # 详细输出

Exit Code:
    0 — 所有 golden queries 通过，总体 recall ≥ threshold
    1 — 部分 golden queries 未达 threshold 或测试异常
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

# 确保 mindforge 在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mindforge.config import load_mindforge_config
from mindforge.recall_service import run_bm25_recall, RecallQuery
from tests.fixtures.recall_benchmark import build_recall_benchmark
from tests.test_recall_benchmark import _make_benchmark_config


def _make_query(query_text: str, **overrides) -> RecallQuery:
    base = {
        "query": query_text,
        "track": None,
        "project": None,
        "tags": (),
        "source_type": None,
        "status": "human_approved",
        "include_drafts": False,
        "since": None,
        "until": None,
        "limit": 20,
        "output_format": "compact",
        "explain": False,
        "ranking": "bm25",
        "weight_bm25": None,
        "weight_value_score": None,
        "weight_review_due": None,
    }
    base.update(overrides)
    return RecallQuery(**base)


def run_quality_gate(threshold: float = 0.8, verbose: bool = False) -> tuple[bool, str]:
    """运行 recall quality gate，返回 (passed, summary)。

    Args:
        threshold: 最低 recall 率阈值（0.0-1.0），默认 0.8
        verbose: 是否输出详细信息

    Returns:
        (passed, summary_string)
    """
    bm = build_recall_benchmark()

    # 创建临时 workspace
    tmp = tempfile.mkdtemp(prefix="recall_gate_")
    tmp_path = Path(tmp)
    try:
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        golden_results: list[dict] = []
        negative_results: list[dict] = []
        total_expected = 0
        total_hit = 0

        # ——— Golden Queries ———
        for gq in bm.golden_queries:
            result = run_bm25_recall(cfg, _make_query(gq.query_text))
            hit_ids = {hit.id for hit in result.hits}
            expected = set(gq.expected_hit_ids)
            matched = expected & hit_ids
            hit_rate = len(matched) / len(expected) if expected else 1.0

            total_expected += len(expected)
            total_hit += len(matched)

            entry = {
                "query": gq.query_text,
                "expected": len(expected),
                "matched": len(matched),
                "hit_rate": hit_rate,
                "passed": hit_rate >= threshold,
                "missing": sorted(expected - hit_ids),
            }
            golden_results.append(entry)

        # ——— Negative Queries ———
        for nq in bm.negative_queries:
            result = run_bm25_recall(cfg, _make_query(nq.query_text))
            hit_ids = {hit.id for hit in result.hits}
            passed = len(hit_ids) == 0
            entry = {
                "query": nq.query_text,
                "hits": len(hit_ids),
                "passed": passed,
                "reason": nq.reason,
                "actual_hits": sorted(hit_ids) if not passed else [],
            }
            negative_results.append(entry)

        # ——— Summary ———
        overall_recall = total_hit / total_expected if total_expected > 0 else 1.0
        golden_passed = sum(1 for r in golden_results if r["passed"])
        golden_total = len(golden_results)
        negative_passed = sum(1 for r in negative_results if r["passed"])
        negative_total = len(negative_results)

        gate_passed = overall_recall >= threshold and negative_passed == negative_total

        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("Recall Quality Gate Report")
        lines.append("=" * 60)
        lines.append(f"Threshold: {threshold:.0%}")
        lines.append(f"Golden Queries: {golden_passed}/{golden_total} passed")
        lines.append(f"Negative Queries: {negative_passed}/{negative_total} passed")
        lines.append(f"Overall Recall: {overall_recall:.1%} ({total_hit}/{total_expected} expected hits)")
        lines.append(f"Gate: {'PASSED' if gate_passed else 'FAILED'}")
        lines.append("")

        if verbose or not gate_passed:
            # ——— Failed Golden Queries ———
            failed_golden = [r for r in golden_results if not r["passed"]]
            if failed_golden:
                lines.append("--- Failed Golden Queries ---")
                for r in failed_golden:
                    lines.append(
                        f"  '{r['query']}': {r['matched']}/{r['expected']} "
                        f"({r['hit_rate']:.0%}), missing={r['missing']}"
                    )
                lines.append("")

            # ——— Failed Negative Queries ———
            failed_negative = [r for r in negative_results if not r["passed"]]
            if failed_negative:
                lines.append("--- Failed Negative Queries ---")
                for r in failed_negative:
                    lines.append(
                        f"  '{r['query']}': {r['hits']} unexpected hits "
                        f"({r['actual_hits']}), reason={r['reason']}"
                    )
                lines.append("")

        # ——— Per-Query Detail (verbose only) ———
        if verbose:
            lines.append("--- Per-Query Detail ---")
            for r in golden_results:
                status = "PASS" if r["passed"] else "FAIL"
                lines.append(
                    f"  [{status}] '{r['query']}': "
                    f"{r['matched']}/{r['expected']} ({r['hit_rate']:.0%})"
                )
            for r in negative_results:
                status = "PASS" if r["passed"] else "FAIL"
                lines.append(
                    f"  [{status}] NEG '{r['query']}': "
                    f"{r['hits']} hits, reason={r['reason']}"
                )

        summary = "\n".join(lines)
        return gate_passed, summary

    finally:
        # 清理临时文件
        import shutil
        shutil.rmtree(tmp_path, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description="Recall Quality Gate — BM25 词法检索质量验证"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.8,
        help="最低 recall 率阈值 (0.0-1.0)，默认 0.8",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="输出每个 query 的详细信息",
    )
    args = parser.parse_args()

    if not 0.0 <= args.threshold <= 1.0:
        print(f"ERROR: threshold must be between 0.0 and 1.0, got {args.threshold}", file=sys.stderr)
        sys.exit(2)

    passed, summary = run_quality_gate(threshold=args.threshold, verbose=args.verbose)
    print(summary)

    if passed:
        print("\nAll recall quality checks passed.", file=sys.stderr)
        sys.exit(0)
    else:
        print("\nRecall quality gate FAILED. See details above.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
