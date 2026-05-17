# TDD: Knowledge Quality & Navigation — Test Strategy

> **Status**: Draft
> **Date**: 2026-05-17
> **Depends on**: [RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md](../rfc/RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md), [SDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md](../sdd/SDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)
> **Related**: [V0_3_ROADMAP.md](../roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md)

---

## 1. 概述

v0.3 所有六个 milestone 遵循 TDD 原则：先写 red test（定义期望行为），再实现，再 green。

每个 milestone 有独立的 test 文件和 golden fixture 数据集。测试全部基于确定性规则，不依赖 LLM 调用或外部 API。

---

## 2. M1: Card Quality Tests

### 2.1 Unit Tests

**File**: `tests/quality/test_rubric.py`

```python
class TestQualityRubric:
    """质量评分规则测试"""

    def test_high_quality_card_scores_above_70(self):
        """高质量卡片（完整结构、具体内容、有 source citation）得分 ≥ 70"""
        ...

    def test_low_quality_card_scores_below_40(self):
        """低质量卡片（太短、无结构、无 citation）得分 < 40"""
        ...

    def test_missing_sections_detected(self):
        """缺少 ## Summary / ## Details 章节的卡片被检测"""
        ...

    def test_source_citation_detected(self):
        """有 source_path 的卡片 source_citation 维度得分 > 0"""
        ...

    def test_consistency_fails_on_self_contradiction(self):
        """内容自相矛盾的卡片 consistency 维度得分降低"""
        ...

    def test_all_dimensions_contribute_to_overall(self):
        """所有 5 个维度加权后得到 overall_score"""
        ...
```

**File**: `tests/quality/test_card_type.py`

```python
class TestCardTypeClassification:
    """卡片类型分类测试"""

    def test_fact_classified_by_observation_keywords(self):
        """包含 'observed' / 'measured' 的卡片分类为 fact"""
        ...

    def test_method_classified_by_procedure_keywords(self):
        """包含 'how to' / 'steps to' 的卡片分类为 method"""
        ...

    def test_unclassified_when_no_keywords_match(self):
        """无关键词匹配时返回 None"""
        ...

    def test_strongest_type_wins_on_mixed_keywords(self):
        """多类型关键词共存时选择得分最高的"""
        ...
```

**File**: `tests/quality/test_warnings.py`

```python
class TestQualityWarnings:
    """质量警告测试"""

    def test_too_short_warning_on_body_under_100_chars(self):
        """body < 100 chars → too_short warning"""
        ...

    def test_missing_sections_warning_on_no_h2_markers(self):
        """body 中无 ## 标记 → missing_sections warning"""
        ...

    def test_no_source_citation_warning(self):
        """card 无 source_id → no_source_citation warning"""
        ...

    def test_vague_language_warning(self):
        """高 vague term 比例 → vague_language warning"""
        ...

    def test_possible_duplicate_warning(self):
        """title 相似度 > 80% → possible_duplicate warning"""
        ...
```

### 2.2 Golden Fixture

```python
# tests/fixtures/quality_golden.py

GOLDEN_CARDS = {
    "high_quality": {
        "title": "Architecture: Service Layer Pattern",
        "body": """## Summary
The service layer encapsulates business logic between controllers and repositories.

## Details
### Implementation
- Every service class implements a protocol interface
- Services are stateless and injected via dependency injection
- Transaction boundaries are managed at the service level

### Rationale
This pattern was chosen after observing that mixing business logic in controllers led to code duplication across 12 endpoints.

## Source
Derived from source: docs/architecture.md, lines 45-62.""",
        "source_id": "src_001",
        "tags": ("architecture", "design-patterns"),
        "expected_level": "high",
        "expected_score_min": 70,
        "expected_warnings": [],
        "expected_type": "decision",
    },
    "low_quality": {
        "title": "Something about code",
        "body": "Not sure but maybe it works sometimes probably.",
        "source_id": None,
        "tags": (),
        "expected_level": "low",
        "expected_score_max": 40,
        "expected_warnings": ["too_short", "missing_sections", "no_source_citation", "vague_language"],
        "expected_type": None,
    },
    "medium_quality": {
        "title": "Database Migration Steps",
        "body": """## Summary
Steps to migrate the database.

## Details
1. Backup data
2. Run migration script
3. Verify results

something might be missing here""",
        "source_id": "src_002",
        "tags": ("database", "migration"),
        "expected_level": "medium",
        "expected_score_min": 40,
        "expected_score_max": 70,
        "expected_warnings": ["vague_language"],
        "expected_type": "method",
    },
}
```

