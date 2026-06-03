# MindForge Web UI Backend Gap Log

Last updated: 2026-06-02

This log prevents the reference-image redesign from implying backend capabilities that do not exist yet.

## Batch 1: Shell, Home, Setup

| page/type | UI expectation from reference | current backend/API support | current UI behavior | needed backend work | priority | safe to show in UI now? | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Home / Welcome Desk | Overview cards for Sources, AI Drafts, Ready for Review, Approved Knowledge | partial | real data when `/api/workflow/summary` is present; fallback to `/api/home/status` workspace/vault/safety counts | If product wants richer source freshness or per-stage deltas, add explicit home dashboard summary fields | P1 | yes | Counts shown are from existing status APIs or clearly minimal fallbacks; no fake cards are rendered. |
| Home / Welcome Desk | Knowledge Flow: Import -> AI Draft -> Human Review -> Approved Knowledge -> Export | yes for product semantics, partial for per-step live activity | static explanatory flow using real product states and links | Optional per-step live status endpoint if future UI wants progress details | P2 | yes | Flow explains current lifecycle boundaries; it does not claim live pipeline automation beyond existing states. |
| Home / Welcome Desk | First-run Configure Real Model card | yes for provider readiness/status, no for one-click setup | status card and CTA route to Setup only | None for status; future improvement could return recommended setup preset from backend | P2 | yes | Sidebar/Home card is status display and navigation, not a hidden provider activation action. |
| Sidebar | Demo Mode / Configure Real Model card | partial | uses `SafetySummary.provider_state`; CTA navigates to `/setup` | Optional richer provider readiness reason summary for sidebar | P2 | yes | It only distinguishes demo vs ready provider and does not modify provider mode. |
| Setup / Model Configuration | Provider -> Connection -> Model -> Validate/Test guide | partial | guide uses `ConfigStatusResponse.provider` and `/api/config/editable`; existing form still saves via current API | Backend could expose a first-run setup wizard shape if future UI needs server-authored steps | P2 | yes | Guide is a UI organization layer over existing editable config/readiness. |
| Setup / Model Configuration | Validate/Test a configured provider | partial | `Validate Config` calls existing `validateSetupConfig`; no real LLM smoke/test is triggered | Add explicit non-generative readiness test endpoint if product wants endpoint/auth verification without content generation | P1 | yes | The UI labels Validate/Test as configuration validation and states no real LLM call occurs. |
| Setup / Model Configuration | Provider presets: Qwen / OpenAI-compatible / Anthropic-compatible / Custom | partial | OpenAI-compatible and Anthropic-compatible are shown as supported mappings; Qwen and Custom are marked manual endpoint configuration | Add first-class provider presets only if backend supports provider-specific defaults and validation | P2 | yes | Presets are explanatory cards, not fake one-click integrations. |
| Setup / Model Configuration | API key display | yes | input is write-only; configured keys are shown only as presence/masked state from editable config | None for Batch 1 | P0 | yes | Preserves secret boundary; no plaintext API key is shown. |
| Setup / Model Configuration | Configure complete -> go to Sources/Drafts | yes for navigation, partial for contextual recommendation | guide text points to Sources after save/validate; no automatic redirect | Optional next-action endpoint could suggest Sources vs Drafts from current state | P3 | yes | Guidance is copy and navigation only; no fake completion state. |

## Batch 2: Sources, Drafts, Review

