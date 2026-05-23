# Web i18n Mixed-Language Follow-Up Spec

**日期**: 2026-05-23
**类型**: fix (i18n / product copy)
**状态**: draft
**来源**: i18n Mixed-language Targeted Review (2026-05-23)

---

## 1. 背景

Milestone C 已实现 i18n 基础设施：`web/src/lib/i18n.ts` 提供 `t(key, locale)` 函数 + `LocaleProvider` + 85+ zh/en 键值对，`web/src/lib/utils.ts` 提供 `friendlyStatus()` 状态码映射。Sidebar、HomePage、DraftsPage、LibraryPage、RecallPage 等核心页面已通过 `useLocale()` 实现中英文切换。

但 targeted review 发现当前 Web 仍然存在大量中英文混用问题，尤其集中在以下区域：

- **SetupPage**: 虽然是最大的 i18n 消费者，但仍有 ~20 处硬编码英文 + 后端数据直出混用
- **SourcesPage**: 0 次 `useLocale()` 调用，~40+ 处硬编码英文
- **TrashPage**: 0 次 `useLocale()` 调用，~15 处硬编码英文
- **Wiki 组件族**: 0 次 `useLocale()` 调用，~25 处硬编码英文
- **SourceAddPanel**: 0 次 `useLocale()` 调用，~20 处硬编码英文

问题根因分 4 类：

| 类别 | 描述 | 示例 |
|------|------|------|
| **C1** | 后端硬编码数据被前端直接展示 | `step.label = "Triage / 初筛"`、`active_strategy_status = "default workflow"` |
| **C2** | 前端组件硬编码英文字符串，未使用 t() | `"Knowledge vault"`、`"Sources"`、`"Process now"` |
| **C3** | i18n 字典缺少对应 key | `sources.*` 只有一个 `sources.edit_frequency` |
| **C4** | 已有映射覆盖率不足 | `friendlyStatus()` 覆盖 7 种卡片状态，但不覆盖 source 状态、workflow 策略状态 |

---

## 2. 问题分类

### 2.1 前端硬编码英文 (C2)

组件源码中直接写了英文字符串，未通过 `t()` 获取。

### 2.2 i18n 字典缺 key (C3)

`web/src/lib/i18n.ts` 的 `copy` 字典缺少以下命名空间的 key：
- `sources.*`（仅 `sources.edit_frequency`）
- `trash.*`（无）
- `wiki.*`（无）
- `source_add.*`（无）
- `setup.model_detail.*` — 模型卡片详情标签
- `setup.diagnostics.*` — 诊断区标签/值
- `setup.wiki_model.*` — Wiki 模型选择区文案

### 2.3 已有 key 但组件未使用 t() (C2+C3)

StatusCard 组件接受 `label`/`value` 字符串 props，调用方负责翻译。但 SetupPage 的调用点未翻译：
```tsx
<StatusCard label="Knowledge vault" value={... ? "Ready" : "Created automatically"} ... />
```

### 2.4 后端返回数据被直接展示 (C1)

- `step.label` = `"Triage / 初筛"`、`"Distill / 提炼"` — 混合中英文
- `step.purpose` — 中文说明，但来自后端硬编码，格式不稳定
- `active_strategy_label` = `"Knowledge Card Workflow"` — 英文
- `active_strategy_status` = `"default workflow"` — 英文
- `active_strategy_description` — 英文
- `source.status_label`、`source.due_status`、`source.processing_status` — 后端直出

### 2.5 用户内容 / 专有名词 / source title 不应翻译

- 用户创建的 source title、卡片内容、Wiki 正文 → **不翻译**
- 产品名 "MindForge" → **不翻译**
- 技术标识 `source_id`、`run_id` → **保留但降级展示**
- adapter 名（如 "openai"、"anthropic"）→ **保留原名**

### 2.6 技术 identifier 应保留但降级展示

- `step.id`（如 "triage"、"distill"）→ 保留为次要信息
- `prompt_version`（如 "v1"）→ 保留
- `modelId` → 保留（用户自定义标识）

### 2.7 按钮、label、help text 必须本地化

所有用户可见 UI copy 必须走 i18n。

---

## 3. 修复原则

