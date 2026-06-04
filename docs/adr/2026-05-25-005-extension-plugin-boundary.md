---
title: "ADR-005: Extension Plugin Boundary Architecture — v3.6"
date: 2026-05-25
status: active
---

# ADR-005: 扩展插件边界架构 — v3.6

## Context

v3.6 要求沉淀 MindForge 的插件边界架构。当前状态:

| 端口 | ABC 存在? | 默认实现 | 注册表 | Manifest |
|------|----------|---------|--------|----------|
| SourceAdapter | ✅ (v0.1 + v0.2) | 13 适配器 | ✅ AdapterRegistry | ❌ |
| LLMProvider | ✅ | 3 提供者 | ✅ 工厂函数 | ❌ |
| GraphPort | ✅ | DeterministicGraphBuilder | ❌ | ❌ |
| RetrievalPort | ✅ | Bm25RetrievalEngine | ❌ | ❌ |
| ExportAdapter | ❌ | 分散在 wiki/library/obsidian_stage | ❌ | ❌ |
| KnowledgeStrategy | ✅ Protocol | 内置策略集 | ✅ 注册表 | ❌ |

**缺口**:
1. ExportAdapter 是唯一完全缺失的端口 ABC
2. 所有端口缺少统一的扩展清单(manifest) — 能力(capabilities)、风险等级、审批策略
3. RetrievalPort 虽有 ABC 但 Bm25RetrievalEngine 未集成到 recall_service (P1 质量债，见审计)
4. GraphPort 和 RetrievalPort 没有正式的注册表

## Decision

### 1. 分层插件架构

```
        ┌──────────────────────────────────┐
        │     ExtensionManifest            │  ← 元数据层（新增）
        │  name/version/capabilities/risk  │
        └──────────┬───────────────────────┘
                   │ 描述
        ┌──────────▼───────────────────────┐
        │     Port ABC / Protocol          │  ← 端口抽象层（已有+补齐）
        │  SourceAdapter / ExportAdapter / │
        │  LLMProvider / GraphPort /       │
        │  RetrievalPort / Strategy        │
        └──────────┬───────────────────────┘
                   │ 实现
        ┌──────────▼───────────────────────┐
        │  Concrete Adapter / Backend      │  ← 实现层（已有+示例）
        │  PlainMarkdown / BM25 /          │
        │  DeterministicGraphBuilder /     │
        │  FakeSourceAdapter / ...         │
        └──────────────────────────────────┘
```

**分层职责**:
- **Manifest 层**: 描述扩展"是什么"——元数据、能力标签、风险等级、审批需求。不参与运行时逻辑。
- **Port 层**: 定义扩展"能做什么"——抽象方法签名和契约。已有 ABC 保持不变。
- **实现层**: 扩展"怎么做"——具体适配器和后端。当前实现保持不变。

### 2. ExtensionManifest 作为统一元数据

新增 `ExtensionManifest` frozen dataclass，包含:

| 字段 | 类型 | 用途 |
|------|------|------|
| name | str | 全局唯一标识 |
| version | str | 语义化版本 |
| description | str | 功能描述 |
| extension_type | ExtensionType | 对应端口类型 |
| capabilities | frozenset[Capability] | 能力标签 |
| risk_level | RiskLevel | LOW/MEDIUM/HIGH/CRITICAL |
| requires_approval | bool | 是否需要用户审批 |
| entry_point | str | Python 导入路径 |
| dependencies | tuple[str, ...] | 额外依赖 |

**与现有 capabilities() 的关系**: `ExtensionManifest.capabilities` 是静态声明，`Adapter.capabilities()` 是运行时查询。两者应保持同步但用途不同:
- Manifest 用于注册表扫描和审批决策（不需要实例化适配器）
- capabilities() 用于运行时能力检查（如 dry-run 模式过滤）

### 3. ExportAdapter 端口

新增 `ExportAdapter` ABC，补齐唯一缺失的端口:

```python
class ExportAdapter(ABC):
    name: str
    export_format: str

    def can_handle(card_ids, target_format) -> bool: ...
    def export(card_ids, output_path, **options) -> ExportResult: ...
    def capabilities() -> frozenset[str]: ...
```

`ExportResult` 是对 `AdapterResult`(sources) 的对等设计:
- success=False + errors 表示失败
- success=True + output_path 指向产出文件
- warnings 记录非致命警告

### 4. 审批策略

由 manifest 自动推导:

| 条件 | requires_approval |
|------|-------------------|
| Capability 含 REAL_API | True |
| Capability 含 NETWORK | True |
| RiskLevel HIGH/CRITICAL | True |
| 仅 LOCAL_FILE + FAKE_SAFE + DRY_RUN + READ_ONLY | False |

**不改变现有安全语义**: 审批策略仅应用于扩展启用决策，不影响 ai_draft → human_approved 的知识审批流程。

### 5. 不做什么

- ❌ 不实现动态插件加载（entry_point 仅文档化用途）
- ❌ 不引入 setuptools entry_points / pluggy / stevedore 等插件框架
- ❌ 不修改现有 ABC 接口（向后兼容）
- ❌ 不强制现有适配器迁移到 manifest 模式（渐进式采用）

## Consequences

### Positive

- 所有 6 种端口类型有统一的元数据描述
- 审批策略可自动化: 已知 manifest 即可判断是否需要用户确认
- ExportAdapter 填补了导出侧的端口空白
- 为未来扩展（如社区贡献的适配器）预留了清晰的插槽

### Negative

- 新增 `extensions/` 包，增加代码量（~200 行核心 + 示例 + tests）
- Manifest 与现有 capabilities() 有概念重叠，需要同步维护
- RetrievalPort 集成问题(P1)不在本次修复范围

### Mitigations

- Manifest 是纯数据类，无运行时开销
- 不强制迁移，现有代码继续工作
- P1 质量债留在 quality debt ledger 中跟踪
