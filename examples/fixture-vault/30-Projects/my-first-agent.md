---
project: my-first-agent
description: 我自己 from-scratch 写的第一个 coding agent，用来验证 harness + checkpoint 设计
default_target: claude-code
learning_tracks:
  - agent-runtime
  - harness-engineering
  - context-engineering
principles:
  - tool 调用必须有超时与可观察日志
  - 每个 tool call 完成都是 checkpoint 候选
  - system prompt 与 message 严格分层
known_risks:
  - 工具调度过于灵活会反向污染 prompt
  - checkpoint 频率不当会拖慢主线程
preferred_workflow:
  - 写 tool → 写测试 → 接入 dispatcher → 加 checkpoint
---

# my-first-agent

> 这是 demo vault 的示例项目主笔记。本笔记**正文**永远不会被 MindForge
> 当作"知识来源"读取；MindForge 只读上面的 frontmatter（profile）。

## 目标

构建一个最小可观察的 coding agent，验证 harness / checkpoint / context 三个原则。

## 当前里程碑

- [x] 工具注册表
- [x] 单 tool 真实跑通
- [ ] 多 tool 串联
- [ ] 完整 checkpoint replay
