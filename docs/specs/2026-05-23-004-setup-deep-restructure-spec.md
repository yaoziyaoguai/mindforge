# MindForge Web UX Milestone E: Setup Deep Restructure Spec

## 1. Background

### 1.1 已完成里程碑

| Milestone | 内容 | 状态 |
|-----------|------|------|
| A | Review UX 清晰化、状态文案用户化、Approve/Reject 操作语义 | done |
| B | Sidebar 导航重构、页面信息层级优化 | done |
| C | i18n 中英文切换、视觉一致性、a11y | done |
| D | Dashboard Action Guidance、NextAction action_key、copy policy | done |

### 1.2 当前问题

Setup 页面是 MindForge Web 最大的用户摩擦点：

1. **Setup 本质是"配置文件搬到网页"**，不是真正的 onboarding。用户打开 Setup 看到的是技术配置表单，不知道自己在连接什么、为什么需要这一步、完成后会发生什么。
2. **fake provider 和 real provider 的区分不清晰**。用户不知道 fake provider 是安全本地路径（不需要 API key），real provider 需要显式 opt-in 并配置 API key。
3. **API key / secrets 安全边界没有在 UI 层面解释**。用户可能误以为在 Web Setup 输入 API key 就等于"已安全保存"，不清楚 key 存储在哪里、谁会读到。
4. **provider readiness / doctor 状态虽然已有后端数据，但前端未充分展示**。用户不知道当前 provider 是否可用、缺什么配置。
5. **source / workflow / processing 的关系不直观**。新用户不清楚"连接模型 → 选择知识源 → 处理流程"这条链路。
6. **Setup / Sources / Processing 相关 NextAction 仍缺少 action_key**，导致前端无法做稳定的本地化展示映射。
7. **EmptyState action.description 仍为原始英文**，缺乏本地化机制。

### 1.3 上一轮遗留 P3/P4 并入

Dashboard Action Guidance (Milestone D) 的 closure commit `da9d586` 完成后，仍有以下 P3/P4：

- **P3**: `web_facade.py` 外 17 个 NextAction 构造点分布在 6 个文件中，仍未补充 action_key。
- **P3**: EmptyState `action.description` 为原始英文，需要 description_key 或等价本地化机制。
- **P3**: Setup / Sources / Processing 页面级 NextAction 一致性审查。

以上 P3/P4 全部并入 Milestone E scope，不单独开 milestone。

## 2. Goals

1. **Setup 页面重构为 onboarding wizard / guided setup**，不再是"配置文件搬到网页"。
2. **清楚区分 fake provider / real provider**，包括视觉标识和解释文案。
3. **清楚说明 API key / secrets 安全边界**：key 存在哪里、谁不能读到、不会发给 agent。
4. **清楚展示 provider readiness / doctor 状态**：当前 provider 是否可用、缺失什么配置。
5. **清楚展示 source / workflow / processing 的关系**：连接模型 → 选择知识源 → 处理流程的链路。
6. **Setup 页面提供明确的下一步行动**（NextAction + action_key）。
7. **补齐 Setup / Sources / Processing 范围内 NextAction 的 action_key**，按页面/服务边界控制 scope。
8. **实现 EmptyState action.description 本地化机制**（description_key）。
9. **确保中英文 UI 切换下 Setup / Sources / EmptyState / NextAction 文案一致**。
10. **保持后端业务语义不变**：不改变 provider / approval / recall 语义。

## 3. Non-goals

1. mail storage / email / mail 功能。
2. provider 业务语义变更。
3. approval / human_approved 语义变更。
4. recall / BM25 语义变更。
5. RAG / embedding。
6. 真实 LLM 调用。
7. 新的大型 UI framework。
8. 后端配置系统重写。
9. Secret storage / keychain 实现（已有 WebConfigSecretManager，不新增）。
10. 全站设计系统大重写。
11. 不修改 `src/mindforge_web/services/web_facade.py`（这是 Dashboard Action Guidance 的范围，不属于本轮 Setup/Sources/Processing）。

## 4. Scope / Implementation Units

### U1: Setup Information Architecture

**目标**: Setup 页面分成清晰区域，每个区域回答用户一个问题。

**区域划分**:

