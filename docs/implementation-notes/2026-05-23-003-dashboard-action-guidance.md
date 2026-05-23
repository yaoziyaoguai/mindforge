# Milestone D: Dashboard & Action Guidance — Implementation Notes

Date: 2026-05-23
Spec: `docs/specs/2026-05-23-003-dashboard-action-guidance-spec.md`

## 1. 实际修改文件

### Modified (12 files)

| File | Change |
|------|--------|
| `src/mindforge_web/schemas.py` | NextAction 新增 `action_key: str \| None = None` |
| `src/mindforge_web/services/web_facade.py` | 4 个 HomePage _next_actions 站点 + 5 个 empty_state NextAction 站点添加 action_key |
| `web/src/api/types.ts` | NextAction interface 新增 `action_key?: string \| null` |
| `web/src/lib/utils.ts` | 新增 `nextActionLabel()` display mapping 函数，9 个 key |
| `web/src/lib/i18n.ts` | 新增 9 个 HomePage section/action guidance i18n key |
| `web/src/components/NextActionCard.tsx` | 接受 `locale` prop，使用 `nextActionLabel()` 优先展示 |
| `web/src/components/EmptyState.tsx` | 接受 `locale` prop，使用 `nextActionLabel()` 优先展示 |
| `web/src/pages/HomePage.tsx` | 3-section layout（系统状态 / 配置检查 / 下一步行动），参数化 detail 文案 |
| `web/src/pages/DraftsPage.tsx` | 传递 `locale` 给 EmptyState |
| `web/src/pages/LibraryPage.tsx` | 传递 `locale` 给 EmptyState |
| `web/src/pages/RecallPage.tsx` | 传递 `locale` 给 EmptyState（3 处） |
| `tests/test_web_product_copy.py` | 新增 8 个 Milestone D 回归测试 |

### New (2 files)

| File | Description |
|------|-------------|
| `docs/dev/copy-policy.md` | UI copy 政策文档，6 条核心规则 + 防回归清单 |
| `docs/specs/2026-05-23-003-dashboard-action-guidance-spec.md` | Milestone D spec |

## 2. Spec 与实现差异

### 2.1 无差异的实现项

- U1: NextAction schema — 可选的 action_key 字段，完全按 spec
- U2: nextActionLabel() display mapping — 完全按 spec
- U3: HomePage 3-section layout — 完全按 spec
- U4: EmptyState action consistency — empty_state NextAction 也添加了 action_key
- U5: copy-policy.md — 完全按 spec
- U6: 回归测试 — 完全按 spec

### 2.2 差异点

- **参数化 i18n 调用方式**: 原计划使用 `t(key, params)` 模式，最终采用代码库已有 convention：`t(key).replace("{count}", String(value))`。这与 WikiStatusBar、WikiSectionRelationshipPreview 等现有用法一致。
- **旧 i18n key 保留**: `home.review_drafts_detail`、`home.manage_sources_detail`、`home.browse_library_detail` 仍在 i18n 字典中（未被引用），不删除以避免意外。
- **EmptyState empty_state NextAction 添加 action_key**: spec 未明确要求，但 U4 审计发现 empty_state NextAction 也缺少本地化支持，一并修复。

## 3. 是否触发 Stop Condition

**否。** 所有 5 个 stop condition 均未触发：
- NextAction action_key 审计: 4 个 HomePage site + 5 个 empty_state site = 9 个 site，均在 1 个文件（web_facade.py），小于 5 文件/20 site 上限
- 未新增后端 API
- 未触碰 provider / approval / recall 语义
- 未进入 mail storage
- Gate 全部 exit code = 0

## 4. action_key 设计

| action_key | 语义 | 使用场景 |
|-----------|------|---------|
| `init_vault` | 初始化知识库 | HomePage next_actions (vault 不存在) |
| `review_drafts` | 审核草稿 | HomePage next_actions (有 pending drafts) |
| `watch_source` | 添加知识源 | HomePage next_actions (无 approved cards) |
| `search_knowledge` | 搜索知识 | HomePage next_actions (默认，系统就绪) |
| `create_drafts` | 新建草稿 | DraftsPage empty_state |
| `search_approved_cards` | 搜索已确认知识 | RecallPage empty_state (empty prompt) |
| `adjust_query` | 调整查询 | RecallPage empty_state (query error) |
| `try_another_query` | 换一个关键词 | RecallPage empty_state (no results) |
| `rebuild_index` | 重建索引 | RecallPage index next_action |

约 30 个其他 NextAction 站点保持 `action_key=None`，前端 fallback 到 `action.label`。

## 5. 后端兼容策略

- `action_key` 默认 `None`，所有现有 NextAction 构造点无需修改即兼容
- Pydantic schema 新增字段为可选，不破坏现有 API contract
- JSON 序列化时 `null` action_key 被序列化为 `null`，前端安全处理

## 6. 前端 Display Mapping 策略

- `nextActionLabel(key, locale)` 返回 `string | null`
- `null` 表示 key 不在映射表中 → 调用方 fallback 到 `action.label`
- key 匹配使用 `Record<Locale, Record<string, string>>` 结构，O(1) 查找
- 禁止字符串匹配推断语言（如 `label.includes("中文")`）

## 7. Copy Policy 决策

见 `docs/dev/copy-policy.md`。核心决策：
- UI copy 必须走 i18n `t()` 函数
- 技术 identifier 降级展示
- 用户内容不翻译
- 格式名保留原文
- NextAction 用 action_key 做 mapping，不靠 label 字符串匹配

## 8. 测试策略

新增 8 个回归测试：
1. `test_next_action_display_mapping_exists` — 验证 9 个 action_key 都在 nextActionLabel 中
2. `test_next_action_card_uses_localized_display` — 验证 NextActionCard 使用 nextActionLabel
3. `test_empty_state_uses_localized_action_label` — 验证 EmptyState 使用 nextActionLabel
4. `test_homepage_i18n_section_keys_complete` — 验证 3 个 section header key
5. `test_homepage_action_guidance_keys_complete` — 验证 6 个参数化 guidance key
6. `test_homepage_uses_localized_action_cards` — 验证 HomePage 传递 locale
7. `test_copy_policy_document_exists` — 验证 copy-policy.md 存在并包含核心规则
8. `test_next_action_does_not_use_label_string_matching` — 反模式检测

## 9. Gate 结果

```
npm --prefix web run build    → EXIT_CODE=0
python -m pytest tests/test_web_product_copy.py -q → 31 passed, EXIT_CODE=0
git diff --check              → EXIT_CODE=0
```

## 10. Browser Smoke 结果

（待执行）

## 11. 剩余 P3/P4

- P3: 其他 30 个 NextAction 站点可逐步添加 action_key
- P3: 旧 i18n key（home.review_drafts_detail 等 3 个）可清理
- P3: EmptyState 的 `action.description` 也可做 display mapping（当前仅 label 本地化）
- P4: StatusCard 的 nextAction inline text 展示与 NextActionCard 的独立卡片展示可进一步统一

## 12. 回退记录

无回退。实现一次通过，未触发 spec review 或 code review 的回退上限。
