# Quality Debt Ledger

v3.0 初始基线，基于 v2.0-v2.5 independent delivery audit (score 93/100)。

更新日期: 2026-05-25

---

## Open Debt

| ID | Priority | Description | Source | Status | Target |
|----|----------|-------------|--------|--------|--------|
| P1-01 | P1 | SearchIndexPort 代码缺失 — changelog 措辞修正 | v2.2 | ✅ resolved (changelog 措辞已修) | v3.0 |
| P2-01 | P2 | v2.4 changelog 路径不一致 | v2.4 | ✅ resolved (路径引用已更新) | v3.0 |
| P2-02 | P2 | web_facade.py 1500+行，多职责聚合 | v2.x | open | v3.1 |
| P2-03 | P2 | Import/Export 无独立导航入口 | v2.4 | open | v3.5 |
| P3-01 | P3 | npm build chunk size >500KB | v2.5 | open (非阻塞) | v3.5 |
| P3-02 | P3 | 1 skipped test (conditional: no runs written) | pre-existing | acknowledged (正常条件跳过) | — |

## Resolved Debt

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| — | pre-existing | ruff 17 errors | Resolved pre-v3.0 (ruff clean in current baseline) |
| — | pre-existing | pytest failures | Resolved pre-v3.0 (full pytest suite clean: 2890 passed) |

---

## Gate Baseline (v3.0)

| Gate | Command | Exit Code | Timeout |
|------|---------|-----------|---------|
| npm build | `npm --prefix web run build` | 0 | no |
| product copy | `python -m pytest tests/test_web_product_copy.py -q` | 0 (72 passed) | no |
| ruff | `ruff check src/ tests/ --statistics` | 0 | no |
| git diff | `git diff --check` | 0 | no |
| full pytest | `python -m pytest tests/ -q` | 0 (2890 passed, 1 skip) | no |
