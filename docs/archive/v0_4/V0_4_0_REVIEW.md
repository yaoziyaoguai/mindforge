# v0.4.0 复盘 — Review Scheduling MVP

## 范围
- 新增三个命令：
  - `mindforge review schedule` — 未来 N 天复习计划（按日期分组，markdown/json）；
  - `mindforge review backlog` — overdue / today / upcoming / missing 四桶；
  - `mindforge review stats` — 聚合统计（仅元数据）。
- 增强 `mindforge review mark`：
  - `--dry-run` 只计算下一次 `review_after`，不写卡片；
  - `--note "..."` 可选单行 ≤200 字符备注，写入 frontmatter `last_review_note`，
    **绝不**进入 body。
- 测试 13 项覆盖：分组、过期归今天、ai_draft 排除、不修改卡片、JSON schema、
  dry-run / note 边界（多行 / 超长拒绝）、telemetry 不泄漏。
- 文档：`docs/V0_4_REVIEW_SCHEDULING_PROTOCOL.md`。
- 版本：`0.3.2 → 0.4.0`。

## 不做（明确边界）
- 不做 SM-2 / FSRS；不做后台调度；不做系统通知；
- 不调 LLM；不读 .env；不发请求；不引 embedding；
- 不改 status；不自动 approve；不批量修改卡片；
- 不写 raw source；不污染 body；
- 不引 sqlite / 任何外部存储。

## 关键设计决定
- **过期 → 今天分桶**：避免 overdue 卡片被排到明天后才被看到。
- **`--include-missing-review-after`**：可选纳入新卡片，但默认不打扰，
  避免每次 schedule 都被新批准的卡片刷屏。
- **`--note` 强约束**：单行 ≤200 字符；多行/超长 → exit 3。这是为了保证
  frontmatter 不会变成自由日记区。
- **不引入新 telemetry 字段以外的内容**：`schedule_days` / `include_missing_review_after` /
  `dry_run` / `note_provided` 全部走 `_ALLOWED_FIELDS` 白名单。

## 测试 / 质量
- 全量 pytest：317 项通过（旧 304 + 新 13）。
- ruff check：通过。
- git diff --check：通过。

## 兼容性
- `mark_card_review` 新增 kwargs `dry_run=False, note=None`，默认行为与
  v0.3.x 等价；旧调用方不受影响。
- `_card_to_safe_dict` 新增 `review_count` / `last_review_result` 两字段；
  对应安全集已在 `tests/test_m4.py` 中扩展。
- 旧 `review mark`/`review due` 行为零变化。

## 下一步建议（择一）
1. **M5.5 / Obsidian 友好度收尾**：vault 命令 + Templater 模板审计；
2. **M5.1 PDF/Docx adapter spike**：扩展 source ingestion；
3. **M6 RAG/embedding spike**：仅 docs/POC，不入主干；
4. **产品化 polish**：`mindforge init` 体验优化、错误信息中文化、首次运行向导。

推荐 **#1 或 #4**：MindForge 已经能"召回 + 复习 + 项目上下文 + telemetry"，
下一步把"看起来像一个完整产品"补齐，比再扩源类型更有用户价值。
