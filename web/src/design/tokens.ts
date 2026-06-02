/**
 * MindForge Design Tokens — 单一真源
 *
 * MindForge 当前有两套 token 系统并存：
 *   A) Tailwind config 扩展色 (tailwind.config.ts) — Sidebar/ViewSwitcher/CollectionPanel/CardWorkspace 等用
 *   B) CSS 自定义属性 (styles.css :root) — DraftList/ApprovalPanel/StatusCard 等用
 *
 * 本文件集中定义两套 token，作为文档和引用源。新组件优先用 A 套 (Tailwind utility classes)。
 * 两套合一是远期目标，不在当前 scope。
 */

// ─── A 套：Tailwind Config 扩展色 ────────────────────────────────
// 来源: web/tailwind.config.ts
// 用法: className="text-ink bg-panel border-line"

export const twColors = {
  surface: "#f7f5f1", // 页面背景
  panel: "#ffffff", // 卡片/面板背景
  ink: "#23211d", // 主文字
  muted: "#6d685f", // 次级文字
  line: "#ddd8cf", // 边框/分割线
  primary: "#2368d1", // 交互/强调蓝
  safe: "#237a57", // 成功/已批准
  warn: "#b66b13", // 警告
  danger: "#b42318", // 错误/危险
} as const;

export const twShadow = {
  subtle: "0 1px 2px rgba(35, 33, 29, 0.08)",
} as const;

// ─── B 套：CSS 自定义属性 ────────────────────────────────────────
// 来源: web/src/styles.css :root
// 用法: style={{ color: "var(--mf-text-primary)" }} 或 className="text-[var(--mf-accent)]"

export const cssColors = {
  bg: "var(--mf-bg)", // #faf9f5
  surface: "var(--mf-surface)", // #ffffff
  surfaceAlt: "var(--mf-surface-alt)", // #f3f1eb
  textPrimary: "var(--mf-text-primary)", // #1c1b18
  textSecondary: "var(--mf-text-secondary)", // #5e5c56
  textTertiary: "var(--mf-text-tertiary)", // #8a8880
  border: "var(--mf-border)", // rgba(0,0,0,0.08)
  accent: "var(--mf-accent)", // #2d7d5f
  accentHover: "var(--mf-accent-hover)", // #236b4f
  draft: "var(--mf-draft)", // #b8860b
  approved: "var(--mf-approved)", // #2d7d5f
  lab: "var(--mf-lab)", // #8a8880
  warning: "var(--mf-warning)", // #cc7a00
  error: "var(--mf-error)", // #c04040
} as const;

export const cssTypography = {
  fontSerif: "var(--mf-font-serif)", // 'Source Serif 4', Georgia, serif
  fontSans: "var(--mf-font-sans)", // 'DM Sans', system-ui, -apple-system, sans-serif
  fontMono: "var(--mf-font-mono)", // 'JetBrains Mono', 'SF Mono', monospace
  display: "var(--mf-text-display)", // 36px
  h1: "var(--mf-text-h1)", // 28px
  h2: "var(--mf-text-h2)", // 22px
  h3: "var(--mf-text-h3)", // 18px
  bodyL: "var(--mf-text-body-l)", // 16px
  body: "var(--mf-text-body)", // 15px
  bodyS: "var(--mf-text-body-s)", // 14px
  caption: "var(--mf-text-caption)", // 12px
  code: "var(--mf-text-code)", // 13px
} as const;

export const cssShadows = {
  flat: "var(--mf-shadow-flat)", // none
  raised: "var(--mf-shadow-raised)", // 3-layer subtle
  card: "var(--mf-shadow-card)", // 4-layer deeper
  overlay: "var(--mf-shadow-overlay)", // modal/dropdown
} as const;

export const cssRadii = {
  sm: "var(--mf-radius-sm)", // 4px
  md: "var(--mf-radius-md)", // 8px
  lg: "var(--mf-radius-lg)", // 10px
  xl: "var(--mf-radius-xl)", // 14px
  full: "var(--mf-radius-full)", // 9999px
} as const;

export const cssSpacing = {
  "2xs": "var(--mf-space-2xs)", // 4px
  xs: "var(--mf-space-xs)", // 8px
  sm: "var(--mf-space-sm)", // 12px
  md: "var(--mf-space-md)", // 16px
  lg: "var(--mf-space-lg)", // 24px
  xl: "var(--mf-space-xl)", // 32px
  "2xl": "var(--mf-space-2xl)", // 48px
  "3xl": "var(--mf-space-3xl)", // 64px
} as const;

// ─── 已知问题 ────────────────────────────────────────────────────
//
// 1. 双系统值不对齐 (e.g. A套 accent=#2368d1 蓝, B套 accent=#2d7d5f 绿)
//    不同页面视觉不一致。需要统一但属于中等规模重构。
//    Slice 2.5 (2026-06-02): 新组件优先用 B套 CSS 变量；Tailwind A套仅用于布局。
//
// 2. CSS 变量引用缺失:
//    - var(--mf-warn) 在 ExportPage 使用，但定义的是 --mf-warning
//    - var(--mf-info) 在 ExportPage 使用，完全未定义
//    - var(--mf-success) 在 QuickStartWizard 使用，完全未定义
//
// 3. SensemakingPage 使用独立第三套 inline CSS 变量 (--bg-secondary 等)，
//    与其他页面不共享 token 体系。
//
// 4. BoundaryBadge / Callout 色彩已统一 (Slice 2.5): 不再使用 5 种独立颜色。

// ─── 使用指南 ────────────────────────────────────────────────────
//
// 新组件推荐：
//   - 布局/颜色优先用 Tailwind utility classes (A套): text-ink, bg-panel, border-line
//   - 复杂阴影/圆角用 CSS var (B套) inline style: style={{ boxShadow: cssShadows.raised }}
//   - 从本文件 import 常量做文档引用，不要在组件中硬编码色值
//
// 示例:
//   import { twColors, cssShadows } from "../design/tokens";
//   <div className="bg-panel text-ink border-line border" style={{ boxShadow: cssShadows.raised }}>