| page/type | UI expectation from reference | current backend/API support | current UI behavior | needed backend work | priority | safe to show in UI now? | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Sources / Adapter Catalog | Cubox, Web Clipper, RSS Feed adapter cards with Browse/Connect buttons | no | Cubox/WebClipper/RSS shown as "Coming Soon" — not clickable or fake-connectable | Implement CuboxAdapter, WebClipperAdapter, RSSAdapter with source registry and ingestion pipeline | P2 | yes | Unimplemented adapters clearly marked "Coming Soon"; no fake data or fake connect flows. |
| Sources / Adapter Catalog | Local Files adapter with source count | yes | "Active" badge shown; source count reflects actual `watched_sources` length | None | P0 | yes | Only implemented adapter shows real count from `/api/sources`. |
| Sources / Import Methods | Watched Import, One-shot CLI, Paste/Folder descriptions | partial | Explainer cards shown; Watched links to existing sources page; CLI/Paste are informational | None for display; paste/folder import already exists in LibraryPage | P1 | yes | Cards explain existing import paths; no fake capabilities. |
| Sources / Watched Sources | Source cards with status, path, metrics, actions | yes | Real data from `/api/sources`; expandable details with metrics; process/copy/frequency actions | None | P0 | yes | All shown data comes from existing API; actions use real backend endpoints. |
| Sources / Empty State | Empty watched sources with CTA to add | yes | Empty state shown when `watched_sources` is empty; CTA to `/setup` | None | P0 | yes | Correctly handles empty data. |
| Drafts / Table List | AI Draft table with title, status, source, score | yes | Real data from `/api/drafts`; only `ai_draft` status items shown; status badge always "AI Draft" | None | P0 | yes | Filters to `ai_draft` status only; does not show `human_approved` in drafts table. |
| Drafts / Empty State | Empty drafts with CTA to add sources | yes | EmptyState component with link to `/sources` | None | P0 | yes | Correctly handles empty data. |
| Drafts / Preview Panel | Draft body preview + actions (Send to Review, View Detail, Move to Trash) | partial | Body preview shown; Move to Trash uses real `moveDraftToTrash` API; Send to Review is placeholder (no backend for direct submit) | Add explicit "submit for review" endpoint if product wants drafts to be flagged for human review without approval | P2 | yes | Send to Review button is present but disabled (no backend support yet); Trash uses real API. |
| Review / Left List | Draft list with search, status badges, source info, value score | yes | Real data from `/api/drafts`; filtered to `ai_draft` only; search filters client-side | None | P0 | yes | All data from existing API; search is client-side filtering. |
| Review / Right Panel | Draft body preview + approval panel (checkbox, Approve with 2-step confirm, Reject) | yes | Body preview from `getDraftDetail`; Approve uses real `approveDraft` API with 2-step confirmation; Reject uses real `rejectDraft` API | None | P0 | yes | Approve/Reject use real backend; 2-step confirm prevents accidental approval; no auto approve. |
| Review / Stats Row | AI Drafts count, Approved count | yes | Counts derived from real `/api/drafts` data | None | P0 | yes | Real counts from API response. |
| Review / Empty State | No drafts pending with guidance | yes | Empty state shown when no `ai_draft` items exist | None | P0 | yes | Correctly handles empty data. |
| Review / Safety Note | "No batch approval, no auto approval" messaging | yes | Static safety note in approval panel | None | P0 | yes | Text is purely UI messaging; no functional claim. |

## Backend -> Frontend Matrix: Batch 1

| backend/API capability | route/service/api file | current frontend surface | expose now? | if no, why | future UI slice | priority |
| --- | --- | --- | --- | --- | --- | --- |
| Home status with safety/workspace/vault/provider/recall summaries | `web/src/api/home.ts`, `/api/home/status` | Home overview, SafetyBar, Sidebar provider card | yes | n/a | Add richer empty states after Batch 2 pages settle | P0 |
| Workflow summary with processed source, ai_draft, human_approved counts | `web/src/api/workflow.ts`, `/api/workflow/summary` | Home overview cards | yes | n/a | Could drive per-stage flow activity badges | P1 |
| Editable setup config and masked secret metadata | `web/src/api/config.ts`, `/api/config/editable` | Setup guide and existing model form | yes | n/a | Improve provider preset form defaults | P0 |
| Provider mode opt-in/out | `web/src/api/config.ts`, provider mode endpoints | Existing Setup activation dialog only | yes, but only in Setup | Sidebar/Home must not activate real mode implicitly | Keep opt-in confirmation in Setup | P0 |
| Setup validation | `web/src/api/config.ts`, `/api/config/validate` | Setup guide Validate Config and existing Validate button | yes | n/a | Add clearer validation result panel | P1 |
| Lab/internal graph/sensemaking/dogfood routes | existing app routes/pages | collapsed Lab only | no main-path exposure | Product boundary says Graph/Sensemaking/Entity/Community are lab/internal, not primary workflow | Separate lab redesign if requested | P3 |

## Backend -> Frontend Matrix: Batch 2

