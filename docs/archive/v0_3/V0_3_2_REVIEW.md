# v0.3.2 复盘 — Recall UX Polish + Index Info JSON

## 范围
- `recall` 增 `--weight-bm25 / --weight-value-score / --weight-review-due`
  本次运行覆盖 hybrid 权重（**不写回 yaml**），便于快速 A/B。
- `recall --explain --format json` 增加 `weight_source` / `active_weights` /
  `index_stale` / per-item `why_this_matched` / `matched_terms` /
  `matched_fields` / `ranking_mode` 字段。
- `recall --explain` compact 输出新增 `why` 行（top field + hybrid breakdown）。
- `index info` 命令（与 `index status` 行为相同），新增 `--json` 给稳定 schema。
- `index status --json` 也支持。
- `doctor` 新增提示：当全部卡片为 `ai_draft` 时建议 `recall --include-drafts`。
- 全 JSON 输出走 `print()`（避免 Rich Console 行宽包裹破坏机器解析）。

## 不做
- 不调 LLM；不读 .env；不引 embedding；不改卡片；不写 raw source；
- 不引入新 ranker；不修改 BM25 字段权重默认；
- 不做远程 telemetry / 不改 `_ALLOWED_FIELDS` 含义。

## 兼容性
- 旧测试 `test_m4` recall json 安全集扩展两字段（`review_count` /
  `last_review_result`）— 来自 frontmatter，仍是安全 metadata。
- v0.3.1 JSON schema 完全向前兼容；新字段是**叠加**，旧消费者不感知。

## 测试
- `tests/test_v0_3_2.py` 10 项：
  - weight override 应用 + 不改 yaml；
  - 非法权重（负数 / 全 0）拒绝；
  - explain JSON 含 v0.3.2 字段；
  - telemetry 不泄漏 query 原文；
  - `index info --json` schema 稳定；
  - `index status --json` 在缺失索引时也能输出；
  - doctor 在仅 ai_draft 时给出 `--include-drafts` hint。
- 全量 `pytest`：通过；ruff：通过。
