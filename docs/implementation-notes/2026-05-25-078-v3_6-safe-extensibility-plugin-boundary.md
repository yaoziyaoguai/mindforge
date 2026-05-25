# v3.6 Safe Extensibility & Plugin Boundary

## 概述

沉淀 MindForge 的插件边界架构：统一 ExtensionManifest 元数据、补齐 ExportAdapter 端口、示例适配器、ADR-005 架构决策。

## 已完成

### U1: Extension Manifest Schema
- `src/mindforge/extensions/manifest.py`：
  - `ExtensionType` 枚举 — 6 种端口类型（SOURCE_ADAPTER、EXPORT_ADAPTER、LLM_PROVIDER、GRAPH_BACKEND、SEARCH_BACKEND、KNOWLEDGE_STRATEGY）
  - `Capability` 枚举 — 7 种能力标签（LOCAL_FILE、FAKE_SAFE、DRY_RUN、REAL_API、READ_ONLY、WRITE、NETWORK），与 SourceAdapter.capabilities() 的 frozenset[str] 对齐
  - `RiskLevel` 枚举 — LOW/MEDIUM/HIGH/CRITICAL 四级风险
  - `ExtensionManifest` frozen dataclass — name/version/description/extension_type/capabilities/risk_level/requires_approval/entry_point/dependencies
  - `derive_approval()` 静态方法 — 根据能力和风险自动推导审批策略

### U2: ExportAdapter ABC
- `src/mindforge/extensions/export_adapter.py`：
  - `ExportResult` frozen dataclass — success/output_path/format/card_count/errors/warnings/metadata
  - `ExportAdapter` ABC — name/export_format/can_handle()/export()/capabilities()
  - 设计上与 SourceAdapter/AdapterResult 保持对等语义

### U3: Sample Adapters
- `src/mindforge/extensions/samples/fake_source_adapter.py`：
  - `FAKE_SOURCE_MANIFEST` — LOW 风险、无需审批、纯本地/fake-safe/dry-run/read-only
  - `FakeSourceAdapter` — 从内存 fake 数据构造 AdapterResult，确定性、零副作用
- `src/mindforge/extensions/samples/fake_export_adapter.py`：
  - `FAKE_EXPORT_MANIFEST` — LOW 风险、无需审批
  - `FakeMarkdownExportAdapter` — 将卡片 ID 集合导出为 Markdown 文件

### U4: ADR-005
- `docs/adr/2026-05-25-005-extension-plugin-boundary.md`：
  - 定义三层架构：Manifest → Port ABC → Implementation
  - ExportAdapter 补齐唯一缺失端口
  - 审批策略自动化：REAL_API/NETWORK → 需审批，LOW + 纯本地 → 免审批
  - 明确不做什么：不动态加载、不引入插件框架、不改现有 ABC

### U5: Tests (37 new)
- `tests/test_extensions.py`：
  - TestExtensionManifest (5) — 创建/不可变性/枚举完整性/能力对齐
  - TestApprovalDerivation (7) — 审批策略推导全覆盖
  - TestExportResult (4) — 成功/失败/warning/metadata
  - TestExportAdapterContract (3) — ABC 履行检查
  - TestFakeSourceAdapter (7) — 匹配/加载/确定性/manifest 对齐
  - TestFakeExportAdapter (7) — 匹配/导出/错误/manifest 对齐
  - TestManifestAlignment (4) — 跨适配器一致性验证

## 设计决策

- **Manifest 不替代 ABC** — Manifest 是静态元数据层，ABC 是运行时契约层，两不冲突
- **ExportAdapter 与 SourceAdapter 对等设计** — ExportResult ↔ AdapterResult，三态契约（success/failure/warning）
- **审批策略仅用于扩展启用** — 不影响 ai_draft → human_approved 的知识审批流程
- **不强制迁移** — 现有 13 个 SourceAdapter、3 个 LLMProvider 可继续工作，渐进式采用 manifest
- **entry_point 仅文档化** — 不做 setuptools entry_points / pluggy / stevedore 动态加载

## Gate 结果

| Gate | Command | Exit Code | Result |
|------|---------|-----------|--------|
| ruff | `ruff check src/ tests/` | 0 | All checks passed |
| product copy tests | `python -m pytest tests/test_web_product_copy.py -q` | 0 | 76 passed |
| npm build | `npm --prefix web run build` | 0 | built in 3.15s |
| pytest full | `python -m pytest tests/ -q` | 0 | ~3027+ passed |
