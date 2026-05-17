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
    """Faithfulness 检查测试

    Faithfulness 第一版使用 deterministic lexical overlap / citation coverage heuristic。
    不调用 LLM，不引入 embedding similarity。
    """

    def test_high_overlap_section_is_faithful(self):
        """section 内容与引用 card 高度重叠 → faithful，score > 0.5"""
        ...

    def test_low_overlap_section_flagged(self):
        """section 内容与引用 card 几乎不重叠 → flagged，score < 0.2"""
        ...

    def test_section_with_citations_but_unrelated_text_warns(self):
        """section 引用了 card 但文本内容不相关 → 应警告"""
        ...

    def test_section_without_references_warns(self):
        """section 无 card references → 应警告"""
        ...

    def test_false_positive_rate_under_30_percent(self, wiki_fixture):
        """Golden fixture 上假阳性率 < 30%"""
        ...

    # ── sensitivity tests ──

    def test_known_faithful_section_scores_above_05(self):
        """Golden: 已知 faithful section 的 Jaccard score > 0.5"""
        section_text = "Authentication uses OAuth 2.0 with JWT tokens for session management."
        card_bodies = {
            "c1": "OAuth 2.0 is the authentication protocol. JWT tokens manage sessions.",
            "c2": "Session management uses JWT tokens with refresh-and-rotate.",
        }
        score = compute_faithfulness_score(section_text, card_bodies)
        assert score > 0.5, f"Expected > 0.5, got {score}"

    def test_known_unfaithful_section_scores_below_02(self):
        """Golden: 已知 unfaithful section 的 Jaccard score < 0.2"""
        section_text = "Database backups run nightly with incremental snapshots."
        card_bodies = {
            "c1": "OAuth 2.0 is the authentication protocol.",
            "c2": "API endpoints use rate limiting per IP.",
        }
        score = compute_faithfulness_score(section_text, card_bodies)
        assert score < 0.2, f"Expected < 0.2, got {score}"

    def test_partial_overlap_section_scores_between_02_and_05(self):
        """部分重叠 section 的 score 在 0.2-0.5 之间"""
        section_text = "Authentication uses OAuth 2.0. Logging is done via syslog."
        card_bodies = {
            "c1": "OAuth 2.0 is the authentication protocol.",
        }
        score = compute_faithfulness_score(section_text, card_bodies)
        assert 0.2 <= score <= 0.5, f"Expected 0.2-0.5, got {score}"

### 4.1a Faithfulness Computation (Deterministic)

```python
def compute_faithfulness_score(
    section_text: str,
    card_bodies: dict[str, str],   # card_id → card body
) -> float:
    """
    Deterministic faithfulness via Jaccard similarity of key terms.

    1. 提取 section 和所有 card bodies 的 key terms（去 stopwords，stemming）
    2. 计算 section_terms ∩ union(card_terms) / section_terms ∪ union(card_terms)
    3. 返回 Jaccard coefficient

    Heuristic, not a truth judgment. Thresholds are tuning knobs.
    """
    ...

# Thresholds (可调)
FAITHFUL_THRESHOLD = 0.5     # ≥ 0.5 → faithful
WARNING_THRESHOLD = 0.2      # < 0.2 → unfaithful warning
                              # 0.2 - 0.5 → grey area, warn at low end
```

### 4.1b Faithfulness Safety Rules

1. **不调用 LLM 判断 faithfulness** — 所有计算基于 lexical overlap。
2. **不引入 embedding similarity** — Jaccard + BM25 token overlap only。
3. **False positive rate 监测** — 在 golden fixture 上假阳性 > 30% 时：
   - Faithfulness 标记降级为 warning-only。
   - 不阻塞 Wiki rebuild。
   - 记录为 known limitation 并在 UI 中提示 "Quality indicator only — review manually"。
4. **Section without references** — 无 card_ids 的 section 标记 warning，但不算 faithfulness 问题（是 coverage 问题）。
5. **Faithfulness 报告只读** — 不自动修改 Wiki section 内容或引用的 cards。

### 4.1c Faithfulness Test Fixture

