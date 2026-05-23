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

- [ ] Model save actually persists to backend
- [ ] No two conflicting save semantics
- [ ] Loading spinner on model save button
- [ ] Success feedback visible after save
- [ ] Error feedback visible on failure
- [ ] API key never leaked to console/DOM
- [ ] Provider config model unchanged
- [ ] zh/en labels correct
- [ ] No P0/P1/P2 introduced

## 8. Gate

```bash
npm --prefix web run build        # must exit 0
python -m pytest tests/test_web_product_copy.py -q  # must exit 0
git diff --check                  # must exit 0
```

## 9. Results

*(To be filled after execution)*

## 10. Conclusion

*(To be filled after execution)*
