# Setup Provider Save Dogfood Finding

## 1. Context

- **Date**: 2026-05-23
- **Source**: Real LLM dogfood run (008) — Phase C user API key configuration friction
- **Finding**: Setup page model-level "保存" button doesn't persist; only global save does

## 2. Reproduction

1. Open Web Setup (`http://127.0.0.1:8765/setup`)
2. Click "添加模型" (Add model)
3. Fill in model config (type, base_url, model, api_key)
4. Click "保存" (the button inside the model edit form, line 449)
5. **Observed**: Edit form closes, model appears in card list, but "未保存的更改" indicator appears at top
6. **Expected**: Model config is persisted to backend
7. Navigate away and return → model config is LOST

## 3. Root Cause

`saveModelEdit()` (SetupPage.tsx:155) only updates local React state via `setForm()`. It does NOT call the `saveSetupConfig()` API. The function name and button label both say "save" but the implementation only applies changes to in-memory form state.

The global `save()` function (line 235) is the ONLY path that calls `saveSetupConfig()` → `PATCH /api/config/editable`.

```typescript
// Line 155-194: Only updates local state, no API call
function saveModelEdit() {
    // ... validation ...
    setForm({ ...form, models: nextModels, ... });
    setEditing(null);  // closes form, but nothing persisted
}

// Line 235-255: Only path to actual persistence
async function save() {
    const response = await saveSetupConfig(patchFromForm(current));
    // ...
}
```

## 4. User Impact

- User fills in API key, clicks "保存" in model form, assumes it's saved
- "未保存的更改" warning appears but user may not notice
- If user navigates away, config is silently lost
- Real dogfood Phase C hit this: user configured DashScope API key, clicked model save, but config wasn't persisted until global save was clicked
- Trust erosion: "did my API key actually save?"

## 5. Fix Strategy

Make `saveModelEdit()` trigger the actual backend save after updating local state.

### Changes

1. **`save()` accepts optional `formOverride` parameter** — allows callers to pass a pre-computed form instead of reading from React state (which may be stale due to batching)
2. **`saveModelEdit()` becomes async, calls `save()` with the computed final form** — single consistent save path
3. **Model save button shows loading/saving state** — same spinner pattern as global save
4. **Success/error feedback inline** — reuse existing `message`/`saveError` state

### Non-changes

- Provider config model: unchanged
- API contract (`PATCH /api/config/editable`): unchanged
- API key handling: unchanged (already password field, never echoed)
- Approval/recall/BM25: unchanged
- Provider business semantics: unchanged

## 6. Implementation

File: `web/src/pages/SetupPage.tsx`

### 6.1 `save()` accepts formOverride

```typescript
async function save(formOverride?: SetupForm) {
    const current = formOverride ?? draftForm;
    // ... same save logic ...
}
```

### 6.2 `saveModelEdit()` calls save

```typescript
async function saveModelEdit() {
    // ... same validation and form computation ...
    const finalForm = { ...form, models: nextModels, ... };
    setForm(finalForm);
    setEditing(null);
    await save(finalForm);
}
```

### 6.3 Model save button loading state

The model save button reuses the global `saving` state — when `saving` is true, the button shows a spinner and is disabled.

## 7. Self-Review Checklist

- [x] Model save actually persists to backend
- [x] No two conflicting save semantics
- [x] Loading spinner on model save button
- [x] Success feedback visible after save
- [x] Error feedback visible on failure
- [x] API key never leaked to console/DOM
- [x] Provider config model unchanged
- [x] zh/en labels correct
- [x] No P0/P1/P2 introduced

## 8. Gate

```bash
npm --prefix web run build        # must exit 0
python -m pytest tests/test_web_product_copy.py -q  # must exit 0
git diff --check                  # must exit 0
```

## 9. Results — Fake Save Smoke (2026-05-23)

### 9.1 Environment

- **Commit**: `c38358a` (fix already applied)
- **Web URL**: `http://127.0.0.1:8765/setup`
- **Backend**: uvicorn, port 8765
- **Browser**: Chrome DevTools MCP

### 9.2 Fake Model Configuration

| Field | Value |
|-------|-------|
| Model ID | `second-smoke-model` |
| Type | `openai` |
| Base URL | `http://localhost:9998` |
| Model | `second-test-model` |
| API Key | `another-dummy-key-xyz` (dummy, not real) |

### 9.3 Smoke Results

| # | Check | Result |
|---|-------|--------|
| 1 | PATCH /api/config/editable emitted | **PASS** — reqid=1966, status 200 |
| 2 | Model persists after page refresh | **PASS** — `second-smoke-model` visible after reload |
| 3 | Success message displayed | **PASS** — "Setup saved" (EN) / "已保存" (ZH) |
| 4 | Loading/saving feedback | **PASS** — button shows spinner + disabled during save |
| 5 | API key NOT leaked in response | **PASS** — masked as `****-xyz` in response body |
| 6 | API key NOT leaked in DOM | **PASS** — "configured · ****-xyz" in UI |
| 7 | API key NOT in console | **PASS** — no console errors or key exposure |
| 8 | Global Save still usable | **PASS** — button present, disabled when no pending changes (correct) |
| 9 | zh-CN labels correct | **PASS** — 保存, 取消, 已配置模型, 保存配置, etc. |
| 10 | en labels correct | **PASS** — Save, Cancel, Configured models, Save setup, etc. |
| 11 | No JS errors in console | **PASS** — only verbose DOM password-field warning |
| 12 | No unexpected 4xx/5xx | **PASS** — all requests returned 200 |

### 9.4 Known P3/P4 Issues (not blocking)

- **P3**: `type=fake` backend models not represented in frontend `configured_models`, causing data inconsistency when default_model references a fake model. Workaround: use only non-fake models for smoke testing.
- **P4**: Dogfood YAML linter auto-removes `provider` field during PATCH operations. Cosmetic, does not affect functionality.

## 10. Conclusion

Setup provider/model Save fix (`c38358a`) is **verified working** via fake browser smoke. Model-level save correctly triggers PATCH /api/config/editable, persists configuration, provides clear success/error feedback, and never leaks API keys. No P0/P1/P2 issues found. Ready for real dogfood verification when appropriate.
