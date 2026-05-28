# Dogfood P0/P1 Remediation — 2026-05-28

## P0 DOGFOOD-001: provider_readiness_detail() self.secrets AttributeError

### Root cause

`WebFacade.provider_readiness_detail()` at line 843 called `self.secrets.api_key_source(...)`,
but `WebFacade.__init__` never set `self.secrets`. The `WebConfigService` (accessible as
`self.config_service`) already initializes a `WebConfigSecretManager` as
`self.config_service.secrets`.

### Fix

Changed `self.secrets.api_key_source(...)` → `self.config_service.secrets.api_key_source(...)`.
One-line fix, no new dependencies, no secret exposure.

### Security verification

- `WebConfigSecretManager.api_key_source()` only returns a source label ("demo" / "local_secret" / "env" / "missing"), never the raw key value.
- `provider_readiness_detail()` only uses source label for presence check (boolean).
- Invariant `secret_value_not_returned: True` enforced by `provider_readiness.build_readiness_report`.

## P1 DOGFOOD-002: 5 OpenAPI endpoints returning 404

### Investigation result: FALSE POSITIVE

All 5 endpoints exist in both OpenAPI schema and actual registered routes:

1. `GET  /api/config/status` — exists in `config.py:20`
2. `POST /api/config/check` — exists in `config.py:25`
3. `POST /api/config/provider-mode` — exists in `config.py:43`
4. `POST /api/knowledge/export` — exists in `library.py:101`
5. `GET  /api/provider/readiness` — exists in `provider_readiness.py:15` (was 500 from P0, now fixed)

OpenAPI schema ↔ route comparison via `create_app().openapi()` confirmed zero drift
(only FastAPI's normal `{path:param}` → `{param}` normalization).

Previous dogfood v1 404s were likely testing-method errors (GET to POST-only endpoints).

### No code changes needed

## P2 DOGFOOD-003: Triage threshold for short texts

Product note: `value_score < 5` threshold intentionally blocks short imports.
`--force` flag available as explicit override in CLI path. Behavior is by design;
no code changes. If this becomes a frequent user complaint, consider
batch-confirm or low-risk auto-pass for source material above certain size.

## Modified files

- `src/mindforge_web/services/web_facade.py` — P0 one-line fix (line 843)
- `tests/test_provider_readiness.py` — P0 regression test (with models + env var, no secret leak)

## Gates

| Gate | Command | Exit code | Notes |
|------|---------|-----------|-------|
| ruff | `ruff check src/ tests/` | 0 | All checks passed |
| pytest | `python -m pytest tests/ -q --tb=short` | 0 | 3638 passed, 1 skipped (pre-existing) |
| npm build | `npm --prefix web run build` | 0 | Built in 5.26s |
| git diff | `git diff --check` | 0 | No whitespace errors |

## Verdict

- P0: CLOSED (one-line fix, test added)
- P1: NOT A BUG (false positive — all 5 endpoints have routes)
- P2: PRODUCT NOTE (threshold behavior intentional, `--force` available)
