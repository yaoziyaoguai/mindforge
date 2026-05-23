---
title: Dashboard & Action Guidance Spec
type: feat
status: draft
origin: docs/plans/2026-05-22-002-feat-web-ux-improvement-plan.md
date: 2026-05-23
---

# Dashboard & Action Guidance — Milestone D

## 1. Background

Milestone A/B/C 完成了 Review 审批流修正、Sidebar 分组导航、全站 i18n 和 visual polish。但 HomePage 仍然是薄薄的状态面板（~33 行），用户看到的是一组数字卡片 + 中英混合的 NextAction 引导。

**当前问题：**

- HomePage StatusCard 只展示原始计数，缺上下文说明。"pending_drafts_count: 6" 不如 "6 张待审核卡片" 直观
- NextAction label 为英文（"Review drafts"），description 为中英混合（"有 ai_draft 等待人工 review..."），用户无法一眼理解
- NextAction 缺少稳定的 `action_key`，前端无法做 localized display mapping，只能直接展示后端生成的自由文本
- 空状态引导虽已在各页面实现，但 action model 不完全一致
- 技术标识（`ai_draft`、`human_approved`、source type 格式名）的使用边界没有书面规则

## 2. Goals

1. **HomePage 升级为行动中心**：每个 StatusCard 回答两个问题 — "当前状态如何？" 和 "我应该做什么？"
2. **NextAction 可本地化**：后端增加可选的 `action_key` 字段，前端通过 display mapping 生成本地化文案
3. **空状态 action model 一致**：所有页面的空状态走统一的 NextAction 模式
4. **Copy policy 固化**：将 i18n 实践中验证的规则写为可引用的工程文档

## 3. Non-goals

- **不改 Setup 页面结构** — 步骤指示器/深度重构留给 Milestone E
- **不改 Review 审批流** — Milestone A 已修，状态良好
- **不改所有 NextAction 构造点** — 仅 HomePage `_next_actions()` 新增 `action_key`，其余站点保持不变（action_key 为可选字段）
- **不改 provider / approval / recall 业务语义**
- **不新增后端趋势 API** — HomePage 仅使用现有 API 数据做更好的组织和展示
- **不引入前端测试框架** — vitest/testing-library 搭建是独立 infra 任务
- **不进入 mail storage / email / mail**

## 4. Scope

### In scope

| Area | What changes |
|------|-------------|
| `NextAction` schema | 新增可选字段 `action_key: str \| None = None` |
| `web_facade.py:_next_actions()` | 4 处 NextAction 构造增加 `action_key` |
| `HomePage.tsx` | 信息架构升级，StatusCard 增加用户化说明，NextAction 分组 |
| `NextActionCard.tsx` | 新增 `action_key` → 本地化 label display mapping，`label` 作为 fallback |
| `StatusCard.tsx` | 增加 guidance text 展示 |
| Copy policy 文档 | 新增 `docs/dev/copy-policy.md` |
| i18n 字典 | 新增 HomePage action guidance 相关 key |
| 测试 | `test_web_product_copy.py` 增加 action guidance / copy policy 相关断言 |

### Out of scope

- All other NextAction construction sites (>6 files, >25 sites) — action_key defaults to None, existing label/description unchanged
- SetupPage refactoring
- Design system infrastructure
- Backend trend/comparison APIs
- Wiki / Library / Recall page changes

## 5. Implementation Units

### U1: NextAction schema — optional action_key

**Goal**: 在 `NextAction` Pydantic model 中增加可选的 `action_key` 字段，向后兼容，前端可用于 localized display mapping。

**Files**:
- Modify: `src/mindforge_web/schemas.py` — `NextAction` 增加 `action_key: str | None = None`
- Modify: `web/src/api/types.ts` — `NextAction` 接口增加 `action_key?: string | null`

**Approach**:
- 字段为 `Optional[str]`，默认 `None`，完全向后兼容
- 现有构造点不需要修改（action_key 自动为 None）
- 仅 HomePage `_next_actions()` 的 4 处构造点增加 `action_key` 赋值

**Verification**:
- 所有现有 NextAction 构造点保持兼容（字段可选，默认 None）
- TypeScript 类型编译通过
- 前端接收 `action_key: null` 时不崩溃，走 fallback 路径

---

### U2: NextAction localized display mapping

**Goal**: 前端接收到 `action_key` 时使用本地化文案展示，`action_key` 缺失时安全 fallback 到 `label`。

**Files**:
- Modify: `web/src/lib/utils.ts` — 新增 `nextActionLabel(actionKey, locale)` display mapping 函数
- Modify: `web/src/components/NextActionCard.tsx` — 使用 mapping 展示 label
- Modify: `web/src/components/StatusCard.tsx` — NextAction 区段使用 mapping
- Modify: `web/src/lib/i18n.ts` — 新增 action guidance zh/en key

