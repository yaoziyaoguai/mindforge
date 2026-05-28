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

## Gates

- `ruff check src/ tests/`: exit 0
- `git diff --check`: exit 0
- `npm --prefix web run build`: exit 0
- `python -m pytest tests/ -q`: exit 0 (1 pre-existing skip, 0 failures)

## Risks

- **Low**: `build_readiness_report` 对空模型返回 `"blocked"` 而非 `"profile_only"`。此差异仅影响 `provider_readiness` API 的输出（内部/诊断工具），不影响主路径 demo 体验。
