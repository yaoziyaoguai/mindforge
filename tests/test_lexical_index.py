"""v2.2 Lexical Index tests — tokenization, BM25 correctness, field weighting.

中文学习型说明：测试 BM25 词法检索的核心行为 —— 分词、索引构建、
字段权重、搜索排序、停用词过滤。所有测试使用合成数据，不调用 LLM。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mindforge.lexical_index import (
    tokenize,
    build_index,
    search,
    resolve_field_weights,
    DEFAULT_FIELD_WEIGHTS,
    SearchHit,
)
from mindforge.cards import CardSummary


# ──────────────────────────────────────────────
# Test fixtures
# ──────────────────────────────────────────────

def _make_card(
    id: str = "c1",
    title: str = "Test Card",
    body: str = "",
    *,
    tags: tuple[str, ...] = (),
    track: str | None = None,
    projects: tuple[str, ...] = (),
    source_type: str | None = None,
    source_title: str | None = None,
    status: str = "human_approved",
) -> CardSummary:
    """创建合成 CardSummary 用于索引测试。"""
    path = Path(f"/fake/vault/cards/{id}.md")
    return CardSummary(
        path=path,
        rel_path=f"cards/{id}.md",
        id=id,
        title=title,
        status=status,
        track=track,
        projects=list(projects),
        tags=list(tags),
        source_type=source_type,
        source_title=source_title,
        principles=[],
        known_risks=[],
        created_at=datetime(2025, 1, 1),
    )


# ──────────────────────────────────────────────
# v2.2 Tokenization enhancement tests
# ──────────────────────────────────────────────

class TestTokenization:
    """v2.2 增强的分词器测试。"""

    def test_basic_ascii_tokenization(self):
        """ASCII 单词正常分词。"""
        tokens = tokenize("hello world")
        assert "hello" in tokens
        assert "world" in tokens

    def test_lowercasing(self):
        """ASCII 单词转为小写。"""
        tokens = tokenize("Hello WORLD")
        assert "hello" in tokens
        assert "world" in tokens
        assert "Hello" not in tokens
        assert "WORLD" not in tokens

    def test_cjk_char_by_char(self):
        """中文逐字切分。"""
        tokens = tokenize("知识图谱")
        assert "知" in tokens
        assert "识" in tokens
        assert "图" in tokens
        assert "谱" in tokens

    def test_empty_text(self):
        """空字符串 → 空 token 列表。"""
        assert tokenize("") == []

    def test_stopword_filtering_default_on(self):
        """默认过滤英文停用词。"""
        tokens = tokenize("the quick brown fox")
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens
        assert "the" not in tokens

    def test_stopword_filtering_can_disable(self):
        """可以关闭停用词过滤。"""
        tokens = tokenize("the quick brown fox", filter_stopwords=False)
        assert "the" in tokens

    def test_non_stopword_preserved(self):
        """非停用词的正确保留。"""
        tokens = tokenize("knowledge graph database")
        assert "knowledge" in tokens
        assert "graph" in tokens
        assert "database" in tokens

    def test_mixed_cjk_and_ascii(self):
        """混合文本：中文逐字 + ASCII 单词。"""
        tokens = tokenize("AI 人工智能 is great")
        assert "ai" in tokens
        assert "great" in tokens
        assert "人" in tokens
        assert "工" in tokens
        assert "is" not in tokens  # stop word

    def test_numbers_preserved(self):
        """数字不被过滤。"""
        tokens = tokenize("model v2 test123")
        assert "v2" in tokens
        assert "test123" in tokens

    def test_stopword_determinism(self):
        """相同输入 → 相同输出（确定性验证）。"""
        t1 = tokenize("the quick brown fox jumps over the lazy dog")
        t2 = tokenize("the quick brown fox jumps over the lazy dog")
        assert t1 == t2

    def test_common_english_stopwords(self):
        """常见停用词表验证（spot check）。"""
        stopwords_to_test = [
            "the", "and", "is", "are", "was", "were",
            "a", "an", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "not", "no",
        ]
        for sw in stopwords_to_test:
            tokens = tokenize(sw)
            assert sw not in tokens, f"'{sw}' should be filtered as stop word"


# ──────────────────────────────────────────────
# Field weighting tests
# ──────────────────────────────────────────────

class TestFieldWeights:
    """v2.2 字段权重解析测试（U3）。"""

    def test_default_weights_include_title_higher_than_body(self):
        """title 权重应高于 body_summary（设计意图）。"""
        assert DEFAULT_FIELD_WEIGHTS["title"] > DEFAULT_FIELD_WEIGHTS["body_summary"]
        assert DEFAULT_FIELD_WEIGHTS["title"] >= 5.0

    def test_resolve_empty_user_fields_returns_defaults(self):
        """空用户配置 → 返回完整默认权重。"""
        resolved = resolve_field_weights(None)
        assert resolved == DEFAULT_FIELD_WEIGHTS
        resolved2 = resolve_field_weights({})
        assert resolved2 == DEFAULT_FIELD_WEIGHTS

    def test_resolve_overrides_single_field(self):
        """用户覆盖单个字段权重。"""
        resolved = resolve_field_weights({"title": 10.0})
        assert resolved["title"] == 10.0
        # 其他字段保持默认
        assert resolved["body_summary"] == DEFAULT_FIELD_WEIGHTS["body_summary"]

    def test_resolve_zero_weight_removes_field(self):
        """权重为 0 → 从结果中移除该字段。"""
        resolved = resolve_field_weights({"tags": 0.0})
        assert "tags" not in resolved
        assert "title" in resolved

    def test_resolve_unknown_alias_ignored(self):
        """未知别名被静默忽略。"""
        resolved = resolve_field_weights({"nonexistent_field": 5.0})
        assert "nonexistent_field" not in resolved

    def test_resolve_user_alias_mapping(self):
        """用户友好别名正确映射到内部字段名。"""
        resolved = resolve_field_weights({"learning_tracks": 8.0})
        assert resolved["track"] == 8.0


# ──────────────────────────────────────────────
# BM25 index building tests
# ──────────────────────────────────────────────

class TestBM25Index:
    """BM25 索引构建和行为测试。"""

    def test_build_index_empty_cards(self):
        """空卡片列表 → 空索引。"""
        index = build_index([])
        assert index.avgdl == 0.0
        assert len(index.docs) == 0

    def test_build_index_single_card(self):
        """单张卡片 → 索引包含 1 个 doc。"""
        card = _make_card(title="Test Knowledge Card")
        index = build_index([card])
        assert len(index.docs) == 1
        assert index.docs[0].title == "Test Knowledge Card"

    def test_index_fields_contain_tokens(self):
        """索引字段应包含正确的 token。"""
        card = _make_card(title="Machine Learning Basics", tags=("ai", "ml"))
        index = build_index([card])
        doc = index.docs[0]
        assert "title" in doc.fields
        # tokens should be lowercase
        assert "machine" in doc.fields["title"]

    def test_search_returns_scored_hits(self):
        """搜索返回排序后的命中列表。"""
        cards = [
            _make_card(id="c1", title="Machine Learning"),
            _make_card(id="c2", title="Deep Learning with Python"),
            _make_card(id="c3", title="Database Design"),
        ]
        index = build_index(cards)
        hits = search(index, "learning")
        assert len(hits) >= 2  # c1 and c2 should match
        for h in hits:
            assert isinstance(h, SearchHit)
            assert h.score > 0

    def test_search_no_match(self):
        """搜索不匹配的词 → 空结果。"""
        cards = [_make_card(title="Python Programming")]
        index = build_index(cards)
        hits = search(index, "zzzxxxxnotexist")
        assert hits == []

    def test_search_filter_by_status(self):
        """filter 应排除非目标状态的卡片。"""
        cards = [
            _make_card(id="c1", title="Card A", status="human_approved"),
            _make_card(id="c2", title="Card B", status="ai_draft"),
        ]
        index = build_index(cards)
        hits = search(index, "card", status_filter="human_approved")
        result_ids = {h.doc.id for h in hits}
        assert "c1" in result_ids
        assert "c2" not in result_ids

    def test_index_determinism(self):
        """相同输入 → 相同索引（确定性验证）。"""
        cards = [
            _make_card(id="c1", title="Test Card", tags=("ai",)),
            _make_card(id="c2", title="Another Card", tags=("ml",)),
        ]
        index1 = build_index(cards)
        index2 = build_index(cards)
        assert index1.avgdl == index2.avgdl
        assert len(index1.docs) == len(index2.docs)
        assert index1.config_hash == index2.config_hash

    def test_search_score_ordering(self):
        """搜索结果的分数应降序排列。"""
        cards = [
            _make_card(id="c1", title="Python Machine Learning Guide"),
            _make_card(id="c2", title="Python Basics"),
            _make_card(id="c3", title="Unrelated Topic"),
        ]
        index = build_index(cards)
        hits = search(index, "python learning")
        scores = [h.score for h in hits]
        assert scores == sorted(scores, reverse=True), "Scores应降序排列"

    def test_field_hits_included(self):
        """SearchHit 应包含 field_hits。"""
        cards = [_make_card(title="Python Guide", tags=("python",))]
        index = build_index(cards)
        hits = search(index, "python")
        assert len(hits) > 0
        assert len(hits[0].field_hits) > 0

    def test_search_tokenized_query(self):
        """查询文本被分词后搜索。"""
        cards = [_make_card(title="The Quick Brown Fox")]  # "the" 被过滤
        index = build_index(cards)
        hits = search(index, "Brown Fox")
        assert len(hits) == 1