**Approach**:
```typescript
// utils.ts — 稳定的 action_key → 本地化文案映射
export function nextActionLabel(key: string | null | undefined, locale?: Locale): string | null {
  if (!key) return null;  // 无 key 时返回 null，调用方 fallback 到 action.label
  const labels: Record<Locale, Record<string, string>> = {
    zh: {
      init_vault: "初始化知识库",
      review_drafts: "审核草稿",
      watch_source: "添加知识源",
      search_knowledge: "搜索知识",
    },
    en: {
      init_vault: "Initialize vault",
      review_drafts: "Review drafts",
      watch_source: "Watch or import source",
      search_knowledge: "Search knowledge",
    },
  };
  return labels[locale ?? "zh"]?.[key] ?? null;
}
```

NextActionCard 使用逻辑：
```typescript
const displayLabel = nextActionLabel(action.action_key, locale) ?? action.label;
```

**关键设计决策**:
- `action_key` 是稳定的 machine-readable identifier，不随 locale 变化
- `label` / `description` 保留为兼容 fallback，缺 `action_key` 时直接展示
- 不靠英文 label 字符串匹配做语言检测
- 映射函数返回 `null` 当 key 不在映射表中，调用方安全处理

**中文学习型注释**: 说明 `action_key` 是展示映射的稳定键，不是业务标识；`label` 是未翻译时的 fallback；i18n 只改变 presentation，不改变 action 行为。

**Verification**:
- `action_key` 存在时展示本地化文案
- `action_key` 为 null/undefined 时 fallback 到 `action.label`
- `action_key` 为未知值（不在映射表）时 fallback 到 `action.label`
- zh/en 切换后 NextAction 文案正确更新

---

### U3: HomePage information architecture upgrade

**Goal**: HomePage 从薄状态面板升级为行动中心。StatusCard 增加上下文说明和下一步引导，NextAction 卡片按优先级分组展示。

**Files**:
- Modify: `web/src/pages/HomePage.tsx`
- Modify: `web/src/components/StatusCard.tsx`

**Approach**:

HomePage 结构调整为三区：

```
┌─────────────────────────────────────┐
│  系统状态                            │
│  [待审核: 6]  [知识源: 3]  [已确认: 15]  │
│  每个卡片含: 数值 + 用户化说明 + 快捷操作   │
├─────────────────────────────────────┤
│  配置检查                            │
│  [模型: 就绪]  [搜索: 可用]           │
│  每个卡片含: 状态图标 + 用户化说明       │
├─────────────────────────────────────┤
│  下一步行动                           │
│  [需要处理: Review drafts →]          │
│  [建议操作: Watch source →]           │
│  卡片含: 本地化标题 + 说明 + 目标链接    │
└─────────────────────────────────────┘
```

- StatusCard 的 `detail` prop 已在显示，改为更具体的用户化说明（通过 i18n key）
- NextAction 卡片使用 `nextActionLabel()` 展示本地化标题
- 保留现有 `onNavigate` callback 模式不改路由

**Verification**:
- HomePage 渲染时不崩溃
- StatusCard 区段分组清晰
- NextAction 展示本地化文案（zh/en）
- 所有导航链接正常

---

### U4: EmptyState action model consistency

**Goal**: 确认所有页面空状态走统一的 NextAction 模式，不一致的修正。

**Files**:
- Review (只读): `DraftsPage.tsx`, `LibraryPage.tsx`, `RecallPage.tsx`, `WikiPage.tsx`
- Modify if needed: 如有空状态未使用 NextAction 模式的，修正

**Approach**:
- Audit 所有页面的空状态实现
- 确保每个空状态都有 `NextAction` 提供下一步引导
- 不做新 UI 组件，仅对齐现有模式

**Verification**:
- 所有页面空状态提供明确的下一步 action
- 无空白面板

---

### U5: Copy policy hardening

**Goal**: 将 i18n 实践中验证的规则写为可引用的工程文档。

**Files**:
- Create: `docs/dev/copy-policy.md`

**Content**:

1. **用户可见 UI copy 必须本地化** — 所有 `t()` 调用，zh/en 字典完整
2. **技术 identifier 降级展示** — `font-mono`、小字号、灰色、括号内，满足开发排查但不抢占用户注意力
3. **用户内容不翻译** — 卡片正文、source title、用户自定义字段
4. **专有名词可保留原名** — Markdown/PDF/HTML 等格式名、BM25 等算法名、MindForge 等产品名
5. **后端 internal id 不直接做主展示文案** — 通过 display mapping 函数转为本地化标签
6. **新增文案必须同时提供 zh/en** — 缺一不可，测试会验证

**Verification**:
- 文档内容与当前实践一致
- 作为后续开发的参考标准

---

### U6: Regression guard for i18n/copy

**Goal**: 增强测试覆盖，防止 i18n/copy 回归。

**Files**:
- Modify: `tests/test_web_product_copy.py`

