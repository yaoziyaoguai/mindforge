"""Guided Onboarding — Sample Workspace Service.

Creates demo knowledge cards about MindForge concepts for the first-run
experience. Cards are pre-approved (human_approved) with [demo sample] source
tag — these are system demo content, not user data. The explicit approval
boundary for user data remains untouched.

纯 fake 数据，不调用 LLM，不读取 secrets。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SAMPLE_WORKSPACE_SCHEMA_VERSION = "0.8"

# ── Demo card templates: MindForge concepts ──────────────────────────
DEMO_CARDS: list[dict] = [
    {
        "id": "demo-mindforge-001",
        "title": "What is MindForge?",
        "tags": ["mindforge", "product", "local-first"],
        "source_type": "demo_sample",
        "source_title": "MindForge Demo Workspace",
        "adapter_name": "PlainMarkdownAdapter",
        "quality_level": "high",
        "quality_score": 90,
        "body": (
            "## What is MindForge?\n\n"
            "MindForge is a **local-first, approval-first personal knowledge compiler**.\n\n"
            "It helps you:\n"
            "- Import knowledge sources (Markdown, TXT, HTML, PDF, DOCX)\n"
            "- Use AI to generate structured knowledge card drafts\n"
            "- Review and explicitly approve each card before it enters your library\n"
            "- Browse, search (BM25), and export your approved knowledge\n\n"
            "Unlike cloud-based tools, MindForge runs entirely on your machine. "
            "Your data stays local."
        ),
    },
    {
        "id": "demo-mindforge-002",
        "title": "Approval-First Architecture",
        "tags": ["mindforge", "approval", "safety"],
        "source_type": "demo_sample",
        "source_title": "MindForge Demo Workspace",
        "adapter_name": "PlainMarkdownAdapter",
        "quality_level": "high",
        "quality_score": 90,
        "body": (
            "## Approval-First Architecture\n\n"
            "Every knowledge card in MindForge goes through an explicit approval boundary:\n\n"
            "1. **Source Import** — files are scanned and parsed\n"
            "2. **AI Draft** (`ai_draft`) — AI generates a draft card from the source\n"
            "3. **Review** — you review the draft\n"
            "4. **Explicit Approval** — you manually confirm the card\n"
            "5. **Human Approved** (`human_approved`) — the card enters your library\n\n"
            "**AI never auto-approves.** The approval step is always manual and explicit. "
            "This is MindForge's core safety principle."
        ),
    },
    {
        "id": "demo-mindforge-003",
        "title": "Why Local-First?",
        "tags": ["mindforge", "privacy", "local-first"],
        "source_type": "demo_sample",
        "source_title": "MindForge Demo Workspace",
        "adapter_name": "PlainMarkdownAdapter",
        "quality_level": "high",
        "quality_score": 85,
        "body": (
            "## Why Local-First?\n\n"
            "MindForge is designed to be local-first from the ground up:\n\n"
            "- **Privacy** — your knowledge never leaves your machine unless you choose to export it\n"
            "- **Offline** — works without internet; no cloud dependency\n"
            "- **Speed** — local file operations are instant; no API latency\n"
            "- **Ownership** — your data lives in plain Markdown files on your disk\n\n"
            "MindForge uses a local BM25 search index (not vector embeddings) and a "
            "deterministic graph (not GraphRAG). Everything is transparent and inspectable."
        ),
    },
    {
        "id": "demo-mindforge-004",
        "title": "Knowledge Lifecycle in MindForge",
        "tags": ["mindforge", "lifecycle", "workflow"],
        "source_type": "demo_sample",
        "source_title": "MindForge Demo Workspace",
        "adapter_name": "PlainMarkdownAdapter",
        "quality_level": "high",
        "quality_score": 85,
        "body": (
            "## Knowledge Lifecycle in MindForge\n\n"
            "The complete knowledge lifecycle has 8 stages:\n\n"
            "```\n"
            "Source / Import\n"
            "  → AI Draft (ai_draft)\n"
            "  → Review (manual review)\n"
            "  → Explicit Approval\n"
            "  → Human Approved (human_approved)\n"
            "  → Library (browse, filter, sort)\n"
            "  → Recall (BM25 lexical search)\n"
            "  → Wiki (LLM-synthesized wiki)\n"
            "  → Export (Markdown / ZIP download)\n"
            "```\n\n"
            "Each stage preserves the explicit approval boundary. "
            "Nothing enters your knowledge library without your confirmation."
        ),
    },
    {
        "id": "demo-mindforge-005",
        "title": "BM25 Search vs. Vector Search",
        "tags": ["mindforge", "search", "bm25"],
        "source_type": "demo_sample",
        "source_title": "MindForge Demo Workspace",
        "adapter_name": "PlainMarkdownAdapter",
        "quality_level": "medium",
        "quality_score": 75,
        "body": (
            "## BM25 Search vs. Vector Search\n\n"
            "MindForge uses **BM25 lexical search** instead of vector/embedding search.\n\n"
            "**BM25 advantages:**\n"
            "- Deterministic — same query always returns same results\n"
            "- No embedding model needed — works without API keys\n"
            "- Fast — local index, no network calls\n"
            "- Transparent — you can inspect the index\n\n"
            "**What BM25 cannot do:**\n"
            "- Semantic search (understanding meaning beyond keywords)\n"
            "- Cross-lingual search\n"
            "- Fuzzy conceptual matching\n\n"
            "MindForge intentionally does NOT use RAG, vector DB, or embedding-based retrieval. "
            "This is a product decision, not a technical limitation."
        ),
    },
    {
        "id": "demo-mindforge-006",
        "title": "Demo Mode & Fake Provider",
        "tags": ["mindforge", "demo", "fake-provider"],
        "source_type": "demo_sample",
        "source_title": "MindForge Demo Workspace",
        "adapter_name": "PlainMarkdownAdapter",
        "quality_level": "medium",
        "quality_score": 80,
        "body": (
            "## Demo Mode & Fake Provider\n\n"
            "MindForge ships with a **fake provider** for safe local testing.\n\n"
            "**What the fake provider does:**\n"
            "- Generates keyword-based summaries (no real LLM)\n"
            "- Extracts key terms from source text\n"
            "- Creates structured draft cards with predictable output\n"
            "- Requires zero configuration\n\n"
            "**When to use a real model:**\n"
            "- For production knowledge work with real content\n"
            "- When you need high-quality AI summaries\n"
            "- When processing complex or technical documents\n\n"
            "You can connect a real LLM anytime via the Setup page. "
            "API keys are stored locally and never sent to MindForge servers."
        ),
    },
]


def _card_frontmatter(card: dict) -> str:
    """Generate YAML frontmatter for a demo card."""
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "---",
        f"id: {card['id']}",
        f"title: {card['title']}",
        "status: human_approved",
        f"source_type: {card['source_type']}",
        f"adapter_name: {card['adapter_name']}",
        f"schema_version: \"{SAMPLE_WORKSPACE_SCHEMA_VERSION}\"",
        f"quality_level: {card['quality_level']}",
        f"quality_score: {card['quality_score']}",
        "profile: fake",
        "provider: fake",
        "strategy_id: knowledge_card",
        "strategy_version: v1",
        "approval_method: demo_sample",
        f"approved_at: {now}",
        f"created_at: {now}",
    ]
    tags = card.get("tags", [])
    if tags:
        lines.append(f"tags: [{', '.join(tags)}]")
    if card.get("source_title"):
        lines.append(f"source_title: {card['source_title']}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _card_path(cards_dir: Path, card_id: str) -> Path:
    """Determine card file path inside the cards directory."""
    track_dir = cards_dir / "demo-workspace"
    track_dir.mkdir(parents=True, exist_ok=True)
    return track_dir / f"{card_id}.md"


def _card_exists(cards_dir: Path) -> bool:
    """Check if any demo card already exists (idempotency guard)."""
    first = DEMO_CARDS[0]
    return _card_path(cards_dir, first["id"]).exists()


def create_demo_cards(cards_dir: Path) -> list[Path]:
    """Create demo knowledge cards in the vault cards directory.

    Returns the list of created card file paths. Idempotent — if demo cards
    already exist, returns empty list without overwriting.
    """
    if _card_exists(cards_dir):
        return []

    created: list[Path] = []
    for card in DEMO_CARDS:
        path = _card_path(cards_dir, card["id"])
        content = _card_frontmatter(card) + "\n" + card["body"] + "\n"
        path.write_text(content, encoding="utf-8")
        created.append(path)

    return created


@dataclass(frozen=True)
class SampleWorkspaceResult:
    """Result of demo workspace creation."""

    created: bool
    card_count: int
    card_paths: tuple[str, ...]
    message: str


def build_sample_workspace(cards_dir: Path) -> SampleWorkspaceResult:
    """Create demo workspace with MindForge concept cards.

    Args:
        cards_dir: Path to the vault cards directory (e.g. vault/20-Knowledge-Cards).

    Returns:
        SampleWorkspaceResult with creation status and card details.
    """
    existing = _card_exists(cards_dir)
    if existing:
        return SampleWorkspaceResult(
            created=False,
            card_count=len(DEMO_CARDS),
            card_paths=(),
            message="Demo workspace already exists. Browse your library to see the sample cards.",
        )

    paths = create_demo_cards(cards_dir)
    return SampleWorkspaceResult(
        created=True,
        card_count=len(paths),
        card_paths=tuple(str(p) for p in paths),
        message=f"Created {len(paths)} demo knowledge cards. Go to Library to explore them.",
    )