### 2.3 Integration Tests

**File**: `tests/quality/test_quality_api.py`

```python
class TestQualityAPI:
    def test_get_card_quality_returns_all_fields(self): ...
    def test_rescore_card_updates_quality_metadata(self): ...
    def test_quality_response_matches_schema(self): ...
```

---

## 3. M4: Source Location Tests

### 3.1 Unit Tests

**File**: `tests/provenance/test_location.py`

```python
class TestSourceLocation:
    """各 source_type 的 location 解析测试"""

    def test_markdown_location_parses_heading_and_lines(self):
        """Markdown location: heading_path + line_start/end"""
        loc = SourceLocation(
            source_type="plain_markdown",
            heading_path=("Architecture", "Authentication"),
            line_start=45,
            line_end=62,
        )
        assert "Architecture > Authentication, lines 45-62" in loc.to_display()

    def test_txt_location_parses_line_range(self):
        """TXT location: line_start/end only"""
        loc = SourceLocation(
            source_type="txt",
            line_start=120,
            line_end=145,
        )
        assert "Lines 120-145" in loc.to_display()

    def test_pdf_location_parses_page_number(self):
        """PDF location: page_number"""
        loc = SourceLocation(
            source_type="pdf",
            page_number=12,
        )
        assert "Page 12" in loc.to_display()

    def test_docx_location_parses_paragraph_range(self):
        """DOCX location: paragraph_start/end"""
        loc = SourceLocation(
            source_type="docx",
            paragraph_start=8,
            paragraph_end=12,
        )
        assert "Paragraphs 8-12" in loc.to_display()

    def test_html_location_parses_selector(self):
        """HTML location: heading_path + css_selector"""
        loc = SourceLocation(
            source_type="html",
            heading_path=("Overview",),
            css_selector="h2#overview > p:nth-child(3)",
        )
        display = loc.to_display()
        assert "Overview" in display

    def test_location_none_fields_omitted_from_display(self):
        """未设置的字段不在 display 中出现"""
        loc = SourceLocation(source_type="pdf")
        # 不应崩溃
        assert loc.to_display()
```

### 3.2 Golden Fixtures

```python
# tests/fixtures/location_golden.py

LOCATION_FIXTURES = {
    "markdown": ({"source_type": "plain_markdown", "heading_path": ("Intro",), "line_start": 1, "line_end": 10}, "§ Intro, lines 1-10"),
    "txt": ({"source_type": "txt", "line_start": 5, "line_end": 20}, "Lines 5-20"),
    "html": ({"source_type": "html", "css_selector": "div.content > p:first-child"}, "div.content > p:first-child"),
    "pdf": ({"source_type": "pdf", "page_number": 3}, "Page 3"),
    "docx": ({"source_type": "docx", "paragraph_start": 1, "paragraph_end": 5}, "Paragraphs 1-5"),
}
```

---

## 4. M2: Wiki Quality Tests

### 4.1 Unit Tests

**File**: `tests/wiki/test_wiki_quality.py`

