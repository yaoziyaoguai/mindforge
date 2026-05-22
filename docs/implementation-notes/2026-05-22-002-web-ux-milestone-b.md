# Web UX Milestone B Implementation Notes

## 实现了什么

全部 7 个 Implementation Unit 已完成（~500 LOC 纯前端改动，零后端变更）：

- **U1: Setup 页面步骤指示器** — 3 步横向 stepper（连接模型 → 选择知识源 → 检查配置），Save 按钮 loading/error state
- **U2: 审批 UX 修正** — 审批按钮 danger→primary 颜色修正，两步确认文案中文化，`friendlyStatus()` 状态标签中文化
- **U3: 空状态引导增强** — `NextAction` 接口扩展 `onClick`，`EmptyState` 支持 href/onClick 双模式，Home/Library/Drafts 页面传引导 action
- **U4: 侧边栏导航分组** — 8 个导航项分为"知识处理"和"知识使用"两个逻辑组，分组标签不可点击
- **U5: 状态 Badge 图标化** — 新增 `statusIcon()`/`statusLabel()`，StatusCard/ConfigChecklist/CardWorkspace badge 增加图标辅助辨识
- **U6: Recall 搜索结果优化** — 分数标签化（高相关/相关/低相关），loading/error/empty 三态完整
- **U7: 知识卡片阅读视图排版** — 正文字体 font-mono→系统字体，section 标题层次，styles.css 排版基线

其中 U1/U2/U3/U6/U7 在前序 commit（`f740573`）中完成，U4/U5 为本轮 commit。

## Plan 未覆盖但执行中必须做的决策

- `statusIcon()` 返回 `LucideIcon | null`，通过 Inline IIFE 在 badge 渲染处调用——避免修改 `statusTone()` 签名，现有调用方零改动
- CardWorkspace status badge 使用 `statusIcon(card.status === "human_approved" ? "ok" : "warn")` 映射，遵循组件已有的双色约定
- SetupPage Save loading/error 实现方式：`saving` state + `saveError` state，与现有 `busy`/`message` 状态并行，不耦合

## Deviations

- 无。实现与 plan 的 7 个 Implementation Unit 完全一致

## 没做什么

- Milestone C / 后续功能
- P3 设计系统演进（响应式断点、loading skeleton、图标系统规范化）
- P4 品牌视觉（插图、空状态图形、情感化设计）
- 前端测试基础设施（vitest + testing-library）
- Setup 页面深度重构（对话式引导、provider 自动检测）

## 风险和 Deferred

- 无前端组件测试覆盖——依赖 npm build（tsc + vite）做类型检查，手工 smoke test 做行为验证
- Deferred 前端测试基础设施搭建后应补 StatusCard/ConfigChecklist/Sidebar 的组件快照测试
- 不涉及后端、API contract、approval 语义、secret handling——零破坏性风险

## 测试/Gate 结果

- `npm --prefix web run build`: exit code 0 ✓
- `python -m pytest -q`: exit code 0（16 product copy tests passed）✓
- `ruff check src tests`: All checks passed ✓
- `git diff --check`: exit code 0 ✓

## 回退记录

- 无回退

---

## Browser Smoke Review Result (2026-05-23)

验证目标 commit：
- `1eef5f6` feat(web): implement ux milestone b — sidebar grouping and status badge icons
- `3c9489b` docs: finalize ux milestone b implementation notes

### 验证结论

- **browser smoke passed**
- P0/P1/P2 = 0
- no hotfix required
- can proceed to Milestone C

### 已验证页面

| 页面 | 路径 | 结果 |
|------|------|------|
| Home | `/` | ✅ StatusCards 显示，NextAction 引导可用 |
| Setup | `/setup` | ✅ 3 步 stepper，ConfigChecklist badges，Save/Validate/Revert |
| Drafts | `/drafts` | ✅ 空状态 "没有待确认的 AI 草稿" + "Create drafts" 链接 |
| Library | `/library` | ✅ 卡片列表 + CardWorkspace（知识内容/来源与历史/技术详情） |
| Recall | `/recall` | ✅ BM25 词法匹配说明，score 标签 "高相关"，loading/error/empty 三态 |
| Sources | `/sources` | ✅ Copy path / Edit frequency / Process now / Stop watching，SummaryMetric |
| Wiki | `/wiki` | ✅ Wiki 内容展示，Table of Contents，Local Graph Preview |

### 已验证能力

- **Sidebar grouping** (U4): "知识处理" (连接模型/知识源/审阅草稿/回收站) + "知识使用" (首页/知识库/Wiki/搜索) ✅
- **Active navigation state**: 每页导航后对应 sidebar 按钮正确高亮 ✅
- **Status badge icons** (U5): Home StatusCard、Setup ConfigChecklist、Library CardWorkspace badge 均显示图标 + 中文标签 ✅
- **Empty states** (U3): Drafts/Library/Home 空状态提供下一步 action ✅
- **console**: 无 error/warn，仅 accessibility hint（form field 缺 id/name）— P3 非阻塞
- **network**: 所有 XHR/fetch 请求均返回 200，无 4xx/5xx

### 已知非阻塞问题

- **P3**: Console accessibility hint — 部分 form fields 缺 id/name attribute（Sources 页 12 处，Recall 页 1 处）
- **P4**: Inline IIFE icon 渲染模式 (`{(() => { const Icon = ...; return ... })()}`) 可读性一般 — implementation notes 已记录为已知 tradeoff

### 后续建议

- Milestone C 可继续
- P3 accessibility hint 可纳入 Milestone C 或后续 UI quality pass
- P4 inline IIFE 可作为代码质量 polish，非阻塞
