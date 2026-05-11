---
source: https://example.com/blog/harness-engineering-101
source_type: webclip_markdown
captured_at: 2026-04-18T20:11:00+08:00
---

# Harness Engineering 101

> 虚构示例。本文用于演示 WebClip adapter 解析。

## 什么是 harness

Harness 是承载 agent 真正能"做事"的那一层：tool registry、tool dispatcher、
权限控制、观察器、错误恢复、超时与并发治理。

## 为什么不要把 harness 写在 prompt 里

把 harness 责任写在 prompt 里会带来三个问题：

- **不可观测**：错误链路只有 LLM 自己知道；
- **不可测试**：没有确定性边界；
- **不可演进**：升级模型就要重写 prompt。

## 推荐做法

把 harness 设计成一个**普通后端服务**：明确接口、明确状态机、明确日志、
明确 metrics、明确错误码。LLM 只是它的一个用户。
