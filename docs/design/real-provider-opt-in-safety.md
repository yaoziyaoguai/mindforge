---
title: "v1.5 I6: 真实 Provider Opt-in 安全文档"
type: design-doc
status: draft
date: 2026-05-25
parent: v1.5 安全集成与导入/导出扩展
priority: P2
---

# 真实 Provider Opt-in 安全文档

## 核心原则

MindForge 默认使用 **fake provider**（不调用任何真实 LLM）。切换到真实 provider 是用户的**显式 opt-in 行为**，系统不会自动启用。

参考实现：`src/mindforge/provider_readiness.py`

## Fake-default 安全模型

```
默认状态: active_profile = "fake"
  ├── 所有 pipeline 使用 fake provider
  ├── 不读取 .env 中的 API key
  ├── 不发起任何外部网络请求（LLM 相关）
  └── 不消耗任何 API 额度
```

fake provider 返回确定性占位输出，足以验证 pipeline 逻辑，但不产生有意义的 AI 内容。

## Opt-in 切换

用户在 `configs/mindforge.yaml` 中显式配置：

```yaml
llm:
  active: openai           # 从 fake 切换到真实 provider
  providers:
    openai:
      provider: openai
      model: gpt-4o
      api_key_env: OPENAI_API_KEY   # 从环境变量读取，不写在 yaml 中
```

API key 通过环境变量注入，**永不写在配置文件或代码中**。

## Readiness 状态机

`provider_readiness.inspect_provider_config()` 返回五种状态：

| 状态 | 含义 | 用户行为 |
|------|------|---------|
| `fake_default` | active_profile == fake | 无需操作；安全默认 |
| `env_only` | env 有 key 但 profile 未切换 | 检查 yaml 配置；可能误以为已启用 |
| `profile_only` | profile != fake 但 key 缺失 | 设置环境变量 |
| `ready` | profile != fake 且 key 存在 | 系统可用真实 LLM |
| `blocked` | 配置异常 | 检查 api_key_env 配置项 |

**env_only 是重要的安全信号**：用户可能设置了 API key 但忘记切换 profile，以为系统在用真实 LLM 而实际上仍在使用 fake provider。

## 什么数据会离开本机

当用户 opt-in 真实 provider 后：

| 数据类型 | 是否发送 | 备注 |
|----------|---------|------|
| Source 原文内容 | 是 | 发送给 LLM 用于生成卡片 |
| Card frontmatter metadata | 否 | 仅本地存储 |
| 文件路径 | 否 | 仅本地使用 |
| Card id / internal id | 否 | 仅本地使用 |
| API key | 是 | 发送给 provider 认证端点（HTTPS） |
| 用户配置中的其他字段 | 否 | 仅本地使用 |

## 什么数据不会离开本机（无论是否 opt-in）

- 所有 Knowledge Card 文件内容（除非用户显式发送给 LLM 处理）
- `.env` 中非 LLM 相关的配置
- vault 路径、文件系统结构
- 卡片审批状态、review 历史
- 本地图谱数据
- BM25 索引

## 支持的 Provider

| Provider | 状态 | 备注 |
|----------|------|------|
| `fake` | 默认 | 不调用外部服务 |
| `openai` | opt-in | 需 `OPENAI_API_KEY` 环境变量 |
| `anthropic` | opt-in | 需 `ANTHROPIC_API_KEY` 环境变量 |
| 其他（Cubox/Upstage 等） | 未实现 | 需先写 provider adapter |

## 用户安全检查清单

在 opt-in 真实 provider 之前，用户应确认：

- [ ] 理解哪些 source 内容会发送给 LLM provider
- [ ] 确认 source 中没有不能离开本机的敏感信息
- [ ] API key 仅通过环境变量设置，不写在 yaml 或代码中
- [ ] 了解 provider 的计费模式
- [ ] 已运行 `mindforge provider status` 确认 readiness 状态

## 系统侧安全措施

MindForge 在代码层面保证：

1. **Presence-only env check**：`provider_readiness.py` 只通过 `os.environ.__contains__` 检查 key 是否存在，**永不读取或打印 key 值**
2. **No key in logs**：API key 不出现日志、错误消息、Web UI 响应中
3. **No key in config**：配置文件只存 `api_key_env` 环境变量名，不存值
4. **Fake fallback**：如果 provider 初始化失败，回退到 fake provider 并报告错误
5. **No auto-switch**：不会因为检测到环境变量而自动切换 provider

## Web UI 行为

- Setup 页面显示 provider readiness 状态（presence-only）
- 不显示 API key 值
- 不提供在浏览器中配置 API key 的输入框
- 切换 provider 需要编辑 yaml 配置文件 + 设置环境变量

## 不在范围内

- 在 Web UI 中配置 API key
- 自动检测和切换 provider
- 多 provider 负载均衡
- Provider 用量统计/计费
- API key 轮换
- 代理配置

## 参考

- `src/mindforge/provider_readiness.py` — readiness 状态机
- `src/mindforge/config.py` — LLMConfig / provider 配置模型
- `src/mindforge/safety_policy.py` — 全局安全边界
