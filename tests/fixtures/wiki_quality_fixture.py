"""M2 Wiki Quality golden fixtures — TDD §4.2。

10 张 approved cards 用于 wiki quality 测试：
- 8 used, 2 unused
- 每个 section 有 card references
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SyntheticCardFixture:
    id: str
    title: str
    body: str
    tags: tuple[str, ...] = ()
    updated_at: str = "2026-01-01T00:00:00"


@dataclass
class WikiQualityFixture:
    approved_cards: list[SyntheticCardFixture] = field(default_factory=list)
    wiki_version: str = "v1.0"
    rebuild_time: str = "2026-01-15T00:00:00"
    used_card_ids: list[str] = field(default_factory=list)
    unused_card_ids: list[str] = field(default_factory=list)
    unused_reasons: dict[str, str] = field(default_factory=dict)
    section_references: list[dict[str, object]] = field(default_factory=list)


def build_wiki_quality_fixture() -> WikiQualityFixture:
    cards = [
        SyntheticCardFixture(
            id="c1", title="OAuth 2.0 Authorization Flow",
            body=(
                "OAuth 2.0 uses authorization code grant for web apps. "
                "The client redirects to the auth server and receives a code."
            ),
            tags=("auth", "security"),
        ),
        SyntheticCardFixture(
            id="c2", title="JWT Token Structure",
            body="JWT tokens have header, payload, and signature. They are base64url-encoded.",
            tags=("auth", "tokens"),
        ),
        SyntheticCardFixture(
            id="c3", title="Refresh Token Rotation",
            body="Refresh tokens should rotate on each use to prevent replay attacks.",
            tags=("auth", "security"),
        ),
        SyntheticCardFixture(
            id="c4", title="Database Migration Strategy",
            body="Use versioned migrations with up/down scripts. Never edit applied migrations.",
            tags=("database", "devops"),
        ),
        SyntheticCardFixture(
            id="c5", title="PostgreSQL Indexing Best Practices",
            body="Use B-tree for equality and range queries. GIN for full-text search.",
            tags=("database", "performance"),
        ),
        SyntheticCardFixture(
            id="c6", title="Connection Pooling with PgBouncer",
            body="PgBouncer pools database connections to reduce overhead on PostgreSQL.",
            tags=("database", "performance"),
        ),
        SyntheticCardFixture(
            id="c7", title="Rate Limiting API Endpoints",
            body="Token bucket algorithm provides smooth rate limiting for REST APIs.",
            tags=("api", "security"),
        ),
        SyntheticCardFixture(
            id="c8", title="API Versioning via URL Path",
            body="Prefix API routes with /v1/, /v2/ for explicit versioning. Deprecate gracefully.",
            tags=("api", "design"),
        ),
        SyntheticCardFixture(
            id="c9", title="Niche Topic: SVG Rendering in CLI",
            body="Rendering SVG in terminal requires converting paths to ANSI escape codes.",
            tags=("cli", "rendering"),
        ),
        SyntheticCardFixture(
            id="c10", title="Short Note",
            body="Just a quick thought.",
            tags=("misc",),
        ),
    ]

    return WikiQualityFixture(
        approved_cards=cards,
        wiki_version="v1.0",
        rebuild_time="2026-01-15T00:00:00",
        used_card_ids=["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"],
        unused_card_ids=["c9", "c10"],
        unused_reasons={
            "c9": "Topic too narrow — SVG rendering not related to web stack",
            "c10": "Card too short — lacks sufficient detail for wiki synthesis",
        },
        section_references=[
            {
                "section_title": "Authentication",
                "card_ids": ("c1", "c2", "c3"),
                "relevance": "primary",
            },
            {
                "section_title": "Database",
                "card_ids": ("c4", "c5", "c6"),
                "relevance": "primary",
            },
            {
                "section_title": "API Design",
                "card_ids": ("c7", "c8"),
                "relevance": "primary",
            },
        ],
    )