1. **用户可见 UI copy 必须走 i18n** — 所有 button、label、heading、help text、placeholder、status 文案
2. **后端 internal id 不直接作为主展示文案** — 对 workflow/strategy/source status 等后端标识，前端 presentation 层做 localized display mapping
3. **不改后端 API** — 所有修复在 `web/src/` 和 `tests/` 内完成
4. **不改内部业务状态字段** — `status`、`processing_status` 等字段值不变，仅改变展示
5. **不翻译用户内容** — 卡片正文、source title、Wiki 内容保持原样
6. **不翻译产品名/adapter 名** — 但需要用本地化说明解释
7. **允许保留技术 id** — 但只能作为 secondary/developer hint（小字、灰色、括号内）

---

## 4. 修复范围

### 4.1 文件允许清单

| 文件 | 改动类型 |
|------|----------|
| `web/src/lib/i18n.ts` | 新增 keys + zh/en 字典条目 |
| `web/src/lib/utils.ts` | 新增 display mapping 函数（workflow step、source status、strategy status） |
| `web/src/pages/SetupPage.tsx` | 硬编码英文 → t() + display mapping |
| `web/src/pages/SourcesPage.tsx` | 全面 i18n 化 + display mapping |
| `web/src/pages/TrashPage.tsx` | 全面 i18n 化 |
| `web/src/pages/WikiPage.tsx` | i18n 化错误消息 |
| `web/src/components/SourceAddPanel.tsx` | 全面 i18n 化 |
| `web/src/components/StatusCard.tsx` | 无需改动（已支持外部翻译） |
| `web/src/components/wiki/WikiHeader.tsx` | i18n 化 |
| `web/src/components/wiki/WikiStatusBar.tsx` | i18n 化 |
| `web/src/components/wiki/WikiEmptyState.tsx` | i18n 化 |
| `web/src/components/wiki/WikiErrorState.tsx` | i18n 化 |
| `web/src/components/wiki/WikiLoadingState.tsx` | i18n 化 |
| `web/src/components/wiki/WikiAdvancedActions.tsx` | i18n 化 |
| `web/src/components/wiki/WikiReadingPane.tsx` | i18n 化 section headings |
| `web/src/components/wiki/WikiTOC.tsx` | i18n 化 |
| `tests/test_web_product_copy.py` | 新增 SourcesPage/TrashPage/Wiki i18n 断言 |
| `docs/implementation-notes/2026-05-23-002-web-i18n-mixed-language-follow-up.md` | 新增 |

### 4.2 文件禁止清单（硬性红线）

- `src/mindforge/` — 所有后端文件
- `src/mindforge_web/` — 所有后端文件（包括 `web_config_service.py`）
- `src/mindforge/strategies/` — 策略定义
- `src/mindforge/strategy_display.py` — 策略展示
- `.env` / secrets
- `package.json` / `package-lock.json` — 不新增依赖

---

## 5. Setup 页面逐项修复

### 5.1 StatusCard 区域（lines 270-271）

| 现状 | 来源 | 操作 | 推荐 key |
|------|------|------|----------|
| `label="Knowledge vault"` | C2 硬编码 | 改为 `t("setup.knowledge_vault")` | 已有 |
| `value="Ready"` | C2 硬编码 | 改为 `t("setup.status_ready")` | `setup.status_ready` |
| `value="Created automatically"` | C2 硬编码 | 改为 `t("setup.vault_auto_created")` | `setup.vault_auto_created` |
| `label="Model config"` | C2 硬编码 | 改为 `t("setup.model_config_status")` | `setup.model_config_status` |
| `value="Configured"` | C2 硬编码 | 改为 `t("setup.model_configured")` | `setup.model_configured` |
| `value="Check setup"` | C2 硬编码 | 改为 `t("setup.model_check_setup")` | `setup.model_check_setup` |

### 5.2 模型卡片详情标签（lines 458-461）

| 现状 | 操作 | 推荐 key |
|------|------|----------|
| `<div>type</div>` | 改为 `t("setup.model_type")` | 已有 |
| `<div>base URL</div>` | 改为 `t("setup.model_base_url")` | 已有 |
| `<div>model</div>` | 改为 `t("setup.model_name")` | 已有 |
| `<div>default</div>` | 改为 `t("setup.model_is_default")` | `setup.model_is_default` |
| `"Yes"/"No"` | 改为 `t("shared.yes")` / `t("shared.no")` | `shared.yes` / `shared.no` |

### 5.3 API key 状态标签（line 445）

| 现状 | 操作 | 推荐 key |
|------|------|----------|
| `API key: {apiKeyLabel}` | `apiKeyLabel` 已是后端返回的展示文案，但前缀 "API key:" 应走 i18n | `setup.model_api_key` 已有，用于 label |

