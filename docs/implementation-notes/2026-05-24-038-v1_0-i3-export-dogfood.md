# v1.0 I3 Export + Dogfood — Implementation Notes

## 变更概要

实现知识卡片安全导出（Markdown 白名单）和一键 dogfood 命令，完成 v1.0 Knowledge Workbench Experience 最后一轮迭代。

## 实现决策

### U1: Export API
- 新增 `POST /api/knowledge/export` endpoint，接受 `{ card_ids: string[] }`
- 复用 `facade.library_card_detail(ref, show_content=True)` 读取卡片，无新增 service 层
- **安全白名单**：仅导出 title + body + status + created_at + source_title
- 不导出 source raw_text、Human Note、API keys、secrets、run_id、prompt_versions 等敏感字段
- 多卡片以 `\n---\n\n` 分隔
- 新增 schema: `ExportCardsRequest`、`ExportCardsResponse`

### U2: Export UI
- LibraryPage 每张卡片新增 checkbox，支持多选
- 工具栏新增「导出选中」按钮 + 全选/取消全选切换
- 选中卡片后通过 `fetch("/api/knowledge/export")` 请求导出
- 使用 `Blob` + `URL.createObjectURL` + `<a>.click()` 触发浏览器下载
- 导出文件名格式：`mindforge-export-YYYY-MM-DD.md`
- 导出成功后清空选择状态

### U3: One-Click Dogfood
- 新增 `justfile`，提供 `just dogfood` 一键命令
- 内部调用 `bash scripts/fake_dogfood.sh`
- `just` 是可选工具，未安装时用户可直接 `bash scripts/fake_dogfood.sh`

### i18n
- 新增 4 个 key：`library.export_selected`、`library.export_select_cards`、`library.select_all`、`library.deselect_all`

## Gate 结果

| Gate | Exit Code | 备注 |
|------|-----------|------|
| `npm --prefix web run build` | 0 | |
| `python -m pytest tests/test_web_product_copy.py -q` | 0 | 新增 3 个测试 |
| `python -m pytest tests/ -q` | 1 (1 pre-existing) | `test_sources_page_uses_source_path_view` 已知失败 |
| `ruff check src tests` | 1 (17 pre-existing) | 与 I1/I2 一致 |
| `git diff --check` | 0 | |

## 已知限制

- Export 仅支持 Markdown，不支持其他格式
- 导出使用同步循环读取卡片（POST body 传入 card_ids），大量卡片时可能较慢
- justfile 仅包装 dogfood 命令，不包含 install/setup 等高级 target
- 无后端运行时无法验证 Export API 端到端行为
