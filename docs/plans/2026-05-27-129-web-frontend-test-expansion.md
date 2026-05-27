# Web Frontend Test Coverage Expansion — Plan

**日期**: 2026-05-27
**状态**: active
**输入**: v3.7 Quality Platform (vitest + happy-dom infrastructure already in place)
**范围**: 扩展现有测试覆盖，从 1 个测试文件扩展到 4 个

---

## Implementation Units

### U1: LoadingSkeleton Tests

**Files**: `web/src/components/__tests__/LoadingSkeleton.test.tsx` (NEW)

Pure CSS component, no hooks, no context, no API calls. 

**Test scenarios:**
- `default` variant renders without error
- `wiki` variant renders
- `library` variant renders 4 stat cards + 6 card skeletons
- `animate-pulse` class present on each variant

### U2: EmptyState Tests

**Files**: `web/src/components/__tests__/EmptyState.test.tsx` (NEW)

Uses `nextActionLabel`/`nextActionDescription` from utils, `NextAction` type from API types. No hooks, no context.

**Test scenarios:**
- Renders title text
- Renders with action label and description
- Renders command as `<code>` when action.command is set
- Renders link when action.href is set
- Renders button when action.onClick is set

### U3: StatusCard Tests

**Files**: `web/src/components/__tests__/StatusCard.test.tsx` (NEW)

Uses `statusIcon`/`statusLabel`/`statusTone`/`nextActionLabel` from utils. No hooks, no context.

**Test scenarios:**
- Renders label and value
- Renders status badge
- Renders detail text when provided
- Renders nextAction when provided
- Renders as `<button>` when href is set
- Renders as `<section>` when no href

---

## Out of Scope (deferred)

- Breadcrumb/SafetyBar — need `useLocale` hook context setup
- Page-level tests — need routing/i18n provider setup
- Components with async data fetching