**Approach**:
- 新增 `test_next_action_keys` — 验证 action_key 映射表中的 key 在 zh/en 字典中完整
- 新增 `test_copy_policy_technical_identifiers` — 验证技术标识不出现在主展示文案中
- 新增 `test_home_page_action_guidance` — 验证 HomePage 相关 key 完整

**Verification**:
- 所有新测试通过

---

## 6. File Scope

### 允许修改

| File | Unit | Change |
|------|------|--------|
| `src/mindforge_web/schemas.py` | U1 | NextAction 增加 `action_key: str \| None = None` |
| `src/mindforge_web/services/web_facade.py` | U1 | `_next_actions()` 4 处增加 `action_key` |
| `web/src/api/types.ts` | U1 | NextAction 接口增加 `action_key?: string \| null` |
| `web/src/lib/utils.ts` | U2 | 新增 `nextActionLabel()` |
| `web/src/components/NextActionCard.tsx` | U2 | 使用 `nextActionLabel()` |
| `web/src/components/StatusCard.tsx` | U2, U3 | NextAction 区段使用 mapping |
| `web/src/pages/HomePage.tsx` | U3 | 信息架构升级 |
| `web/src/lib/i18n.ts` | U2, U3 | 新增 action guidance key |
| `docs/dev/copy-policy.md` | U5 | 新建 copy policy 文档 |
| `tests/test_web_product_copy.py` | U6 | 新增回归测试 |

### 禁止修改

- `src/` 除 schemas.py 和 web_facade.py 外的所有文件
- provider / approval / recall 相关代码
- mail storage 相关代码
- `.env` / secrets

## 7. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `action_key` 映射表条目过多 | Low | 维护负担 | 仅 HomePage 的 4 个 key，后续按需扩展 |
| 现有 NextActionCard 调用方行为改变 | Low | 运行时错误 | `action_key` 为 optional，缺省时行为与旧代码完全一致 |
| HomePage 重构引入 layout 回归 | Medium | 视觉破损 | 保留现有 grid 结构，仅增强内容层 |
| Copy policy 与实际实践不一致 | Low | 文档误导 | 基于已验证的 i18n follow-up 实践编写 |

## 8. Stop Conditions

1. **NextAction 构造点审计**: 如果需要改动的构造点超过 1 个文件或 5 处（仅限 HomePage `_next_actions()`），停止并将 action_key 推广拆为独立 mini-spec
2. **HomePage 需要新 API**: 如果 StatusCard 升级需要的趋势/比较数据当前 API 不返回，降级为纯前端 layout + copy 优化，不新增 API
3. **触碰 provider / approval / recall 语义**: 立即停止
4. **出现 mail storage / email scope**: 立即停止
5. **npm build / pytest / git diff --check 任一 exit code ≠ 0**: 修复后才能继续

## 9. Test Strategy

### 现有测试增强
- `test_web_product_copy.py`:
  - 新增 `test_next_action_keys` — 验证 action_key 映射表 key 在 zh/en 字典完整
  - 新增 `test_home_page_action_guidance_keys` — 验证 HomePage 相关 i18n key
  - 新增 `test_copy_policy_technical_identifiers` — 验证技术标识不出现在主文案中

### Gate
- `npm --prefix web run build` — EXIT_CODE=0
- `python -m pytest tests/test_web_product_copy.py -q` — EXIT_CODE=0
- `git diff --check` — EXIT_CODE=0

### Browser smoke
- HomePage 可打开，中文/英文模式正常
- NextAction 文案本地化正确
- Language toggle 后 action copy 更新
- Sidebar 无回归
- Console 无 error

## 10. Execution Plan

按 recursive engineering workflow loop：

1. **写 spec** (本文档)
2. **自审 spec** — 检查 scope / stop conditions / non-goals / 与已有 MS 的一致性
3. **实现**: U1 → U2 → U3 → U4 → U5 → U6（U1 是 U2 的前提，U2 是 U3 的前提）
4. **写 implementation notes**
5. **自审代码**
6. **运行 gate**
7. **Browser smoke**
8. **Commit + push main**

## 11. Open Questions

### Resolved During Spec

- **action_key 是否所有 NextAction 都要加?** 否 — 仅 HomePage `_next_actions()` 的 4 个 key，action_key 为可选字段，其余站点不变
- **HomePage 是否新增后端 API?** 否 — 仅用现有 `/api/home` 返回数据做更好的前端组织
- **Setup 深度重构?** 留给 Milestone E
- **NextAction i18n 是否独立 Milestone?** 否 — 并入 Dashboard & Action Guidance 作为 U1+U2

### Deferred to Implementation

- StatusCard guidance text 的具体 i18n key 命名
- HomePage 三段式布局的具体视觉实现
- NextAction 映射表的完整 key 列表（初始 4 个，实现时根据所有 `_next_actions()` 分支确定）
