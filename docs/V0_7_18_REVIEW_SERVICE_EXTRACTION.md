# v0.7.18 Review Service Extraction

## 本版本目标

v0.7.18 的目标是把 `review weekly` 中真正属于复习业务判断、数据聚合、review
window 和 `human_approved` selection 的逻辑，从 `src/mindforge/cli.py` 抽到
`src/mindforge/review_service.py`。

这不是为了降低 `cli.py` 行数。行数只是症状；本轮关注的是让 weekly review 的
领域规则可独立测试、可阅读，并让 CLI 回到参数、日志和输出层。

## 为什么 review 是核心架构边界

Review 是 MindForge 把长期记忆转化为复习任务的入口。它必须默认只使用
`human_approved` 卡片；如果把 `ai_draft` 混进 weekly summary，就等于绕过了
approval gate，让 AI 草稿进入正式学习闭环。

因此 review service 的边界与 approval service 互相配合：

- `approval_service.py` 负责显式人审闸门；
- `review_service.py` 只消费已经 human-approved 的结构化卡片摘要；
- review 不会自动 approve，也不会改变任何 card status。

## 本轮抽出了什么

新增 `src/mindforge/review_service.py`，抽出：

- weekly review window calculation；
- `human_approved` cards selection；
- `ai_draft` exclusion；
- overdue / due this week / reviewed this week / next week preview 聚合；
- forgotten / partial 聚合；
- suggested focus tracks 的纯计数计算；
- project distribution 计数；
- structured empty state；
- scan errors 透传。

## review_service 的职责

`review_service.py` 接收 `MindForgeConfig` 和可选固定 `now`，返回
`WeeklyReviewResult` dataclass。它依赖：

- `cards.iter_cards`
- `cards.filter_cards`
- `MindForgeConfig`

它可以被 CLI、未来 presenter 或测试依赖。它可以独立测试，并且降低 CLI 读者在
`review weekly` 中同时理解 Typer、RunLogger、Markdown、JSON 和业务聚合的负担。

## review_service 不负责什么

它不负责：

- Typer 参数；
- Rich / console 输出；
- Markdown 渲染；
- JSON stdout schema 渲染；
- `--output` 文件写入；
- RunLogger；
- LLM/provider/env；
- Obsidian note 写入；
- approval 状态转换；
- review mark 写入；
- RAG / embedding。

## CLI 现在少承担什么

`cli.py` 不再直接承担 weekly review 的 cards loading、approved-only filtering、
窗口计算、分桶聚合、focus score 和 project distribution。CLI 仍保留：

- 命令入口；
- config path loading；
- RunLogger；
- Markdown/JSON 输出；
- 用户可见 next actions 和 workflow bridge 文案；
- `--output` 写报告文件。

## 保持不变的用户行为

- `mindforge review weekly` 命令名和参数不变；
- Markdown section 名称和语义不变；
- JSON `version=1` schema 不变；
- `next_actions` 仍由 CLI 输出；
- `review weekly` 仍不调 LLM、不读 `.env`、不写卡片；
- `ai_draft` 仍不会进入默认 weekly review。

## 被测试保护的边界

新增 `tests/test_review_service.py` 覆盖：

- weekly review window calculation；
- approved cards aggregation；
- `ai_draft` 不被当作 `human_approved`；
- `human_approved` cards 可以进入 review；
- empty review state；
- malformed card 进入 `scan_errors`，不阻断 valid card；
- due / reviewed / preview 窗口边界；
- 不调用 LLM/HTTP；
- 不读取 `.env`；
- 不依赖 Typer/Rich/console；
- 不写正式 Obsidian notes；
- 不改变 card status；
- 不自动 approve；
- 与 `approval_service` 的显式 approve 语义不冲突。

原有 CLI 黑盒测试继续保护外部输出语义。

## review_service 和 approval_service 的关系

`approval_service.py` 是写入闸门：只有明确的人审动作可以把 `ai_draft` 变成
`human_approved`。

`review_service.py` 是只读消费者：它只读取 `human_approved` 安全摘要并生成复习
聚合结果。它不能调用 approval service 来自动批准，也不能修改 `status` 字段。

## 后续建议

v0.7.19 可以优先治理 Obsidian CLI handler：当前 Obsidian 命令入口仍在
`cli.py` 中占用较多认知空间，但应保持 staged-export / preflight / manual
inspection 的安全边界，不引入 apply/write-back。
