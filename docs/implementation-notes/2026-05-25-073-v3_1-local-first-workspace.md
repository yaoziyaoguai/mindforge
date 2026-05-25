# v3.1 Local-first Workspace Persistence & Migration

## 概述

建立 local-first workspace 数据布局文档、示例 fixture 和契约测试。web_facade.py domain 拆分留待 v3.1 U2。

## 已完成

### U1: Workspace 数据布局文档
- `docs/dev/workspace-data-layout.md` — 完整的数据目录结构、schema 版本、Card 数据模型字段表、安全分级、local-first 原则、迁移策略

### U2: 示例 Workspace Fixture
- `tests/fixtures/sample_workspace.py` — 可复用的示例 workspace 构建器
- 包含: 5 张合成卡片 (3 approved + 1 draft + 1 trashed)、3 个源文件、有效配置、state.json
- 纯 fake 数据，不涉及真实私人资料
- deterministic 输出，每次构建相同结构

### U3: Workspace Fixture 契约测试
- `tests/test_workspace_fixture_contract.py` — 9 个契约测试
- 验证: 目录结构完整性、YAML/JSON 格式合法性、卡片必填字段、body 内容、三种 status 覆盖、schema version 一致性、无真实数据泄露

## 设计决策

- **Markdown + YAML frontmatter 作为数据格式** — 用户可读、可编辑、git-friendly
- **路径约定优于数据库** — vault 目录结构即数据组织，不引入额外数据库
- **fake provider 用于测试** — 所有 LLM 相关测试使用 `provider: fake`，不调用真实 API

## 已知限制

- web_facade.py (1990 行) 尚未拆分 — 留待 v3.1 U2
- 当前无活跃 schema 迁移需求 — 版本 0.7 稳定