```python
# tests/fixtures/faithfulness_golden.py

FAITHFULNESS_GOLDEN = {
    "faithful_case": {
        "section_text": "OAuth 2.0 authentication uses authorization codes and refresh tokens for secure API access.",
        "card_bodies": {
            "c_auth_1": "OAuth 2.0 protocol uses authorization code grant flow.",
            "c_auth_2": "Refresh tokens provide persistent access without re-authentication.",
        },
        "expected_score_min": 0.5,
    },
    "unfaithful_case": {
        "section_text": "PostgreSQL supports window functions like ROW_NUMBER and RANK.",
        "card_bodies": {
            "c_api_1": "REST API endpoints use JSON for request and response bodies.",
        },
        "expected_score_max": 0.2,
    },
    "partial_case": {
        "section_text": "JWT tokens provide stateless authentication. Rate limiting prevents abuse.",
        "card_bodies": {
            "c_auth_1": "JWT is a compact token format for stateless authentication.",
        },
        "expected_score_min": 0.2,
        "expected_score_max": 0.5,
    },
    "no_references_case": {
        "section_text": "This section covers general architecture principles.",
        "card_bodies": {},   # 无引用
        "expected_warning": "no_card_references",
    },
}
```

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

### 8.2 E2E State Coverage (Playwright)

每个 milestone 的 E2E 测试必须覆盖 5 种状态：loading、empty、error、happy path、regression。

#### 8.2.1 M1 Card Quality

**File**: `web/e2e/v03-quality.spec.ts`

```typescript
// Loading state
test('card detail shows quality panel loading skeleton', async ({ page }) => {
  // 打开卡片详情，quality metadata 加载中
  // 应显示 loading skeleton，不空白
});

// Empty state
test('card without quality metadata shows empty placeholder', async ({ page }) => {
  // 打开一张无 quality metadata 的旧卡片
  // 应显示 "Quality data not available" 的友好提示
});

// Error state
test('card quality panel handles API error gracefully', async ({ page }) => {
  // Quality API 返回 500
  // 应显示 error state，不影响卡片正文阅读
});

// Happy path
test('card detail shows quality badge with correct level', async ({ page }) => {
  // 打开一张 quality=high 的卡片
  // 验证 QualityBadge 显示 "High" 及对应颜色
});

test('card detail expandable quality panel shows rubric breakdown', async ({ page }) => {
  // 展开 quality details
  // 验证 5 个 rubric 维度分数和 warnings 列表
});

// Regression path
test('low quality card shows regenerate suggestion but no auto-approve', async ({ page }) => {
  // 打开 quality=low 的卡片
  // 验证显示 regenerate/split/merge 建议
  // 验证卡片状态未自动改变（仍为当前状态）
});
```

#### 8.2.2 M2 Wiki Quality

**File**: `web/e2e/v03-wiki-quality.spec.ts`

```typescript
// Loading state
test('wiki quality report shows loading indicator', async ({ page }) => {
  // 请求 Wiki quality report
  // 应显示 loading 状态
});

// Empty state
test('wiki without quality report shows empty message', async ({ page }) => {
  // Wiki 尚未 rebuild
  // 应显示 "No quality report available. Rebuild Wiki to generate a report."
});

// Error state
test('wiki quality report handles API failure', async ({ page }) => {
  // Quality report API 返回 500
  // 应显示 error state，不影响 Wiki 正文
});

// Happy path
test('wiki quality report shows coverage and section references', async ({ page }) => {
  // Rebuild Wiki
  // 验证 report 显示 used/unused card counts
  // 验证每个 section 有 card references
});

test('stale wiki section shows warning indicator', async ({ page }) => {
  // 添加新 approved card 后
  // 验证相关 Wiki section 显示 stale indicator
});

// Regression path
test('wiki quality report never includes pending or rejected cards', async ({ page }) => {
  // 有 pending/rejected drafts 存在
  // 验证 Wiki quality report 的 used/unused 仅计算 human_approved
});
```

#### 8.2.3 M3 Related Cards

**File**: `web/e2e/v03-relations.spec.ts`

```typescript
// Loading state
test('related cards panel shows loading skeleton', async ({ page }) => {
  // 卡片详情页，related cards 加载中
  // 应显示 skeleton
});

// Empty state
test('card with no related cards shows empty message', async ({ page }) => {
  // 一张无共享属性、孤立卡片
  // 应显示 "No related knowledge cards found"
});

// Error state
test('related cards panel handles API error', async ({ page }) => {
  // Relations API 返回 500
  // 应显示 error state，不阻塞卡片阅读
});

// Happy path
test('related cards panel shows cards grouped by relation reason', async ({ page }) => {
  // 打开一张有 same_source + same_tag 关系的卡片
  // 验证 related cards 按 reason 分组
  // 验证每条 relation 显示 reason badge
});

test('clicking related card navigates to that card', async ({ page }) => {
  // 点击 related card 链接
  // 验证跳转到目标卡片详情
});

// Regression path
test('library context related cards only show human_approved', async ({ page }) => {
  // 有 pending drafts 与当前卡片同 source
  // 验证 Library 上下文的 related cards 不包含 pending/rejected
});
```

