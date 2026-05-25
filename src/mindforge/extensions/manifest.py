"""扩展清单(Extension Manifest)数据模型。

统一描述 SourceAdapter / ExportAdapter / Provider / GraphBackend / SearchBackend
等插件边界的元数据，支撑 capability/risk/approval 三层审批策略。

设计原则:
- 与现有 SourceAdapter.capabilities() 返回的 frozenset[str] 兼容
- 不替代已有 ABC/Protocol，仅补充元数据层
- 不做动态加载，manifest 仅用于文档化和静态校验
"""

from dataclasses import dataclass
from enum import Enum


class ExtensionType(str, Enum):
    """扩展类型 — 对应已有的端口抽象。"""

    SOURCE_ADAPTER = "source_adapter"
    EXPORT_ADAPTER = "export_adapter"
    LLM_PROVIDER = "llm_provider"
    GRAPH_BACKEND = "graph_backend"
    SEARCH_BACKEND = "search_backend"
    KNOWLEDGE_STRATEGY = "knowledge_strategy"


class Capability(str, Enum):
    """扩展能力标签 — 与 SourceAdapter.capabilities() 的 frozenset[str] 对齐。

    LOCAL_FILE: 仅读取本地文件，不发网络请求
    FAKE_SAFE: 可在 fake/sample 数据上安全运行，不访问真实外部服务
    DRY_RUN: 支持干跑模式，不产生副作用
    REAL_API: 需要调用真实外部 API（需用户显式配置 API key）
    READ_ONLY: 只读操作，不修改数据
    WRITE: 写操作，可能修改文件或数据库
    NETWORK: 需要网络访问
    """

    LOCAL_FILE = "local_file"
    FAKE_SAFE = "fake_safe"
    DRY_RUN = "dry_run"
    REAL_API = "real_api"
    READ_ONLY = "read_only"
    WRITE = "write"
    NETWORK = "network"


class RiskLevel(str, Enum):
    """风险等级 — 影响审批策略。

    LOW: fake/local/read-only 操作，无需审批
    MEDIUM: 读写操作但不涉及外部服务，或仅读外部 API
    HIGH: 调用外部 API 或修改关键数据
    CRITICAL: 修改审批语义或安全边界
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ExtensionManifest:
    """扩展清单 — 描述一个扩展的元数据。

    用途:
    - 静态文档化插件边界
    - 审批策略自动化依据 (LOW 跳过审批, HIGH 需确认, CRITICAL 需显式授权)
    - 健康检查/就绪状态报告中展示

    不用于动态加载。entry_point 是 Python 完整导入路径，仅文档化用途。
    """

    name: str
    """扩展名称，全局唯一标识符。如 'plain_markdown', 'bm25_lexical', 'fake_export_markdown'"""

    version: str
    """语义化版本字符串。如 '1.0.0'"""

    description: str
    """一句话描述扩展做了什么。"""

    extension_type: ExtensionType
    """扩展类型，对应端口抽象。"""

    capabilities: frozenset[Capability]
    """能力标签集合。空集合表示无可声明能力。"""

    risk_level: RiskLevel
    """风险等级。LOW 的扩展可在 fake/sample 环境自动启用。"""

    requires_approval: bool
    """是否需要用户显式审批才能启用。
    - Capability 含 REAL_API → True
    - RiskLevel HIGH/CRITICAL → True
    - 纯 local/fake/dry-run → False
    """

    entry_point: str
    """Python 完整导入路径。如 'mindforge.extensions.samples.fake_source_adapter.FakeSourceAdapter'"""

    dependencies: tuple[str, ...] = ()
    """额外依赖列表。如 ('pypdf', 'python-docx')。空 tuple 表示无额外依赖。"""

    author: str = ""
    homepage: str = ""

    @staticmethod
    def derive_approval(capabilities: frozenset[Capability], risk_level: RiskLevel) -> bool:
        """根据能力和风险自动推导是否需要审批。

        REAL_API 或网络能力始终需要审批。
        HIGH/CRITICAL 风险始终需要审批。
        LOW 风险 + 纯 local/file/fake-safe/dry-run 能力不需要审批。
        """
        if Capability.REAL_API in capabilities or Capability.NETWORK in capabilities:
            return True
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return True
        return False