| backend/API capability | route/service/api file | current frontend surface | expose now? | if no, why | future UI slice | priority |
| --- | --- | --- | --- | --- | --- | --- |
| Draft list with ai_draft/human_approved filtering | `web/src/api/drafts.ts`, `/api/drafts` | DraftsPage table + ReviewPage list | yes | n/a | Server-side pagination for large draft sets | P1 |
| Draft detail with body and frontmatter | `web/src/api/drafts.ts`, `/api/drafts/:id` | DraftsPage preview + ReviewPage preview | yes | n/a | Full body view in ReviewPage detail panel | P1 |
| Draft approval (approve/reject) | `web/src/api/approval.ts`, `/api/drafts/:id/approve`, `/api/drafts/:id/reject` | ReviewPage approval panel | yes | n/a | Add reject reason field to UI | P1 |
| Draft body save/edit | `web/src/api/drafts.ts`, PATCH `/api/drafts/:id` | DraftsPage CardWorkspace (existing) | yes | n/a | Inline body editor in ReviewPage | P2 |
| Draft move to trash | `web/src/api/trash.ts`, `/api/drafts/:id/trash` | DraftsPage trash button | yes | n/a | Trash action in ReviewPage too | P2 |
| Watched sources list with metrics | `web/src/api/sources.ts`, `/api/sources` | SourcesPage watched sources section | yes | n/a | Source-level drill-down pages | P2 |
| Source scan/process | `web/src/api/sources.ts`, `/api/sources/:id/scan` | SourcesPage "Process now" button | yes | n/a | Background scan progress indicator | P2 |
| Source frequency update | `web/src/api/sources.ts`, `/api/sources/:id/frequency` | SourcesPage frequency selector | yes | n/a | None | P0 |
| Source delete/stop watching | `web/src/api/sources.ts`, `/api/sources/:id` | SourcesPage "Stop watching" button | yes | n/a | None | P0 |
| Cubox adapter | not implemented | SourcesPage "Coming Soon" card | no | Backend CuboxAdapter not implemented | Implement Cubox ingestion pipeline | P2 |
| Web Clipper adapter | not implemented | SourcesPage "Coming Soon" card | no | Backend WebClipperAdapter not implemented | Implement web clipper integration | P2 |
| RSS Feed adapter | not implemented | SourcesPage "Coming Soon" card | no | Backend RSSAdapter not implemented | Implement RSS feed ingestion | P2 |

## Batch 3: Library, Wiki, Export

### Reference -> Backend Matrix

| page/type | UI expectation from reference | current backend/API support | current UI behavior | needed backend work | priority | safe to show in UI now? | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Library / Filter Tabs | All Knowledge, By Source, By Track, Favorites, Recently Viewed | partial | All/By Source/By Track work client-side on real data; Favorites/Recently Viewed disabled (no backend) | Add favorites/bookmarks endpoint and recently-viewed tracking | P2 | yes | Implemented tabs filter real human_approved cards; disabled tabs clearly marked. |
| Library / Table | Knowledge table with title, source, date, status, tags | yes | Real data from `/api/library/cards`; only `human_approved` shown | None | P0 | yes | All columns from existing API; LibraryCardResponse has title, source_type, created_at, status, tags. |
| Library / Detail Panel | Right-side detail panel with card body | yes | Uses `getLibraryCardDetail` API; shows body, source, provenance | None | P0 | yes | Real API call per selected card. |
| Library / Graph Explorer | Graph visualization button | no | Removed from LibraryPage — Graph is lab/internal, not main path | None for Library; graph exists as separate page | P3 | yes | Removed to protect product boundary; graph is not main-path. |
| Library / Community Panel | Knowledge community panel | no | Removed from LibraryPage — Community is lab/internal | None | P3 | yes | Removed to protect product boundary; community is not main-path. |
| Library / Favorites | Favorite/starred knowledge | no | Filter tab disabled; star icon in table is visual only, no backend | Add favorites/bookmarks endpoint | P3 | yes | UI element shown but non-functional; no fake data. |
| Library / Recently Viewed | Recently viewed tracking | no | Filter tab disabled; no backend tracking | Add view-count tracking per card | P3 | yes | Filter tab disabled with Coming Soon label. |
| Wiki / Filter Tabs | All Pages, Favorites, Recent, Recently Updated | partial | All Pages works on real wiki sections; Favorites/Recent/Recently Updated disabled | Add wiki page favorites, view tracking, update timestamps | P3 | yes | All Pages filters real wiki sections; disabled tabs marked Coming Soon. |
| Wiki / Page List | Section list with card count | yes | Real data from `/api/wiki/page`; sections with card counts | None | P0 | yes | Section data from existing wiki API. |
| Wiki / Quality Metrics | Coverage, faithfulness, unused, stale, gaps | yes | Real data from `/api/wiki/quality`; shown in collapsible details | None | P0 | yes | All metrics from real API. |
| Wiki / Rebuild | LLM + deterministic rebuild | yes | `POST /api/wiki/rebuild` with mode parameter | None | P0 | yes | Existing rebuild endpoint. |
| Wiki / New Page | Create new wiki page manually | no | Button shown but no backend support | Add wiki page creation endpoint | P2 | yes | Button is placeholder; no fake capability. |
| Export / Format Cards | Markdown, ZIP, PDF, HTML, Word, JSON | partial | Markdown/ZIP enabled and working; PDF/HTML/Word/JSON marked Coming Soon | Implement PDF/HTML/Word/JSON export formats | P2 | yes | Only implemented formats are functional; Coming Soon cards are disabled. |
| Export / Scope | All / By Tag / By Track | yes | Real filtering on approved cards; tag/track dropdowns populated from API | None | P0 | yes | Filtering works on real human_approved data. |
| Export / Download | Markdown download, ZIP download | yes | Uses `/api/knowledge/export` and `/api/knowledge/export/download` | None | P0 | yes | Real download endpoints. |
| Export / Options | Include metadata, TOC, tags, frontmatter | no | Options checkboxes shown but not sent to backend yet | Add export options to export API request body | P2 | yes | Options UI prepared; backend integration pending. |
| Export / Recent Exports | Recent export history | no | Section not shown (no backend tracking) | Add export history tracking | P3 | yes | Omitted rather than faked. |

