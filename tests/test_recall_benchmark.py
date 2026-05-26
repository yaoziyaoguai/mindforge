"""v4.9 — BM25 Recall 质量基准测试。

验证 golden recall fixtures 的完整性，并使用实际 BM25 引擎验证
每个 golden query 的预期命中率和每个 negative query 的 0 hits 预期。

中文学习型说明：这些测试建立了 recall 质量的可复现测量基线。
当 BM25 参数或 tokenizer 变更时，这些测试会立即检测到 recall 退化。
这是 Direction C (Recall/Search Quality Lab) 的核心基础设施。
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from mindforge.config import load_mindforge_config
from mindforge.recall_service import RecallQuery, run_bm25_recall
from tests.fixtures.recall_benchmark import (
    GoldenCard,
    build_recall_benchmark,
)


# ---------------------------------------------------------------------------
# Helpers — 从 GoldenCard 创建真实的卡片文件
# ---------------------------------------------------------------------------


def _write_golden_card(cards_dir: Path, card: GoldenCard) -> None:
    """将 GoldenCard 写入 Knowledge-Cards 目录下的 .md 文件。

    生成标准的 MindForge frontmatter + body 格式，使 BM25 索引能
    正确读取 title/tags/body_sections 等字段。
    """
    fm: dict = {
        "id": card.card_id,
        "title": card.title,
        "status": card.status,
        "tags": list(card.tags),
    }
    if card.track:
        fm["track"] = card.track
    if card.projects:
        fm["projects"] = list(card.projects)
    if card.source_type:
        fm["source_type"] = card.source_type
    if card.source_title:
        fm["source_title"] = card.source_title
    if card.value_score is not None:
        fm["value_score"] = card.value_score

    front = "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}"
        for key, value in fm.items()
    )

    body_parts: list[str] = []
    for section_title, section_content in card.body_sections:
        body_parts.append(f"## {section_title}\n{section_content}\n")

    body = "\n".join(body_parts) if body_parts else "[fake] placeholder body"

    (cards_dir / f"{card.card_id}.md").write_text(
        f"---\n{front}\n---\n\n{body}\n", encoding="utf-8"
    )


def _make_benchmark_config(tmp_path: Path, cards: tuple[GoldenCard, ...]) -> Path:
    """创建隔离的 dogfood 配置和卡片文件，返回 config 文件路径。"""
    vault = tmp_path / "vault"
    cards_dir = vault / "20-Knowledge-Cards"
    inbox_dir = vault / "00-Inbox"
    cards_dir.mkdir(parents=True)
    inbox_dir.mkdir(parents=True)

    for card in cards:
        _write_golden_card(cards_dir, card)

    cfg = {
        "version": 0.7,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {"enabled": [], "registry": {}},
        "state": {
            "workdir": str(tmp_path / ".mindforge"),
            "state_file": "state.json",
            "runs_dir": "runs",
            "index_file": "index.jsonl",
            "backup_state": True,
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {
                "fake": {
                    "triage": "fake_alias",
                    "distill": "fake_alias",
                    "link_suggestion": "fake_alias",
                    "review_questions": "fake_alias",
                    "action_extraction": "fake_alias",
                }
            },
            "models": {
                "fake_alias": {"provider": "fake", "type": "fake", "model": "fake"}
            },
        },
        "prompts": {
            "triage_version": "v1",
            "distill_version": "v1",
            "link_suggestion_version": "v1",
            "review_questions_version": "v1",
            "action_extraction_version": "v1",
        },
        "logging": {"level": "INFO", "file": str(tmp_path / "mf.log")},
    }
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(
        yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return cfg_path


def _make_query(query_text: str, **overrides) -> RecallQuery:
    """构造 RecallQuery，默认 bm25 模式 + human_approved filter。"""
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


# ---------------------------------------------------------------------------
# Fixture 完整性测试
# ---------------------------------------------------------------------------


class TestRecallBenchmarkFixture:
    """验证 golden recall benchmark fixture 的结构完整性。"""

    def test_cards_not_empty(self):
        bm = build_recall_benchmark()
        assert len(bm.cards) == 12, f"应有 12 张 golden cards，实际 {len(bm.cards)}"

    def test_all_card_ids_unique(self):
        bm = build_recall_benchmark()
        ids = [c.card_id for c in bm.cards]
        assert len(ids) == len(set(ids)), f"card_id 重复: {ids}"

    def test_all_cards_have_title_and_body(self):
        bm = build_recall_benchmark()
        for card in bm.cards:
            assert card.title, f"{card.card_id} 缺少 title"
            assert card.body_sections, f"{card.card_id} 缺少 body_sections"

    def test_golden_queries_not_empty(self):
        bm = build_recall_benchmark()
        assert len(bm.golden_queries) >= 10, (
            f"至少需要 10 个 golden queries，实际 {len(bm.golden_queries)}"
        )

    def test_expected_hits_reference_valid_cards(self):
        bm = build_recall_benchmark()
        card_ids = {c.card_id for c in bm.cards}
        for gq in bm.golden_queries:
            for hit_id in gq.expected_hit_ids:
                assert hit_id in card_ids, (
                    f"query '{gq.query_text}' 的 expected_hit_id '{hit_id}' "
                    f"不在 golden cards 中"
                )

    def test_negative_queries_exist(self):
        bm = build_recall_benchmark()
        assert len(bm.negative_queries) >= 4, (
            f"至少需要 4 个 negative queries，实际 {len(bm.negative_queries)}"
        )

    def test_negative_queries_have_reason(self):
        bm = build_recall_benchmark()
        for nq in bm.negative_queries:
            assert nq.reason, f"negative query '{nq.query_text}' 缺少 reason"

    def test_covers_english_queries(self):
        bm = build_recall_benchmark()
        en_queries = [
            gq for gq in bm.golden_queries
            if all(ord(c) < 128 for c in gq.query_text.replace(" ", ""))
        ]
        assert len(en_queries) >= 5, f"至少需要 5 个英文查询，实际 {len(en_queries)}"

    def test_covers_cjk_queries(self):
        bm = build_recall_benchmark()
        cjk_queries = [
            gq for gq in bm.golden_queries
            if any(ord(c) > 127 for c in gq.query_text)
        ]
        assert len(cjk_queries) >= 3, f"至少需要 3 个中文查询，实际 {len(cjk_queries)}"

    def test_covers_multi_word_queries(self):
        bm = build_recall_benchmark()
        multi_word = [gq for gq in bm.golden_queries if len(gq.query_text.split()) >= 3]
        assert len(multi_word) >= 2, f"至少需要 2 个多词查询，实际 {len(multi_word)}"


# ---------------------------------------------------------------------------
# BM25 召回质量测试 — 核心回归保护
# ---------------------------------------------------------------------------


class TestRecallGoldenQueries:
    """使用实际 BM25 引擎验证 golden queries 的召回质量。

    这些测试是 recall quality gate 的核心：如果 BM25 参数或 tokenizer
    变更导致 recall 退化，这些测试会立即失败。
    """

    def test_single_keyword_architecture(self, tmp_path: Path):
        """查询 'architecture' 应至少命中 arch-001 和 arch-002。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("architecture"))

        hit_ids = {hit.id for hit in result.hits}
        assert "arch-001" in hit_ids, (
            f"'architecture' 应命中 arch-001，实际 hits: {hit_ids}"
        )
        assert "arch-002" in hit_ids, (
            f"'architecture' 应命中 arch-002，实际 hits: {hit_ids}"
        )

    def test_single_keyword_security(self, tmp_path: Path):
        """查询 'security' 应至少命中 sec-001 和 sec-002。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("security"))

        hit_ids = {hit.id for hit in result.hits}
        assert "sec-001" in hit_ids, (
            f"'security' 应命中 sec-001，实际 hits: {hit_ids}"
        )
        assert "sec-002" in hit_ids, (
            f"'security' 应命中 sec-002，实际 hits: {hit_ids}"
        )

    def test_single_keyword_dogfood(self, tmp_path: Path):
        """查询 'dogfood' 应至少命中 dogfood-001 和 dogfood-002。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("dogfood"))

        hit_ids = {hit.id for hit in result.hits}
        assert "dogfood-001" in hit_ids, (
            f"'dogfood' 应命中 dogfood-001，实际 hits: {hit_ids}"
        )
        assert "dogfood-002" in hit_ids, (
            f"'dogfood' 应命中 dogfood-002，实际 hits: {hit_ids}"
        )

    def test_multi_word_python_async_testing(self, tmp_path: Path):
        """查询 'python async testing' 应至少命中 test-002。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("python async testing"))

        hit_ids = {hit.id for hit in result.hits}
        assert "test-002" in hit_ids, (
            f"'python async testing' 应命中 test-002，实际 hits: {hit_ids}"
        )

    def test_multi_word_bm25_retrieval_recall(self, tmp_path: Path):
        """查询 'BM25 retrieval recall' 应至少命中 test-001。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("BM25 retrieval recall"))

        hit_ids = {hit.id for hit in result.hits}
        assert "test-001" in hit_ids, (
            f"'BM25 retrieval recall' 应命中 test-001，实际 hits: {hit_ids}"
        )

    def test_cjk_architecture(self, tmp_path: Path):
        """查询 '架构设计' 应至少命中 arch-001。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("架构设计"))

        hit_ids = {hit.id for hit in result.hits}
        assert "arch-001" in hit_ids, (
            f"'架构设计' 应命中 arch-001，实际 hits: {hit_ids}"
        )

    def test_cjk_security_boundary(self, tmp_path: Path):
        """查询 '安全边界' 应至少命中 sec-001。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("安全边界"))

        hit_ids = {hit.id for hit in result.hits}
        assert "sec-001" in hit_ids, (
            f"'安全边界' 应命中 sec-001，实际 hits: {hit_ids}"
        )

    def test_cjk_knowledge_quality(self, tmp_path: Path):
        """查询 '知识卡片质量' 应至少命中 cn-001。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("知识卡片质量"))

        hit_ids = {hit.id for hit in result.hits}
        assert "cn-001" in hit_ids, (
            f"'知识卡片质量' 应命中 cn-001，实际 hits: {hit_ids}"
        )

    def test_cjk_chinese_retrieval(self, tmp_path: Path):
        """查询 '中文检索' 应至少命中 cn-002。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("中文检索"))

        hit_ids = {hit.id for hit in result.hits}
        assert "cn-002" in hit_ids, (
            f"'中文检索' 应命中 cn-002，实际 hits: {hit_ids}"
        )

    def test_exact_title_match(self, tmp_path: Path):
        """精确 title 匹配 'MindForge 安全边界设计' 应命中 sec-001（title 权重最高）。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("MindForge 安全边界设计"))

        hit_ids = {hit.id for hit in result.hits}
        assert "sec-001" in hit_ids, (
            f"精确 title 应命中 sec-001，实际 hits: {hit_ids}"
        )


class TestRecallNegativeQueries:
    """验证 negative queries（预期 0 hits 的查询）确实返回 0 hits。"""

    def test_ml_query_no_hits(self, tmp_path: Path):
        """查询 'machine learning' 不应命中任何 golden card。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("machine learning neural network"))

        hit_ids = {hit.id for hit in result.hits}
        assert len(hit_ids) == 0, (
            f"'machine learning' 预期 0 hits，实际命中: {hit_ids}"
        )

    def test_blockchain_query_no_hits(self, tmp_path: Path):
        """查询 'blockchain' 不应命中任何 golden card。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("blockchain cryptocurrency"))

        hit_ids = {hit.id for hit in result.hits}
        assert len(hit_ids) == 0, (
            f"'blockchain' 预期 0 hits，实际命中: {hit_ids}"
        )

    def test_cjk_character_tokenization_limitation(self, tmp_path: Path):
        """记录 CJK 字符级 tokenization 的已知限制。

        中文学习型说明：当前 BM25 tokenizer 将中文字符拆分为单个字符
        （如 "架构"→["架","构"]），导致任意中文查询都能匹配几乎所有含中文
        的卡片。这使得 negative CJK queries 不可行——无法构造一个"绝对不匹配"
        的中文查询。

        此测试验证该限制仍然存在，作为未来引入 jieba 分词或 bigram 索引的
        需求证据。
        """
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        # 任意中文查询都会命中多张卡片（字符级匹配）
        result = run_bm25_recall(cfg, _make_query("量子计算"))

        hit_ids = {hit.id for hit in result.hits}
        # 当前预期：字符级 tokenization 导致命中 > 0
        assert len(hit_ids) > 0, (
            "CJK 字符级 tokenization 限制：任意中文查询应至少命中一些卡片。"
            "如果此断言失败（0 hits），说明 tokenizer 行为已变更，需更新此测试。"
        )

        # 但命中的卡片不应包含高相关性匹配——所有命中应来自字符级巧合
        for hit in result.hits:
            # title 字段权重 5.0，单字符命中 title 可产生 ~4.0 的 score。
            # 阈值 5.5 留有安全余量，同时确保未引入真正的语义匹配。
            assert hit.score < 5.5, (
                f"CJK 字符级查询 '{hit.id}' 的 score={hit.score:.3f} 不应过高，"
                f"确认未引入语义匹配。如果引入 jieba 分词，需调整此阈值。"
            )

    def test_quantum_query_no_hits(self, tmp_path: Path):
        """查询 'quantum computing' 不应命中任何 golden card。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("quantum computing schrodinger"))

        hit_ids = {hit.id for hit in result.hits}
        assert len(hit_ids) == 0, (
            f"'quantum computing' 预期 0 hits，实际命中: {hit_ids}"
        )

    def test_kubernetes_query_no_hits(self, tmp_path: Path):
        """查询 'kubernetes docker' 不应命中任何 golden card。"""
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        result = run_bm25_recall(cfg, _make_query("kubernetes docker container orchestration"))

        hit_ids = {hit.id for hit in result.hits}
        assert len(hit_ids) == 0, (
            f"'kubernetes docker' 预期 0 hits，实际命中: {hit_ids}"
        )