```python
class TestWikiCoverage:
    """Wiki coverage 计算测试"""

    def test_all_approved_cards_used_gives_full_coverage(self):
        """10 approved cards, 10 used → coverage_rate = 1.0"""
        ...

    def test_unused_cards_listed_with_reasons(self):
        """8 used, 2 unused → unused_cards 列出原因"""
        ...

    def test_coverage_report_matches_fixture(self, wiki_fixture):
        """Golden fixture: 10 cards, 8 used, 2 unused → 验证报告"""
        ...

class TestFaithfulness:
    """Faithfulness 检查测试"""

    def test_high_overlap_section_is_faithful(self):
        """section 内容与引用 card 高度重叠 → faithful"""
        ...

    def test_low_overlap_section_flagged(self):
        """section 内容与引用 card 几乎不重叠 → flagged"""
        ...

    def test_false_positive_rate_under_30_percent(self, wiki_fixture):
        """Golden fixture 上假阳性率 < 30%"""
        ...

class TestStaleness:
    """Staleness 检测测试"""

    def test_new_card_matching_section_topic_marks_stale(self):
        """新 approved card 的 topic 匹配已有 section → section 标记 stale"""
        ...

    def test_card_updated_after_wiki_rebuild_marks_stale(self):
        """card updated_at > wiki rebuild time → 标记 stale"""
        ...

class TestConflictingClaims:
    """冲突声明检测测试"""

    def test_opposite_claims_same_topic_detected(self):
        """同一 topic 的矛盾声明被检测"""
        card_a = MagicMock(title="Exercise increases productivity", tags=["productivity"])
        card_b = MagicMock(title="Exercise decreases productivity", tags=["productivity"])
        conflicts = detect_conflicting_claims(card_a, card_b)
        assert len(conflicts) == 1

    def test_same_direction_claims_not_detected(self):
        """同向声明不标记为冲突"""
        card_a = MagicMock(title="Exercise increases productivity", tags=["productivity"])
        card_b = MagicMock(title="Exercise also increases focus", tags=["productivity"])
        conflicts = detect_conflicting_claims(card_a, card_b)
        assert len(conflicts) == 0
```

### 4.2 Golden Fixture

```python
# tests/fixtures/wiki_quality_fixture.py

WIKI_QUALITY_FIXTURE = {
    "approved_cards": [
        {"id": "c1", "title": "Auth Pattern", "body": "...", "tags": ["auth"]},
        {"id": "c2", "title": "DB Migration", "body": "...", "tags": ["database"]},
        {"id": "c3", "title": "API Design", "body": "...", "tags": ["api"]},
        {"id": "c4", "title": "Short note", "body": "just a sentence", "tags": []},
        {"id": "c5", "title": "Duplicate title", "body": "...", "tags": ["auth"]},
        # ... 5 more
    ],
    "wiki_sections": [
        {"title": "Authentication", "card_ids": ["c1", "c5"]},
        {"title": "Database", "card_ids": ["c2"]},
        {"title": "API Layer", "card_ids": ["c3"]},
    ],
    "expected_used": 5,       # c1, c2, c3, c5, ...
    "expected_unused": 2,     # c4, ...
    "expected_stale": [],
    "expected_conflicts": [],
}
```

---

## 5. M3: Related Cards Tests

### 5.1 Unit Tests

**File**: `tests/relations/test_related_cards.py`

```python
class TestRelatedCards:
    """Related cards 关系计算测试"""

    def test_same_source_cards_are_related(self, card_fixture):
        """共享 source_id 的卡片被关联"""
        ...

    def test_same_tag_cards_are_related(self, card_fixture):
        """共享 ≥1 tag 的卡片被关联"""
        ...

    def test_same_wiki_section_cards_are_related(self, card_fixture):
        """同 Wiki section 的卡片被关联"""
        ...

    def test_related_cards_have_correct_reason(self):
        """每条关系边 reason 正确"""
        ...

    def test_library_context_only_returns_approved(self):
        """Library 上下文仅返回 human_approved"""
        ...

    def test_related_cards_sorted_by_strength_desc(self):
        """关系按 strength 降序排列"""
        ...

    def test_max_5_per_reason_type(self):
        """每种 reason 最多 5 条"""
        ...

    def test_performance_under_500ms_for_1000_cards(self, large_fixture):
        """1000 cards 时计算时间 < 500ms"""
        ...
```

### 5.2 Golden Fixture

```python
# tests/fixtures/relations_golden.py

RELATIONS_FIXTURE = {
    "cards": [
        {"id": "c1", "source_id": "src_1", "tags": ["auth", "security"], "wiki_sections": ["Authentication"]},
        {"id": "c2", "source_id": "src_1", "tags": ["auth"], "wiki_sections": ["Authentication"]},
        {"id": "c3", "source_id": "src_2", "tags": ["database"], "wiki_sections": ["Database"]},
        {"id": "c4", "source_id": "src_2", "tags": ["database", "migration"], "wiki_sections": ["Database"]},
        {"id": "c5", "source_id": "src_3", "tags": ["api"], "wiki_sections": ["API Layer"]},
    ],
    "query_card": "c1",
    "expected_relations": [
        {"target": "c2", "reasons": ["same_source", "same_tag", "same_wiki_section"]},
    ],
    "expected_no_relation": ["c5"],  # c5 与 c1 无共享属性
}
```

