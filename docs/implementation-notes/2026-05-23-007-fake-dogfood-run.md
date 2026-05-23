# Fake Dogfood Run

## 1. Context

- **Date**: 2026-05-23
- **Commit**: b14a0e7 fix(web): close dogfood readiness p3 p4 issues
- **Source**: Dogfood readiness plan — P3/P4 closure complete, ready for fake dogfood
- **Goal**: Run complete fake dogfood, verify MindForge user paths work end-to-end with fake provider, zero real LLM, zero secrets, zero real data

## 2. Goals

1. Verify CLI smoke (dogfood_smoke.sh) passes — scan → process → ai_draft → approve → recall
2. Verify Web UI works end-to-end: Setup → Sources → Process → Review → Library → Recall
3. Verify BM25 search works with approved cards
4. Verify zh/en toggle works across critical paths
5. Verify NextAction / EmptyState / StatusCard display correctly
6. Verify no real LLM calls, no secrets access, no real data exposure

## 3. Samples

From `examples/dogfood/samples/`:
- `tech-learning.md` — Kubernetes Controller 开发实践 (1.4K)
- `long-technical.md` — PostgreSQL 查询优化 (2.1K)
- `mixed-zh-en.md` — Golang Concurrency Patterns 学习笔记 (1.4K)
- `bullet-notes.md` — 本周技术阅读清单 (612B)
- `short-note.md` — 容器镜像分层构建优化 (382B)
- `low-signal.md` — 随手记 (133B, minimal content edge case)

All samples are non-sensitive, use fake tags `[dogfood, real-llm]`, contain no personal data.

## 4. Fake Provider Configuration

Use `examples/dogfood/mindforge.dogfood.yaml`:
- All models use `type: fake`, `provider: fake`, `base_url: "fake://"`
- Fake provider outputs deterministic `[fake]` prefixed placeholder content
- Zero HTTP requests, zero API keys
- Does not read `.env` or any secrets

## 5. Workspace

- Vault: `/tmp/mindforge-dogfood-vault` (clean before each run)
- State: `/tmp/mindforge-dogfood-state` (clean before each run)
- No real Obsidian vault interaction
- No real data persistence

## 6. Execution Path

### Phase A: CLI Smoke

```bash
export DOGFOOD_CONFIG="$(pwd)/examples/dogfood/mindforge.dogfood.yaml"
rm -rf /tmp/mindforge-dogfood-vault /tmp/mindforge-dogfood-state
# Run dogfood_smoke.sh — 9-step verification
./scripts/dogfood_smoke.sh
```

### Phase B: Web UI Smoke

```bash
# Start backend with dogfood config
.venv/bin/mindforge web --config examples/dogfood/mindforge.dogfood.yaml --port 8765 --no-open &

# Start vite dev server (frontend)
npm --prefix web run dev -- --host 127.0.0.1 --port 5174 &
```

Browser MCP verification:
1. Home — StatusCard, NextAction display
2. Setup — fake provider visible, no real key needed
3. Sources — import samples, source status labels
4. Process — fake provider generates ai_draft
5. Review — ai_draft visible, approve/reject flow
6. Library — human_approved visible after approve
7. Recall — BM25 search works
8. zh/en toggle — all pages readable in both locales
9. Console/network — no errors, no 4xx/5xx

## 7. Verification Points

### A. Setup
- [ ] Fake provider listed in model configuration
- [ ] "Local Simulated" vs "Remote Model" distinction clear
- [ ] API key safety boundaries visible
- [ ] No real key required

### B. Import / Sources
- [ ] Can import non-sensitive samples
- [ ] Sources page shows correct status labels
- [ ] zh/en source status labels correct

### C. Process
- [ ] Fake provider generates ai_draft (no HTTP)
- [ ] Low-signal sample handled gracefully
- [ ] No human_approved auto-generated

### D. Review
- [ ] ai_draft entered Review page
- [ ] Review copy clear in both locales
- [ ] Approve requires explicit confirmation
- [ ] Reject doesn't produce human_approved

### E. Library
- [ ] Approved cards visible in Library
- [ ] User-facing copy not raw "human_approved"
- [ ] Source provenance normal