`apiKeyLabel` 本身来自后端的 `api_key_status_label` 或前端拼接，属于 C1。由于 api_key 展示信息来自后端，且已在 `api_key_source` 分支中做了前端拼接（`configured · ****`），这部分保持现状，仅改前缀 label。

### 5.4 Workflow 区域（lines 497-550）

**Backend 数据直出的 workflow step 展示** — 这是 Setup 页面最核心的混用问题。

| 现状 | 来源 | 操作 |
|------|------|------|
| `step.label` = "Triage / 初筛" 等 | C1 后端 | 前端做 step label mapping，不直接展示后端 label |
| `step.purpose` | C1 后端 | 保留中文 purpose，但加 zh/en 双版本作为 fallback |
| `active_strategy_label` = "Knowledge Card Workflow" | C1 后端 | 前端 mapping → 中文 "知识卡片工作流" / 英文 "Knowledge Card Workflow" |
| `active_strategy_status` = "default workflow" | C1 后端 | 前端 mapping → 中文 "默认工作流" / 英文 "Default workflow" |
| `active_strategy_description` | C1 后端 | 保留，后端提供的是产品说明，已是用户向文案 |
| `<label>Model</label>` (line 530) | C2 硬编码 | 改为 `t("setup.model_name")` |
| `"Prompt: ..."` (line 558) | C2 硬编码 | 改为 `t("setup.prompt_preview_title")` |
| `"View prompt (v1)"` | 按钮已用 `t("setup.workflow_view_prompt")`，版本号保留 | OK |

**修复策略**：在 `web/src/lib/utils.ts` 或 `web/src/lib/i18n.ts` 新增 lookup table：

```typescript
// workflow step id → display label mapping
const WORKFLOW_STEP_LABELS: Record<Locale, Record<string, string>> = {
  zh: {
    triage: "初筛",
    distill: "提炼",
    link_suggestion: "关联建议",
    review_questions: "复习问题",
    action_extraction: "行动项提取",
  },
  en: {
    triage: "Triage",
    distill: "Distill",
    link_suggestion: "Link Suggestion",
    review_questions: "Review Questions",
    action_extraction: "Action Extraction",
  },
};

// strategy status → display label mapping
const STRATEGY_STATUS_LABELS: Record<Locale, Record<string, string>> = {
  zh: { "default workflow": "默认工作流" },
  en: { "default workflow": "Default workflow" },
};

// strategy display name mapping（key 是后端 active_strategy_label 的值）
const STRATEGY_NAME_LABELS: Record<Locale, Record<string, string>> = {
  zh: { "Knowledge Card Workflow": "知识卡片工作流" },
  en: { "Knowledge Card Workflow": "Knowledge Card Workflow" },
};
```

### 5.5 Wiki 模型选择区（lines 581-589）

| 现状 | 操作 | 推荐 key |
|------|------|----------|
| `"Use default model"` | 改为 `t("setup.wiki_use_default")` | `setup.wiki_use_default` |
| `"Complete model setup to generate Wiki."` | 改为 `t("setup.wiki_no_model_hint")` | `setup.wiki_no_model_hint` |
| `"Will use ${modelId} for Wiki synthesis."` | 改为 `t("setup.wiki_will_use_model")` + 插值 | `setup.wiki_will_use_model` |

### 5.6 诊断区（lines 612-615）

| 现状 | 操作 | 推荐 key |
|------|------|----------|
| `<dt>Knowledge vault</dt>` | 改为 `t("setup.knowledge_vault")` | 已有 |
| `<dt>Model configured</dt>` | 改为 `t("setup.diag_model_configured")` | `setup.diag_model_configured` |
| `<dt>Secret configured</dt>` | 改为 `t("setup.diag_secret_configured")` | `setup.diag_secret_configured` |
| `<dt>Last validation result</dt>` | 改为 `t("setup.diag_last_validation")` | `setup.diag_last_validation` |
| `<dd>Yes</dd> / <dd>No</dd> / <dd>Ready</dd>` | 改为 `t("shared.yes/no")` / `t("setup.status_ready")` | shared |

### 5.7 验证错误消息（lines 160-206）

