# MindForge 文档

这是 MindForge 的文档入口，帮助用户和开发者快速定位需要的文档。 | [English version](README-en.md)

---

## 用户文档

### 中文

| 文档 | 说明 |
|------|------|
| [快速入门](zh-CN/getting-started.md) | 安装、初始化与首次使用指南 |
| [用户指南](zh-CN/user-guide.md) | 完整功能说明 |
| [模型配置](zh-CN/model-setup.md) | LLM provider 配置详解 |
| [Source 管理](zh-CN/sources.md) | 添加和管理知识来源 |
| [审阅与审批](zh-CN/review-and-approval.md) | AI 草稿审阅与审批流程 |
| [Library / Recall / Wiki](zh-CN/library-recall-wiki.md) | 知识浏览、检索、Wiki、Health 与 Graph |
| [Web Wiki](zh-CN/web-wiki.md) | Web Wiki 页面使用指南 |
| [配置参考](zh-CN/configuration.md) | 完整配置参考 |
| [Troubleshooting](zh-CN/troubleshooting.md) | 常见问题诊断 |
| [FAQ](zh-CN/faq.md) | 常见问题解答 |

### English

| 文档 | 说明 |
|------|------|
| [Getting Started](en/getting-started.md) | Installation and first-run guide |
| [User Guide](en/user-guide.md) | Complete feature guide |
| [Model Setup](en/model-setup.md) | LLM provider configuration |
| [Sources](en/sources.md) | Managing knowledge sources |
| [Troubleshooting](en/troubleshooting.md) | Common issues and solutions |

---

## 开发者文档

| 文档 | 说明 |
|------|------|
| [架构概览](dev/architecture.md) | 代码架构说明 |
| [架构地图](dev/architecture-map.md) | 模块与子系统地图 |
| [贡献指南](dev/contributing.md) | 如何为 MindForge 贡献代码 |
| [测试规范](dev/testing.md) | 测试框架与规范 |
| [Workspace 数据布局](dev/workspace-data-layout.md) | Workspace 目录与数据组织 |
| [发布流程](dev/release-process.md) | 版本发布流程 |
| [Copy 规范](dev/copy-policy.md) | UI 文案规范 |
| [设计系统](dev/design-system.md) | 设计系统参考 |

---

## 架构决策记录 (ADR)

| 文档 | 说明 |
|------|------|
| [ADR-001: Retrieval Backend](adr/2026-05-24-001-retrieval-backend.md) | 检索后端选型 |
| [ADR-002: Kuzu Graph Backend](adr/2026-05-24-002-kuzu-graph-backend.md) | 图数据库后端选型 |
| [ADR-003: Retrieval Quality Baseline](adr/2026-05-25-003-retrieval-quality-baseline.md) | 检索质量基线 |
| [ADR-004: Graph Query Capability Gap](adr/2026-05-25-004-graph-query-capability-gap-analysis.md) | 图查询能力差距分析 |
| [ADR-005: Extension Plugin Boundary](adr/2026-05-25-005-extension-plugin-boundary.md) | 扩展插件边界 |
| [ADR-006: Graph Ontology v1](adr/2026-05-25-006-graph-ontology-v1.md) | 图本体 v1 |
| [ADR-007: Graph Backend Decision](adr/2026-05-25-007-graph-backend-decision.md) | 图后端决策 |

---

## 设计文档

| 文档 | 说明 |
|------|------|
| [Target Architecture Map](design/2026-05-26-100-target-architecture-map.md) | 目标架构地图 |
| [Web Design Direction](design/2026-05-26-102-mindforge-web-design-direction.md) | Web 设计方向 |
| [Web Design Shotgun Comparison](design/2026-05-26-104-web-design-shotgun-comparison.md) | Web 设计方案比较 |
| [Final Web Design Decision](design/2026-05-26-105-final-web-design-decision.md) | Web 最终设计决策 |
| [Obsidian Binding Design](design/obsidian-binding-design.md) | Obsidian 绑定设计 |
| [Real Provider Opt-in Safety](design/real-provider-opt-in-safety.md) | 真实模型 opt-in 安全设计 |
| [RFC: Source Adapter V2](design/rfc/RFC_0001_SOURCE_ADAPTER_V2.md) | Source 适配器 RFC |
| [RFC: Wiki Presentation V2](design/rfc/RFC_0002_WIKI_PRESENTATION_V2.md) | Wiki 展示 RFC |
| [RFC: Knowledge Quality & Navigation](design/rfc/RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md) | 知识质量与导航 RFC |
| [v2.0-v2.5 Changelog](design/v2.0-v2.5-changelog.md) | v2.0-v2.5 变更日志 |

---

## 用户验证

| 文档 | 说明 |
|------|------|
| [Validation Protocol](product/validation-protocol.md) | 用户验证协议 |
| [Test Script](product/test-script.md) | 测试脚本 |
| [Observer Checklist](product/observer-checklist.md) | 观察者检查表 |
| [Feedback Form](product/feedback-form.md) | 反馈表单 |
| [Sample Workspace Validation](product/sample-workspace-validation.md) | Sample Workspace 验证 |

---

## Lab / Internal 功能说明

以下功能属于 lab/internal/experimental，**不是** MindForge 主产品路径，不在主导航暴露，不承诺 API 稳定性：

| 功能 | 状态 | 说明 |
|------|------|------|
| Graph Page（独立全页） | internal | 保留 `/graph` 路由但不在主导航；Library 页面 GraphExplorer 是主入口 |
| Sensemaking Workspace | lab | 实验性分析（基于简单 heuristics），已从主导航隐藏 |
| Entity Resolution | lab | ConceptCandidate 确定性检测，不支持自动升级 |
| GraphRepository | internal | GraphPort 之上的 Repository Pattern 封装，当前仅测试使用 |
| Extension Plugin | lab | ExtensionManifest/ExportAdapter 是架构预留，无生产价值闭环 |
| Dogfood 场景 | internal | 开发者/维护者工具，非用户主路径 |

当前主产品路径：
```
Source / Import → ai_draft → Review → explicit approval
    → human_approved → Library → Recall (BM25) / Wiki (LLM synthesis) → Export
```
