# Web IA/UX Loop 2 — Post-Dogfood Audit

Date: 2026-05-27
Baseline HEAD: `97d57fb`
Task type: `ui_ux_polish`
Scope: Web IA/UX P1/P2 fixes based on post-governance global red team audit (2026-05-27-118)

## Browser / MCP

Chrome DevTools MCP was available but not used for this loop. All findings based on source code review of web/src/ pages, components, and i18n strings. Browser smoke should be done in a follow-up loop when the dev server is running.

## Pages Inspected

| Page | Status | Issues Found |
|------|--------|-------------|
| Sidebar | Reviewed | Dogfood in tools group (P1) |
| DogfoodPage | Reviewed | No internal/dev banner (P1) |
| LocalGraphPreview | Reviewed | Hardcoded English strings (P1) |
| ExportPage | Reviewed | Copy already accurate, no changes needed |
| SetupPage | Reviewed | Already well-structured: 3-step disclosure, fake-default, activation checklist |
| GraphPage | Reviewed | Already has lab/internal notice for unsupported NodeTypes |
| SensemakingPage | Reviewed | Already has prominent LAB/INTERNAL banner |
| HealthPage | Reviewed | No issues |

## P1 Fixes Applied

### P1-01: Dogfood nav exposure
- **Before**: `/dogfood` in Sidebar "tools" group alongside Health, Export, Trash — visible as normal user feature
- **After**: Moved to collapsed "lab" section — hidden by default, clearly experimental
- **Additional**: Added LAB/INTERNAL banner at top of DogfoodPage explaining it's internal dev validation evidence

### P1-02: Internal term sanitization (LocalGraphPreview)
- **Before**: Hardcoded English strings "Local Graph Preview", "Local graph", "No deterministic relationships found yet..."
- **After**: All strings use i18n keys (`local_graph.title`, `local_graph.section_title`, `local_graph.empty`, `local_graph.related_count`)
- **i18n**: Added Chinese ("局部关系预览") and English ("Local Relationship Preview") translations

### P1-03: Export copy drift
- **Finding**: Export page copy already accurate — explicitly states browser-local download, no Obsidian write, no external service
- **No changes needed** to ExportPage or its i18n strings

### P2: Setup cognitive load
- **Finding**: SetupPage already has 3-step progressive disclosure (models/sources/review), fake-default green banner with explicit activation dialog, collapsed advanced settings
- **No changes needed**

## Remaining UX Debt

- Browser smoke on all pages (need running dev server)
- User guide docs still reference outdated Export/Import state (docs debt, not web)
- web_facade.py architectural debt (separate workstream: Architecture Quality Reset)

## Recommendation

Web IA/UX Loop 2 P1 fixes are complete. Next workstream should be Architecture Quality Reset, which needs a spec/plan before implementation.