---

## 6. M5: Knowledge Health Tests

### 6.1 Unit Tests

**File**: `tests/health/test_health_service.py`

```python
class TestHealthReport:
    """健康报告测试"""

    def test_review_backlog_detected(self, vault_with_pending_drafts):
        """pending drafts > threshold → review_backlog issue"""
        ...

    def test_orphan_cards_detected(self, vault_with_orphans):
        """无 related cards 且无 wiki reference → orphan issue"""
        ...

    def test_low_quality_cards_detected(self, vault_with_low_quality):
        """quality=low 的卡片数 → low_quality issue"""
        ...

    def test_duplicates_detected(self, vault_with_duplicates):
        """potential duplicate pairs → duplicates issue"""
        ...

    def test_wiki_stale_sections_detected(self, vault_with_stale_wiki):
        """stale Wiki sections → wiki_stale issue"""
        ...

    def test_each_issue_has_severity_and_suggested_action(self):
        """每个 issue 有 severity + reason + suggested_action"""
        ...

    def test_no_auto_mutation(self, vault_with_issues):
        """health report 不自动修改任何卡片"""
        original_state = snapshot(vault_with_issues)
        compute_health_report(vault_with_issues)
        assert vault_with_issues == original_state

    def test_false_positive_rate_under_20_percent(self, golden_vault):
        """Golden vault 已知 10 issues → 报告应 ≥8 正确 (假阳性 < 20%)"""
        ...

class TestHealthCLI:
    """CLI 测试"""

    def test_health_command_outputs_summary(self): ...
    def test_health_verbose_outputs_full_report(self): ...
    def test_health_json_outputs_valid_json(self): ...
```

### 6.2 Golden Vault Fixture

```python
# tests/fixtures/health_golden.py

HEALTH_GOLDEN_VAULT = {
    "cards": [
        {"id": "c_low_1", "status": "human_approved", "quality_level": "low", "source_id": None, "tags": []},
        {"id": "c_orphan", "status": "human_approved", "quality_level": "medium", "source_id": "src_1", "tags": []},
        {"id": "c_dup_a", "status": "human_approved", "quality_level": "high", "title": "Auth Pattern Guide", "source_id": "src_2", "tags": ["auth"]},
        {"id": "c_dup_b", "status": "human_approved", "quality_level": "high", "title": "Auth Pattern Guidelines", "source_id": "src_3", "tags": ["auth"]},
        {"id": "c_normal", "status": "human_approved", "quality_level": "high", "source_id": "src_4", "tags": ["api"]},
    ],
    "pending_drafts": 3,
    "wiki_stale_sections": ["Authentication"],
    "expected_issues": [
        {"code": "review_backlog"},
        {"code": "orphans", "affected": ["c_orphan"]},
        {"code": "low_quality", "affected": ["c_low_1"]},
        {"code": "duplicates", "affected": ["c_dup_a", "c_dup_b"]},
        {"code": "wiki_stale"},
    ],
}
```

---

## 7. M6: Local Graph Tests

### 7.1 Unit Tests

**File**: `tests/relations/test_graph.py`

```python
class TestLocalGraph:
    """Local graph 构建测试"""

    def test_card_centered_graph_has_1_hop_neighbors(self, graph_fixture):
        """Card-centered graph 包含 1-hop 邻居"""
        ...

    def test_graph_nodes_have_correct_types(self):
        """节点类型: card, source, wiki_section, tag"""
        ...

    def test_graph_edges_have_correct_reasons(self):
        """边 reason 正确"""
        ...

    def test_wiki_section_centered_graph_shows_referenced_cards(self):
        """Wiki section graph 显示引用的 cards"""
        ...

    def test_node_href_enables_navigation(self):
        """Card node 的 href 可点击跳转"""
        ...

    def test_graph_computation_under_1s_for_100_nodes(self, large_graph_fixture):
        """100 节点时计算时间 < 1s"""
        ...

    def test_nodes_capped_at_50_with_show_all_option(self):
        """节点超出 50 时截断"""
        ...
```

### 7.2 Golden Graph Fixture

