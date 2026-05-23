# MindForge Web UX Milestone G: Wiki Reading Experience Spec

**Date**: 2026-05-23
**Type**: feat
**Status**: spec
**Precursor**: Milestone F (Knowledge Card Browsing) done + browser smoke passed

---

## 1. Background

Milestones A-F 已将 Library 从 sidebar 列表升级为 Card Grid 浏览体验，Home/Dashboard/Setup 基本可用。当前 Wiki 页面功能完整（12 个分解组件，状态栏/TOC/阅读面板/参考来源/关系预览），但阅读体验仍然偏工程化。

Milestone F spec §3 Non-Goals 明确将以下 Wiki 改进列为 deferred：Wiki TOC Scroll Spy / Print Export / Reader mode。

**本 milestone 目标：将 Wiki 从"功能页面"升级为"阅读体验"。**

---

## 2. Goals

1. Wiki 阅读面板排版优化 — 字体层级、行距、段落间距、最大阅读宽度
2. TOC scroll spy — 当前阅读位置在 TOC 中高亮
3. Print / export styles — 打印时隐藏导航/状态栏/TOC，只保留内容
4. Reader mode toggle — 一键收起侧边面板，全宽阅读
5. i18n / copy 覆盖新 UI 文案
6. 不改变后端 API、Wiki rebuild 逻辑、approval 语义

---

## 3. Non-Goals

- RAG / embedding
- Wiki section 编辑（仍是只读）
- Wiki rebuild 触发逻辑变更
- 新 npm 依赖
- 全局设计系统重写
- 后端 API 变更
- Real LLM 调用

---

## 4. Design Decisions

### 4.1 TOC Scroll Spy 策略

使用 `IntersectionObserver` 监听每个 Wiki section 的可见性，在 TOC 中高亮当前 section 的链接。纯前端实现，不引入 scroll 库。

- Observer threshold: `[0, 0.25, 0.5, 0.75, 1]`
- 高亮逻辑: 取 `intersectionRatio` 最大的可见 section
- 滚动容器: `window` (全页滚动)

### 4.2 Print Styles

在 `styles.css` 中增加 `@media print` 规则：
- 隐藏: nav, SafetyBar, TOC sidebar, Wiki header/status bar, rebuild buttons, Local Graph Preview, Troubleshooting
- 保留: 阅读内容 (overview + sections + open questions + additional cards)
- 字体: 系统 serif (Georgia/Times)，更易读
- 链接: 显示 URL 在括号中（`a[href]::after { content: " (" attr(href) ")" }`）

### 4.3 Reader Mode

- 在 WikiStatusBar 或 WikiHeader 增加 toggle button
- Toggle on: 隐藏左侧 TOC、Wiki header metadata、Local Graph Preview、Knowledge Sources
- Toggle off: 恢复完整布局
- State: React `useState`，不持久化（每次进入 Wiki 默认完整模式）
- 动画: 不需要（瞬切即可）

### 4.4 Typography Polish

- 正文 `line-height: 1.8` (当前 `leading-relaxed` ≈ 1.625，可微调)
- 增大 section 标题字号和间距
- `max-w-[720px]` → `max-w-[680px]` (稍微收窄更易读)
- Overview 段落首行不缩进

### 4.5 Related Sections

在 WikiSection 底部增加 "Related sections" 链接（使用已有的 `section.related_sections` 字段），点击跳转到同页面对应 section anchor。

---

## 5. Implementation Units

### U1: Print Styles (`web/src/styles.css`)

**Goal:** 为 Wiki 页面添加 `@media print` 规则，打印时只显示阅读内容

**Files:**
- Modify: `web/src/styles.css`

**Approach:**
- 在 CSS 文件末尾追加 `@media print` 块
- 使用 CSS 选择器隐藏非内容元素
- 设置打印友好的字体和字号
- 链接 URL 展开

**Verification:**
- 浏览器打印预览中不显示导航、状态栏、TOC、按钮
- 打印预览中保留 Wiki 内容文本
- 不影响屏幕显示

**Test scenarios:**
- Happy path: 打印预览只显示阅读内容
- Edge case: 无内容的 Wiki section 不打印空白区域

---

### U2: TOC Scroll Spy (`web/src/components/wiki/WikiTOC.tsx`)

**Goal:** TOC 中当前阅读位置的 section 链接高亮