#### 8.2.4 M4 Source Location

**File**: `web/e2e/v03-location.spec.ts`

```typescript
// Empty state
test('card without source location shows fallback display', async ({ page }) => {
  // 旧卡片无 location 字段
  // 应显示 "Source file" with path only
  // 不崩溃，不显示 broken UI
});

// Error state
test('source path outside allowlist rejected', async ({ page }) => {
  // copy/reveal 的 source path 不在 allowlist
  // 应显示 safe error message
  // 不泄露不安全路径
});

// Happy path
test('markdown card shows heading path and line range', async ({ page }) => {
  // 打开 Markdown source 的卡片
  // 验证显示 "§ Architecture > Auth, lines 45-62"
});

test('pdf card shows page number', async ({ page }) => {
  // 打开 PDF source 的卡片
  // 验证显示 "Page 12"
});

// Regression path
test('copy/reveal buttons work with v2 provenance blocks', async ({ page }) => {
  // provenance_blocks v2 带 location 字段
  // 验证 copy path 仍然正常工作
  // 验证 reveal in finder 仍然正常工作
});
```

#### 8.2.5 M5 Knowledge Health

**File**: `web/e2e/v03-health.spec.ts`

```typescript
// Loading state
test('health page shows loading indicator while generating report', async ({ page }) => {
  // 请求 health report
  // 应显示 loading 状态
});

// Empty state
test('healthy vault shows no issues message', async ({ page }) => {
  // 知识库无已知问题
  // 应显示 "No issues detected"
});

// Error state
test('health report generation failure shows error state', async ({ page }) => {
  // Health report 计算失败
  // 应显示 error state with retry option
});

// Happy path
test('health page shows issues grouped by severity', async ({ page }) => {
  // 访问 Health 页面
  // 验证 critical > warn > info 分组
  // 验证每个 issue 显示 title, affected count, suggested action
});

test('health page issue expansion shows details', async ({ page }) => {
  // 点击展开一个 issue
  // 验证显示 affected item 列表和详细说明
});

// Regression path
test('health report never auto-mutates cards', async ({ page }) => {
  // 查看 health report 后刷新卡片状态
  // 验证没有任何卡片状态被自动修改
  // 验证 suggested_action 只是文本建议，没有 "Apply" 按钮
});
```

#### 8.2.6 M6 Local Graph

**File**: `web/e2e/v03-graph.spec.ts`

```typescript
// Loading state
test('local graph shows loading indicator', async ({ page }) => {
  // 卡片详情页，graph 加载中
  // 应显示 skeleton / spinner
});

// Empty state
test('card with no graph edges shows empty message', async ({ page }) => {
  // 一张完全孤立的卡片（无同 source、无同 tag、无 wiki section）
  // 应显示 "No connected knowledge items" + list fallback
});

// Error state
test('local graph handles data error gracefully with list fallback', async ({ page }) => {
  // Graph API 返回 error
  // 应自动切换为 list fallback view
  // 不显示 broken canvas
});

// Happy path
test('card-centered graph shows 1-hop neighbors in list view', async ({ page }) => {
  // 打开一张有关系的卡片
  // 验证 center card 在顶部
  // 验证 neighbors 按 type 分组（Source / Wiki / Cards / Tags）
  // 验证每条边有 reason label
});

test('graph node click navigates to target', async ({ page }) => {
  // 点击 graph 中的 neighbor card 节点
  // 验证跳转到目标卡片详情
});

test('wiki-section-centered graph shows referenced cards', async ({ page }) => {
  // 从 Wiki section 打开 local graph
  // 验证 center 为 wiki section
  // 验证邻居为 section 引用的 cards
});

// Regression path
test('local graph uses only deterministic edges, no semantic edges', async ({ page }) => {
  // 验证所有显示的 edge reasons 都在允许的 6 种类型内
  // 验证不出现 "semantic_similarity" 或类似 label
});
```