### Backend -> Frontend Matrix: Batch 3

| backend/API capability | route/service/api file | current frontend surface | expose now? | if no, why | future UI slice | priority |
| --- | --- | --- | --- | --- | --- | --- |
| Library card list with status filtering | `web/src/api/library.ts`, `/api/library/cards` | LibraryPage table list | yes | n/a | Server-side pagination + favorites sorting | P0 |
| Library card detail | `web/src/api/library.ts`, `/api/library/cards/:id` | LibraryPage detail panel | yes | n/a | Rich provenance visualization | P0 |
| Library bulk actions (export, tag, track) | `web/src/api/library.ts`, bulk endpoints | LibraryPage bulk actions bar | yes | n/a | None | P0 |
| Wiki status | `web/src/api/wiki.ts` (via fetch), `/api/wiki/status` | WikiPage status bar | yes | n/a | None | P0 |
| Wiki page content | `web/src/api/wiki.ts` (via fetch), `/api/wiki/page` | WikiPage section list | yes | n/a | Full page navigation with TOC | P0 |
| Wiki quality metrics | `web/src/api/wiki.ts` (via fetch), `/api/wiki/quality` | WikiPage quality collapsible | yes | n/a | None | P0 |
| Wiki rebuild | `web/src/api/wiki.ts` (via fetch), `/api/wiki/rebuild` | WikiPage rebuild button | yes | n/a | None | P0 |
| Wiki related sections | `web/src/api/wiki.ts` (via fetch), `/api/wiki/related-sections` | fetched but not yet surfaced in UI | no | No clear UI placement in new design | Add related-sections sidebar in detail view | P2 |
| Knowledge export (markdown) | `web/src/api/library.ts` (via fetch), `/api/knowledge/export` | ExportPage preview + download | yes | n/a | None | P0 |
| Knowledge export download (zip) | `web/src/api/library.ts` (via fetch), `/api/knowledge/export/download` | ExportPage download | yes | n/a | None | P0 |
| Export options (metadata, TOC, tags, frontmatter) | not in export API yet | ExportPage options checkboxes | no | Backend export API doesn't accept options | Add options to export request body | P2 |

## Batch 4: Fake Mode QA Findings (2026-06-02)

### QA Matrix

| page | opens | demo mode visible | buttons work | empty states correct | product boundaries safe | score |
| --- | --- | --- | --- | --- | --- | --- |
| Home | yes | yes (sidebar + safety bar) | nav links, CTA all work | N/A (has demo data) | yes — no fake real-provider activation | 9/10 |
| Setup | yes | yes (Demo / Fake Provider section) | add model, validate disabled until filled | N/A | yes — API key only masked, validate warns no real LLM call | 9/10 |
| Sources | yes | yes (safety bar) | "立即处理" works, Cubox/WebClipper/RSS disabled | N/A (has 1 local file source) | yes — source ≠ provider clearly separated | 9/10 |
| Drafts | yes | yes | "浏览草稿" link works | yes — empty state with CTA to sources | yes — only ai_draft shown, no auto-mixing | 8/10 |
| Review | yes | yes | N/A (empty) | yes — guidance text present | yes — no Approve All, no auto approve | 8/10 |
| Library | yes | yes | detail panel, export, search, filter, sort work | N/A (has 6 demo cards) | yes — only human_approved shown | 9/10 |
| Wiki | yes | yes | search, sections expand/collapse work | yes — warns model needed for LLM synthesis | yes — no RAG/vector DB claims | 8/10 |
| Export | yes | yes | preview, download work, format cards correct | N/A (has 6 approved cards) | yes — PDF/HTML/Word/JSON disabled, options collapsible Coming Soon | 9/10 |

