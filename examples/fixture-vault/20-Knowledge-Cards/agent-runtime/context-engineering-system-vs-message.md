---
id: context-engineering-system-vs-message
title: System Prompt 是不可变常量，Message 是事件流
status: ai_draft
track: context-engineering
projects:
  - my-first-agent
tags:
  - context-engineering
  - prompt
value_score: 6
source_id: demo-chat-001
source_type: chat_export
created_at: 2026-04-20T15:00:00+08:00
updated_at: 2026-04-21T20:00:00+08:00
adapter_name: ChatExportAdapter
confidence: medium
---

## AI Summary

把"会话级稳定不变"的内容（角色、工具签名、安全契约、输出格式）放进
system prompt；把"动态的"内容（用户诉求、工具结果、长文档）放进 message
或 tool result。一句口诀：system prompt 是不可变常量，message 是事件流。

## Source Excerpt

> system prompt 是不可变常量，message 是事件流。

## Action Items

- [ ] 把 my-first-agent 的 system prompt 拆分：稳定 vs 动态
- [ ] 给每个 system prompt 段加版本号

## Principles

- system prompt 是 contract
- message 是 state

## Human Note

（待补充）
