# MindForge Web Architecture

## Scope

MindForge Web v1 is a local presentation and control layer over the existing
MindForge backend. It serves one user on localhost and helps that user inspect
configuration, source state, draft review state, approval boundaries, and local
recall without using the CLI for every step.

It intentionally does not introduce accounts, cloud sync, OAuth, payments,
multi-user permissions, deployment hosting, RAG, embeddings, semantic merge,
Obsidian plugins, TUI, or desktop packaging.

## Layering

The first version uses this flow:

```text
React UI
  -> FastAPI APIRouter controller
  -> mindforge_web.services Web Facade
  -> existing mindforge service / policy / storage modules
  -> local files under the configured vault and .mindforge workdir
```

Routers are thin controllers. They validate request payloads, call the facade,
and return Pydantic schemas. They do not assemble card state by hand and do not
perform approval writes directly.

The Web Facade is the only Web-specific orchestration layer. It converts Web
questions into existing MindForge use-cases:

- app/config paths: `mindforge.app_context`
- provider readiness: `mindforge.provider_readiness`
- Cubox readiness: `mindforge.cubox_readiness`
- source and workspace state: `mindforge.config`, `mindforge.scanner`,
  `mindforge.checkpoint`
- draft queue and preview: `mindforge.approval_service`, `mindforge.cards`
- approval write boundary: `mindforge.approval_service.approve_explicit_card`
- recall: `mindforge.recall_service`

## Approval Boundary

Web approval preserves the same human boundary as the CLI:

1. The user opens one explicit draft.
2. The UI shows source and draft context.
3. The user checks that the source was reviewed.
4. The user confirms the approve action.
5. The API requires `confirm: true` and `reviewed_source: true`.
6. The facade calls `approve_explicit_card` with one explicit card path.

No list endpoint, status endpoint, config endpoint, or recall endpoint can
produce `human_approved`. Reject in the first version records an honest
unavailable response unless a safe reject service exists; it must not pretend to
write.

## Secret Handling

The Web API may report presence of configured env keys, but never their values.
It may identify key names declared by config, such as provider `api_key_env`
names, because the CLI already treats those names as configuration metadata.
It must not return:

- `.env` file contents
- API key values
- token values
- raw provider request/response bodies
- raw Python tracebacks

The frontend should render configured/missing state only.

## Startup

`mindforge web` is a CLI adapter in `src/mindforge/web_cli.py`. It parses host,
port, open-browser, vault override, and config path options, then delegates to
`mindforge_web.server`.

Default host is `127.0.0.1`. Public bind addresses require the user to pass a
different host explicitly, and the CLI should still warn that MindForge Web is a
single-user local console.

## Frontend Structure

The frontend lives under `web/` and is a small React + Vite + TypeScript app.
It uses Tailwind for local design tokens and a small fetch wrapper for server
state. It intentionally avoids Redux and complex global state in the first
version.

Primary folders:

- `web/src/api`: typed fetch clients and shared API types
- `web/src/components`: reusable layout/status/review components
- `web/src/pages`: route-level pages
- `web/src/lib`: tiny local helpers only, not a generic utility dumping ground

## Honest Unavailable Responses

Some desired Web actions may not have a safe backend use-case yet. In v1 those
endpoints should return a structured unavailable result with:

- `available: false`
- a human-readable explanation
- a next action
- no fake success

This applies especially to local source import and reject persistence until the
core backend has a clear service boundary for those writes.

## Test Strategy

Backend tests use FastAPI TestClient and temporary vaults. Required coverage:

- health/status endpoints work with local fake config
- config status and home status never expose secret values
- draft list and detail use safe fields
- approve requires confirmation and reviewed-source payload
- approve calls the existing approval service and writes only the selected card
- reject returns an honest structured response

Frontend validation uses `npm run build` and browser smoke tests against a
running localhost server.