### Issues Found and Fixed

1. **Missing i18n key `library.col_title`** — Library table header showed raw key "library.col_title" instead of "标题". Fixed by adding zh/en equivalents.
2. **Missing i18n key `nav.review`** — Sidebar showed raw key "nav.review" instead of "人工审阅". Fixed by adding zh/en equivalents.
3. **Missing i18n key `shared.safety_notice`** — Export page safety section showed raw key. Fixed by adding zh/en equivalents.

### Fake Mode Main Path Status

- Source → Process: "立即处理" triggered on Local Files adapter ✓
- Process → Drafts: Background processing initiated; drafts may take time to appear in fake mode
- Drafts → Review: Review page correctly shows empty when no drafts exist ✓
- Library → Export: 6 demo cards exported successfully via Markdown preview and download ✓

### Screenshots

- `tmp/fake-qa-home.png`
- `tmp/fake-qa-setup.png`
- `tmp/fake-qa-sources.png`
- `tmp/fake-qa-drafts.png`
- `tmp/fake-qa-review.png`
- `tmp/fake-qa-library.png`
- `tmp/fake-qa-wiki.png`
- `tmp/fake-qa-export.png`
- `tmp/fake-qa-library-fixed.png` (after i18n fixes)

### Gates

- `git diff --check`: pass (exit 0)
- `web/ npm run build`: pass (tsc -b && vite build completed in 4.72s)
- `main` synced with `origin/main`: yes (0 0 after push)
- `pictures/` not staged: yes (untracked only)
- working tree: clean (only untracked pictures/, tmp/)

## Batch 5: Setup / Source Flow UX Remediation (2026-06-02)

### Problem Summary

User-reported UX issues in Setup/Sources/Model Configuration flow:
1. Sources "新来源" button jumped to Setup page instead of adding source inline
2. "添加模型" button had no clear visual feedback
3. Demo Mode in sidebar was a clickable button that only navigated to /setup (loop)
4. "验证配置" name implied real LLM connectivity test, but only checked local config
5. Qwen shown as independent provider card instead of OpenAI-compatible example
6. Setup page copy too engineering-heavy

### Changes Made

| change | files modified | backend impact |
| --- | --- | --- |
| Sources "新来源" opens inline SourceAddPanel | `SourcesPage.tsx` | none — uses existing `addWatchedSource` API |
| "添加模型" → "配置模型" with scroll-to-form feedback | `SetupPage.tsx`, `i18n.ts` | none |
| Demo Mode → status chip (non-clickable) | `Sidebar.tsx`, `i18n.ts` | none |
| "验证配置" → "检查配置" with tooltip | `SetupPage.tsx`, `i18n.ts` | none |
| Provider types converged to 4: OpenAI native, Anthropic native, OpenAI-compatible, Custom | `SetupPage.tsx`, `i18n.ts` | none — UI-only presets |
| Engineering chips moved to single safety note | `SetupPage.tsx`, `i18n.ts` | none |
| Sources page desc updated to reference inline add | `SourcesPage.tsx`, `i18n.ts` | none |

### Backend Gap Assessment

No backend changes required. All changes are frontend UX improvements using existing APIs:
- Source add: existing `POST /api/sources` endpoint
- Model config: existing `POST /api/config` endpoint
- Validate: existing `POST /api/config/validate` endpoint (already local-only, no LLM calls)
- Provider mode: existing mode toggle endpoints (unchanged)

### Assets

No external assets were added in Batch 1 or Batch 2.

## Batch 6: Review / Library / Wiki / Lab UX Remediation (2026-06-03)

### Problem Summary

