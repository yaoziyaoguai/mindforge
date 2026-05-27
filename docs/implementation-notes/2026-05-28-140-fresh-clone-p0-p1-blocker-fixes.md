# 2026-05-28 — Fresh Clone P0/P1 Blocker Fixes

## P0: CLI auto-fallback fake provider: refine demo vs needs_setup boundary

**Root cause:** `apply_provider_selection()` in `cli_runtime.py` had a loose
condition `if cfg.llm.default_model is None and not cfg.llm.models:` for the
auto-fallback to fake provider. For a clean clone with the bundled
`configs/mindforge.yaml` (`models: {}`, `default_model: null`), this condition
was already correct.

**Misdiagnosis risk:** An earlier iteration of this fix expanded the fallback
to also trigger on `model_setup_readiness` returning `"needs_setup"` (models
configured but API keys missing). That would silently swallow the real missing-key
error path, breaking 6 existing tests in `test_watch_import_cli.py` that rely on
the system reporting "Model setup is incomplete" when a user has explicitly
configured a real provider but not set up the API key.

**Actual fix:** Replaced the implicit condition with a direct
`model_setup_readiness(cfg)` check that only triggers fake fallback on
`status == "demo"` (empty models). `"needs_setup"` is treated as a deliberate
user intent to use real models and passes through to the runtime error reporting.

**File changed:** `src/mindforge/cli_runtime.py:200-207`

## P1: sample-workspace API HTTP 500 — str/Path TypeError

**Root cause:** `web_facade.py:1093` passed `self.cfg.vault.cards_dir` (a raw
string like `"20-Knowledge-Cards"`) to `build_sample_workspace(cards_dir: Path)`,
which does `cards_dir / "demo-workspace"` inside — causing
`TypeError: unsupported operand type(s) for /: 'str' and 'str'`.

**Fix:** Changed to `self.cfg.vault.cards_path` which is a `Path` computed as
`root / cards_dir` by `VaultConfig.cards_path`.

**File changed:** `src/mindforge_web/services/web_facade.py:1093`

## Tests added

- `tests/test_cli_runtime.py` (new): 5 tests for `apply_provider_selection`
  - Empty models → fake fallback
  - Placeholder model without secrets → keeps user provider (needs_setup is NOT demo)
  - Explicit real provider → not overwritten
  - Explicit fake provider → bypasses readiness
  - Legacy `--profile fake` flag → still works

- `tests/test_web_api.py`: 2 new tests
  - `test_sample_workspace_api_returns_200_not_500` — standard vault config
  - `test_sample_workspace_api_with_custom_cards_dir` — custom cards_dir name

## Gates

- `ruff check src/ tests/`: exit 0
- `git diff --check`: exit 0
- `python -m pytest tests/ -q`: exit 0 (3693 passed, 1 skipped)
- `npm --prefix web run build`: exit 0

## Risks

- The `model_setup_readiness()` import adds a dependency from `cli_runtime` to
  `model_setup_readiness`, which in turn depends on `secret_store`. This is
  acceptable since both are core modules and the import is gated behind the
  `not selected` path.
