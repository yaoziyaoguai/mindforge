# MindForge Milestone G: Wiki Reading Experience — Implementation Notes

**Date**: 2026-05-24
**Status**: implemented
**Spec**: `docs/specs/2026-05-23-006-wiki-reading-experience-spec.md`

## Implementation Summary

5 个 Implementation Units 全部完成：

| Unit | What | Approach |
|------|------|----------|
| U1 | Print Styles | `@media print` CSS rules — 隐藏 aside/button/SafetyBar/wiki-chrome，打印 serif 字体 |
| U2 | TOC Scroll Spy | `IntersectionObserver` on section DOM elements，取 intersectionRatio 最大者高亮 |
| U3 | Reader Mode Toggle | `readerMode` state in WikiPage → WikiStatusBar toggle button → 条件渲染 WikiTOC/WikiSection sidebar |
| U4 | Typography Polish | `max-w-[720px]` → `max-w-[680px]`，新增 `.wiki-prose` (line-height: 1.8) + h2/h3 spacing |
| U5 | i18n + Contract Tests | 4 新 key：`wiki.reader_mode_on/off`、`wiki.related_sections`、`wiki.toc_label` + contract test assertions |

## Key Decisions

- **Reader mode prop drilling**: readerMode 通过 WikiPage → WikiReadingPane → WikiSection 链传递，仅 2 层，无需 Context
- **TOC active link 高亮策略**: 使用 `intersectionRatio` 最大值判定当前 section，而非首个可见 section。多个 section 同时可见时选择最突出的
- **Print styles 选择器**: 使用 `section[aria-label="Safety Bar"]` 精确匹配 SafetyBar，避免 fragile 的结构选择器
- **Error/empty state 中的 reader mode**: 传 `readerMode={false}` + noop callback，reader mode 仅在 wiki 内容存在时可见

## Known Limitations

- **Browser MCP 不可用**: 本次 smoke 通过 curl + build 验证（HTTP 200、JS/CSS bundle 含新 key、build exit 0 = tsc + vite 均通过），未做浏览器交互式验证
- **wiki.related_sections / wiki.toc_label**: keys 已添加到 i18n 字典但暂无组件引用，为后续迭代预留。spec §4.5 描述的 Related Sections 功能本次未实现（不在 IU 范围内）
- **Print 样式未逐页验证**: 通过 CSS bundle 确认 @media print 规则已打入，但未在真实打印预览中逐项验证。低风险——纯 CSS 改动，不影响交互功能
