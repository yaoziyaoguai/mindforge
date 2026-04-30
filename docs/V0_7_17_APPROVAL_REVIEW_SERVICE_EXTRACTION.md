# v0.7.17 Approval / Review Service Extraction

## 本版本目标

v0.7.17 的目标是治理 approve/review 相关的主代码巨石化问题，优先把
`ai_draft -> human_approved` 人审闸门的业务判断从 `cli.py` 抽到可独立测试的
service 边界。行数下降只是副作用，不是本轮 KPI。

## 为什么这是核心架构边界

Approval 是 MindForge long-term memory 的入口：只有人显式确认后的卡片才能进入
默认 recall、review 和 project context。这个边界如果被 CLI 展示逻辑、LLM
pipeline 或批量便捷操作冲散，就会让 AI 草稿被误当成人类确认过的知识复用。

Review 依赖这个边界：默认 review 只能聚合 `human_approved` 卡片，不能把
`ai_draft` 当成正式学习材料。因此 approval/review 的服务边界必须比普通 CLI
整理更谨慎。

## 本轮抽出了什么

新增 `src/mindforge/approval_service.py`，把 approve workflow 里的领域判断集中到
service：

- pending `ai_draft` 候选筛选；
- `source_id -> card_path` 解析；
- `approve show` 的 frontmatter 白名单 preview；
- 批量 approve 的候选计划；
- 显式 approve 的结构化结果和结构化错误；
- service-level `card id` 精确查找能力，供测试和后续 CLI 演进使用。

已有 `src/mindforge/approver.py` 继续作为单卡写入原语，负责真正的
`ai_draft -> human_approved` frontmatter/state 转换。`approval_service.py` 不替代
它，而是在 CLI 与写入原语之间表达 workflow 边界。

## approval_service 职责

`approval_service.py` 负责 approve 领域里的业务前置条件和结构化结果：

- 输入 `MindForgeConfig`、card path、source id、card id 或 list filters；
- 输出 dataclass 结果或 `ApprovalServiceError`；
- 只使用 cards/checkpoint/approver 等本地结构化 API；
- 不依赖 Typer、Rich、console；
- 可以被 service-level tests 独立覆盖。

## approval_service 不负责什么

它不负责：

- CLI 参数定义和 exit code 呈现；
- Rich table / Markdown / JSON stdout 格式；
- RunLogger 事件写法；
- LLM/provider/env 解析；
- 读取卡片正文来辅助 approve；
- 写正式 Obsidian notes；
- 自动选择卡片并 approve；
- 改写 SourceAdapter / SourceDocument / processor 主链路。

## 是否抽了 review_service

本轮没有新增 `review_service.py`。

原因：`review weekly` 的核心数据聚合确实适合后续抽取，但当前函数还同时承担
RunLogger、Markdown/JSON payload 组装、空状态 next actions 和学习任务文案。
如果本轮一起抽，容易把 review service 做成“为了搬代码而搬代码”的低内聚模块。
因此 v0.7.17 只做 approval_service，并把 review service 留作 v0.7.18 候选。

## CLI 现在少承担什么

`cli.py` 不再直接承担：

- pending approve 候选过滤；
- bulk approve 候选计划；
- `source_id` 反查 `card_path` 的业务判断；
- approve preview 的路径解析和 frontmatter 白名单读取；
- 单卡 approve 的业务错误结构化。

CLI 仍保留 Typer 参数、用户可见输出、RunLogger 事件和现有命令语义。

## 保持不变的用户行为

- `mindforge approve --card <path>` 仍是显式人审主路径；
- `mindforge approve --source-id <id>` 仍按 state.json 反查卡片；
- `mindforge approve list` 默认只列出 `ai_draft`；
- `mindforge approve show` 仍只展示安全 frontmatter 摘要；
- `mindforge approve --all` 没有 `--dry-run` 或 `--confirm` 时仍拒绝；
- `mindforge review weekly` 对外行为本轮不改。

## 被测试保护的 human-approved 边界

新增 `tests/test_approval_service.py` 覆盖：

- 只列出 pending `ai_draft`；
- no pending draft 返回空结构；
- approve 必须有明确目标；
- approve 后状态变为 `human_approved`；
- `human_approved` 重复 approve 幂等，不刷新 timestamp；
- 不存在的 card id 返回结构化错误；
- 损坏 frontmatter 返回结构化错误；
- list/preview 不会自动 approve；
- 不调用 LLM/HTTP；
- 不读取 `.env`；
- 不依赖 Typer/Rich/console；
- 不越权修改其他 cards；
- 不写正式 Obsidian notes。

原有 CLI 黑盒测试继续保护外部命令和输出语义。

## 后续建议

v0.7.18 可以优先做 `review_service.py`，但应先把职责限定为 weekly review 数据聚合：
review window、approved cards selection、`ai_draft` 排除、focus score 纯计数和结构化
result。Markdown/JSON 呈现应留在 CLI 或 presenter，避免把 review service 做成新的
展示巨石。
