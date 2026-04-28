---
title: "ReAct Loop 中加 checkpoint 的两种方式"
url: "https://example.com/post/react-checkpoint"
author: "Some Author"
tags: ["agent", "runtime"]
created: "2026-04-27T08:00:00"
savedAt: "2026-04-27T22:30:00"
---

# ReAct Loop 中加 checkpoint 的两种方式

正文段落 1：介绍 ReAct loop 与状态机思路。

正文段落 2：对比两种 checkpoint 实现。

## Highlights

> 第一条高亮：ReAct 循环里 step-level 的 checkpoint 可以让 agent 在崩溃后从最近一步恢复。

我自己的批注：这点很关键。

> 第二条高亮：另一种思路是 episode-level checkpoint，按 task 维度落盘。

> 第三条高亮：选择哪种取决于失败成本与重放成本的权衡。

## 其他段

后面的内容不应被视作 highlights。
