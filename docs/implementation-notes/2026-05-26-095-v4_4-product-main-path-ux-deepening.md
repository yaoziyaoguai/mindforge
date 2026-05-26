# v4.4 Product Main Path UX Deepening — Implementation Notes

**日期**: 2026-05-26
**输入**: `docs/plans/2026-05-25-094-next-deepening-roadmap.md` Direction A
**状态**: completed

---

## 执行摘要

v4.4 在不新增功能、不扩张 Graph/Sensemaking、不引入 RAG/embedding 的前提下，完成了产品主路径 UX 深化的三个 loop。

### Commits

| Loop | Commit | Description |
|------|--------|-------------|
| A1 | `f955923` | feat: v4.4 A1 — HomePage first-run guided onboarding |
| A2 | `d612842` | feat: v4.4 A2 — Import paths explanation + review clarity |
| A3 | `c21d362` | feat: v4.4 A3 — Export safety explanation + format descriptions |

---

## A1: First-Run Guided Onboarding

### 问题
新用户打开 HomePage 时，如果 workspace 为空（零卡片、零知识源），看不到任何引导。所有仪表板卡片显示 0，快速操作栏的文字没有上下文。

### 修改
- `web/src/pages/HomePage.tsx`: 新增 `FirstRunGuide` 组件，当 `totalCards === 0 && sourceCount === 0` 时显示
- `web/src/lib/i18n.ts`: 新增 14 个 i18n key (zh + en)，覆盖 4 个引导步骤 + 安全说明

### FirstRunGuide 结构
1. **连接模型（或使用安全演示模式）** → `/setup`
2. **添加知识源** → `/sources`
3. **审阅 AI 草稿** → `/drafts`
4. **构建知识库** → `/library`
5. 底部安全说明：MindForge 是本地优先工具，默认不调用真实 LLM、不处理真实私人资料、不写真实 Obsidian vault

### 设计决策
- 仅在完全空 workspace 时显示（不是基于 cookie/localStorage 的"首次访问"判断）
- 引导卡片可点击跳转到对应页面
- 不引入 guided tour / wizard overlay 等复杂交互模式

---

## A2: Import and Review Clarity

### 问题
- SourcesPage 只展示 watched sources，用户不知道还有 CLI one-shot import 和 Library paste/folder import 两种方式
- DraftsPage 在有待审草稿时缺少"为什么 AI 草稿需要审阅"的解释

### 修改
- `web/src/pages/SourcesPage.tsx`: 新增 `ImportPathCard` 组件，在页面顶部展示三种导入路径
- `web/src/pages/DraftsPage.tsx`: 在 header 和 draft list 之间新增 `why_review` 信息横幅（蓝色 info 样式）
- `web/src/lib/i18n.ts`: 新增 12 个 i18n key (zh + en)

### 设计决策
- ImportPathCard 不改变任何现有交互，仅作为信息展示
- why_review 横幅明确：确认操作始终需要显式手动执行，不会自动发生
- 不改变 DraftList 的卡片展示逻辑（已有 source/strategy/value_score/tags 展示）

---

## A3: Export Safety Explanation

### 问题
Export 预览仅显示格式选择器和卡片列表，缺少：
- 格式用途说明（Markdown vs JSON vs OPML vs ZIP 的区别）
- 安全说明（不会写 Obsidian vault 或本地文件系统）

### 修改
- `web/src/pages/LibraryPage.tsx`: 导出预览中新增格式描述行 + 安全说明行
- `web/src/lib/i18n.ts`: 新增 10 个 i18n key (zh + en)

### 设计决策
- 安全说明放在格式选择器下方，斜体、细线分隔
- 格式描述随选择动态变化，同时作为 button title 属性
- 不改变导出 API 行为或格式内容

---

## Gate Results (All Loops)

每个 loop 的 gate 均通过：

| Gate | Command | Exit Code | Notes |
|------|---------|-----------|-------|
| npm build | `npm --prefix web run build` | 0 | 1650 modules, built in <5s |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 | 84 passed |
| ruff | `ruff check src/ tests/ docs/` | 0 | All checks passed |
| full pytest | `python -m pytest tests/ -q --tb=short` | 0 | All passed (1 skipped: conditional) |
| git diff | `git diff --check` | 0 | Clean |

---

## 未做事项

以下 v4.4 roadmap candidate loops 未在本轮执行（授权但未选）：

- A4: Library organization MVP（filters/saved views）
- A5: Recall/Wiki/Export 深层解释（当前基础解释已存在）
- A6: User journey tests（Web smoke gate）

原因：前三项已覆盖最高价值的 friction 点，后三项适合后续单独 spec。

---

## 已知限制

- FirstRunGuide 依赖 `totalCards === 0 && sourceCount === 0` 判断，如果用户先配了模型再清空 workspace，引导仍然不会出现（这是正确的行为：用户已经知道怎么用了）
- ImportPathCard 提到的 CLI one-shot import 需要用户切换到终端，Web 页面无法直接执行
- Export 安全说明是静态文案，不反映实际 API 行为（API 行为由后端保证）

---

## 硬红线遵守

- 未读取 `.env` 或 secrets
- 未调用真实 LLM、Cubox、Upstage 或外部服务
- 未处理真实私人资料
- 未写真实 Obsidian vault
- 未做 RAG answering / embedding / vector DB
- 未新增大型依赖
- 未破坏 explicit approval / human_approved 语义
- 未 auto approve
- 未把 API key / secrets 打印到 logs/DOM/console/notes

---

## 下一步建议

v4.4 Direction A 主路径 UX 深化已完成。建议下一步：

1. **v4.5 Recall/Search Quality Lab** — 建立 recall fixtures、query explain report、BM25 tuning
2. **v4.6 Documentation/System Simplification** — canonical docs index、archive markers、limitations truth
3. **Product decision needed**: 是否继续 v4.5/v4.6 还是进入 v3.7+ 架构债务偿还（web_facade.py 分解等）
