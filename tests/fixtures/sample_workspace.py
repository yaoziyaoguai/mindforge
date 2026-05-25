"""v3.1 — 示例 workspace fixture，用于本地迁移和 dogfood 场景测试。

设计原则：
- 纯 fake 数据，不涉及真实私人资料
- deterministic，每次生成相同结构
- 可覆盖 ai_draft / human_approved / trashed 三种状态
- 不调用 LLM / embedding / 外部服务
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 示例 workspace 版本
# ---------------------------------------------------------------------------
SAMPLE_WORKSPACE_SCHEMA_VERSION = "0.7"
SAMPLE_WORKSPACE_CONFIG_VERSION = 0.7


def create_sample_config(workspace_dir: Path) -> Path:
    """在 workspace_dir 下生成 mindforge.yaml 示例配置。"""
    import yaml

    vault = workspace_dir / "vault"
    config = {
        "version": SAMPLE_WORKSPACE_CONFIG_VERSION,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {
            "enabled": ["plain_markdown"],
            "registry": {
                "plain_markdown": {
                    "adapter": "PlainMarkdownAdapter",
                    "inbox_subdir": "ManualNotes",
                    "file_glob": "*.md",
                    "enabled": True,
                }
            },
        },
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
                "fake_alias": {
                    "provider": "fake",
                    "type": "fake",
                    "base_url": "fake://",
                    "model": "fake",
                    "timeout_seconds": 5,
                    "max_retries": 0,
                }
            },
        },
        "prompts": {
            "triage_version": "v1",
            "distill_version": "v1",
            "link_suggestion_version": "v1",
            "review_questions_version": "v1",
            "action_extraction_version": "v1",
        },
    }
    cfg_path = workspace_dir / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return cfg_path


# ---------------------------------------------------------------------------
# 示例知识卡片模板
# ---------------------------------------------------------------------------

SAMPLE_CARDS = [
    {
        "id": "agent-runtime-001",
        "title": "Agent Runtime 启动流程",
        "status": "human_approved",
        "track": "agent-runtime",
        "tags": ["agent", "runtime", "lifecycle"],
        "source_type": "plain_markdown",
        "adapter_name": "PlainMarkdownAdapter",
        "quality_level": "high",
        "quality_score": 85,
        "body": "## Agent Runtime 启动流程\n\nAgent 启动经过三个阶段：初始化、配置加载、运行时注册。",
    },
    {
        "id": "agent-runtime-002",
        "title": "Tool Calling 协议设计",
        "status": "human_approved",
        "track": "agent-runtime",
        "tags": ["agent", "tool-calling", "protocol"],
        "source_type": "plain_markdown",
        "adapter_name": "PlainMarkdownAdapter",
        "quality_level": "high",
        "quality_score": 90,
        "body": "## Tool Calling 协议\n\n统一的 tool calling 接口定义，支持多种 LLM provider。",
    },
    {
        "id": "knowledge-graph-001",
        "title": "确定性知识图谱设计",
        "status": "human_approved",
        "track": "knowledge-graph",
        "tags": ["graph", "deterministic", "knowledge"],
        "source_type": "plain_markdown",
        "adapter_name": "PlainMarkdownAdapter",
        "quality_level": "medium",
        "quality_score": 70,
        "body": "## 确定性图谱\n\n基于共享标签、来源、Wiki 章节构建。不使用 embedding 或 LLM。",
    },
    {
        "id": "draft-card-001",
        "title": "待审批的安全策略更新",
        "status": "ai_draft",
        "track": "security",
        "tags": ["security", "policy"],
        "source_type": "plain_markdown",
        "adapter_name": "PlainMarkdownAdapter",
        "quality_level": "medium",
        "quality_score": 65,
        "body": "## 安全策略草案\n\n待审批的安全策略更新内容。",
    },
    {
        "id": "trashed-card-001",
        "title": "已废弃的旧方案",
        "status": "trashed",
        "track": "archive",
        "tags": ["deprecated"],
        "source_type": "plain_markdown",
        "adapter_name": "PlainMarkdownAdapter",
        "quality_level": "low",
        "quality_score": 30,
        "body": "## 旧方案\n\n已被新方案替代的旧设计文档。",
    },
]


def _card_frontmatter(card: dict) -> str:
    """生成卡片 YAML frontmatter。"""
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "---",
        f"id: {card['id']}",
        f"title: {card['title']}",
        f"status: {card['status']}",
        f"track: {card['track']}",
        f"source_type: {card['source_type']}",
        f"adapter_name: {card['adapter_name']}",
        f"schema_version: \"{SAMPLE_WORKSPACE_SCHEMA_VERSION}\"",
        f"quality_level: {card['quality_level']}",
        f"quality_score: {card['quality_score']}",
        "profile: fake",
        "provider: fake",
        "strategy_id: knowledge_card",
        "strategy_version: v1",
        f"created_at: {now}",
    ]
    tags = card.get("tags", [])
    if tags:
        lines.append(f"tags: [{', '.join(tags)}]")
    lines.append("---")
    return "\n".join(lines) + "\n"


def create_sample_cards(vault_root: Path) -> list[Path]:
    """在 vault 目录下生成示例知识卡片。

    返回所有创建的卡片路径列表。
    """
    cards_dir = vault_root / "20-Knowledge-Cards"
    created: list[Path] = []

    for card in SAMPLE_CARDS:
        track_dir = cards_dir / card["track"]
        track_dir.mkdir(parents=True, exist_ok=True)

        card_path = track_dir / f"{card['id']}.md"
        content = _card_frontmatter(card) + "\n" + card["body"] + "\n"
        card_path.write_text(content, encoding="utf-8")
        created.append(card_path)

    return created


def create_sample_sources(vault_root: Path) -> list[Path]:
    """在 vault 下生成示例源文件。"""
    inbox = vault_root / "00-Inbox" / "ManualNotes"
    inbox.mkdir(parents=True, exist_ok=True)

    sources = [
        ("agent-runtime-overview.md", "# Agent Runtime Overview\n\nAgent 运行时总览。\n"),
        ("tool-calling-design.md", "# Tool Calling Design\n\n工具调用协议设计文档。\n"),
        ("knowledge-graph-notes.md", "# Knowledge Graph Notes\n\n知识图谱设计笔记。\n"),
    ]

    created: list[Path] = []
    for filename, content in sources:
        path = inbox / filename
        path.write_text(content, encoding="utf-8")
        created.append(path)

    return created


def create_sample_state(state_dir: Path) -> Path:
    """生成示例 state.json。"""
    state = {
        "version": SAMPLE_WORKSPACE_SCHEMA_VERSION,
        "schema_version": SAMPLE_WORKSPACE_SCHEMA_VERSION,
        "runs": [],
        "source_registry": {},
    }
    state_path = state_dir / "state.json"
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    return state_path


def build_sample_workspace(workspace_dir: Path) -> Path:
    """构建完整的示例 workspace。

    Usage:
        workspace = build_sample_workspace(tmp_path / "sample-workspace")
        cfg = MindForgeConfig.from_yaml(workspace / "mindforge.yaml")
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)

    vault = workspace_dir / "vault"
    state_dir = workspace_dir / ".mindforge"
    state_dir.mkdir(parents=True, exist_ok=True)

    create_sample_config(workspace_dir)
    create_sample_sources(vault)
    create_sample_cards(vault)
    create_sample_state(state_dir)

    # 创建导出目录
    (workspace_dir / "exports").mkdir(exist_ok=True)

    return workspace_dir
