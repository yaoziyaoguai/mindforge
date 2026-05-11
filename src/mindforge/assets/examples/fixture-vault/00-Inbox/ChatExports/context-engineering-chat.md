---
source_type: chat_export
captured_at: 2026-04-20T15:00:00+08:00
title: 关于 Context Engineering 的一段对话
---

# 关于 Context Engineering 的一段对话

> 虚构示例对话，用于演示 ChatExport adapter。

## User

我在做一个 coding agent，应该把哪些信息放进 system prompt？

## Assistant

简短答案：**只放"会话级稳定不变"的内容**。例如：

- 角色与边界；
- 工具列表与签名；
- 安全契约（哪些事不能做）；
- 输出格式约束。

不要放进 system prompt：

- 当前会话状态；
- 用户具体诉求；
- 工具返回结果；
- 长文档全文。

那些应该走 **context window 中后段** 或 **tool result**。

## User

也就是说 system prompt 是 contract，message 是 state？

## Assistant

完全正确。一个有用的口诀：**system prompt 是不可变常量，message 是事件流。**