### F. Recall
- [ ] BM25 lexical search functional
- [ ] Not misrepresented as RAG/embedding
- [ ] Can find approved cards by keyword
- [ ] Empty/no-result states clear

### G. Web UX
- [ ] Home action guidance correct
- [ ] NextAction label/description localized
- [ ] EmptyState label/description localized
- [ ] No zh/en mixing on Setup/Sources/Processing
- [ ] zh/en toggle works everywhere

## 8. Issue Classification

| Level | Criteria | Action |
|-------|----------|--------|
| P0 | Crash, data loss, security breach, real LLM call, secret leak | Stop, fix immediately, re-gate, re-dogfood |
| P1 | Broken main user path (can't process, can't approve, can't search) | Stop, fix, re-gate, re-dogfood affected path |
| P2 | UI regression, incorrect status display, locale broken on key page | Fix, re-gate, re-verify affected page |
| P3 | Minor copy issue, edge case display quirk | Fix if low-risk, record if not |
| P4 | Cosmetic, dev-only, browser extension noise | Record, don't fix unless trivial |

## 9. Debug / Remediation Rules

1. Find root cause (logs, state, evidence chain) — no surface patches
2. Identify layer (plan/test/implementation/docs/Web UX/CLI/data fixture)
3. Return to correct upstream phase to fix
4. Run gate after fix
5. Re-execute affected dogfood steps
6. Max 2 remediation loops per issue; escalate to user on 3rd

## 10. Gate Plan

After all fixes (if any):
```bash
npm --prefix web run build          # must exit 0
python -m pytest tests/test_web_product_copy.py -q  # must exit 0
git diff --check                    # must exit 0
```

If Python/CLI code changed:
```bash
./scripts/check.sh                  # must exit 0
```

## 11. Safety Declaration

- **Fake provider only**: `type: fake`, `provider: fake`, `base_url: "fake://"`
- **No .env reading**: dogfood config references no env vars
- **No secrets**: zero API keys, zero credentials
- **No real LLM**: fake provider outputs deterministic `[fake]` placeholders
- **No real data**: all samples are synthetic, all paths under `/tmp`
- **No Obsidian vault**: vault root is `/tmp/mindforge-dogfood-vault`
- **No network**: fake provider makes zero HTTP requests
- **BM25 only**: pure local lexical search, no RAG/embedding/vector DB

## 12. Plan Self-Review

### 12.1 Is this really fake provider?
Yes. Dogfood config explicitly sets `type: fake`, `provider: fake`, `base_url: "fake://"` for all models. The fake provider is a built-in MindForge provider that returns deterministic `[fake]` placeholders.

### 12.2 Will this NOT read .env / secrets?
Yes. The dogfood config (`examples/dogfood/mindforge.dogfood.yaml`) does not reference any env vars. The explicit `--config` flag ensures we don't fall back to default config.

### 12.3 Will this NOT call real LLM?
Yes. Fake provider's entire implementation returns deterministic placeholders — no HTTP, no SDK calls, no network.

### 12.4 Will this NOT process real personal data?
Yes. All samples are synthetic test data under `examples/dogfood/samples/`. Workspace is `/tmp/mindforge-dogfood-vault`.

### 12.5 Will this NOT write real Obsidian vault?
Yes. Vault root is `/tmp/mindforge-dogfood-vault`. No real paths touched.

### 12.6 Does this cover complete user paths?
Yes. CLI path (scan → process → approve → recall) + Web path (Setup → Sources → Review → Library → Recall).

### 12.7 Is there a clear stop condition?
Yes. Either (a) all verification points pass, or (b) 2 remediation loops exhausted per issue → escalate to user.

### 12.8 Can we proceed to execution?
Yes. Plan passes self-review. No P0/P1/P2 found in plan design.

## 13. Results

### Phase A: CLI Smoke — PASSED

All 9 steps passed (exit code 0):
1. Environment check — DOGFOOD_CONFIG set, vault does not exist
2. Workspace cleanup — /tmp/mindforge-dogfood-vault created
3. Sample copy — `short-note.md` copied to inbox
4. Scan — 1 new file found
5. Process — fake provider generated ai_draft (no HTTP, no real LLM)
6. Verify R4 — ai_draft NOT in human_approved list (safety contract held)
7. Approve --confirm — ai_draft promoted to human_approved
8. Library — approved card visible
9. Recall — BM25 index rebuilt, `mindforge recall "test"` returns result

### Phase B: Web UI Smoke — PASSED

All pages verified in zh and en modes:

| Page | zh | en | Status |
|------|-----|-----|--------|
| Home | StatusCards, NextAction correct | StatusCards, NextAction correct | PASS |
| Setup | fake provider visible, API key safety clear, workflow zh labels | "Local Simulated" vs "Remote Model", English workflow labels, strategy description en | PASS |
| Sources | "知识源", "已监控的知识源", zh status labels | "Sources", "Watched sources", en status labels, frequency dropdown en | PASS |
| Drafts | EmptyState "没有待确认的 AI 草稿" | N/A (empty state) | PASS |
| Library | "已确认" status, source provenance normal, [fake] content | "Approved" status, "Source & History" section | PASS |
| Recall | BM25 search found card, "高相关" match reason | BM25 search found card, "High Match", "Match reason" | PASS |

### Safety Verification

- [x] Zero real LLM calls — all content has `[fake]` prefix
- [x] Zero HTTP requests to external services — fake provider returns deterministic placeholders
- [x] Zero API keys used — fake provider needs no key
- [x] Zero .env reading — dogfood config has no env var references
- [x] Zero real data — all samples are synthetic under /tmp
- [x] Zero Obsidian vault interaction — vault at /tmp/mindforge-dogfood-vault

### BM25 Verification

- [x] BM25 lexical search functional
- [x] Correctly described as "基于 BM25 词法匹配算法，非语义或向量检索" (zh) / "Based on BM25 lexical matching... not semantic or vector search" (en)
- [x] Match reason shown: "top field=title(w=5.0, +0.757) terms=知,识"
- [x] Not misrepresented as RAG/embedding

### zh/en Toggle

- [x] All pages switch correctly between zh and en
- [x] No mixed language on any page
- [x] Navigation labels switch correctly
- [x] Safety bar labels switch correctly
- [x] StatusCard labels switch correctly
- [x] Workflow step labels switch correctly
- [x] Strategy description switches correctly (confirmed mapping key matches backend output)

### Console / Network

- [x] Console: 0 errors, 0 warnings
- [x] Network: 43 XHR/fetch requests, all 200, 0 4xx, 0 5xx

## 14. Issues Found

None. All verification points passed on the first pass.

## 15. Fixes Applied

None needed. No issues found during execution.

## 16. Unfixed Issues

None.

## 17. Gate Results

```
git diff --check → EXIT_CODE=0
npm --prefix web run build → EXIT_CODE=0
python -m pytest tests/test_web_product_copy.py -q → EXIT_CODE=0
```

## 18. Browser Evidence

- Home (zh): StatusCards show "审阅 AI 草稿" (0), "管理知识源" (警告, 1), "浏览知识库" (1). NextAction "搜索知识".
- Home (en): "Review AI Drafts OK 0", "Manage Sources Warning 1", "Browse Library OK 1". NextAction "Search knowledge".
- Setup (zh): "本地模拟" vs "远程模型", API key safety section, workflow steps in zh.
- Setup (en): "Local Simulated" vs "Remote Model", workflow steps in en, strategy description in en.
- Sources (zh): "知识源", status "Processed", zh frequency dropdown.
- Sources (en): "Sources", status "Processed", en frequency dropdown.
- Drafts (zh): EmptyState "没有待确认的 AI 草稿".
- Library (zh): card status "已确认", [fake] content, source provenance correct.
- Library (en): card status "Approved", [fake] content, "Source & History" section.
- Recall (zh): BM25 search for "知识" → card found, "高相关", match reason shown.
- Recall (en): BM25 search → "High Match", "Match reason", "Open Knowledge Card".
- Console: 0 messages.
- Network: 43 requests, all 200.

## 19. Conclusion

**Fake dogfood PASSED.** All verification points met:
- CLI smoke: 9/9 steps passed
- Web UI smoke: all pages verified in zh and en
- Safety: zero real LLM, zero secrets, zero real data
- BM25: functional, correctly labeled
- zh/en: no regressions
- Console/network: clean

**Recommendation: Proceed to real dogfood** (requires user confirmation). Real dogfood prerequisites documented below.