User-reported UX issues from real browser trial:
1. "人工审阅" and "审阅草稿" sidebar tabs looked duplicate, users confused about the difference
2. Library first click on a card showed empty detail panel (interaction bug)
3. Card detail content cramped in narrow side panel (max 50% width, 70vh height)
4. Wiki default state unclear when approved knowledge exists but Wiki not generated
5. Lab/Graph/Sensemaking visual style inconsistent with main web

### Changes Made

| change | files modified | backend impact |
| --- | --- | --- |
| Remove `/drafts` from primary sidebar nav; move to Lab section | `Sidebar.tsx` | none |
| Library empty-state CTA updated from `/drafts` → `/review` | `LibraryPage.tsx` | none |
| Add `detailLoading` state to Library; show loading indicator instead of blank | `LibraryPage.tsx` | none |
| Widen Library detail panel grid from `1fr 1fr` → `2fr 3fr` | `LibraryPage.tsx` | none |
| Increase Library detail panel max-h from `70vh` → `85vh` | `LibraryPage.tsx` | none |
| Add Wiki empty-state for existing Wiki with no sections (shows refresh CTA + approved count) | `WikiPage.tsx` | none |
| Polish SensemakingPage header/tabs/LAB banner to use main web design tokens | `SensemakingPage.tsx` | none |

### Root Cause: Library first-click detail empty bug

**Location:** `LibraryPage.tsx:166-172` (before fix)

**Causal chain:**
1. User clicks first card → `selectCard(ref)` called
2. `setSelected(ref)` updates selected state
3. `setDetail(null)` **synchronously clears** detail state
4. Detail panel renders (condition: `selected &&`) — panel appears but `detail` is null
5. Inside panel: `!error && detail` — detail is null, **nothing renders**
6. `useEffect` fires async `getLibraryCardDetail()` — request in flight
7. Panel shows blank until response returns
8. Second click works because the first request already completed and cached detail

**Fix:** Replace `setDetail(null)` with `setDetailLoading(true)` in `selectCard()`. Add loading indicator in detail panel.

### Backend Gap Assessment

| capability | status | safe to show? | notes |
| --- | --- | --- | --- |
| Library full-detail API (`getLibraryCardDetail`) | **supported** | yes | Real API, working |
| Wiki auto-generation on approved knowledge | **manual rebuild required** | yes | User must click "生成 Wiki" or "刷新 Wiki"; no auto-trigger |
| Wiki related pages / history / spaces | **partial** | yes | `/api/wiki/related-sections` exists but not surfaced in UI |
| Graph / Sensemaking current support | **lab/internal, deterministic only** | yes | BFS + set operations only; no LLM/embedding/vector DB |
| Review / Drafts duplicate entry | **IA history** | resolved | Merged into single `/review` entry; `/drafts` moved to Lab |

### Assets

No external assets were added.
\n### Endpoint Diagnosis & Readiness Semantics\n\n- 当前 readiness 状态已从 “Ready” 改为 “Configured / Not verified”（配置已保存 / 尚未测试连接），仅代表本地配置已保存，不代表外部提供商网络可达。\n- 真正的 “Test Connection”（测试连接）功能尚未实现。\n- `base_url` 格式要求：用户需要填写服务根路径（如包含 `/v1`），不应包含 `/chat/completions`，系统会自动拼接。\n- 真实连接失败可能来自 endpoint、network、proxy、key、model 多种原因，现在会在 UI 和日志中统一提示”模型连接失败。请检查 base URL、网络代理、provider 类型、model name 或 API key。”

### Batch 7: Setup Model Save UX Fix

**User report:** “配置完模型的时候，第一次点模型配置部分的保存没有反应，按全局的保存的才保存”

**Root cause:** `saveModelEdit()` 存在两个问题：
1. 验证失败时使用 `setMessage()` 显示绿色成功消息，视觉上与成功提示无区别，用户误以为”无反应”
2. `await save()` 未包裹在 try/catch 中，API 错误抛出 unhandled rejection，React 可能抑制状态更新
3. `if (!form || !editing) return` 零反馈退出

**Fix:**
- 所有验证错误改用 `setSaveError()`，显示在红色错误横幅中
- 添加 try/catch 包裹 `await save()`，捕获 save 抛出的错误并静默处理（save 已设置 saveError）
- 添加 missing i18n key `setup.validation.form_not_loaded`
- 顺便修复 i18n.ts 中 pre-existing 语法错误（line 1553 转义引号）

**Files changed:**
- `web/src/pages/SetupPage.tsx` — saveModelEdit error handling
- `web/src/lib/i18n.ts` — new i18n key + fix escaped quotes bug