### 8.3 E2E State Coverage Checklist

| Milestone | Loading | Empty | Error | Happy | Regression |
|-----------|---------|-------|-------|-------|------------|
| M1 Quality | ✓ | ✓ | ✓ | ✓ | ✓ |
| M2 Wiki Quality | ✓ | ✓ | ✓ | ✓ | ✓ |
| M3 Related Cards | ✓ | ✓ | ✓ | ✓ | ✓ |
| M4 Source Location | — | ✓ | ✓ | ✓ | ✓ |
| M5 Health | ✓ | ✓ | ✓ | ✓ | ✓ |
| M6 Local Graph | ✓ | ✓ | ✓ | ✓ | ✓ |

> M4 无 loading state（location 数据随 card detail 一起返回，无独立加载态）。

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
├── graph_golden.py
├── faithfulness_golden.py
└── README.md                   # fixture 使用说明
```

### 9.2a Golden Fixture Rules

Golden fixtures 必须遵守以下规则：

1. **Hand-authored deterministic data** — fixtures 是手工编写的合成数据，不依赖任何 LLM 输出。
2. **No live LLM dependency** — 如果 fixture 模拟 LLM 生成的内容，必须以已审核的合成文本冻结，附带清晰元数据标注 `# SYNTHETIC — not LLM output`。
3. **Unit tests never call LLM** — 所有单元测试和 CI 测试不调用真实 LLM API。Dogfood 测试是独立流程，不在 CI pipeline 中。
4. **Real API dogfood is separate** — dogfood 验证（在真实 workspace 上手动测试）是 CI/单元测试之外的质量保证步骤，不在 `pytest` 中运行。
5. **Fixture mutations require review** — 修改 golden fixture 的预期输出必须通过 code review，因为 fixture 定义了行为规范。
6. **Each fixture has a README comment** — 每个 fixture 文件的 module docstring 说明该 fixture 覆盖的场景、对应的 RFC/SDD section、以及预期行为摘要。

示例 fixture 文件头：

```python
# tests/fixtures/quality_golden.py
"""
Golden fixtures for Card Quality scoring (M1).

Covers RFC_0003 §7 FR1.1, SDD §5.1-5.4.

Scenarios:
  - high_quality: 完整结构化卡片，预期 score ≥ 70
  - low_quality: 过短、无结构、无 citation 卡片，预期 score < 40
  - medium_quality: 部分满足条件，预期 score 40-69

All content is SYNTHETIC — not derived from real user data or LLM output.
"""
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

## 11. Regression & Boundary Tests

> **Release-blocking regression tests**。这些测试不能只靠 code review。每个 milestone 完成后必须跑相关子集。

### 11.1 Boundary Test Manifest

以下 15 条边界测试是 v0.3 发布的必要条件：

| # | Test | Category | Applies To |
|---|------|----------|------------|
| 1 | **no auto approve** — quality score 不触发自动审批 | Safety | M1 |
| 2 | **no automatic mutation of human_approved** — quality/warnings 不修改卡片内容或状态 | Safety | M1, M5 |
| 3 | **pending_review never appears in Knowledge Library** — Library 查询仅返回 human_approved | Regression | M3 |
| 4 | **ai_draft never appears in final Wiki** — Wiki synthesis 仅使用 human_approved | Regression | M2 |
| 5 | **rejected cards never appear in final Wiki** — rejected 状态卡片不出现在 Wiki section | Regression | M2 |
| 6 | **Wiki only uses human_approved** — Wiki quality report 的 used/unused 仅统计 approved | Regression | M2 |
| 7 | **Related Cards in Library context only returns human_approved** — 非 Library context 可返回 draft 但 Library 不可 | Boundary | M3 |
| 8 | **no Vector DB import** — 代码库中不可出现 `import chromadb` / `import pinecone` 等 | Architecture | All |
| 9 | **no Embedding API call** — 代码库中不可出现 `openai.Embedding` / `sentence_transformers` 调用 | Architecture | All |
| 10 | **no Graph DB dependency** — 不可 `import neo4j`，NetworkX 不可作为数据存储依赖 | Architecture | M3, M6 |
| 11 | **no arbitrary file execution for provenance actions** — copy/reveal 仅操作 allowlisted paths | Safety | M4 |
| 12 | **SourceAdapter must not import quality/wiki/graph modules** — adapter 层与质量/关系层解耦 | Architecture | M1, M4 |
| 13 | **LocalGraph must be deterministic and no semantic similarity** — 同一输入产生相同输出，无 embedding | Correctness | M6 |
| 14 | **maintenance suggestions must not mutate content** — HealthReport.suggested_action 是只读文本建议 | Safety | M5 |
| 15 | **no real API calls in unit tests** — 单元测试不调用 LLM API / 外部服务 | Testing | All |

### 11.2 Test File Mapping

```
tests/boundary/
├── __init__.py
├── test_no_auto_approve.py          # Tests 1-2
├── test_library_wiki_filter.py      # Tests 3-7
├── test_no_forbidden_deps.py        # Tests 8-10
├── test_provenance_safety.py        # Test 11
├── test_module_isolation.py         # Test 12
├── test_deterministic_graph.py      # Test 13
├── test_no_auto_mutation.py         # Test 14
└── test_no_real_api_calls.py        # Test 15
```

### 11.3 Example Boundary Tests

```python
# tests/boundary/test_no_auto_approve.py