```python
# tests/fixtures/graph_golden.py

GRAPH_GOLDEN = {
    "cards": [
        {"id": "center_card", "source_id": "src_1", "tags": ["auth", "security"], "wiki_sections": ["Authentication"]},
        {"id": "neighbor_1", "source_id": "src_1", "tags": ["auth"], "wiki_sections": ["Authentication"]},
        {"id": "neighbor_2", "source_id": "src_1", "tags": ["security"], "wiki_sections": []},
        {"id": "neighbor_3", "source_id": "src_2", "tags": ["auth"], "wiki_sections": ["Authentication"]},
        {"id": "unrelated", "source_id": "src_3", "tags": ["database"], "wiki_sections": ["Database"]},
    ],
    "center_id": "center_card",
    "expected_nodes": {"center_card", "neighbor_1", "neighbor_2", "neighbor_3", "src_1", "auth", "security", "Authentication"},
    "expected_edges": [
        ("center_card", "neighbor_1"),  # same_source + same_tag + same_wiki_section
        ("center_card", "neighbor_2"),  # same_source + same_tag
        ("center_card", "neighbor_3"),  # same_tag + same_wiki_section
    ],
    "expected_no_edges": [("center_card", "unrelated")],
}
```

---

## 8. Integration & E2E Tests

### 8.1 API Integration Tests

**File**: `tests/integration/test_v03_api.py`

```python
class TestV03API:
    def test_quality_endpoint_returns_valid_schema(self, client): ...
    def test_relations_endpoint_returns_related_cards(self, client): ...
    def test_health_endpoint_returns_report(self, client): ...
    def test_graph_endpoint_returns_local_graph(self, client): ...
```

### 8.2 E2E Tests (Playwright)

**File**: `web/e2e/v03-quality.spec.ts`

```typescript
test('card detail shows quality badge', async ({ page }) => {
  // 打开一张已知 quality 的卡片
  // 验证 QualityBadge 显示正确的 level
});

test('related cards panel shows neighbor cards', async ({ page }) => {
  // 打开一张已知有 related cards 的卡片
  // 验证 RelatedCards panel 显示邻居卡片及 reason
});

test('health page shows issues with severity', async ({ page }) => {
  // 访问 Health 页面
  // 验证 issue 列表、severity badge、suggested action 显示
});

test('local graph shows connected nodes', async ({ page }) => {
  // 打开 card detail
  // 验证 local graph preview 显示 neighbors
});
```

---

## 9. Mock & Test Isolation

### 9.1 Mock Boundaries

| Layer | Mock Strategy |
|-------|---------------|
| LLM 调用 | 不 mock — v0.3 所有测试不调 LLM |
| File system | Synthetic fixtures in temp dirs (tmp_path) |
| Database | In-memory SQLite / fixture dict |
| External APIs | 不涉及 |
| Embedding | 不涉及 |

### 9.2 Fixture Reuse

所有 golden fixture 放在 `tests/fixtures/` 目录，跨 milestone 共享：

```
tests/fixtures/
├── __init__.py
├── quality_golden.py
├── location_golden.py
├── wiki_quality_fixture.py
├── relations_golden.py
├── health_golden.py
└── graph_golden.py
```

---

## 10. TDD Workflow per Milestone

每个 milestone 遵循以下 TDD 流程：

```
1. Write golden fixture          → 定义已知输入/输出
2. Write red test                → tests/<module>/test_*.py, 验证 test FAIL
3. Implement minimal code        → src/mindforge/<module>/*.py
4. Run test → GREEN              → pytest tests/<module>/ -v
5. Refactor                      → 清理代码，确保 ruff clean
6. Verify coverage ≥ 80%         → pytest --cov=src/mindforge/<module> --cov-report=term-missing
7. Integration test (if API)     → tests/integration/test_v03_api.py
8. E2E test (if UI)              → web/e2e/v03-*.spec.ts (Playwright)
9. Dogfood verification          → 在 dogfood workspace 验证
```

---

## 11. References

- [RFC 0003](../rfc/RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)
- [SDD Knowledge Quality](../sdd/SDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)
- [V0.3 Roadmap](../roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md)
- [Python Testing Rules](../../../../.claude/rules/python/testing.md)
- [Common Testing Rules](../../../../.claude/rules/common/testing.md)
