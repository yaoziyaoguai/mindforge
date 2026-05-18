"""M5 Knowledge Health golden fixtures — TDD §6.2。

已知问题 vault 用于验证 health report 正确性。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SyntheticHealthCard:
    id: str
    status: str = "human_approved"
    quality_level: str = "medium"
    source_id: str | None = None
    tags: tuple[str, ...] = ()
    title: str = ""

@dataclass
class HealthGoldenVault:
    cards: list[SyntheticHealthCard] = field(default_factory=list)
    pending_drafts: int = 0
    wiki_stale_sections: tuple[str, ...] = ()
    expected_issue_codes: list[str] = field(default_factory=list)


def build_health_golden_vault() -> HealthGoldenVault:
    return HealthGoldenVault(
        cards=[
            SyntheticHealthCard(
                id="c_low_1", status="human_approved",
                quality_level="low", title="Low quality card",
            ),
            SyntheticHealthCard(
                id="c_orphan", status="human_approved",
                quality_level="medium", source_id="src_1",
            ),
            SyntheticHealthCard(
                id="c_dup_a", status="human_approved",
                quality_level="high", title="Auth Pattern Guide",
                tags=("auth",),
            ),
            SyntheticHealthCard(
                id="c_dup_b", status="human_approved",
                quality_level="high", title="Auth Pattern Guidelines",
                tags=("auth",),
            ),
            SyntheticHealthCard(
                id="c_normal", status="human_approved",
                quality_level="high", source_id="src_4",
                tags=("api",), title="API Design",
            ),
        ],
        pending_drafts=3,
        wiki_stale_sections=("Authentication",),
        expected_issue_codes=[
            "review_backlog",
            "orphans",
            "low_quality",
            "duplicates",
            "wiki_stale",
        ],
    )
