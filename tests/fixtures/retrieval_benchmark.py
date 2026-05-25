"""v3.2 — 检索质量评估 benchmark fixtures。

设计原则：
- 纯 deterministic，不调用 LLM/embedding/vector DB
- 合成知识卡片带有已知 ground truth 关系
- 可重复运行，每次输出相同结果
- 覆盖：same_source, same_tag, same_wiki_section, unrelated (负例)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Benchmark 卡片定义
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkCard:
    """单张 benchmark 卡片。"""

    card_id: str
    title: str
    status: str = "human_approved"
    source_id: str | None = None
    tags: tuple[str, ...] = ()
    wiki_sections: tuple[str, ...] = ()
    body: str = ""


@dataclass(frozen=True)
class GroundTruthRelation:
    """一条已知的 ground truth 关系。"""

    source_id: str
    target_id: str
    relation_type: str  # same_source, same_tag, same_wiki_section


@dataclass(frozen=True)
class RetrievalBenchmark:
    """完整的检索质量 benchmark。"""

    cards: tuple[BenchmarkCard, ...]
    ground_truth: tuple[GroundTruthRelation, ...]
    unrelated_pairs: tuple[tuple[str, str], ...]  # 预期无关系的卡片对（负例）


def build_benchmark() -> RetrievalBenchmark:
    """构建标准 benchmark 数据集。

    覆盖场景：
    - 3 张 agent-runtime 卡片（共享 tags: agent, runtime）
    - 2 张来自同一 source 的卡片（design-doc.md）
    - 2 张在同一 wiki section 的卡片（Architecture）
    - 2 张完全无关的卡片（负例）
    """
    cards = (
        BenchmarkCard(
            card_id="agent-001",
            title="Agent Runtime 启动流程",
            source_id="agent-runtime-overview.md",
            tags=("agent", "runtime", "lifecycle"),
            wiki_sections=("Agent Runtime",),
            body="Agent 启动经过三个阶段：初始化、配置加载、运行时注册。",
        ),
        BenchmarkCard(
            card_id="agent-002",
            title="Agent Tool Calling 协议",
            source_id="tool-calling-design.md",
            tags=("agent", "tool-calling", "protocol"),
            wiki_sections=("Agent Runtime",),
            body="统一的 tool calling 接口定义，支持多种 LLM provider。",
        ),
        BenchmarkCard(
            card_id="agent-003",
            title="Agent 错误处理策略",
            source_id="error-handling-notes.md",
            tags=("agent", "runtime", "error-handling"),
            wiki_sections=("Agent Runtime",),
            body="Agent 运行时的错误分类、重试策略和降级方案。",
        ),
        BenchmarkCard(
            card_id="design-001",
            title="系统架构设计概览",
            source_id="design-doc.md",
            tags=("architecture", "design"),
            wiki_sections=("Architecture",),
            body="MindForge 整体系统架构的分层设计和模块边界。",
        ),
        BenchmarkCard(
            card_id="design-002",
            title="数据模型设计细节",
            source_id="design-doc.md",
            tags=("data-model", "design"),
            wiki_sections=("Architecture",),
            body="Knowledge Card 数据模型、字段定义和状态机设计。",
        ),
        BenchmarkCard(
            card_id="wiki-001",
            title="确定性知识图谱",
            source_id="knowledge-graph-notes.md",
            tags=("graph", "deterministic"),
            wiki_sections=("Knowledge Graph",),
            body="基于共享标签、来源、Wiki 章节构建确定性关系图谱。",
        ),
        BenchmarkCard(
            card_id="wiki-002",
            title="社区检测算法",
            source_id="community-notes.md",
            tags=("graph", "community"),
            wiki_sections=("Knowledge Graph",),
            body="确定性社区检测——基于共享成员的多层级分组。",
        ),
        BenchmarkCard(
            card_id="unrelated-001",
            title="Python 性能优化笔记",
            source_id="python-notes.md",
            tags=("python", "performance"),
            wiki_sections=("Python",),
            body="Python 代码性能优化的常见技巧和工具。",
        ),
        BenchmarkCard(
            card_id="unrelated-002",
            title="Git 工作流最佳实践",
            source_id="git-notes.md",
            tags=("git", "workflow"),
            wiki_sections=("Git",),
            body="Git 分支策略、commit message 规范和 code review 流程。",
        ),
    )

    # Ground truth 关系
    ground_truth = (
        # agent-001, agent-002, agent-003 共享 tags "agent"
        GroundTruthRelation("agent-001", "agent-002", "same_tag"),
        GroundTruthRelation("agent-001", "agent-003", "same_tag"),
        GroundTruthRelation("agent-002", "agent-003", "same_tag"),
        # agent-001, agent-003 共享 tags "runtime"
        # agent-001, agent-002, agent-003 共享 wiki_section "Agent Runtime"
        GroundTruthRelation("agent-001", "agent-002", "same_wiki_section"),
        GroundTruthRelation("agent-001", "agent-003", "same_wiki_section"),
        GroundTruthRelation("agent-002", "agent-003", "same_wiki_section"),
        # design-001, design-002 共享 source_id "design-doc.md"
        GroundTruthRelation("design-001", "design-002", "same_source"),
        # design-001, design-002 共享 wiki_section "Architecture"
        GroundTruthRelation("design-001", "design-002", "same_wiki_section"),
        # wiki-001, wiki-002 共享 tags "graph"
        GroundTruthRelation("wiki-001", "wiki-002", "same_tag"),
        # wiki-001, wiki-002 共享 wiki_section "Knowledge Graph"
        GroundTruthRelation("wiki-001", "wiki-002", "same_wiki_section"),
    )

    # 负例：预期无关系的卡片对
    unrelated_pairs = (
        ("agent-001", "unrelated-001"),
        ("agent-001", "unrelated-002"),
        ("design-001", "unrelated-001"),
        ("design-001", "unrelated-002"),
        ("wiki-001", "unrelated-001"),
        ("unrelated-001", "unrelated-002"),  # 不同 tags，不同 source，不同 wiki_section
    )

    return RetrievalBenchmark(
        cards=cards,
        ground_truth=ground_truth,
        unrelated_pairs=unrelated_pairs,
    )


def cards_to_relation_records(cards: tuple[BenchmarkCard, ...]) -> list[dict[str, Any]]:
    """将 BenchmarkCard 转换为 relations engine 可接受的输入格式。

    与 web_facade._relation_record 保持一致的结构。
    """
    return [
        {
            "id": c.card_id,
            "title": c.title,
            "status": c.status,
            "source_id": c.source_id,
            "tags": list(c.tags),
            "wiki_sections": list(c.wiki_sections),
        }
        for c in cards
    ]