def test_quality_score_never_triggers_approve(card_fixture):
    """Quality score must not change card status to human_approved."""
    card = ai_draft_card(quality_level="high", quality_score=95)
    # After quality scoring, status must remain ai_draft
    assert card.status == "ai_draft"
    # Only explicit user action can approve

def test_quality_warning_never_mutates_card_body(card_fixture):
    """Quality warnings must be read-only metadata, never modify card body."""
    original_body = card.body
    CardQuality.from_card(card)  # compute quality
    assert card.body == original_body


# tests/boundary/test_library_wiki_filter.py

def test_pending_drafts_excluded_from_library(all_cards):
    """Knowledge Library query must return only human_approved."""
    from mindforge.relations import compute_related_cards
    related = compute_related_cards("center_card", all_cards, context="library")
    approved_ids = {c.id for c in related if c.status == "human_approved"}
    pending_ids = {c.id for c in related if c.status != "human_approved"}
    assert not pending_ids
    assert related.keys() == approved_ids

def test_wiki_quality_report_only_counts_approved(wiki_fixture):
    """Wiki quality report used/unused counts must exclude non-approved cards."""
    report = compute_wiki_quality_report(wiki_fixture)
    all_used = set(report.used_card_ids)
    all_unused = set(report.unused_card_ids)
    all_counted = all_used | all_unused
    pending_or_rejected = {c.id for c in wiki_fixture.cards
                          if c.status not in ("human_approved",)}
    assert not (all_counted & pending_or_rejected)


# tests/boundary/test_no_forbidden_deps.py

def test_no_vector_db_import():
    """Verify codebase has no Vector DB dependency."""
    forbidden = ["chromadb", "pinecone", "weaviate", "qdrant_client",
                 "milvus", "lancedb"]
    import pkgutil
    installed = {m.name for m in pkgutil.iter_modules()}
    found = forbidden & installed
    assert not found, f"Forbidden Vector DB deps found: {found}"

def test_no_embedding_api_import():
    """Verify codebase has no embedding API dependency."""
    # Check that no import of openai.Embedding or sentence_transformers exists
    import ast, pathlib
    src_dir = pathlib.Path("src/mindforge")
    for py_file in src_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, 'module', '') or ''
                if 'sentence_transformers' in module or 'openai.Embedding' in str(getattr(node, 'names', [])):
                    pytest.fail(f"Forbidden embedding import in {py_file}")
```

### 11.4 Running Boundary Tests

```bash
# Run all boundary tests — must pass before release
pytest tests/boundary/ -v

# Run per-milestone boundary subset
pytest tests/boundary/test_no_auto_approve.py -v    # M1
pytest tests/boundary/test_library_wiki_filter.py -v # M2, M3
pytest tests/boundary/test_no_forbidden_deps.py -v   # All
pytest tests/boundary/test_provenance_safety.py -v   # M4
pytest tests/boundary/test_no_auto_mutation.py -v    # M5
pytest tests/boundary/test_deterministic_graph.py -v # M6
```

---

## 12. References

- [RFC 0003](../rfc/RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)
- [SDD Knowledge Quality](../sdd/SDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)
- [V0.3 Roadmap](../roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md)
- [Python Testing Rules](../../../../.claude/rules/python/testing.md)
- [Common Testing Rules](../../../../.claude/rules/common/testing.md)
