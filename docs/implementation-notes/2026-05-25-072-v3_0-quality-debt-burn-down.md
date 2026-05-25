# v3.0 Quality Debt Burn-down

## 概述

清偿 v2.0-v2.5 independent delivery audit (score 93/100) 发现的质量债。

## 已处理

### P1-01: SearchIndexPort changelog 措辞
- 问题: changelog 声称 SearchIndexPort 已建立，但代码中不存在
- 修复: 修正措辞为"留待后续需要时补充"，反映实际状态
- 文件: `docs/design/v2.0-v2.5-changelog.md`

### P2-01: v2.4 路径引用不一致
- 问题: changelog 引用 `import_service.py`/`export_service.py`/`import_validation.py` 但代码在 `web_facade.py`/`routers/library.py`
- 修复: 更新每个单元的实际代码位置
- 文件: `docs/design/v2.0-v2.5-changelog.md`

### P3-02: Skipped test
- 确认: `test_v0_3_1.py:345` — `pytest.skip("no runs written")` — 正常条件跳过
- 无修复需要

### 质量基础设施
- 新增 `docs/dev/quality-debt-ledger.md` — 质量债账本 + gate baseline
- 新增 `docs/plans/2026-05-25-070-v2_0_to_v2_5-independent-delivery-audit.md` — 交付审计
- 新增 `docs/plans/2026-05-25-071-v3_0_to_v3_6-long-horizon-roadmap.md` — 长期路线

## 递延

- P2-02: web_facade.py 巨石 → v3.1 处理
- P2-03: Import/Export 独立导航 → v3.5 处理
- P3-01: npm chunk size warning → v3.5 处理

## Gate Baseline

全部 gate clean (完整输出，无 tail/head):
- `npm --prefix web run build` — EXIT 0
- `python -m pytest tests/test_web_product_copy.py -q` — EXIT 0 (72 passed)
- `ruff check src/ tests/ --statistics` — EXIT 0
- `git diff --check` — EXIT 0
- `python -m pytest tests/ -q` — EXIT 0 (2890 passed, 1 skip: conditional "no runs written")
