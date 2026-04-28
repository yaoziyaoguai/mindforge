# v0.4 Review Scheduling Protocol

> 本协议定义 MindForge **本地复习计划**的边界与字段；
> 这不是后台调度器、不是系统通知、不是 Anki/SRS 替代品。

## 1. 三个新命令

### `mindforge review schedule`

为未来 N 天的复习生成计划，按日期分组。

```
mindforge review schedule
mindforge review schedule --days 14
mindforge review schedule --track agent-runtime
mindforge review schedule --project my-first-agent
mindforge review schedule --include-missing-review-after
mindforge review schedule --format markdown
mindforge review schedule --format json
mindforge review schedule -o /tmp/plan.md
```

**关键行为**
- 默认 `--days 7`；上限 365；
- 仅纳入 `status: human_approved`；
- 过期卡片（`review_after <= now`）归到"今天"分桶，避免被忘掉；
- `--include-missing-review-after`：把从未 review 过 / 缺该字段的卡片
  也归到今天，便于"我刚批准的新卡今天就排进去"；
- 不调 LLM；不读 .env；不发请求；不修改任何卡片；
- 输出包含的字段是 `_card_to_safe_dict` 白名单子集。

### `mindforge review backlog`

把当前积压分到四桶：`overdue / today / upcoming / missing`。

```
mindforge review backlog
mindforge review backlog --limit 100 --format json
mindforge review backlog --track agent-runtime
```

与 `schedule` 的差异：
- `schedule` 关注"未来 N 天的计划"；
- `backlog` 关注"现在欠了多少"，把 `overdue` / `missing` 当成第一公民。

### `mindforge review stats`

聚合统计（不含任何卡片正文）：

```
mindforge review stats
mindforge review stats --json
```

输出（JSON schema v1）：

```json
{
  "version": 1,
  "generated_at": "...",
  "total_human_approved": 42,
  "due_today": 3,
  "overdue": 5,
  "upcoming_7_days": 8,
  "missing_review_after": 4,
  "reviewed_count": 15,
  "average_review_count": 2.4,
  "result_breakdown": {"remembered": 9, "partial": 4, "forgotten": 2}
}
```

## 2. `review mark` 增量

```
mindforge review mark --card <path> --result remembered
mindforge review mark --card <path> --result partial --dry-run
mindforge review mark --card <path> --result forgotten --note "卡在 ReAct 循环步骤 3"
```

- `--dry-run`：只计算下次 `review_after`，**不**写文件；
- `--note`：可选**单行 ≤ 200 字符**字符串；写入 frontmatter
  `last_review_note` 字段。**绝不**写入卡片 body / Source Excerpt /
  Human Note 区。多行或超长 note 立即 fail-fast，exit code 3。

字段写入仍然只有这些（沿用 M4 契约）：
- `reviewed_at`
- `review_count`
- `last_review_result`
- `review_after`
- `last_review_note`（仅当 `--note` 给出时）

## 3. 时区

CardSummary.review_after 可能 naive；统一对齐 `datetime.now().astimezone()`
的 tzinfo，避免跨时区漂移。

## 4. 不做（v0.4 边界）

- 不做 SM-2 / FSRS 等遗忘曲线算法；区间仍是 `cfg.review.intervals` 三档；
- 不做后台调度 / 系统提醒 / cron；schedule 只是把"该复习哪些卡"打到 stdout 或 --output；
- 不修改 status；不自动 approve；不批量改卡；
- 不引入 sqlite / 数据库；frontmatter 即是真相之源；
- 不调 LLM；不引 embedding。

## 5. 与 telemetry 的关系

三个新命令复用 `RunLogger` emit `review_due_listed` 事件（M4 已有），
新增字段经过 `_filters_dict` + `_ALLOWED_FIELDS` 白名单：
- `schedule_days`
- `include_missing_review_after`
- `dry_run`
- `note_provided`（bool；不记录 note 内容）

绝不记录卡片标题、body、note 文本。
