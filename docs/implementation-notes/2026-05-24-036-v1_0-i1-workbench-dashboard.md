# v1.0 I1 Workbench Dashboard — Implementation Notes

## 变更概要

将 HomePage 从 NextAction 列表升级为知识工作台仪表盘，实现 U1-U4。

## 实现决策

### U1: Knowledge Overview Cards
- 4 张概览卡片水平排列（`sm:grid-cols-2 lg:grid-cols-4`）
- 数据来源：`HomeStatusResponse`（approved/pending）+ `/api/knowledge/health` + `/api/wiki/status`（异步 fetch）
- 左侧彩色边框指示状态（绿/琥珀/蓝）

### U2: Attention Feed
- 从 health report issues 和 recall status 动态计算关注项
- 按优先级排序：high（待审批）> medium（过期/低质量）> low（孤立卡片）> info（索引重建）
- 匹配 health issue code：`stale`, `quality`, `orphan` 子串匹配
- `source_warnings` 当前未在 attention feed 中展示（低优先级 info）

### U3: Quick Actions Bar
- 3 个紧凑按钮，替换原来的 NextAction 列表
- 作为辅助入口而非主视觉焦点

### U4: Unified Breadcrumb
- 新增 `Breadcrumb` 组件，渲染在 AppShell 的 main 区域顶部
- 基于 URL path 自动生成面包屑，route → label 映射集中配置
- 首页（`/`）不显示面包屑（路径无分段）

### i18n
- 新增 15 个 key（dashboard + breadcrumb + attention feed）
- 旧 HomePage key 已移除（不再使用 StatusCard/NextActionCard 布局）

## Gate 结果

| Gate | Exit Code | 备注 |
|------|-----------|------|
| `npm --prefix web run build` | 0 | |
| `python -m pytest tests/test_web_product_copy.py -q` | 0 | |
| `python -m pytest tests/ -q` | 1 (1 pre-existing) | `test_sources_page_uses_source_path_view` 已知失败 |
| `ruff check src tests` | 1 (17 pre-existing) | stash 验证全为 pre-existing |
| `git diff --check` | 0 | |

## Browser Smoke

- HomePage Dashboard 正确渲染 4 张概览卡片
- Attention Feed 空状态正确展示
- Quick Actions 3 按钮正确渲染
- 卡片点击导航正确（测试：已确认知识 → /library）
- Breadcrumb 在子页面正确渲染（首页 > 知识库）
- 无 console error（仅 1 个 pre-existing accessibility warning）
- zh locale 完整覆盖所有新 i18n key

## 已知限制

- Attention feed 的 `source_warnings` 未匹配展示（code 不在过滤列表中），后续可按需添加
- Breadcrumb 在多级路径（如 `/library?card=xxx`）仅显示路径层级，不显示动态标题
- Wiki section count 依赖 `/api/wiki/status` endpoint 返回 `section_count` 字段
