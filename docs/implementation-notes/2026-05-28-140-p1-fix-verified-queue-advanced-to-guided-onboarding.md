# P1 Pipeline Blocker Fix Verified + AUTOPILOT-QUEUE Advanced

日期: 2026-05-28

## 背景

产品创新审计将 P1 pipeline blocker (`PROD-01`) 列为最高优先级。实际上该修复已在 `87453f0` 中实现，但 CPS/ledger 存在 truth drift:
- AUTOPILOT-QUEUE ITEM-1 仍标记为 `current_node=pending`
- PROD-01 仍标记为 `open`
- CPS HEAD 仍引用旧 commit `e6f6d09`

## 做了什么

**验证现有修复:**
- CLI 路径: `apply_provider_selection()` 在无模型时自动注入 fake LLM profile
- Web 路径: `_ensure_processing_model_configured()` 在无模型时自动注入 fake LLM profile
- 11 个 auto-fallback 测试全部通过 (pytest 0, 100%)
- 全量 gate: pytest (0, 100%), npm build (0), ruff (0)

**治理 truth sync:**
- CPS: HEAD `e6f6d09` → `aef49df`，日期 2026-05-27 → 2026-05-28
- CPS: PROD-01 → resolved (commit `87453f0`, 验证通过)
- CPS: AUTOPILOT-QUEUE ITEM-1 → done，ITEM-2 (Guided Onboarding) 成为下一 active
- CPS: 推荐优先顺序更新为产品创新审计的三级 bet 体系
- CPS: notes 引用列表精简，新增最新 governance truth sync note 路径

**下一阶段:**
AUTOPILOT-QUEUE ITEM-2 (Guided Onboarding Design) 需要 `/brainstorming` session 和用户验证，`hard_stop_required=true`。不可自动继续。

## 修改文件
- `docs/dev/CURRENT_PROJECT_STATE.md` — truth sync: HEAD, PROD-01, AUTOPILOT-QUEUE, 推荐顺序
- `docs/dev/progress-ledger.md` — 新增 loop entry
- `docs/implementation-notes/2026-05-28-140-p1-fix-verified-queue-advanced-to-guided-onboarding.md` — 本文件

## Gates
- `git diff --check`: 0
- `ruff check src/ tests/`: 0 (All checks passed!)
- `python -m pytest tests/`: 0 (100%, ~3030 passed)
- `npm --prefix web run build`: 0 (built in 5.18s)

## 关键确认
- P1 pipeline blocker 修复功能完整且 gate 验证通过
- 不涉及新产品代码、UI、架构、dogfood 改动
- 不读取 .env/secrets、不调用真实 LLM
- explicit approval / human_approved 语义未触碰
