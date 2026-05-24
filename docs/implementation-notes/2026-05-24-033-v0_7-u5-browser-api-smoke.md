# v0.7 U5 Browser & API Smoke 实现笔记

## 日期
2026-05-24

## 目标
浏览器端到端验证 GraphNavigationPanel、GraphExplorer、discovery context API。

## 环境

| 项目 | 值 |
|------|-----|
| Dogfood config | `examples/dogfood/mindforge.dogfood.yaml` |
| Vault | `/tmp/mindforge-dogfood-vault` |
| Cards | 6 张 approved cards (fake provider) |
| Web server | `127.0.0.1:8766` |

## Smoke 结果

### API 验证

| 端点 | 状态 | 细节 |
|------|------|------|
| `/api/library/cards` | 200 | 6 cards |
| `/api/graph/node?ref=fake-0e90b1&depth=1` | 200 | 1-hop graph |
| `/api/graph/node?ref=fake-0e90b1&depth=2` | 200 | 2-hop graph |
| `/api/graph/explore?node_type=tag&node_id=fake&depth=1` | 200 | Tag-centered graph |
| `/api/quality/cards/fake-0e90b1` | 200 | Quality data |
| `/api/provenance/cards/fake-0e90b1/location` | 200 | Provenance |

### Evidence 质量

- 63 edges, all with `detail.relation_reason` (100% 覆盖)
- 0 edges with `↔` machine format
- Evidence text 用户可读（包含共享 entity 名称或合理 fallback）

### Browser UI

| 页面 | 结果 |
|------|------|
| Home | 正常渲染，safety bar 显示正确 |
| Library | GraphExplorer 可见，node type tabs (Source/Tag/Wiki Section) 切换正常，placeholder i18n 正确 |
| Card Detail | GraphNavigationPanel 渲染，按 EdgeType 分组，evidence 展示，2-hop 展开/折叠正常 |
| Local Graph Preview | 节点和边渲染正确，link 可点击跳转 |
| Related Cards | 按 relation reason 分组显示 |

### Console / Network

- Console errors: 0
- Console warnings: 0
- Network 4xx/5xx: 0 (所有 12 个 API 请求返回 200)

## 已知限制

- Wiki rebuild 在 fake provider 下失败 (`FakeProvider 不识别的 stage: wiki_synthesis`)，但不影响 graph 功能
- GraphExplorer edge type badge 仍显示英文技术标识符（已记录为已知限制）
- Source node label 使用 sha1 hash（fake dogfood 数据限制，真实数据下使用 source title）

## v0.7 完成状态

所有 5 个 units 完成：

| Unit | 状态 | Gate |
|------|------|------|
| U1 Evidence Text Quality | done | pytest pass + ruff pass |
| U2 Relation Reason Granularity | done | pytest pass + ruff pass |
| U3 Graph UI Copy Audit | done | npm build pass + product copy test pass |
| U4 Test Gap Closure | done | pytest 96/96 pass |
| U5 Browser/API Smoke | done | browser smoke pass, 0 errors |

## 下一步

v0.8 — Lexical Retrieval Foundation（按 v0.7-v1.0 roadmap §2）
