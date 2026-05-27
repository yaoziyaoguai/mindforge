# Web Product UX Deepening — Loop 1 (P2 Fixes)

**日期**: 2026-05-27
**Workstream**: Web Product UX Deepening
**Task type**: ui_ux_polish

## 来源

- Dogfood v2 发现的 2 个 P2 UX 摩擦: Export breadcrumb、SafetyBar model status
- Codex audit §10.B 推荐次优先: Web Product UX Deepening
- CPS AUTOPILOT-QUEUE-ITEM-1

## 修复内容

### P2-1: Export breadcrumb "export" → "导出知识"

- **文件**: `web/src/components/Breadcrumb.tsx`
- **变更**: routeLabels 中新增 `/export: "nav.export"` 映射
- **效果**: Export 页面面包屑从 raw path "export" 变为国际化标签 "导出知识"
- **安全性**: 纯前端展示层 fix，不影响任何产品语义

### P2-2: SafetyBar 模型状态 "待检查" → "本地模拟"

- **文件**: 
  - `src/mindforge/model_setup_readiness.py` — 无模型时返回 "demo" 而非 "needs_setup"
  - `web/src/components/SafetyBar.tsx` — 处理 "demo" provider_state (绿色/安全)
  - `web/src/lib/i18n.ts` — 新增 `safety.model_demo` ("本地模拟" / "local simulation")
- **变更**: 当 cfg.llm.models 为空时（P1 修复后的 auto-fallback fake 场景），SafetyBar 显示绿色 "本地模拟" 而非黄色 "待检查"
- **安全性**: 不改变 fake provider 注入逻辑，不读取 secrets，不调用 LLM。仅改变状态标签，fake 行为不变。

### Ruff 修复

- **文件**: `tests/test_watch_schedule_baseline.py`
- **变更**: 移除 line 606 的无意义 f-string 前缀 (F541)

## Gate Results

| Command | Exit Code | Notes |
|---------|-----------|-------|
| `ruff check src tests` | 0 | All checks passed |
| `npm --prefix web run build` | 0 | 1651 modules, 4.85s |
| `npx vitest run` | 0 | 6 files, 50 passed |
| `python -m pytest tests/ -q --tb=short` | 0 | 100%, 1 skip (expected) |
| `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 | 100% |
| `git diff --check` | 0 | clean |

## 未修复的 Dogfood v2 P3 发现

以下 P3 项未在此 loop 处理，作为 Web UX Deepening 后续 batch 候选:

1. Setup page first-run 引导不够突出
2. Library 页面排序/筛选 UX 可优化
3. Wiki 页面空状态引导不足
4. Recall 页面检索结果相关性反馈缺失
5. Export 页面下载按钮位置不够明显

## 安全性声明

- 未读取 `.env` / secrets
- 未调用真实 LLM / Cubox / Upstage
- 未处理真实私人资料
- 未写真实 Obsidian vault
- 未改变 explicit approval / human_approved 语义
- 纯前端展示层 fix + 后端状态标签语义修正

## 下一步

继续 CPS AUTOPILOT-QUEUE-ITEM-1 (Web Product UX Deepening) 剩馀 P3 项，或 ADVANCE to ITEM-2 (Targeted Architecture Quality Reset)。
