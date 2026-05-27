# P1 管道阻塞修复 — demo/fake 模式自动回退

日期: 2026-05-27

## 问题

`mindforge import` 在用户未配置任何真实模型时报错:

```
ConfigError: No model configured for stage 'triage'
```

这与 Web UI 承诺的 "安全模式：本地模拟" 矛盾。用户需要零配置 demo 体验，
但 CLI 和 Web 处理管道在无模型时会直接报错退出。

根因: `REQUIRED_STAGES` 定义的 5 个处理阶段 (triage → distill → link_suggestion
→ review_questions → action_extraction) 在 `LLMConfig.resolve_stage_alias()` 中
找不到对应模型时抛出 `ConfigError`。`with_fake_llm_profile()` 可以注入 fake
路由但仅在显式传递 `--profile fake` / `--provider fake` 时调用。

## 修复

### 修复点 1: CLI adapter — `apply_provider_selection()` (`cli_runtime.py`)

在 `apply_provider_selection()` 的无选择分支末尾增加自动回退:

```python
if not selected:
    if cfg.llm.default_model is None and not cfg.llm.models:
        safe_llm = with_fake_llm_profile(cfg.llm)
        return replace(cfg, llm=safe_llm, ...)
```

触发条件: `default_model is None` AND `models` 为空 — 即用户确实未配置任何模型。
fake profile 仅在内存中注入，不写入 YAML，不污染 Setup UI。
用户配置真实模型后 `models` 非空，自动回退不再触发。

### 修复点 2: Web service — `_ensure_processing_model_configured()` (`web_source_service.py`)

Web 导入/扫描路径在 `_ensure_processing_model_configured()` 中验证模型配置。
同样改为: 无模型时注入 fake profile，有模型时正常验证。

注意: `cfg` 不是 frozen dataclass，可原地修改 `cfg.llm`。

### 安全保证

- fake models 仅在内存注入，不写 YAML，不污染 Setup UI
- 用户添加真实 model 后 `models` 非空 → 自动回退不再触发
- 不修改 `MindForgeConfig` 的 frozen 语义（`LLMConfig` 保持 frozen）
- 不改变 `ai_draft` → `human_approved` explicit approval 语义
- fake model card 仍标记为 `ai_draft`，不会自动绕过 Review

## 测试更新

9 个测试从期望 "无模型 → error" 改为期望 "无模型 → auto-fallback to fake":

| 测试文件 | 测试数 | 变更 |
|---------|--------|------|
| `test_web_api.py` | 2 | `test_web_process/watch_scan_without_model_auto_fallback_to_fake`: 期望 200 + ok=True |
| `test_watch_import_cli.py` | 4 | CLI import/process/watch 无模型时 expect succeeded |
| `test_watch_schedule_baseline.py` | 3 | fake fallback 成功 → last_processed_at 非空, status 非 failed |

## Gate

- `ruff check src/ tests/`: exit 0 (All checks passed!)
- `python -m pytest tests/ -q --tb=short`: exit 0 (100% pass, no failures)
- `npm --prefix web run build`: exit 0 (built in 5.25s)
- `python -m pytest tests/test_web_product_copy.py -q --tb=short`: exit 0 (80 passed)
- `git diff --check`: exit 0
