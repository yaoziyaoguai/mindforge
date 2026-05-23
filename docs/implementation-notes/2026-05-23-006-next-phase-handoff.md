# MindForge Next Phase Handoff — Milestone G: Wiki Reading Experience

**Date**: 2026-05-23
**From session**: Post-Milestone F smoke + next phase planning
**To**: Fresh Claude session (recommended — context is low)

---

## Current State

### Repo

- **Branch**: main
- **HEAD**: `63844ad` docs: record milestone F browser smoke results
- **main ↔ origin/main**: 0 0 (aligned)
- **Working tree**: clean

### Completed Milestones

| Milestone | What | Status |
|-----------|------|--------|
| A | UX P0 fixes (Setup stepping, approval UX, empty states) | done |
| B | UX P1/P2 polish (sidebar groups, status icons, Recall, CardWorkspace typography) | done |
| C | i18n, accessibility, visual polish (~200 i18n keys, zh/en toggle) | done |
| D | Dashboard Action Guidance (Home page action cards, NextAction system) | done |
| E | Setup Deep Restructure (3-step wizard, model CRUD, provider config) | done |
| F | Knowledge Card Browsing Experience (Card Grid, Summary Panel, Related Cards) | done |
| G | **Wiki Reading Experience** | **planned** |

### Recent Commits (top 5)

```
63844ad docs: record milestone F browser smoke results
70c7782 feat(web): upgrade library from sidebar list to card grid browsing experience
eec4ee7 docs: record setup provider save smoke
c38358a fix(web): clarify setup provider save behavior
cd6d23f docs: record real llm dogfood run
```

### Milestone F Browser Smoke: PASSED
- All 5 implementation units verified
- All pages regression free (Home, Setup, Library, Drafts, Wiki)
- 28 API calls all 200, no JS errors
- zh/en i18n correct
- P0/P1/P2: none

---

## Next Phase Decision

### Recommendation: Milestone G — Wiki Reading Experience

### Why

1. **Completes the product arc.** A-F built infrastructure (browsing, approval, i18n, setup). G polishes the end-user reading experience.
2. **Natural deferred work.** Milestone F spec §3 explicitly deferred "Wiki TOC Scroll Spy / Print Export / Reader mode" to a future milestone.
3. **Purely frontend.** No backend changes, no API changes, no LLM calls. Safe and reversible.
4. **Data already available.** All Wiki data comes from existing `/api/wiki/page` — no new endpoints needed.
5. **Measurable impact.** The Wiki is functional but reads like an engineering dashboard. Reader mode + print styles + scroll spy transforms it into a genuine reading experience.

### What NOT to Revisit

- Milestone B sidebar grouping
- Milestone C i18n (keys already exist, just add new ones)
- Milestone D action guidance
- Milestone E setup restructuring
- Milestone F card grid / summary panel / related cards

---

## Milestone G Spec

**Path**: `docs/specs/2026-05-23-006-wiki-reading-experience-spec.md`
**Status**: draft (written, not yet reviewed)

**5 Implementation Units:**

| Unit | What | Files | Complexity |
|------|------|-------|------------|
| U1 | Print Styles | `styles.css` | Low (CSS only) |
| U2 | TOC Scroll Spy | `WikiTOC.tsx`, `WikiSection.tsx` | Medium (IntersectionObserver) |
| U3 | Reader Mode Toggle | `WikiPage.tsx`, `WikiStatusBar.tsx`, `i18n.ts` | Medium (layout toggle) |
| U4 | Typography Polish | `styles.css`, `WikiReadingPane.tsx` | Low (CSS values) |
| U5 | i18n + Contract Tests | `i18n.ts`, `test_web_product_copy.py` | Low (~6 new keys) |

**Total estimated touch**: ~8 files, ~200 LOC

---

## Execution Checklist (for next session)

### Phase 0: Environment
- [ ] `git pull --ff-only origin main`
- [ ] Confirm working tree clean
- [ ] Read `docs/specs/2026-05-23-006-wiki-reading-experience-spec.md`
- [ ] Read `web/src/pages/WikiPage.tsx` and all 12 wiki components

### Phase 1: Spec Review
- [ ] Self-review spec — check scope, edge cases, completeness
- [ ] Fix spec issues before coding

### Phase 2: Implementation (U1 → U4 → U2 → U3 → U5)
- [ ] U1: Print styles (CSS only, test in browser print preview)
- [ ] U4: Typography (CSS + WikiReadingPane)
- [ ] U2: TOC Scroll Spy (IntersectionObserver)
- [ ] U3: Reader Mode (state toggle in WikiPage)
- [ ] U5: i18n keys + contract tests

### Phase 3: Gate
- [ ] `npm --prefix web run build` (exit 0)
- [ ] `python -m pytest tests/test_web_product_copy.py -q` (all pass)
- [ ] `git diff --check` (exit 0)

### Phase 4: Browser Smoke
- [ ] Wiki page — reader mode toggle
- [ ] Wiki page — TOC scroll spy follows scroll position
- [ ] Print preview — only content visible
- [ ] zh/en toggle — new keys verified
- [ ] Console — no JS errors
- [ ] Network — all 200
- [ ] Regression — Home, Setup, Library, Drafts still work

### Phase 5: Ship
- [ ] `git add` + commit
- [ ] `git push origin main`
- [ ] Confirm 0 0 alignment

---

## Hard Constraints (same as always)

1. 不要读取 .env / secrets
2. 不要调用真实 LLM / API
3. 不要处理真实私人资料
4. 不要改 provider / approval / recall / BM25 语义
5. 不要做 RAG / embedding
6. 不要新增大型框架 / npm 依赖
7. 不要 tag / release / PR
8. Fast lane main: gate 通过后直接 commit + push

---

## If Blocked

If Milestone G spec review uncovers issues that can't be resolved without user input, or if the spec needs significant revision — write findings to `docs/implementation-notes/2026-05-23-006-wiki-reading-experience-review-findings.md` and commit. Don't start implementing on a flawed spec.
