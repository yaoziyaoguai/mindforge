---
project: my-first-agent
description: "个人 Agent Runtime 实验项目（示例 profile）"
default_target: claude-code
principles:
  - "先看日志、checkpoint、runtime_observer、session、状态字段和真实事件链路，再决定是否改代码。"
  - "关键代码必须有中文学习型注释/docstring，解释架构边界和为什么这么做。"
known_risks:
  - "不要只根据 UI 表象打补丁。"
  - "不要让模型自动批准 human_approved。"
preferred_workflow:
  - "先做只读诊断。"
  - "再做最小补丁。"
  - "最后跑测试和 smoke。"
---

# my-first-agent

> 本文件 frontmatter 由 `mindforge project context` 在 v0.2.2 起读取，
> 用作项目级稳定上下文（principles / known_risks / preferred_workflow /
> default_target / description）。
>
> **MindForge 永远不读本文正文**，正文里随手写的草稿 / SECRET / 临时
> 笔记不会被打进 context pack（详见 `docs/M5_3_PROJECT_CONTEXT_PROTOCOL.md`）。

## 项目笔记区域（人手维护）

把跟该项目相关的人手笔记放这里。MindForge 不解析、不汇总、不写回。