```
┌─────────────────────────────────────────┐
│  Step 1: Connect Model / 连接模型        │
│  - 我现在用的是什么模型？                 │
│  - fake provider vs real provider 区别    │
│  - 当前 provider readiness 状态           │
│  - 模型配置（折叠高级选项）                │
├─────────────────────────────────────────┤
│  Step 2: Choose Sources / 选择知识源      │
│  - 哪些来源正在被监控？                   │
│  - 如何添加新的知识源？                   │
│  - 每种 source type 的含义               │
├─────────────────────────────────────────┤
│  Step 3: Processing & Next / 处理与下一步 │
│  - 处理流程概览（workflow stages）        │
│  - 当前处理状态                           │
│  - 下一步应该做什么？                     │
└─────────────────────────────────────────┘
```

**要求**:
- 不改 provider config model。
- 不改 API contract (`/api/config/editable`, `/api/config/status`, `/api/sources`, `/api/workflow/summary`)。
- 如果现有 API 不支持某些状态展示，只做前端 copy/layout，不新增后端 API。
- 每个 section header 使用 i18n key，zh/en 均可切换。

### U2: Setup Wizard / Progressive Disclosure

**目标**: 用户不应一次看到所有配置细节。高级配置折叠或降级展示。

**实现**:

- 保留现有 3-step wizard 结构 (`SetupStep = "models" | "sources" | "review"`)。
- 每个 step 增加引导文案，解释"这一步为什么需要"。
- 高级配置（base_url 覆写、model 覆写、timeout、max_retries）默认折叠，点击 "Advanced / 高级" 展开。
- Step indicator 显示完成状态（当前在哪个 step、哪些 step 已完成）。

**不改变**:
- wizard step 切换逻辑（现有 `setStep` 状态管理）。
- form state 在 step 切换时保留（现有实现已保证）。

### U3: Provider Safety Copy

**目标**: 用户清楚理解 fake provider 和 real provider 的安全边界。

**实现**:

1. **Provider 类型标识**：在 provider 选择区域显示类型标签。
   - `fake` → "本地模拟 (Local Simulated)" / "无需 API Key / No API Key Required"
   - `openai_compatible` / `anthropic` / `anthropic_compatible` → "远程模型 (Remote Model)" / "需要 API Key / API Key Required"

2. **API Key 安全说明文案**（新增 i18n key `setup.api_key_safety`）:
   - zh: "API Key 仅保存在本地 secret store 中，不会提交到 Git 仓库，也不会发送给 AI Agent。"
   - en: "Your API key is stored only in the local secret store. It is never committed to Git or sent to AI agents."

3. **Provider Readiness 状态展示**：利用现有 `provider_status()` 返回的数据，展示:
   - Active profile name
   - API key 是否已配置（present / missing）
   - Base URL 来源（config default / env / missing）
   - Model 来源（config default / env / missing）
   - 整体 readiness: "Ready / 就绪" 或 "Incomplete / 未完成"

4. **不读取 .env，不展示 raw key 值**。

### U4: Processing Workflow Copy & Action Consistency

**目标**: 修复 Processing workflow 区域中可能的中英文混用，internal id 降级展示。

**实现**:

1. **Workflow stage 展示映射**：`workflowStepLabel()` 已有 5 个 stage 的 zh/en 映射，确认覆盖所有展示点。
2. **Strategy name 展示映射**：`strategyNameLabel()` 已覆盖 `knowledge_card` / `five_stage`。
3. **Source status 展示映射**：`sourceStatusLabel()`, `sourceRunStatusLabel()`, `sourceDueStatusLabel()` 已覆盖。
4. **审查 SetupPage 中所有仍可能裸奔 internal id 的位置**，统一走 display mapping。
5. **保留 technical id 作为 secondary / developer hint**（小字、灰色、可选展示）。

### U5: NextAction action_key Completion (Setup/Sources/Processing Scope)

**目标**: 补齐本轮范围内所有 NextAction 构造点的 action_key。

**范围限制**: 只补齐以下 3 个服务文件中的 NextAction 构造点：

| 文件 | 构造点 | 建议 action_key |
|------|--------|-----------------|
| `web_config_service.py` | `cubox_status_item` (provider_status) | `setup.configure_cubox` |
| `web_config_service.py` | `watch_summary` (provider_status) | `setup.manage_watched_sources` |
| `web_source_service.py` | `list_sources()` → Create source folder | `sources.create_source_folder` |
| `web_source_service.py` | `watch_sources()` → Add watched source | `sources.add_watched_source` |
| `web_source_service.py` | `watch_delete()` → Back to watch list | `sources.back_to_watch_list` |
| `web_source_service.py` | `_ingestion_next_actions()` → View source status | `sources.view_source_status` |
| `web_source_service.py` | `_ingestion_next_actions()` → Review drafts | `sources.review_drafts` |
| `web_source_service.py` | `available_imports()` → Add watch | `sources.add_watch_from_import` |
| `web_source_service.py` | `available_imports()` → Import once | `sources.import_once` |
| `processing_run_service.py` | `next_actions_for_record()` → running state | `processing.view_run_status` |
| `processing_run_service.py` | `next_actions_for_record()` → has drafts | `processing.review_drafts` |
| `processing_run_service.py` | `next_actions_for_record()` → failed state | `processing.retry_processing` |
| `processing_run_service.py` | `next_actions_for_record()` → default state | `processing.view_sources` |

