---
id: agent-runtime-checkpoint
title: Agent Runtime 必须显式 Checkpoint
status: human_approved
track: agent-runtime
projects:
  - my-first-agent
tags:
  - checkpoint
  - agent-runtime
value_score: 8
source_id: demo-cubox-001
source_url: https://example.com/agent-runtime-checkpoint
source_type: cubox_markdown
created_at: 2026-04-15T08:30:00+08:00
updated_at: 2026-04-21T20:00:00+08:00
review_after: 2026-04-25T00:00:00+08:00
review_count: 1
last_review_result: remembered
adapter_name: CuboxMarkdownAdapter
confidence: high
---

## AI Summary

长会话 agent 必须把关键状态显式落盘成 checkpoint，否则进程崩溃 / 用户中断
/ 工具异常都会造成不可恢复的状态丢失。checkpoint 不是日志，而是"可恢复执行点"。

## Source Excerpt

> Checkpoint 不是日志，而是"可恢复执行点"

## Action Items

- [ ] 在 my-first-agent 中给每个 tool call 完成节点加 checkpoint
- [ ] 抽取 checkpoint 序列化协议为独立模块

## Principles

- checkpoint 是结构化状态，不是文本日志
- 任意 checkpoint 必须可以 replay 出当前状态
- checkpoint 频率与故障半径成反比

## Known Risks

- 过密 checkpoint 会带来写入压力
- checkpoint schema 漂移需要版本字段

## Human Note

呼应 my-first-agent 中 tool dispatcher 的设计，先做"每个 tool call 完成"的最小 checkpoint。
