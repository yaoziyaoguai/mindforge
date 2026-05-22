---
title: Golang Concurrency Patterns 学习笔记
date: 2026-05-17
tags: [dogfood, real-llm, golang, concurrency]
---

# Golang Concurrency Patterns

## Goroutine 与 Channel 基础

Go 语言的并发模型基于 CSP（Communicating Sequential Processes），核心原则是：

> Don't communicate by sharing memory; share memory by communicating.

### Channel 方向控制

```go
// 只写 channel
func producer(out chan<- int) {
    for i := 0; i < 10; i++ {
        out <- i
    }
    close(out)
}

// 只读 channel
func consumer(in <-chan int) {
    for v := range in {
        fmt.Println(v)
    }
}
```

## 常用 Pattern 总结

| Pattern | 适用场景 | 核心机制 |
|---------|---------|---------|
| Fan-out / Fan-in | 并行处理多个任务 | 多个 goroutine 从同一 channel 读取 |
| Pipeline | 流水线式数据处理 | 串联多个 channel 阶段 |
| Context cancellation | 超时控制与优雅退出 | context.WithTimeout / WithCancel |

## errgroup 的使用

对于需要 error propagation 的并发场景，`golang.org/x/sync/errgroup` 是更推荐的选择：

```go
g, ctx := errgroup.WithContext(ctx)
g.Go(func() error { return doTaskA(ctx) })
g.Go(func() error { return doTaskB(ctx) })
if err := g.Wait(); err != nil {
    // handle the first error
}
```

## 避坑指南

- **goroutine leak**: 确保每个 goroutine 都有退出路径
- **channel deadlock**: unbuffered channel 的发送和接收必须在不同 goroutine
- **race condition**: 使用 `go run -race` 或 `go test -race` 检测数据竞争