**不在本轮范围**:
- `web_review_service.py`（属于 Review 页面，非 Setup/Sources/Processing）
- `web_facade.py`（属于 HomePage/Dashboard，已在 Milestone D 覆盖）
- 其他非 Setup/Sources/Processing 的服务文件

**要求**:
- action_key 必须稳定、机器可读、与 label 解耦。
- label / description 保留 fallback。
- 不改变 href / command / onClick 行为。
- 前端 `nextActionLabel()` 映射表同步扩展。

### U6: EmptyState action.description Localization

**目标**: EmptyState 的 `action.description` 也能走本地化映射。

**实现**:

1. **新增 `description_key` 字段**到 `NextAction` Pydantic model（Optional[str], default None）。
2. **前端新增 `nextActionDescription(key, locale)` 函数**，与 `nextActionLabel()` 同模式。
3. **EmptyState 组件** 使用 `nextActionDescription(action.description_key, locale) ?? action.description` 渲染。
4. **i18n 字典扩展**：新增 `nextActionDescription` mapping section。
5. **向后兼容**：无 `description_key` 时 fallback 到原始 `action.description` 字符串。
6. **不靠英文 label 字符串匹配**，不翻译用户内容。

**description_key 初始覆盖**（与已有 action_key 对应的 description）:

| action_key | description_key | zh description | en description |
|------------|-----------------|----------------|-----------------|
| `home.go_to_review` | `home.go_to_review.desc` | 审核 AI 生成的草稿，决定批准或驳回 | Review AI-generated drafts and decide to approve or reject |
| `home.go_to_library` | `home.go_to_library.desc` | 浏览已批准的知识卡片和 Wiki | Browse approved knowledge cards and wiki |
| `home.configure_sources` | `home.configure_sources.desc` | 管理知识源和自动处理流程 | Manage knowledge sources and processing |
| `home.go_to_setup` | `home.go_to_setup.desc` | 配置模型连接和处理参数 | Configure model connections and processing |
| `empty.no_drafts` | `empty.no_drafts.desc` | 添加知识源并开始处理，生成第一批 AI 草稿 | Add sources to start processing and generate your first AI drafts |
| `empty.no_approved` | `empty.no_approved.desc` | 审核 AI 草稿并批准优质卡片，构建知识库 | Review drafts and approve quality cards to build your knowledge base |
| `empty.no_sources` | `empty.no_sources.desc` | 添加 Markdown、PDF 或 DOCX 文件作为知识源 | Add markdown, PDF, or DOCX files as knowledge sources |
| `empty.no_results` | `empty.no_results.desc` | 调整搜索词或筛选条件后重试 | Try adjusting your search terms or filters |
| `empty.no_wiki` | `empty.no_wiki.desc` | 批准知识卡片后重建 Wiki，生成结构化知识视图 | Approve cards and rebuild the wiki to generate a structured knowledge view |

### U7: Source Type / Technical Identifier Policy

**目标**: 技术 identifier 降级展示，周围解释文案本地化。

**实现**:

1. **格式名保留**：`Markdown`, `HTML`, `PDF`, `DOCX`, `Plain Text` 等格式名可保留英文。
2. **周围解释文案必须本地化**：如 "Source Type: Markdown" → zh: "来源类型：Markdown（标记文本）"。
3. **技术 identifier 降级**：如 `adapter_name: "PlainMarkdownAdapter"` → secondary display（小字灰色），不出现主展示位置。
4. **SourcePage** 中 `source_type` 展示复查，确保不裸奔 `adapter_name`。

### U8: Regression Guard

**目标**: 确保所有变更不引入回归。

**实现**:

1. **test_web_product_copy.py 扩展**:
   - 新增 `description_key` fallback 测试。
   - 新增 Setup / Sources / Processing action_key 覆盖测试。
   - 新增 provider safety copy key 存在性测试。
   - 新增 workflow internal id 不裸奔测试。

2. **测试不脆**:
   - 不靠精确字符串匹配 action_key 值列表（用 pattern 匹配）。
   - i18n key 存在性用宽松检查（key 在字典中即可，不检查具体文案）。

