---
title: Kubernetes Controller 开发实践
date: 2026-05-15
tags: [dogfood, real-llm, kubernetes, golang, controller]
---

# Kubernetes Controller 开发实践

## 学习动机

最近在项目中需要开发一个自定义 Kubernetes Controller 来管理内部资源的生命周期。之前只有使用 kubectl 的经验，没有实际开发过 Controller。

## 核心概念理解

### Controller 的工作原理

Kubernetes Controller 本质上是一个控制循环（Control Loop），持续监控资源的实际状态与期望状态，并通过调谐（Reconcile）使两者趋于一致。

### Informer 与 WorkQueue

Informer 负责监听 API Server 的资源变更事件并维护本地缓存，WorkQueue 负责对事件进行限流和去重。这两个组件是 Controller 高效运行的基础。

### CRD 定义

Custom Resource Definition (CRD) 允许用户扩展 Kubernetes API。开发 Controller 的第一步通常是定义 CRD 的 schema 和 validation 规则。

## 实践踩坑记录

1. RBAC 权限配置遗漏导致 Controller 无法 List/Watch 资源
2. Finalizer 机制理解不足导致资源删除卡住
3. Status 子资源更新与 Spec 更新需要使用不同的 Client 方法

## 下一步学习计划

- 深入学习 controller-runtime 库的源码
- 了解 Operator SDK 和 Kubebuilder 的差异
- 实践编写 Webhook Admission Controller
