# v0.4 U6 Relationship Golden Tests & Browser Smoke 实现笔记

## 日期
2026-05-24

## 目标
为 v0.4 全部 5 个实现单元（U1-U5）编写 golden tests 并完成 browser smoke 验证。

## 实现方案

### 测试文件

`tests/test_v0_4_relationships.py` — 11 个 golden tests，3 个 test class：

**TestHealthReportGolden（6 tests）**：
- `test_health_report_detects_orphan_cards` — 验证检测孤立卡片
- `test_health_report_detects_low_quality` — 验证检测低质量卡片
- `test_health_report_detects_missing_provenance` — 验证检测缺失来源
- `test_health_report_detects_duplicates` — 验证检测重复卡片
- `test_health_report_returns_stats` — 验证统计字段
- `test_health_report_empty_vault_is_clean` — 空 vault 无问题

**TestProvenanceTrail（3 tests）**：
- `test_trail_404_for_nonexistent_card` — 不存在卡片返回 404
- `test_trail_returns_source_for_known_card` — 验证 source 字段
- `test_trail_returns_sibling_cards` — 验证 sibling cards

**TestLibraryCardDetail（2 tests）**：
- `test_card_detail_includes_local_graph` — 验证 local_graph 结构
- `test_card_detail_includes_related_cards` — 验证 related_cards 分组

### 测试基础设施

复用现有项目模式：
- `_make_vault(tmp_path)` — 创建带正确配置的临时 vault
- `_write_card(cards_dir, name, frontmatter, body)` — 写入知识卡片
- `_make_client(tmp_path)` — 创建 FastAPI TestClient
- 配置结构与 `test_web_api.py` 的 `_write_config` 保持一致
- `mkdir(parents=True, exist_ok=True)` 避免 FileExistsError

### Browser Smoke

所有 v0.4 页面通过 browser smoke：
- `/library?card=<id>` — Card detail 含 local graph + related cards
- `/library?card=<id>` — Provenance trail 面包屑链
- `/wiki` — Wiki 页面含 related sections 导航
- `/health` — Health report 含 stats + issues + exploration links
- `/library` — 卡片网格正常渲染
- `/library?cards=id1,id2` — 过滤功能正常，Clear filter 按钮可用

### Gate

| Gate | 命令 | Exit Code |
|------|------|-----------|
| ruff check | `ruff check tests/test_v0_4_relationships.py` | 0 |
| npm build | `npm --prefix web run build` | 0 |
| pytest (v0.4) | `python -m pytest tests/test_v0_4_relationships.py -q` | 0 (11 passed) |
| pytest (product copy) | `python -m pytest tests/test_web_product_copy.py -q` | 0 (50 passed) |
| git diff --check | `git diff --check` | 0 |

## 关键设计决策

1. **复用现有模式**：fixture helpers 结构与 `test_web_api.py` 保持一致，LLM config 使用 fake provider
2. **pytest 模块导入**：移除后 ruff 不再报 F401，pytest fixture 自动发现不需要显式 import
3. **最小化配置**：_make_client 不再重复调用 _make_vault，避免冗余目录创建

## 已知限制

- Browser smoke 依赖 dev server 手动启动和 MCP 浏览器工具
- Golden tests 不覆盖前端 UI 行为，仅验证 API 响应结构