| 现状 | 操作 | 推荐 key |
|------|------|----------|
| `"Model id is required."` | 改为 `t("setup.validation.model_id_required")` | 新增 |
| `"Type is required."` | 改为 `t("setup.validation.type_required")` | 新增 |
| `"Model name is required."` | 改为 `t("setup.validation.model_name_required")` | 新增 |
| `"Cannot delete model ... it is the default model."` | 改为模板字符串 | `setup.validation.cannot_delete_default` |
| `"Cannot delete model ... referenced by routing steps"` | 改为模板字符串 | `setup.validation.cannot_delete_routed` |

### 5.8 已使用 t() 但 zh 值仍是英文的项

| key | 当前 zh 值 | 修复 |
|-----|-----------|------|
| `setup.default_model` | "Default model" | → "默认模型" |
| `setup.default_model_desc` | "Workflow steps without an explicit route use this model." | → "未指定路由的工作流步骤将使用此模型。" |
| `setup.processing_workflow` | "Processing workflow" | → "处理工作流" |
| `setup.processing_workflow_desc` | "MindForge turns sources..." | → 中文 |
| `setup.wiki_generation` | "Wiki generation" | → "Wiki 生成" |
| `setup.knowledge_vault` | "Knowledge vault" | → "知识库目录" |
| `setup.knowledge_vault_desc` | "MindForge stores approved cards..." | → 中文 |
| `setup.diagnostics` | "Diagnostics for advanced users" | → "高级诊断" |
| `setup.diagnostics_desc` | "These are read-only..." | → 中文 |
| `setup.validation_passed` | "Validation passed" | → "验证通过" |
| `setup.no_model_configured` | "No model configured" | → "未配置模型" |
| `setup.workflow_uses_default` | "(uses default)" | → "（使用默认）" |
| `setup.workflow_active` | "Active workflow" | → "当前工作流" |

这些 zh 值在 Milestone C 时只提供了英文，需要补齐中文。

---

## 6. Sources / Odysseus 页面修复范围

### 6.1 SourcesPage 全面 i18n 化

当前 SourcesPage **0 次 useLocale() 调用**。需要：

1. 引入 `useLocale()`
2. 所有硬编码英文字符串通过 `t()` 获取
3. 后端数据字段（status_label、due_status、processing_status）通过 display mapping 展示

### 6.2 逐项修复清单

| 现状（硬编码英文） | 推荐 key | 说明 |
|---|---|---|
| `<h1>Sources</h1>` | `sources.title` | 页面标题 |
| `"MindForge monitors local files..."` | `sources.subtitle` | 页面说明 |
| `"Add source in Setup"` | `sources.add_source_in_setup` | 按钮文案（出现 2 次） |
| `"Watched sources"` | `sources.watched_sources` | 区块标题 |
| `"Manage existing watched files..."` | `sources.watched_sources_desc` | 区块说明 |
| `"Source details:"` | `sources.source_details` | |
| `"Path"` | `sources.path` | |
| `"Status"` | `sources.status` | SummaryItem label |
| `"Run status"` | `sources.run_status` | |
| `"Last scan"` | `sources.last_scan` | |
| `"Last updated"` | `sources.last_updated` | |
| `"Next scan / Due"` | `sources.next_scan_due` | |
| `"Frequency"` | `sources.frequency` | |
| `"Last run summary"` | `sources.last_run_summary` | |
| `"New"` / `"Changed"` / `"Missing"` / `"Skipped"` / `"Drafts created"` / `"Errors"` | `sources.metric.*` | SummaryMetric labels |
| `"Actions"` | `sources.actions` | |
| `"Process now"` / `"Processing..."` | `sources.process_now` / `sources.processing` | |
| `"Open related knowledge"` | `sources.open_related_knowledge` | |
| `"Edit frequency"` | `sources.edit_frequency` | 已有 key |
| `"Copy path"` / `"Copy display path"` | `sources.copy_path` / `sources.copy_display_path` | |
| `"Stop watching"` | `sources.stop_watching` | |
| `"Built-in inbox"` / `"User-added source"` | `sources.builtin_inbox` / `sources.user_added_source` | source type 标签 |
| `"Recursive: yes"` / `"Recursive: no"` | `sources.recursive_yes` / `sources.recursive_no` | |
| `"Diagnostics"` | `sources.diagnostics` | |
| `"Skipped reasons"` | `sources.skipped_reasons` | |
| `"Advanced / Technical details"` | `sources.advanced_tech_details` | |
| `"This only stops future monitoring..."` | `sources.stop_watching_warning` | 确认消息 |
| `"Removing a watched source only stops..."` | `sources.remove_warning` | |
| `"Processing in the background..."` | `sources.processing_background` | |
| `"Starting background processing..."` | `sources.starting_background` | |
| `"Try Process now again..."` | `sources.try_process_again` | |
| `"No draft was generated..."` | `sources.no_draft_generated` | |
| `"No safe source path to copy."` | `sources.no_safe_path` | |
| `"Copied source path."` | `sources.copied_source_path` | |
| `"Copied safe display path only."` | `sources.copied_safe_path` | |
| `"Copy path failed"` | `sources.copy_path_failed` | |
| `"Source path not available"` | `sources.source_path_unavailable` | |
| `"Request failed"` / `"Process failed"` / `"Edit frequency failed"` | 复用 `shared.*` 或新增 `sources.*` | |

