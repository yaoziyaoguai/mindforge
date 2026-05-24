# v1.4 W7: Safe Export Review UX — Implementation Note

**Date:** 2025-05-25
**Status:** Complete

## What was done

在 LibraryPage 导出流程中添加"导出预览"确认步骤。用户点击"导出选中"后，不再直接下载，而是先展示导出预览面板，待用户确认后才执行下载。

## Changes

### LibraryPage.tsx
- **`exportSelected()` → `startExport()` + `confirmExport()`**: 拆分导出为两步流程
- **`showExportPreview` state**: 控制预览面板显隐
- **导出预览面板**: 琥珀色边框面板，位于 header 下方：
  - 显示卡片数量、导出格式（Markdown）
  - 网格展示所有待导出卡片标题
  - 可滚动的卡片清单（max-h-48）
  - "确认下载" + "取消" 两个按钮
- **`cancelExport()`**: 关闭预览面板，不清空选择，允许用户调整选择后重新预览

### i18n
- 新增 6 个 keys (zh + en): `library.export_preview_title`, `library.export_preview_desc`, `library.export_confirm`

## Design rationale

- **Preview before download**: 防止用户误操作导出错误内容，提供最后的审查机会
- **Amber tone**: 使用 amber 色系暗示"需要确认"的中间状态，区别于绿色成功/红色错误
- **Reusable selection**: 取消预览不清空选择，用户可调整后重新预览

## v1.4 W6: Dogfood Report UX — SKIPPED

W6 要求将 dogfood 结果前台化，但当前没有 dogfood API endpoint（如 `GET /api/dogfood/report`）且 dogfood CLI 为独立脚本。创建 UI 需要先建立 API 层，属于 P2 + 需要后端基础设施 → 延迟到后续版本。

## v1.4 Summary

| Unit | Capability | Priority | Status |
|------|-----------|----------|--------|
| W1 | Relationship Map UX 升级 | P0 | ✅ |
| W2 | Knowledge Community Browser | P0 | ✅ |
| W3 | Source Provenance Trail UX | P1 | ✅ |
| W4 | Knowledge Health Dashboard | P1 | ✅ |
| W5 | Approval Lifecycle UX 增强 | P1 | ✅ |
| W6 | Dogfood Report UX | P2 | ⏭️ Skipped |
| W7 | Safe Export Review UX | P2 | ✅ |

## Gates

- npm build: exit 0
- ruff check: All checks passed
- pytest: exit 0, 100% pass
- git diff --check: clean