class TestRecallBenchmarkRegression:
    """recall 质量回归保护 — 确保 benchmark 自身稳定。"""

    def test_all_golden_queries_have_minimum_recall(self, tmp_path: Path):
        """全部 golden queries 的 recall 率应 ≥ 70%（至少 expected_hits 的 70% 命中）。

        这是最重要的回归测试。如果此测试失败，说明 BM25 配置变更导致了
        recall 退化，需要调查根因后再调整 expected_hit_ids。
        """
        bm = build_recall_benchmark()
        cfg_path = _make_benchmark_config(tmp_path, bm.cards)
        cfg = load_mindforge_config(cfg_path)

        failed_queries: list[str] = []
        total_expected = 0
        total_hit = 0

        for gq in bm.golden_queries:
            result = run_bm25_recall(cfg, _make_query(gq.query_text))
            hit_ids = {hit.id for hit in result.hits}
            expected = set(gq.expected_hit_ids)
            matched = expected & hit_ids
            hit_rate = len(matched) / len(expected) if expected else 1.0

            total_expected += len(expected)
            total_hit += len(matched)

            if hit_rate < 0.7:
                missing = expected - hit_ids
                failed_queries.append(
                    f"  '{gq.query_text}': {len(matched)}/{len(expected)} hit, "
                    f"missing={missing}, actual_hits={hit_ids}"
                )

        overall_recall = total_hit / total_expected if total_expected > 0 else 1.0

        assert len(failed_queries) == 0, (
            "以下 golden queries 未达 70% recall 阈值:\n"
            + "\n".join(failed_queries)
        )

        assert overall_recall >= 0.7, (
            f"总体 recall {overall_recall:.1%} < 70%，"
            f" {total_hit}/{total_expected} expected hits 命中"
        )

    def test_recall_benchmark_stable_across_runs(self, tmp_path: Path):
        """同一 benchmark 连续运行 3 次应得到相同结果（确定性验证）。"""
        bm = build_recall_benchmark()

        results: list[dict[str, set[str]]] = []
        for _ in range(3):
            # 每次创建新的临时目录，避免磁盘索引缓存干扰
            import tempfile
            run_tmp = tempfile.mkdtemp()
            run_path = Path(run_tmp)
            cfg_path = _make_benchmark_config(run_path, bm.cards)
            cfg = load_mindforge_config(cfg_path)

            run_hits: dict[str, set[str]] = {}
            for gq in bm.golden_queries:
                result = run_bm25_recall(cfg, _make_query(gq.query_text))
                run_hits[gq.query_text] = {hit.id for hit in result.hits}
            results.append(run_hits)

        # 验证所有 run 的 hit_ids 集合一致
        for gq in bm.golden_queries:
            first_hits = results[0][gq.query_text]
            for i, run_result in enumerate(results[1:], start=2):
                assert run_result[gq.query_text] == first_hits, (
                    f"query '{gq.query_text}' 在 run 1 和 run {i} 之间结果不一致: "
                    f"{first_hits} vs {run_result[gq.query_text]}"
                )
