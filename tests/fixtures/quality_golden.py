"""M1 golden fixtures — 高质量/中质量/低质量 synthetic cards。

这些 fixtures 覆盖 SDD §5.1-5.4 的所有 rubric 维度、warning 和 card type 分类。
所有数据为 synthetic，不包含真实用户数据。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SyntheticCard:
    """synthetic card 输入，模拟卡片 frontmatter + body 结构。"""
    id: str
    title: str
    body: str
    status: str = "ai_draft"
    source_id: str | None = None
    source_path: str | None = None
    source_type: str | None = None
    tags: tuple[str, ...] = ()
    strategy_version: str | None = None


# ---------------------------------------------------------------------------
# 高质量卡片 — 预期 overall_score ≥ 70, quality_level = "high"
# ---------------------------------------------------------------------------

HIGH_QUALITY_CARDS = {
    "well_structured_fact": SyntheticCard(
        id="card_hq_001",
        title="Architecture: Service Layer Pattern in Backend Systems",
        body="""## Summary
The service layer pattern encapsulates business logic between controllers and data access layers, providing a clean separation of concerns. This pattern was observed in 12 out of 15 reviewed backend codebases.

## Details
### Implementation
- Every service class implements a protocol interface defined in the domain layer
- Services are stateless and injected via dependency injection container
- Each service method corresponds to exactly one business use case

### Trade-offs
- Increases code volume by approximately 15% compared to fat-controller approach
- Requires disciplined interface design upfront
- Testing becomes significantly easier due to mockable boundaries

### Observed Results
In the sampled codebases, teams using this pattern reported 40% fewer regression bugs and 25% faster onboarding time for new developers.
""",
        status="ai_draft",
        source_id="src_architecture_notes",
        source_path="notes/architecture-patterns.md",
        source_type="markdown",
    ),
    "comprehensive_method": SyntheticCard(
        id="card_hq_002",
        title="How to Implement Database Migration Strategy with Zero Downtime",
        body="""## Summary
A step-by-step procedure for implementing database migrations without service interruption, validated across PostgreSQL and MySQL deployments.

## Details
### Step 1 — Expand
Add new columns with NULL defaults. Never rename or remove existing columns in this phase. The application code continues to read old schema.

### Step 2 — Dual Write
Application writes to both old and new schema paths. Backfill existing rows through a background job with batch size of 1000 rows per transaction.

### Step 3 — Migrate Reads
Gradually shift read queries to new schema, monitoring error rates at each step. Maintain rollback capability throughout.

### Step 4 — Contract
Remove old schema paths once new schema has been stable for at least one full deployment cycle (typically 2 weeks).
""",
        status="ai_draft",
        source_id="src_db_migration",
        source_path="docs/database/migration-guide.md",
        source_type="markdown",
    ),
    "specific_insight": SyntheticCard(
        id="card_hq_003",
        title="Key Insight: Code Review Turnaround Time Correlates with Merge Frequency",
        body="""## Summary
Analysis of 1,200 pull requests across 8 engineering teams revealed a surprising pattern: teams with median review turnaround under 4 hours merge 3.2x more frequently than teams with turnaround over 24 hours.

## Details
### Data
- Sample: 1,200 PRs from 8 teams over 6 months
- Metric: time from PR open to first review comment
- Finding: Spearman correlation of -0.71 between turnaround time and weekly merge count

### Interpretation
The relationship is likely bidirectional — faster reviews encourage more frequent small PRs, which in turn are easier to review quickly. This creates a virtuous cycle that compounds over time.

### Limitations
Correlation does not equal causation. Teams with faster review times may also have other practices (smaller PRs, better test coverage) that contribute to higher merge frequency.
""",
        status="ai_draft",
        source_id="src_eng_metrics",
        source_path="research/engineering-metrics-2025.md",
        source_type="markdown",
    ),
}

# ---------------------------------------------------------------------------
# 中质量卡片 — 预期 overall_score 40-69, quality_level = "medium"
# ---------------------------------------------------------------------------

MEDIUM_QUALITY_CARDS = {
    "short_but_structured": SyntheticCard(
        id="card_mq_001",
        title="Decision: Adopt TypeScript for New Frontend Modules",
        body="""## Summary
Team decided to adopt TypeScript for all new frontend modules starting Q3.

## Details
Decision was made after evaluating alternatives. The team agreed on TypeScript because of better tooling support and type safety.
""",
        status="ai_draft",
        source_id="src_team_decision",
        source_path="decisions/frontend-stack.md",
        source_type="markdown",
    ),
    "vague_claim": SyntheticCard(
        id="card_mq_002",
        title="Something About Testing Maybe",
        body="""## Summary
Testing is probably important for software quality. Many people might think that writing tests could help reduce bugs, but it's something that varies.

## Details
There are maybe several approaches to testing. Some teams seem to do it well, others might not. It probably depends on the context and what kind of project you have. Testing could be beneficial in some situations but maybe not in others.
""",
        status="ai_draft",
        source_id=None,
        source_path=None,
        source_type=None,
    ),
    "no_source_citation": SyntheticCard(
        id="card_mq_003",
        title="REST API Design Best Practices",
        body="""## Summary
REST APIs should follow consistent naming conventions and use proper HTTP status codes.

## Details
### Naming
- Use plural nouns for collections (/users, /orders)
- Use nested routes for related resources
- Use query parameters for filtering and pagination

