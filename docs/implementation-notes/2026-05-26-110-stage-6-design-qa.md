# Stage 6 Design QA — Implementation Notes

**Date:** 2026-05-26
**HEAD:** `07bd8a0`
**Status:** Completed (browser-assisted QA pass)

---

## QA Methodology

Used Chrome DevTools MCP to inspect the live Vite dev server at `http://127.0.0.1:5174/`. Checked 8 page types: Home, Drafts, Library, Wiki, Health, Recall, Setup, Sources.

Due to no backend running (API calls fail), the Library and some data-dependent pages showed empty/error states. Design token verification and header styling checks were still possible via CSS computed style inspection.

## Design Token Verification (all passed)

| Token | Expected | Actual | Status |
|-------|----------|--------|--------|
| `--mf-accent` | #2d7d5f | #2d7d5f | ✓ |
| `--mf-bg` | #faf9f5 | #faf9f5 | ✓ |
| `--mf-font-serif` | "Source Serif 4", Georgia, serif | "Source Serif 4", Georgia, serif | ✓ |
| `--mf-font-sans` | "DM Sans", system-ui, -apple-system, sans-serif | "DM Sans", system-ui, -apple-system, sans-serif | ✓ |
| `.page-header h1` font | Source Serif 4 | Source Serif 4 (28px) | ✓ |
| Focus ring | 2px solid --mf-accent | `button:focus-visible, a:focus-visible, input:focus-visible { outline: 2px solid var(--mf-accent); }` | ✓ |
| Old blue (#2368d1) | 0 instances | 0 instances | ✓ |
| Forest Green accent | Present in buttons, sidebar, links | 5 instances on Drafts page alone | ✓ |
| Lab collapsed default | aria-expanded="false" | aria-expanded="false" | ✓ |
| Sidebar active item | Forest Green left-border | 2px solid rgb(45, 125, 95) | ✓ |

## Issue Found & Fixed: `.page-header` consistency (4 files)

4 page headers were using plain `<header>` or bare `<h1>` with Tailwind utility classes (`text-2xl font-semibold text-ink`), missing the `.page-header` CSS class that applies serif font, proper sizing, and spacing:

| File | Before | After |
|------|--------|-------|
| `web/src/components/wiki/WikiHeader.tsx` | `<header>` + `text-2xl font-semibold text-ink` | `<header className="page-header">` |
| `web/src/pages/HealthPage.tsx` | Bare `<h1 className="text-2xl...">` | Wrapped in `<header className="page-header">` |
| `web/src/pages/SourcesPage.tsx` | `<header>` + `text-2xl font-semibold text-ink` | `<header className="page-header">` |
| `web/src/pages/SetupPage.tsx` | `<header>` + `text-2xl font-semibold text-ink` | `<header className="page-header">` |

These were the only pages not updated in Stages 1-5. The original implementation plan listed only Home, Drafts, Library, Recall, and EmptyState as Stage 5 scope — Health, Wiki, Sources, and Setup were missed.

## Responsive Check

| Width | Overflow | Status |
|-------|----------|--------|
| 375px (mobile) | scrollWidth > clientWidth | ⚠️ horizontal overflow — pre-existing, sidebar not collapsed |
| 1024px (desktop) | no overflow | ✓ |

The mobile overflow is a pre-existing condition — the Sidebar component doesn't collapse to a hamburger menu on mobile. This was never in scope for the design refresh and would require a separate UX project.

## Inline Style Audit

- No Lucide `style` prop issues found (all icons wrapped in `<span>` or use className)
- No remaining `#2368d1` / old blue hex values in source
- All inline `style={{ }}` use `var(--mf-*)` references, no hardcoded hex values

## Gates

| Gate | Command | Exit | Timeout |
|------|---------|------|---------|
| Build | `npm --prefix web run build` | 0 | no |
| Git diff | `git diff --check` | 0 | no |
| Product copy tests | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 | no |

## Not Done (deferred)

- Full backend API running for data-rich page QA (Library card shadows, ApprovalPanel interaction)
- Mobile responsive deep-dive (sidebar collapse)
- Accessibility audit (color contrast ratios, keyboard navigation, screen reader)
- Performance trace audit
