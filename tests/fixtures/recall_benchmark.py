"""v4.9 — BM25 Recall 质量基准 fixtures。

设计原则：
- 纯 deterministic，不调用 LLM/embedding/vector DB
- 合成知识卡片带有真实的中英文内容（非 [fake] 占位符）
- 每个 golden query 记录 expected_hit_ids（至少应命中的 card ID 集合）
- 覆盖：英文查询、中文查询、短查询、多词查询、negative queries（预期 0 hits）
- 可重复运行，每次输出相同结果

与 retrieval_benchmark.py 的区别：
- retrieval_benchmark.py 测的是 graph/relation 检索
- recall_benchmark.py 测的是 BM25 text recall（关键词→卡片）
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Golden Card 定义 — 12 张 synthetic approved cards
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoldenCard:
    """一张 golden recall benchmark 卡片。

    frontmatter 字段对应 CardSummary 的安全字段；
    body 包含 ## 段落，对应被 BM25 索引的 body_summary / body_actions 等字段。
    """

    card_id: str
    title: str
    status: str = "human_approved"
    track: str | None = None
    tags: tuple[str, ...] = ()
    projects: tuple[str, ...] = ()
    source_type: str | None = None
    source_title: str | None = None
    value_score: int | None = None
    body_sections: tuple[tuple[str, str], ...] = ()
    """(body_section_title, body_section_content) 对。"""


@dataclass(frozen=True)
class GoldenQuery:
    """一条 golden recall query 及其预期结果。"""

    query_text: str
    """BM25 查询文本。"""

    expected_hit_ids: tuple[str, ...]
    """至少应该命中的 card_id 集合（子集匹配即可，不要求 exact match）。"""

    ranking: str = "bm25"
    """检索模式：bm25 或 hybrid。"""

    status_filter: str = "human_approved"
    """卡片状态过滤。"""

    include_drafts: bool = False

    max_expected_hits: int | None = None
    """预期命中数的上限（可选，用于验证不返回过多无关结果）。"""


@dataclass(frozen=True)
class NegativeQuery:
    """预期 0 hits 的 query。"""

    query_text: str
    reason: str
    """为什么这个 query 预期 0 hits 的简短说明。"""


@dataclass(frozen=True)
class RecallBenchmark:
    """完整的 BM25 recall 质量基准。"""

    cards: tuple[GoldenCard, ...]
    golden_queries: tuple[GoldenQuery, ...]
    negative_queries: tuple[NegativeQuery, ...]


def build_recall_benchmark() -> RecallBenchmark:
    """构建标准 BM25 recall benchmark 数据集。

    覆盖场景：
    - 英文单关键词查询（architecture, security, testing, deployment）
    - 英文多词查询（python async, deployment strategy）
    - 中文查询（架构设计、安全边界）
    - 短查询（2-3 字符）
    - CJK 查询
    - 中文多词查询
    - Negative queries（不存在的内容）
    """
    cards: tuple[GoldenCard, ...] = (
        GoldenCard(
            card_id="arch-001",
            title="MindForge 系统架构设计",
            track="engineering",
            tags=("architecture", "design", "python"),
            source_type="markdown",
            source_title="MindForge Architecture Overview",
            value_score=8,
            body_sections=(
                ("AI Summary", "MindForge 采用分层架构：Web API 层、Service 层、Retrieval 层。"
                 "核心数据流是 Source → ai_draft → human_approved → Library。"
                 "所有检索通过 BM25 词法索引完成，不使用 embedding 或向量数据库。"),
                ("Action Items", "保持 web_facade.py 的渐进式分解，不引入微服务架构。"),
                ("Principles", "本地优先、显式审批、确定性检索、安全边界不可绕过。"),
            ),
        ),
        GoldenCard(
            card_id="arch-002",
            title="RetrievalPort 抽象边界设计",
            track="engineering",
            tags=("architecture", "retrieval", "python"),
            source_type="markdown",
            source_title="Retrieval Architecture Design",
            value_score=7,
            body_sections=(
                ("AI Summary", "RetrievalPort 定义了词法检索的统一抽象边界。"
                 "当前唯一实现是 Bm25RetrievalEngine，委托到 lexical_index 模块。"
                 "未来可接入 SQLite FTS5 等后端，recall_service 无需改动。"),
                ("Principles", "依赖抽象而非具体实现。每个检索后端必须实现 search 和 hybrid_search 方法。"),
            ),
        ),
        GoldenCard(
            card_id="sec-001",
            title="MindForge 安全边界设计",
            track="engineering",
            tags=("security", "design", "safety"),
            source_type="markdown",
            source_title="Security Boundary Design",
            value_score=9,
            body_sections=(
                ("AI Summary", "MindForge 安全边界包括：不读取 .env/secrets、不调用真实 LLM（除非显式 opt-in）、"
                 "不写真实 Obsidian vault、不做 RAG/embedding/vector DB。"
                 "显式审批语义不可绕过：ai_draft 只能通过 --confirm 变为 human_approved。"
                 "不存在 auto-approve 路径。"),
                ("Known Risks", "fake provider 确定性输出但内容稀疏——只从文件名提取关键词，"
                 "不读取源文件实际内容。这使 recall 质量依赖于源文件命名质量。"),
            ),
        ),
        GoldenCard(
            card_id="sec-002",
            title="Approval 审批链路安全分析",
            track="engineering",
            tags=("security", "approval", "review"),
            source_type="markdown",
            source_title="Approval Chain Security",
            value_score=8,
            body_sections=(
                ("AI Summary", "审批链路的核心不变式：ai_draft 状态不会自动变更为 human_approved。"
                 "所有状态变更需经过 ApprovalService.approve() 方法，该方法检查显式确认标志。"
                 "测试覆盖 approval boundary 的所有已知 bypass 尝试。"),
            ),
        ),
        GoldenCard(
            card_id="test-001",
            title="BM25 词法检索测试策略",
            track="engineering",
            tags=("testing", "bm25", "recall"),
            source_type="markdown",
            source_title="BM25 Testing Strategy",
            value_score=6,
            body_sections=(
                ("AI Summary", "BM25 检索的测试策略包括：golden fixtures 定义已知卡片和查询，"
                 "验证 expected_hit_ids 全部命中。Negative queries 验证 0 hits 场景。"
                 "所有测试纯 deterministic，不依赖 embedding 或外部服务。"
                 "测试覆盖中英文查询、短查询、多词查询。"),
            ),
        ),
        GoldenCard(
            card_id="test-002",
            title="Python 异步 IO 测试模式",
            track="engineering",
            tags=("testing", "python", "async"),
            source_type="markdown",
            source_title="Python Async IO Testing",
            value_score=5,
            body_sections=(
                ("AI Summary", "Python 异步 IO 测试使用 pytest-asyncio。"
                 "关键模式：@pytest.mark.asyncio 装饰器、AsyncMock for 协程 mock、"
                 "asyncio.wait_for 设置超时防止测试挂起。"),
            ),
        ),
        GoldenCard(
            card_id="deploy-001",
            title="MindForge 部署策略",
            track="engineering",
            tags=("deployment", "devops", "python"),
            source_type="markdown",
            source_title="Deployment Strategy",
            value_score=7,
            body_sections=(
                ("AI Summary", "MindForge 支持 pip install 和本地开发两种部署方式。"
                 "Web 前端使用 Vite + React，后端使用 Python FastAPI。"
                 "部署时需注意：fake provider 是默认 provider，用户需显式配置真实模型。"
                 "静态文件由 FastAPI 直接 serve，不需要独立的前端服务器。"),
                ("Action Items", "确认 npm build 产物在 web/dist/ 下，被 FastAPI mount 到 /app。"),
            ),
        ),
        GoldenCard(
            card_id="deploy-002",
            title="蓝绿部署与回滚策略",
            track="engineering",
            tags=("deployment", "strategy", "rollback"),
            source_type="markdown",
            source_title="Blue-Green Deployment",
            value_score=6,
            body_sections=(
                ("AI Summary", "蓝绿部署通过维护两套完全独立的生产环境来降低部署风险。"
                 "回滚策略应在部署前确定，包括回滚触发条件、回滚步骤、数据兼容性验证。"),
            ),
        ),
        GoldenCard(
            card_id="cn-001",
            title="知识卡片质量评估标准",
            track="knowledge",
            tags=("质量", "评估", "标准"),
            source_type="markdown",
            source_title="知识卡片质量标准",
            value_score=8,
            body_sections=(
                ("AI Summary", "知识卡片质量评估包含五个维度：准确性、完整性、可追溯性、"
                 "新鲜度、可操作性。每张 ai_draft 卡片在生成时附带 quality_score 和 "
                 "quality_level，帮助用户在审批时判断卡片是否值得入库。"),
            ),
        ),
        GoldenCard(
            card_id="cn-002",
            title="中文检索优化方案",
            track="knowledge",
            tags=("检索", "中文", "优化"),
            source_type="markdown",
            source_title="中文检索优化",
            value_score=7,
            body_sections=(
                ("AI Summary", "中文检索面临分词挑战。当前 BM25 使用空格和标点分词，"
                 "对中文文本的索引覆盖率不足。改进方向包括：引入 jieba 分词、"
                 "bigram 字符级索引、或混合索引策略。这些改进需在 RetrievalPort 边界内进行。"),
                ("Principles", "中文分词改进不能依赖外部 API 或云端服务，必须纯本地执行。"),
            ),
        ),
        GoldenCard(
            card_id="dogfood-001",
            title="v4.9 MindForge-on-MindForge Dogfood 执行报告",
            track="product",
            tags=("dogfood", "v4.9", "recall"),
            source_type="markdown",
            source_title="v4.9 Dogfood Report",
            value_score=9,
            body_sections=(
                ("AI Summary", "v4.9 使用 MindForge 仓库内 30 个非敏感项目文档作为 source material。"
                 "30/30 文档成功通过 Source → ai_draft → human_approved 全路径。"
                 "Recall 命中率 4/10 (40%)，根因是 fake provider 只从文件名提取关键词，"
                 "不读取文档实际内容。这证明 fake provider 适合 pipeline 验证但不适合内容理解。"),
                ("Known Risks", "fake provider 的内容稀疏性是 recall 质量的天花板。"
                 "synthetic dogfood recall 10/10 是因为文件名本身就是关键词。"
                 "真实项目文档的文件名不携带完整语义。"),
            ),
        ),
        GoldenCard(
            card_id="dogfood-002",
            title="Dogfood 安全边界验证",
            track="product",
            tags=("dogfood", "security", "safety"),
            source_type="markdown",
            source_title="Dogfood Safety Verification",
            value_score=8,
            body_sections=(
                ("AI Summary", "每次 dogfood 必须验证安全边界：零网络请求、零 API key 使用、"
                 "零真实私人资料处理、零 Obsidian vault 写入。Fake provider 确定性输出。"
                 "显式审批语义不可绕过——library 在 approve 前必须为空。"),
            ),
        ),
    )

    # Golden queries — 每个 query 记录 expected_hit_ids（至少应命中的 card_id）
    golden_queries: tuple[GoldenQuery, ...] = (
        # ── 英文单关键词 ──
        GoldenQuery(
            query_text="architecture",
            expected_hit_ids=("arch-001", "arch-002"),
        ),
        GoldenQuery(
            query_text="security",
            expected_hit_ids=("sec-001", "sec-002"),
        ),
        GoldenQuery(
            query_text="testing",
            expected_hit_ids=("test-001", "test-002"),
        ),
        GoldenQuery(
            query_text="deployment",
            expected_hit_ids=("deploy-001", "deploy-002"),
        ),
        GoldenQuery(
            query_text="dogfood",
            expected_hit_ids=("dogfood-001", "dogfood-002"),
        ),
        # ── 英文多词查询 ──
        GoldenQuery(
            query_text="python async testing",
            expected_hit_ids=("test-002",),
        ),
        GoldenQuery(
            query_text="deployment strategy rollback",
            expected_hit_ids=("deploy-002",),
        ),
        GoldenQuery(
            query_text="BM25 retrieval recall",
            expected_hit_ids=("test-001",),
        ),
        # ── 中文查询 ──
        GoldenQuery(
            query_text="架构设计",
            expected_hit_ids=("arch-001", "arch-002"),
        ),
        GoldenQuery(
            query_text="安全边界",
            expected_hit_ids=("sec-001",),
        ),
        GoldenQuery(
            query_text="知识卡片质量",
            expected_hit_ids=("cn-001",),
        ),
        GoldenQuery(
            query_text="中文检索",
            expected_hit_ids=("cn-002",),
        ),
        # ── 中文多词 ──
        GoldenQuery(
            query_text="部署策略 回滚",
            expected_hit_ids=("deploy-001", "deploy-002"),
        ),
        # ── 精确匹配（title 字段权重最高） ──
        GoldenQuery(
            query_text="MindForge 安全边界设计",
            expected_hit_ids=("sec-001",),
        ),
    )

    # Negative queries — 预期 0 hits
    # 中文学习型说明：CJK 字符级 tokenization（如 "架构"→["架","构"]）使单个
    # 中文字符极易匹配任意含中文的卡片。因此 negative queries 仅使用英文长短语，
    # 确保主题词不在任何 golden card 中出现。
    # CJK negative query 的不可行性是已知限制，记录在 test_recall_benchmark.py
    # 的 test_cjk_character_tokenization_limitation 中。
    negative_queries: tuple[NegativeQuery, ...] = (
        NegativeQuery(
            query_text="machine learning neural network",
            reason="所有 golden cards 不涉及 ML/神经网络主题",
        ),
        NegativeQuery(
            query_text="blockchain cryptocurrency ethereum",
            reason="所有 golden cards 不涉及区块链/加密货币",
        ),
        NegativeQuery(
            query_text="quantum computing schrodinger",
            reason="所有 golden cards 不涉及量子计算",
        ),
        NegativeQuery(
            query_text="kubernetes docker container orchestration",
            reason="所有 golden cards 不涉及容器编排",
        ),
    )

    return RecallBenchmark(
        cards=cards,
        golden_queries=golden_queries,
        negative_queries=negative_queries,
    )