### Status Codes
- 200 for successful GET/PATCH
- 201 for successful POST (with Location header)
- 204 for successful DELETE
- 400 for validation errors
- 404 for not found
""",
        status="ai_draft",
        source_id=None,  # 无 source citation — 导致扣分
        source_path=None,
        source_type=None,
    ),
}

# ---------------------------------------------------------------------------
# 低质量卡片 — 预期 overall_score < 40, quality_level = "low"
# ---------------------------------------------------------------------------

LOW_QUALITY_CARDS = {
    "extremely_short": SyntheticCard(
        id="card_lq_001",
        title="Note",
        body="Something about something. Not sure what exactly. Maybe useful later?",
        status="ai_draft",
        source_id=None,
        source_path=None,
        source_type=None,
    ),
    "no_structure_at_all": SyntheticCard(
        id="card_lq_002",
        title="Random Thoughts on Code",
        body="code is hard. debugging is harder. sometimes things work and I don't know why. other times things break and I also don't know why. probably just need more practice.",
        status="ai_draft",
        source_id=None,
        source_path=None,
        source_type=None,
    ),
    "self_contradicting": SyntheticCard(
        id="card_lq_003",
        title="The Best Programming Language",
        body="""## Summary
Python is the best programming language for all tasks. It should be used everywhere.

## Details
However, Python is completely unsuitable for system programming and should never be used for performance-critical tasks. Every language has its strengths and weaknesses, so no single language can be the best for everything.
""",
        status="ai_draft",
        source_id=None,
        source_path=None,
        source_type=None,
    ),
}

# ---------------------------------------------------------------------------
# Card type classification fixtures — 用于 test_card_type.py
# ---------------------------------------------------------------------------

CARD_TYPE_FIXTURES = {
    "fact": SyntheticCard(
        id="card_type_fact",
        title="Measured Performance Improvement",
        body="The latency was measured at 45ms under peak load. Observed throughput reached 1200 requests per second. These values were recorded during the load test on 2025-03-15.",
    ),
    "claim": SyntheticCard(
        id="card_type_claim",
        title="The Argument for Microservices",
        body="This paper argues that microservices improve team autonomy. It claims that deployment frequency increases by 3x. The author asserts that maintenance burden decreases over time.",
    ),
    "decision": SyntheticCard(
        id="card_type_decision",
        title="Team Decision on Database Choice",
        body="The team decided to use PostgreSQL for the primary data store. We chose to avoid vendor lock-in and agreed on a 12-month evaluation period. The architecture committee resolved the dispute about MySQL vs PostgreSQL.",
    ),
    "method": SyntheticCard(
        id="card_type_method",
        title="How to Set Up CI/CD Pipeline",
        body="This procedure describes how to configure GitHub Actions for continuous deployment. Follow these steps to set up the pipeline: first, define the trigger events. The approach uses matrix builds for multiple environments.",
    ),
    "risk": SyntheticCard(
        id="card_type_risk",
        title="Risk of Database Connection Pool Exhaustion",
        body="A critical pitfall is connection pool exhaustion under high load. Watch out for unclosed connections in error paths. The failure mode manifests as timeout errors cascading through dependent services.",
    ),
    "question": SyntheticCard(
        id="card_type_question",
        title="What Is the Optimal Team Size for Microservices?",
        body="How can we determine the optimal team size? Why does team productivity decrease beyond 8 members? When should a team be split into smaller units? These remain open questions in the industry.",
    ),
    "insight": SyntheticCard(
        id="card_type_insight",
        title="Interesting Pattern in Bug Reports",
        body="A surprising pattern emerges from the bug database: 80% of critical bugs are reported within 48 hours of a deployment. The key insight is that monitoring should be intensified during this window. An interesting lesson is that most of these bugs are configuration-related rather than code defects.",
    ),
    "mixed_fact_method": SyntheticCard(
        id="card_type_mixed",
        title="How We Measured and Improved Build Times",
        body="We measured build times and found they averaged 12 minutes. The procedure we followed to reduce them: first, we profiled each build step. We observed that dependency resolution took 40% of the time.",
    ),
    "no_type_match": SyntheticCard(
        id="card_type_none",
        title="Miscellaneous Notes",
        body="Just some random notes from the meeting. Nothing particularly structured or classified.",
    ),
}

# ---------------------------------------------------------------------------
# Warning fixtures — 用于 test_warnings.py
# ---------------------------------------------------------------------------

WARNING_FIXTURES = {
    "too_short": SyntheticCard(
        id="warn_short",
        title="Brief Note",
        body="Very short content.",  # < 100 chars
    ),
    "missing_sections": SyntheticCard(
        id="warn_no_sections",
        title="Unstructured Content",
        body="This text has no markdown section headers at all. It is just plain text without any structure or organization.",
    ),
    "no_source": SyntheticCard(
        id="warn_no_source",
        title="Good Content Without Source",
        body="## Summary\nWell-structured content but no source citation.\n\n## Details\nThis card has sections but lacks a source reference.",
        source_id=None,
        source_path=None,
    ),
    "vague_language": SyntheticCard(
        id="warn_vague",
        title="Uncertain Ideas",
        body="## Summary\nSomething might be important. Maybe we should probably look into this. It could possibly be related to the other thing that someone mentioned.",
    ),
}