### 6.3 source status / run status display mapping

现在 `source.status_label` 直出后端值。对需要映射的值做前端 lookup：

```typescript
// source.processing_status → display label
const SOURCE_RUN_STATUS_LABELS: Record<Locale, Record<string, string>> = {
  zh: {
    idle: "空闲",
    queued: "排队中",
    running: "处理中",
    completed: "已完成",
    failed: "失败",
    partial_failed: "部分失败",
  },
  en: {
    idle: "Idle",
    queued: "Queued",
    running: "Running",
    completed: "Completed",
    failed: "Failed",
    partial_failed: "Partial failure",
  },
};

// source.status → display label
const SOURCE_STATUS_LABELS: Record<Locale, Record<string, string>> = {
  zh: { active: "监控中", paused: "已暂停", error: "异常" },
  en: { active: "Watching", paused: "Paused", error: "Error" },
};

// source.due_status → display label
const SOURCE_DUE_STATUS_LABELS: Record<Locale, Record<string, string>> = {
  zh: { due: "到期", overdue: "已逾期", upcoming: "未到", manual: "手动" },
  en: { due: "Due", overdue: "Overdue", upcoming: "Upcoming", manual: "Manual" },
};
```

### 6.4 frequency 选项 i18n

`SourceAddPanel` 中的 `frequencyOptions` 当前硬编码英文。改为函数，接受 locale 参数：

```typescript
export function frequencyOptions(locale: Locale) { ... }
```

或在组件内用 t() 映射。

### 6.5 专有名词保留

以下不翻译：
- **source adapter 名**：如 "local_fs"、"cubox" — 保留原名
- **用户 source title / path**：用户内容
- **产品名 "MindForge"**
- **"BM25"** — 算法名
- **run_id** — 技术标识

---

## 7. Trash 页面修复范围

### 7.1 逐项修复

| 现状 | 推荐 key |
|------|----------|
| `<h1>Trash</h1>` | `trash.title` |
| `"Trash contains knowledge cards..."` | `trash.subtitle` |
| `"Trash is empty."` | `trash.empty` |
| `"Approved"` / `"Draft"` | 复用 `friendlyStatus()` 映射 |
| `"Previous status"` | `trash.previous_status` |
| `"Trashed at"` | `trash.trashed_at` |
| `"Original path"` | `trash.original_path` |
| `"Source title"` | `trash.source_title` |
| `"Restore"` | `trash.restore` |
| `"Close"` | `shared.close` 已有 |
| `"Select a trashed card to preview."` | `trash.select_to_preview` |
| `"Failed to load card detail"` | `trash.load_failed` |
| `"Restore failed"` | `trash.restore_failed` |

---

## 8. Wiki 组件族修复范围

WikiPage 本身不直接渲染大量文案（委托给子组件），但子组件几乎未 i18n 化。

### 8.1 WikiHeader

| 现状 | 操作 |
|------|------|
| `title = "Wiki"` | 默认值改为 `t("wiki.title")` |
| description 硬编码 | 改为 `t("wiki.subtitle")` |

### 8.2 WikiStatusBar

| 现状 | 操作 |
|------|------|
| `"Status: "` | `t("wiki.status_label")` |
| `"Ready"` / `"Not built"` | `t("wiki.status_ready")` / `t("wiki.status_not_built")` |
| `"Last rebuilt: "` | `t("wiki.last_rebuilt")` |
| `"Cards in Wiki: "` | `t("wiki.cards_in_wiki")` |
| `"Knowledge cards: "` | `t("wiki.knowledge_cards")` |
| `"New approved knowledge..."` | `t("wiki.new_approved_hint")` |
| `"Rebuild Wiki with LLM synthesis"` | `t("wiki.rebuild_tooltip")` |
| `"Refresh Wiki"` / `"Generate Wiki"` | `t("wiki.refresh")` / `t("wiki.generate")` |

