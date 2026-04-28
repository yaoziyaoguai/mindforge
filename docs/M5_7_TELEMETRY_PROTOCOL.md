# M5.7 · Local Telemetry Protocol（v0.2.3）

> 本文定义 MindForge **本地 only** 的 usage telemetry 协议。
> 上线于 v0.2.3。配合 [`V0_2_3_REVIEW.md`](./V0_2_3_REVIEW.md) 阅读。

---

## 0. 定位（先讲清楚不是什么）

MindForge telemetry **不是**：

- ❌ 不是埋点上传（默认且永久 `local_only`）
- ❌ 不是云端分析 / 用户画像 / dashboard
- ❌ 不是 LLM 调用日志（那是 `runs/*.jsonl` 的 `RunLogger`）
- ❌ 不记录任何 raw source / card body / prompt / completion / api key

MindForge telemetry **是**：

- ✅ 一份纯本地的命令使用观察日志
- ✅ 帮助你（用户自己）回答："我到底用了哪些命令？多频繁？是否成功？耗时？"
- ✅ 字段经过**白名单**过滤，结构稳定可 grep
- ✅ 与业务命令的成败 **完全解耦**（写盘失败也不影响业务）

---

## 1. 字段白名单（唯一真理来源 = `src/mindforge/telemetry.py::ALLOWED_FIELDS`）

| 字段 | 类型 | 含义 |
|---|---|---|
| `event_name` | str | 事件类型，目前仅 `command_completed` |
| `command` | str | 命令名（如 `project-context` / `project-update-evidence` / `recall` / `review-due`） |
| `success` | bool | 是否成功 |
| `duration_ms` | int | 命令耗时毫秒 |
| `result_count` | int | 结果条数（recall hits / context cards / evidence cards 等） |
| `project_count` | int | 该次命令涉及的项目数（多项目 context 有意义） |
| `card_count` | int | 该次命令涉及的卡片数 |
| `error_code` | str | 失败时记 `type(exc).__name__`，截断到 80 字符 |
| `timestamp` | ISO8601 | 命令完成时刻 |
| `mindforge_version` | str | 当前 MindForge 版本 |

**任何**不在白名单内的字段会被 `record_event` 二次过滤丢弃 —
这是防御性设计，避免未来误传。

---

## 2. 严格禁止的字段（绝不会被记录）

- `raw_text` / source 原文 / card body / `## Source Excerpt` 段
- `prompt` / `completion` / model output 任何片段
- `api_key` / `Authorization` / `Bearer ...` / `sk-...`
- `.env` 内容
- 项目名（`project_name`）/ 卡片标题 / 卡片 path / 用户绝对私有路径
- 关键词原文（recall 的 query / track 名 / tag）

→ 即使代码里"想加上"，也会因 `ALLOWED_FIELDS` 过滤而落不到盘上。
测试 `tests/test_v0_2_3.py::test_telemetry_*_does_not_leak_*` 多角度
断言这一点。

---

## 3. 存储位置

- 文件：`<state.workdir>/telemetry.jsonl`（如 `.mindforge/telemetry.jsonl`）
- 格式：每行一个 JSON 对象，字段顺序固定（写入端用稳定 dict 顺序）
- `.gitignore` 已包含 `.mindforge/telemetry.jsonl`，**永远不会**进 git
- 写盘失败（OSError / 磁盘满 / 权限）静默 swallow，**不影响**业务命令
- 没有自动 rotate / cleanup —— 你愿意可以手动 `rm`，不会影响功能

---

## 4. 配置

`configs/mindforge.yaml`：

```yaml
telemetry:
  enabled: true        # 默认开
  local_only: true     # 永远 true；保留字段是为了在文档/UI 中明示"不上传"
```

- `enabled: false` → `record_event` 立即返回，**零 IO、零文件创建**
- `local_only` 是**契约字段**，非开关：MindForge 没有"上传"代码路径
- 旧 yaml（无 `telemetry` 块）走默认值 `enabled=true, local_only=true`

---

## 5. CLI

### 5.1 `mindforge telemetry status`

打印：

- enabled / local_only
- 文件路径 + 是否存在
- event 总数

### 5.2 `mindforge telemetry summary`

聚合统计（**不展示任何业务字段**）：

- total / success / failure 计数
- 最常用命令 Top N · 平均 duration_ms
- 最近错误按 `error_code` 分组

不做：dashboard / 时间序列图 / 用户画像 / 跨设备聚合。

---

## 6. 实现要点（看代码即可）

| 模块 | 责任 |
|---|---|
| `telemetry.py::TelemetryConfig` | 解析 / 默认值 |
| `telemetry.py::record_event` | 白名单过滤 + 原子追加写 + 失败 swallow |
| `telemetry.py::measure(workdir, cfg, command)` | 上下文管理器：自动算 `duration_ms`、捕获异常→ `error_code` |
| `telemetry.py::TelemetryHandle.set_counts(...)` | 命令体内更新 `result_count` / `card_count` / `project_count` |
| `telemetry.py::summarize` | 纯聚合函数（无 IO） |
| `cli.py` | 在 `project context` / `project update-evidence` / `recall` / `review due` 入口包 `with measure(...) as h:` |

异常仍正常抛出（不吞业务异常），但 `success=False` + `error_code` 会被记录。

---

## 7. 与 RunLogger 的区别

| 维度 | RunLogger (`runs/*.jsonl`) | Telemetry (`telemetry.jsonl`) |
|---|---|---|
| 范围 | LLM 调用与 5-stage pipeline | 任意 CLI 命令的元数据 |
| 是否记录内容 | 受配置控制（`record_prompts` / `record_outputs`） | **绝不** |
| 字段稳定性 | 跟 stage / provider 演进 | 严格白名单（10 字段，只增不破） |
| 触发时机 | `process` 主链路 | 每条业务命令 |
| 默认开关 | 跟随主流程 | `enabled: true` 但 `local_only` |

两者**互不依赖**：删 telemetry.jsonl 不影响 runs；删 runs 不影响 telemetry。

---

## 8. 反模式（永远不要做）

1. ❌ "为了 debug 临时记一下 prompt" → 写到别的地方去，绝不进 telemetry
2. ❌ "加个 project_name 字段帮我看哪个项目用得多" → 暴露隐私 / 工作信息
3. ❌ "顺便上传到一个匿名服务" → MindForge 没有 HTTP client，这一条是契约
4. ❌ "把 recall 的 query 记下来做关键词云" → 关键词常常是项目名 / 客户名 / 私事

如有这些需求，请新建一个**独立、显式 opt-in、可审查**的工具，而**不是**
扩展 telemetry 字段集。
