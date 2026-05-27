# Guided Onboarding MVP — Implementation Notes

日期: 2026-05-27

## What was built

Guided Onboarding MVP (v0.7) — 首次运行零配置引导体验。

### Backend (U1-U2)

- **Sample Workspace Service** (`src/mindforge/services/sample_workspace.py`): 生成 6 张 MindForge 概念 demo 知识卡片，纯 fake 数据，不调用 LLM。
- **API Endpoint** (`POST /api/sample-workspace`): 在 `routers/library.py` 中新增，通过 `WebFacade.create_sample_workspace()` 委托。
- Demo 卡片直接创建为 `human_approved` + `approval_method: demo_sample`，系统 demo 内容不经过用户数据的 `ai_draft` → `human_approved` 审批管道。

### Frontend (U3-U7)

- **OnboardingHint** (`web/src/components/OnboardingHint.tsx`): 可关闭的顶部提示横幅，8 个页面通过 AppShell 的 `PAGE_KEY_MAP` 自动注入。
- **QuickStartWizard** (`web/src/components/QuickStartWizard.tsx`): 3 步首次向导（了解 → 创建 → 探索），调用 `POST /api/sample-workspace`。
- **HomePage** 替换旧的 `FirstRunGuide`（~50 行删除），改用 `QuickStartWizard`。
- **AppShell** 新增 `PAGE_KEY_MAP` 和 `<OnboardingHint>` 注入。
- **i18n**: 33 个 zh + 33 个 en key 已加入 `web/src/lib/i18n.ts`。

### Tests (U8)

- `tests/test_sample_workspace.py`: 5 tests — 创建、幂等、字段验证、frontmatter 结构
- `web/src/components/__tests__/OnboardingHint.test.tsx`: 6 tests
- `web/src/components/__tests__/QuickStartWizard.test.tsx`: 7 tests
- `tests/test_web_product_copy.py`: 新增 2 tests（key 完整性 + 组件 useLocale 验证）
- `tests/test_review_approval_boundary.py`: `sample_workspace.py` 加入允许列表

## Decisions & Trade-offs

1. **Demo 卡片直接 human_approved** — 系统 demo 内容，非用户数据。`approval_method: demo_sample` 标记清晰区分。
2. **Per-session dismiss** — OnboardingHint 用 React state 控制关闭，MVP 不持久化。用户刷新后提示重新出现，这是合理行为。
3. **QuickStartWizard 替换 FirstRunGuide** — 旧的 FirstRunGuide 是 4 步卡片网格（不可交互），新 wizard 3 步可执行（真正创建 demo workspace）。
4. **AppShell 注入 OnboardingHint** — 集中管理，避免每个页面单独引入。

## Known Limitations

- OnboardingHint dismiss 不持久化（per-session only）
- Demo 卡片不触发 Graph/Sensemaking
- 首次运行检测仅用 `totalCards === 0 && sourceCount === 0`，不覆盖部分创建场景
- 无页面遮罩 tour overlay

## Gate Results

| Gate | Command | Exit |
|------|---------|------|
| ruff | `ruff check src/ tests/ docs/` | 0 |
| git diff | `git diff --check` | 0 |
| python tests | `python -m pytest tests/ -q` | 0 |
| npm build | `npm --prefix web run build` | 0 |
| vitest | `npm --prefix web run test -- --run` | 0 |
