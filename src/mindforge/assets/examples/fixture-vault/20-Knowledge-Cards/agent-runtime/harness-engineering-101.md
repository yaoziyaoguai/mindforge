---
id: harness-engineering-101
title: Harness 是 agent 真正能"做事"的那一层
status: human_approved
track: harness-engineering
projects:
  - my-first-agent
tags:
  - harness
  - agent-runtime
value_score: 7
source_id: demo-webclip-001
source_url: https://example.com/blog/harness-engineering-101
source_type: webclip_markdown
created_at: 2026-04-18T20:11:00+08:00
updated_at: 2026-04-21T20:00:00+08:00
review_after: 2026-05-05T00:00:00+08:00
review_count: 0
adapter_name: WebClipMarkdownAdapter
confidence: medium
---

## AI Summary

把 harness 责任写在 prompt 里会让系统不可观测、不可测试、不可演进。
Harness 应该被设计成普通后端服务：明确接口、状态机、日志、metrics、错误码。

## Source Excerpt

> 把 harness 设计成一个普通后端服务：明确接口、明确状态机、明确日志、
> 明确 metrics、明确错误码。LLM 只是它的一个用户。

## Action Items

- [ ] 把 harness 的工具调度器抽到独立模块
- [ ] 给每个 tool 加超时与 cancel

## Principles

- LLM 是 harness 的一个用户，不是 harness 本身
- harness 必须可独立测试，不依赖 LLM

## Known Risks

- harness 接口设计过于灵活会反向污染 LLM 输出