### 8.3 WikiEmptyState

| 现状 | 操作 |
|------|------|
| `"No approved cards"` + description | `t("wiki.empty.no_approved")` |
| `"Model setup required"` + description | `t("wiki.empty.model_required")` |
| `"Wiki not built yet"` + description | `t("wiki.empty.not_built")` |

### 8.4 WikiErrorState

| 现状 | 操作 |
|------|------|
| `"Wiki unavailable"` | `t("wiki.error_unavailable")` |
| `"Retry"` | `t("wiki.retry")` |

### 8.5 WikiLoadingState

| 现状 | 操作 |
|------|------|
| `"Building Wiki"` | `t("wiki.building")` |
| description | `t("wiki.building_desc")` |

### 8.6 WikiAdvancedActions

| 现状 | 操作 |
|------|------|
| `"Troubleshooting"` | `t("wiki.troubleshooting")` |
| description | `t("wiki.troubleshooting_desc")` |
| `"Safe fallback rebuild"` | `t("wiki.safe_fallback_rebuild")` |

### 8.7 WikiReadingPane

| 现状 | 操作 |
|------|------|
| `"Open Questions"` | `t("wiki.open_questions")` |
| `"Additional knowledge cards"` | `t("wiki.additional_cards")` |
| `"Warnings"` | `t("wiki.warnings")` |

### 8.8 WikiTOC

| 现状 | 操作 |
|------|------|
| `"Contents"` | `t("wiki.contents")` |
| `"Hide Contents"` | `t("wiki.hide_contents")` |
| `"(untitled)"` | `t("wiki.untitled_section")` |

### 8.9 WikiPage

| 现状 | 操作 |
|------|------|
| `"Failed to load wiki content from server."` | `t("wiki.load_failed")` |
| `"Wiki rebuild failed due to a network or server error."` | `t("wiki.rebuild_failed")` |

---

## 9. SourceAddPanel 修复

SourceAddPanel 位于 SetupPage 的 step="sources" 和 SourcesPage 共用。

| 现状 | 推荐 key |
|------|----------|
| `"Add a file or folder"` | `source_add.title` |
| `"MindForge automatically detects..."` | `source_add.desc` |
| `"Manual means no automatic scanning..."` | `source_add.manual_desc` |
| `"No model configured..."` | `source_add.no_model_warning` |
| `"Add a model in Setup"` | `source_add.add_model_link` |
| `"Path input"` | `source_add.path_input` |
| `"Pick file name"` + tooltip | `source_add.pick_file` |
| `"Pick folder name"` + tooltip | `source_add.pick_folder` |
| `"Frequency"` | `source_add.frequency` |
| `"Add source"` | `source_add.add_source` |
| `"Add and process now"` | `source_add.add_and_process` |
| `"Type or paste the full absolute path..."` | `source_add.path_hint` |
| `"View in Sources"` | `source_add.view_in_sources` |
| `"Configure a model before processing"` | `source_add.configure_model_first` |
| frequency options labels（"Manual"、"Hourly" 等） | frequency options i18n |
| `"Starting background processing..."` | `source_add.starting_background` |
| `"Adding source..."` | `source_add.adding` |
| `"Request failed"` | `source_add.request_failed` |

---

## 10. Sidebar 修复

Sidebar 已使用 `useLocale()`，但语言切换按钮的 title 属性仍有硬编码：

| 现状 | 操作 | 推荐 key |
|------|------|----------|
| `title="Switch to English"` | 改为 `t("nav.switch_to_en")` | `nav.switch_to_en` |
| `title="切换到中文"` | 改为 `t("nav.switch_to_zh")` | `nav.switch_to_zh` |

---

## 11. 全站扫描范围

### 11.1 已确认 i18n 完整的页面（无需大改）

- **HomePage**: 使用 `useLocale()`，所有文案通过 t() — 无需改动
- **DraftsPage**: 使用 `useLocale()`，所有文案通过 t() — 无需改动
- **LibraryPage**: 使用 `useLocale()`，所有文案通过 t() — 无需改动
- **RecallPage**: 使用 `useLocale()`，所有文案通过 t() — 无需改动