**Files:**
- Modify: `web/src/components/wiki/WikiTOC.tsx`
- Modify: `web/src/components/wiki/WikiSection.tsx` (如有必要，给 section 加 `id` 标记)

**Approach:**
- 用 `IntersectionObserver` 监听每个 Wiki section (通过 `id={section.id}` DOM 属性)
- 维护 `activeSectionId` state
- TOC 中 `activeSectionId` 匹配的链接使用 `text-primary font-medium` 样式
- Observer 在组件挂载时创建，卸载时 disconnect

**Verification:**
- 滚动页面时 TOC 高亮跟随变化
- 顶部 section 进入视口时 TOC 第一个链接高亮
- 多个 section 同时可见时高亮占比最大的

**Test scenarios:**
- Happy path: 从上到下滚动，TOC 高亮依次切换
- Edge case: 快速滚动时高亮不闪烁
- Edge case: 页面底部时最后一个 section 高亮

---

### U3: Reader Mode Toggle (`web/src/pages/WikiPage.tsx`)

**Goal:** 一键切换完整布局 / 纯阅读布局

**Files:**
- Modify: `web/src/pages/WikiPage.tsx`
- Modify: `web/src/components/wiki/WikiStatusBar.tsx`
- Modify: `web/src/lib/i18n.ts`

**Approach:**
- 在 WikiPage 新增 `readerMode` state (default false)
- 在 WikiStatusBar 或 WikiHeader 增加 toggle button (Eye / EyeOff icon)
- Reader mode on: WikiPage 不渲染 WikiTOC, WikiStatusBar metadata, LocalGraphPreview, Knowledge Sources
- 内容区宽度从 `max-w-[720px]` 放宽到 `max-w-[800px]`（reader mode 特有）
- i18n key: `wiki.reader_mode_on` / `wiki.reader_mode_off`

**Verification:**
- Toggle 按钮可切换 reader mode
- Reader mode 下只显示阅读内容
- 切换不回丢失滚动位置
- 按钮文案中英文正确

**Test scenarios:**
- Happy path: 点击切换 → 布局从双栏变单栏阅读 → 再点击恢复
- Edge case: 快速双击不导致状态错乱

---

### U4: Typography Polish (`web/src/styles.css`, `web/src/components/wiki/WikiReadingPane.tsx`)

**Goal:** 优化 Wiki 阅读排版

**Files:**
- Modify: `web/src/styles.css`
- Modify: `web/src/components/wiki/WikiReadingPane.tsx`

**Approach:**
- 正文行高调整为 `leading-relaxed` 到自定义 `1.8`（仅在 Wiki reading 区域）
- 段落间距微调
- 标题层级视觉区分 (h2/h3/h4)
- 可选: `max-w-[680px]` 收窄阅读宽度

**Verification:**
- 阅读面板文字排版舒适，行距适当
- 标题层级清晰
- 不改动非 Wiki 区域样式

---

### U5: i18n + Contract Tests

**Goal:** 为新增 UI 文案添加 i18n key

**Files:**
- Modify: `web/src/lib/i18n.ts` (新增 ~6 keys)
- Modify: `tests/test_web_product_copy.py` (新增对应测试)

**New keys:**
- `wiki.reader_mode_on` / `wiki.reader_mode_off`
- `wiki.print` (optional, if print button added)
- `wiki.related_sections`
- `wiki.toc_label`

**Verification:**
- 所有新增 key 在 zh/en 字典中非空
- 合同测试验证 key 完整性

---

## 6. Gate Requirements

- `npm --prefix web run build` exit 0
- `python -m pytest tests/test_web_product_copy.py -q` 全部通过
- `git diff --check` exit 0
- Browser smoke: Wiki reader mode, TOC scroll spy, print preview

## 7. Dependencies

- None. 所有数据来自现有 API。
- 不依赖 Milestone A-F 的未完成部分。

## 8. Risks

| Risk | Mitigation |
|------|------------|
| IntersectionObserver 性能 | 只有 ~5-15 个 section，阈值设为少量几个值，性能无影响 |
| Print styles 跨页面泄漏 | 使用 `@media print` + 特定选择器限定 Wiki 页面 |
| Reader mode toggle 位置不当 | 放在 WikiStatusBar 中已有按钮旁边，不新增单独行 |
