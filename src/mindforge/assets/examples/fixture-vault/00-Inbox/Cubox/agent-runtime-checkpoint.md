---
source_url: https://example.com/agent-runtime-checkpoint
source_type: cubox_markdown
title: 为什么 Agent Runtime 需要显式 Checkpoint
captured_at: 2026-04-15T08:30:00+08:00
tags:
  - agent-runtime
  - checkpoint
---

# 为什么 Agent Runtime 需要显式 Checkpoint

> 这是一份**虚构的示例**文档，仅用于 MindForge demo vault。

Agent runtime 在长会话场景下，必须把**关键状态**显式落盘成 checkpoint，
否则进程崩溃 / 用户中断 / 工具异常都会造成不可恢复的状态丢失。

## Highlights

- ==Checkpoint 不是日志，而是"可恢复执行点"==
- ==每个 tool call 完成都应该是一个 checkpoint 候选==
- ==状态机 + checkpoint 共同构成 agent 的"事件溯源"==

## 关键观点

1. checkpoint 是**结构化状态**，不是文本日志；
2. 任意 checkpoint 必须可以 replay 出当前状态；
3. checkpoint 频率与故障半径成反比。
