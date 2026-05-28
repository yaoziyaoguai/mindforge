# Bundled Config: Empty Models for Zero-Config Demo Path

- **Date**: 2026-05-28
- **Task type**: bug_fix (product decision)
- **Workstream**: Fresh Clone P0/P1 Blocker Fixes

## Product Decision

**MindForge fresh clone 默认体验必须走安全 demo/fake provider path。**
Real LLM 必须 opt-in。Placeholder model 不应破坏默认 demo path。

### What changed

`src/mindforge/assets/configs/mindforge.yaml` 的 `llm` 段从 placeholder model 改为空模型：

```yaml
# Before (blocked demo path):
llm:
  default_model: main
  models:
    main:
      type: openai_compatible
      base_url: "https://your-router.example.com/v1"
      model: "your-model-name"
      ...
  routing: {triage: main, distill: main, ...}

# After (zero-config demo):
llm:
  default_model: null
  models: {}
  routing: {}
```

### Why this is safe

- Config schema 已支持空模型（`config.py:1091` 明确注释："首次安装可以没有模型"）
- `model_setup_readiness(cfg)` 在 `models={}` 时返回 `"demo"` → `apply_provider_selection()` 自动注入 fake provider
- `LLMConfig.resolve_stage_alias` 会在空模型时抛 `ConfigError`，但 `with_fake_llm_profile` 在 resolve 之前就替换了整个 LLMConfig
- `build_readiness_report` 空模型时返回 `opt_in_state="blocked"`（安全 demo 状态），不变更用户 config

### Real LLM opt-in 路径不变

- Web Setup 页面用户显式配置模型 + API key → `models` 非空 → `model_setup_readiness` 返回 `"ready"` 或 `"needs_setup"`
- CLI `mindforge config` 显式设置 → 同上
- `mindforge init` 使用 `mindforge.user.yaml` 模板（独立于 bundled config）→ 不受影响

## Modified Files

| File | Change |
|------|--------|
| `src/mindforge/assets/configs/mindforge.yaml` | `llm` 段: placeholder model → `default_model: null, models: {}, routing: {}` |
| `tests/test_config.py` | `test_real_mindforge_yaml_loads`: 断言空模型 |
| `tests/test_roadmap_completion_safety.py` | `test_shipped_config`: `"default_model: main"` → `"default_model: null"` |
| `tests/test_v013_stage2_consistency.py` | `test_provider_readiness_json_schema`: `"profile_only"` → `"blocked"`; `test_llm_ping`: 构造临时 config 含真实模型但缺 key |
| `tests/test_v013_stage5_closure_boundaries.py` | `test_bundled_llm_config`: `"default_model: main"` → `"default_model: null"` |

## Gates (主 repo, HEAD `2119b01`)

| Gate | Exact Command | Timeout | Exit |
|------|--------------|---------|------|
| ruff | `ruff check src/ tests/` | no | 0 |
| git diff | `git diff --check` | no | 0 |
| npm build | `npm --prefix web run build` | no | 0 |
| pytest (主 repo) | `python -m pytest tests/ -q` | no | 0 (1 pre-existing skip: `test_vault_relative_path_resolution_scenarios`) |

### Gate evidence correction (2026-05-28)

上一轮报告的 fresh clone pytest gate 存在以下问题，本修正记录：

1. **命令问题**: 使用了 `pytest ... | tail -15; echo "EXIT: $?"` — `$?` 捕获的是 `tail` 的 exit code，不是 pytest 的 exit code。这是 gate evidence 违规（§8.1）。
2. **exit code 报告不准确**: 上一轮 fresh clone 中 `test_doctor_logic_hides_demo_env_and_profile_hints` 因路径名含 "dogfood" 而失败，但被口头标记为 "1 pre-existing path-name artifact" 后仍写 PASS。按 gate evidence rule，失败就是失败，不应绕过。
3. **根因**: v2 fresh clone 初始版本含旧 bundled config（placeholder model），拉取最新代码后全部 pass（真实 exit 0）。问题在于上一轮跑 pytest 时 fresh clone 尚未包含 tests 修复。

## Fresh clone v3 verification (HEAD `2119b01`)

v3 fresh clone 路径: `/tmp/mindforge-fresh-clone-v3`（不含 "dogfood" 子串，避免路径名 artifact）。

### 验证步骤和结果

| # | 验证项 | 命令/方法 | 结果 |
|---|--------|----------|------|
| 1 | bundled config | `grep default_model / models / routing` | `default_model: null`, `models: {}`, `routing: {}` |
| 2 | pytest (full) | `.venv/bin/python -m pytest tests/ -q` | exit 0, 全部 pass |
| 3 | zero-config demo path | `model_setup_readiness() → status="demo"`; `apply_provider_selection(cfg, provider=None, legacy_profile=None) → selected="fake"` | 自动注入 fake provider |
| 4 | real provider without key | temp config: real model + no key → `status="needs_setup"`, `smoke.ran=False`, `blocker="profile_only"` | 无静默 fake 回退 |

### pytest (v3) gate evidence

- **Exact command**: `/tmp/mindforge-fresh-clone-v3/.venv/bin/python -m pytest tests/ -q`
- **Timeout**: no
- **Real exit code**: 0
- **No pipe to tail/head/truncated output used**

## Risks

- **Low**: `build_readiness_report` 对空模型返回 `"blocked"` 而非 `"profile_only"`。此差异仅影响 `provider_readiness` API 的输出（内部/诊断工具），不影响主路径 demo 体验。
