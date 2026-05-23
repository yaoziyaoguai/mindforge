# Dogfood Readiness Browser Smoke

## 1. Context

- **Date**: 2026-05-23
- **Scope**: Browser smoke test for fake dogfood readiness
- **Method**: Browser MCP (headed Chromium) against `http://127.0.0.1:5174/` (Vite dev + backend proxy)
- **Backend**: `mindforge web --no-open --port 8765` from current repo
- **Vault**: `/Users/jinkun.wang/work_space/mindforge/vault` (1 approved card, 0 drafts, 0 inbox pending)
- **Locale tested**: zh (简体中文) and en (English)

## 2. Pages Smoked

| Page | zh OK | en OK | Console Errors | Notes |
|------|-------|-------|----------------|-------|
| Home (/) | Yes | Yes | 0 | NextAction description_key working after backend restart |
| Setup (/setup) | Mostly | Mostly | 2 (accessibility) | P2: zh mode has English "API key status is shown as..." ; en mode has Chinese workflow descriptions |
| Sources (/sources) | Mostly | Yes | 0 | P2: zh mode has English "scan/process remain available only..." |
| Drafts (/drafts) | Yes | N/A | 0 | Empty state, Chinese copy clean |
| Library (/library) | Mostly | N/A | 0 | P2: "Source path is not accessible." hardcoded English |
| Wiki (/wiki) | Mostly | N/A | 0 | P2: mixed labels "Cards included", "Last rebuilt" etc. |
| Search (/search) | Yes | N/A | 0 | Shows same content as Home (intentional? routing TBD) |
| Trash (/trash) | Yes | Yes | 0 | Clean empty state both locales |

## 3. Findings Summary

### P2 (should fix before real dogfood)

| ID | Page | Description | Root Cause |
|----|------|-------------|------------|
| P2-1 | All | SafetyBar labels not localized (always English) | SafetyBar component hardcoded strings, not using t() |
| P2-2 | Setup | "API key status is shown as present/missing only." appears in English in zh mode | Hardcoded English string in SetupPage |
| P2-3 | Setup | Workflow step descriptions in Chinese when locale=en | API returns Chinese descriptions; no workflow step display mapping (similar to NextAction pattern but not yet implemented) |
| P2-4 | Setup | "正常"/"警告" status labels not translated in en mode | API status values need display mapping via friendlyStatus() |
| P2-5 | Sources | "scan/process remain available only for Advanced / Troubleshooting..." English in zh mode | Hardcoded English in SourcesPage |
| P2-6 | Wiki | "Cards included", "Last rebuilt", "Action Items", "Provenance", "Source card", "Card path" hardcoded English | WikiPage mixed hardcoded labels |

### P3 (nice to fix, doesn't block)

| ID | Page | Description |
|----|------|-------------|
| P3-1 | Setup | Form fields missing associated labels (5 instances) |
| P3-2 | Setup | Form fields missing id/name attributes (6 instances) |
| P3-3 | Sources | Source status values ("Manual", "Missing", "Failed") are technical labels; could use display mapping |
| P3-4 | Library | "Source path is not accessible." hardcoded English |
| P3-5 | Search | /search shows Home content — may be intentional or routing gap |

### P4 (polish)

| ID | Page | Description |
|----|------|-------------|
| P4-1 | Setup | Workflow step technical IDs ("triage", "distill") shown alongside Chinese names — acceptable per copy policy but could be demoted further |
| P4-2 | All | React DevTools info message in console |

## 4. What Worked Well

1. **NextAction action_key/description_key mechanism**: Working correctly. Home NextAction "搜索知识" / "Search knowledge" properly localized in both locales after backend restart.
2. **Provider safety copy**: Clear distinction between 本地模拟/Local Simulated and 远程模型/Remote Model in both locales.
3. **Empty states**: Drafts ("没有待确认的 AI 草稿"), Trash ("回收站为空") — clean Chinese copy.
4. **Navigation sidebar**: Consistent zh/en labels for all 8 navigation items.
5. **Language toggle**: Instant switching between zh/en, no page reload needed.
6. **No crash/500/network errors**: All API endpoints returned 200.
7. **No secret leakage**: API keys not visible in UI, Safety Bar shows "check" not raw key.
8. **No real LLM calls**: Smoke only exercised Web UI, no processing triggered.

## 5. Gate Results

| Gate | Command | Exit Code |
|------|---------|-----------|
| Web build | `npm --prefix web run build` | 0 |
| Copy tests | `python -m pytest tests/test_web_product_copy.py -q` | 0 (46 passed) |
| Diff check | `git diff --check` | 0 |

## 6. Backend Restart Issue

The browser smoke initially connected to a stale backend from `/private/tmp/mindforge-real-dogfood-20260520-141432/` which was running older code without `action_key`/`description_key` in NextAction API responses. After killing that server and restarting from the current repo, NextAction localization worked correctly.

**Lesson**: For future smoke tests, verify the backend is serving from the expected repository before starting.

## 7. Conclusion

**Fake dogfood readiness**: The app is functionally ready. Pages load, navigation works, language toggle works, no crashes, no network errors. The remaining P2 issues are i18n coverage gaps (SafetyBar, workflow descriptions, Wiki labels) that should be addressed before real dogfood but don't block fake dogfood (local testing without real LLM).

**Next priorities**:
1. Fix P2-1 (SafetyBar i18n) — highest impact, affects all pages
2. Fix P2-3 (workflow step display mapping) — Setup page is the primary onboarding surface
3. Address remaining P2s in a single i18n follow-up milestone
4. P3/P4 can be addressed incrementally
