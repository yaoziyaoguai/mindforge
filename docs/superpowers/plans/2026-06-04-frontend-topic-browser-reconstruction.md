# Frontend Topic Browser Reconstruction Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the deprecated LLM Wiki rebuild UI with a runtime Topic Browser that consumes `/api/topics` endpoints.

**Architecture:** New `web/src/api/topics.ts` API client fetches from `/api/topics`. `WikiPage.tsx` is rewritten as a thin adapter composing `TopicBrowser`, which orchestrates `TopicList` + `TopicView` + `TopicContextPanel`. All old "Generate Wiki" / `/api/wiki/rebuild` calls are removed. No new dependencies.

**Tech Stack:** React 19, TypeScript, Tailwind CSS, Vitest + Testing Library, custom i18n (LocaleProvider)

**API Contract:** `docs/specs/topic_view_api.md` — `GET /api/topics` → `TopicListResponse`, `GET /api/topics/{topic_name}` → `TopicViewResponse` (404 for no approved cards)

---

## Current Problems

1. `WikiPage.tsx` calls `/api/wiki/status`, `/api/wiki/page`, `/api/wiki/quality`, `/api/wiki/related-sections` — all legacy endpoints
2. "Generate Wiki" button calls `POST /api/wiki/rebuild` which returns 410
3. "Safe fallback rebuild" calls `POST /api/wiki/rebuild` with `mode: "deterministic"` which also returns 410
4. `docs/zh-CN/web-wiki.md` describes old Generate Wiki flow
5. Navigation says "Wiki" but content is LLM synthesis, not runtime topic view

## Target Experience

User visits `/wiki` → sees:
- **Left sidebar**: Topic list from `GET /api/topics`, each with topic name, clickable
- **Center**: Selected topic's cards from `GET /api/topics/{name}`, showing card details
- **Right**: Selected card's relations/provenance context
- **Empty state**: Clear message when no topics exist (no approved cards)
- **No Generate Wiki button**, no `/api/wiki/rebuild` calls

## Component Tree

```
WikiPage (thin adapter)
└── TopicBrowser (orchestration: selected topic state, loading)
    ├── TopicList (left: list of topic names)
    ├── TopicView (center: cards for selected topic)
    │   └── TopicCard (single card display, repeated)
    └── TopicContextPanel (right: selected card's relations)
```

## File Changes

### Create
- `web/src/api/topics.ts` — `listTopics()`, `getTopic(name)`
- `web/src/components/wiki/TopicBrowser.tsx` — orchestration
- `web/src/components/wiki/TopicList.tsx` — topic sidebar
- `web/src/components/wiki/TopicView.tsx` — card list for topic
- `web/src/components/wiki/TopicCard.tsx` — single card
- `web/src/components/wiki/TopicContextPanel.tsx` — relations panel
- `web/src/pages/__tests__/WikiPage.test.tsx` — component tests

### Modify
- `web/src/pages/WikiPage.tsx` — full rewrite as thin adapter
- `web/src/lib/i18n.ts` — add topic-related i18n keys

### Docs
- `docs/zh-CN/web-wiki.md` — rewrite for Topic View

### Not Touched
- Old wiki components under `web/src/components/wiki/` (keep for potential legacy read, not imported by new WikiPage)
- `web/src/api/wiki.ts` (keep types for any legacy consumers, not imported by new WikiPage)
- Backend code (no changes)

## Self-Review Checklist

- [x] Does NOT call `/api/wiki/rebuild`
- [x] Does NOT treat legacy wiki as core experience
- [x] Does NOT break approval boundary (only shows `approval_state: "human_approved"`)
- [x] No new large dependencies
- [x] Not over-engineered — 5 focused components
- [x] Uses existing API contract as-is

## Acceptance Criteria

1. `npm run build` passes
2. WikiPage renders topic list from API, shows cards on selection
3. No `/api/wiki/rebuild` calls in WikiPage code
4. Generate Wiki buttons removed
5. Empty state handled for no topics / no approved cards
6. `docs/zh-CN/web-wiki.md` updated to Topic View