### 11.2 需修复的页面

| 页面/组件 | 当前 i18n 状态 | 修复量估计 |
|-----------|---------------|-----------|
| SetupPage | 部分 i18n（~20 处混用） | 中等 |
| SourcesPage | 0 i18n | 大 |
| TrashPage | 0 i18n | 中等 |
| WikiPage | 部分（2 处错误消息硬编码） | 小 |
| Wiki 子组件（8 个） | 0 i18n | 中等 |
| SourceAddPanel | 0 i18n | 中等 |

---

## 12. 测试策略

### 12.1 为什么之前的测试没抓住

`tests/test_web_product_copy.py` 的覆盖缺口：

1. **SourcesPage 没有 i18n 断言** — `test_sources_path_actions_and_status_copy_are_user_safe()` 检查了很多字符串在源码中的存在性，但没有检查 `useLocale` 是否被引入
2. **TrashPage 无测试** — 完全没有覆盖
3. **Wiki 组件无测试** — 完全没有覆盖
4. **后端 internal id 直出未覆盖** — 没有测试验证 `step.label` 是否走 mapping
5. **zh 值自身仍是英文** — 没有测试验证 i18n 字典的中文值是否真的是中文

### 12.2 新增测试

1. **`test_sources_page_uses_i18n()`** — 验证 SourcesPage 引入 useLocale，关键硬编码字符串不存在
2. **`test_trash_page_uses_i18n()`** — 验证 TrashPage 引入 useLocale
3. **`test_wiki_components_use_i18n()`** — 验证 wiki 子组件使用 i18n
4. **`test_source_add_panel_uses_i18n()`** — 验证 SourceAddPanel 使用 i18n
5. **`test_i18n_zh_values_are_chinese()`** — 验证 zh 字典中的值不是纯英文（允许专有名词和技术标识白名单）
6. **`test_setup_workflow_labels_not_hardcoded()`** — 验证 SetupPage 不对 step.label 直出

### 12.3 白名单

允许出现在用户可见 UI 中的英文：
- 产品名：MindForge
- 技术标识：BM25、API key（作为 label，但 value 应翻译）
- Adapter 名：openai、anthropic、openai_compatible、anthropic_compatible
- 代码标识符：modelId 等（仅 secondary 位置）
- 版本号：v1、v2 等

### 12.4 测试不应过脆

- 不检查精确的字符串匹配（允许空格/标点变化）
- 不检查 t() 调用次数
- 检查关键文案是否在源码中出现，而非精确位置
- 白名单机制允许合法的英文术语

---

## 13. 非目标（明确排除）

1. **mail storage** — 不进入
2. **backend API change** — 不改 `src/mindforge/`、`src/mindforge_web/`
3. **provider / approval / recall semantic change** — 不改后端语义
4. **RAG / embedding** — 不改
5. **real LLM call** — 不调用
6. **large i18n framework** — 不引入 react-i18next、react-intl 等重依赖
7. **Web redesign** — 不改布局、颜色、交互流程
8. **translating user content** — 不翻译
9. **Odysseus 后端实现** — Odysseus 是 source adapter 名，保留但不做新实现
10. **新增依赖** — package.json 不变

---

## 14. 实现优先级

| 优先级 | 范围 | 理由 |
|--------|------|------|
| P0 | SetupPage 混用修复 + zh 值补中文 | 这是用户配置入口，混用最影响信任感 |
| P1 | SourcesPage 全面 i18n 化 | 核心用户页面，当前 0 i18n |
| P1 | 后端数据 display mapping（workflow step、strategy、source status） | 根因修复，不改后端 |
| P2 | TrashPage i18n 化 | 用户可见页面 |
| P2 | Wiki 组件族 i18n 化 | 用户可见页面 |
| P2 | SourceAddPanel i18n 化 | Setup 和 Sources 共用 |
| P3 | Sidebar tooltip i18n | 已有 i18n，收尾细节 |
| P3 | 测试增强 | 防回归 |

---

## 15. 允许的后端只读参考

以下文件可以读取以理解数据形状，但**不得修改**：

- `src/mindforge_web/services/web_config_service.py` — 理解 workflow step 数据组装
- `src/mindforge/strategy_display.py` — 理解策略展示
- `src/mindforge/strategies/knowledge_card.py` — 理解策略名
- `src/mindforge/config.py` — 理解 REQUIRED_STAGES