## 5. File Scope

### 允许修改

**Spec & Docs**:
- `docs/specs/2026-05-23-004-setup-deep-restructure-spec.md` (新增)
- `docs/implementation-notes/2026-05-23-004-setup-deep-restructure.md` (新增)
- `docs/dev/copy-policy.md` (更新)

**Frontend**:
- `web/src/pages/SetupPage.tsx`
- `web/src/pages/SourcesPage.tsx`
- `web/src/components/EmptyState.tsx`
- `web/src/components/NextActionCard.tsx`
- `web/src/components/StatusCard.tsx`
- `web/src/lib/i18n.ts`
- `web/src/lib/utils.ts`
- `web/src/api/types.ts`

**Backend (仅 NextAction action_key/description_key 补充)**:
- `src/mindforge_web/services/web_config_service.py`
- `src/mindforge_web/services/web_source_service.py`
- `src/mindforge_web/services/processing_run_service.py`

**Tests**:
- `tests/test_web_product_copy.py`

### 禁止修改

- approval / human_approved 语义相关后端逻辑
- provider 调用语义
- recall / BM25 后端语义
- mail storage
- 真实 LLM execution logic
- 不相关 Web pages
- `src/mindforge_web/services/web_facade.py`

## 6. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | Setup scope creep — wizard 变成全功能 onboarding flow | Medium | High | 严格限定 U1-U8，不改后端 API |
| 2 | NextAction 构造点跨服务过多 | Low | Medium | 已限定 Setup/Sources/Processing 3 个文件 |
| 3 | description_key 机制过度设计 | Low | Medium | 与 action_key 同模式，不复用新抽象 |
| 4 | i18n copy key 继续散落 | Medium | Low | 使用现有 i18n.ts 结构，不新增翻译文件 |
| 5 | provider safety copy 误导用户以为已安全保存 | Low | High | 文案明确说明"本地 secret store"，不声称"加密" |
| 6 | workflow internal id 被误翻译 | Low | Medium | 只走 display mapping，不翻译 internal id |
| 7 | form state 在 wizard step 切换时丢失 | Low | Medium | 现有实现已保证，本轮不改 form state 管理 |
| 8 | tests 过脆 — action_key 列表精确匹配 | Low | Low | 用 pattern 匹配，不硬编码完整列表 |
| 9 | browser smoke 需要真实 provider | Medium | Medium | 只用 fake provider 做 smoke |

## 7. Stop Conditions

1. 需要新增后端 provider config API → stop。
2. 需要 secret storage / keychain 新实现 → stop。
3. 需要真实 LLM 调用 → stop。
4. 需要改变 provider / approval / recall 语义 → stop。
5. 需要修改 mail/email/storage → stop。
6. NextAction 构造点超过本轮 Setup/Sources/Processing 范围 → stop。
7. description_key 机制需要大范围重构（触及后端 schema 以外） → stop。
8. P0/P1/P2 无法在 2 次回退内关闭 → stop, escalate to user。

## 8. Test Strategy

### 8.1 Build Gate

```bash
npm --prefix web run build
```

### 8.2 Product Copy Tests

```bash
python -m pytest tests/test_web_product_copy.py -q
```

### 8.3 Diff Check

```bash
git diff --check
```

### 8.4 Browser Smoke (with Browser MCP)

1. Setup wizard 可打开，3 个 step 可切换。
2. zh/en 语言切换有效，Setup 文案跟随切换。
3. fake provider / real provider 区分可见。
4. API key 安全说明文案可见。
5. Provider readiness 状态展示正确。
6. Processing workflow copy 无中英文混用。
7. Sources 页面无中英文混用。
8. EmptyState action label + description 均本地化。
9. Console 无 error。
10. Network 无明显 4xx/5xx。
11. 不泄露 API key。
12. 不调用真实 LLM。

## 9. Execution Plan

1. **Spec 自审**：写完 spec 后自审，重点检查 scope、P3/P4 纳入、stop conditions。
2. **Spec 不过则回退**：最多 2 次。
3. **Spec 通过后实现**：按 U1-U8 顺序实现。
4. **写 implementation notes**：记录实际修改、spec 差异、回退记录。
5. **代码自审**：检查 P0/P1/P2、语义红线、scope 越界。
6. **Gate**：`npm build` + `pytest` + `git diff --check`。
7. **Browser smoke**：Browser MCP 验证。
8. **Commit + push main**：fast lane。
9. **输出 Big Loop Report**。
