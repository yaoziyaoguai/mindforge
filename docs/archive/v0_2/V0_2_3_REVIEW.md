# MindForge v0.2.3 · M5.3 收尾 + M5.7 复盘

> 范围：**多 project 联合上下文** + **30-Projects evidence block 幂等追加**
> + **本地 only telemetry**。
> 上一轮：[V0_2_2_REVIEW.md](./V0_2_2_REVIEW.md)
> 协议：[M5_3_PROJECT_CONTEXT_PROTOCOL.md](./M5_3_PROJECT_CONTEXT_PROTOCOL.md) ·
> [M5_7_TELEMETRY_PROTOCOL.md](./M5_7_TELEMETRY_PROTOCOL.md)

---

## 1. v0.2.3 增量能力清单

### 1.1 多 project 联合上下文

```
mindforge project context my-first-agent agent-tool-harness
mindforge project context a b --target claude-code
mindforge project context a b --format json
mindforge project context a b --output /tmp/ctx.md
mindforge project context a b --include-drafts --limit 20
```

- 单 project 行为**完全不变**（v0.2.2 的 markdown / json 字段全部保留）
- 多 project 走独立渲染器 `multi_project_context.py`，输出顺序固定 11 段：
  1. `# Multi-Project Context · a · b`
  2. `## Source Notice`（每个 project 一行 found 状态）
  3. `## Project Profiles`（按输入顺序，逐项目段）
  4. `## Cross-project Learning Tracks`
  5. `## Cross-project Principles`（按 source 标注 `from project [a]` /
     `from card [card-x] (project a)`，**不**自动裁决冲突）
  6. `## Cross-project Known Risks`（同上）
  7. `## Project-specific Cards`（按项目分段；**path 级去重**：
     重复卡片只归第一个匹配项目）
  8. `## Shared Action Items`
  9. `## Review Due`
  10. `## Suggested Prompt`（明确"multi-project context pack"）
  11. `## Excluded Content (safety guarantee)`
- 缺 profile 的项目 → **只对该 project 降级**为 cards-only，其他正常
- target 解析顺序：CLI > 第一个 found 的 profile.default_target > `generic`
- JSON 输出：`mode: "multi_project"` + `version: 2`

### 1.2 `mindforge project update-evidence`

```
mindforge project update-evidence a            # 写盘
mindforge project update-evidence a --dry-run  # 仅打印
mindforge project update-evidence a --include-drafts
```

- 把当前已确认 Knowledge Cards 的**安全摘要**幂等写入
  `30-Projects/<name>.md` 的受控区块：

  ```
  <!-- MINDFORGE:EVIDENCE:START -->
  ## MindForge Evidence
  Last updated: ...
  - [Card Title](../20-Knowledge-Cards/.../xxx.md)
    - status / learning_track / value_score / review_after
  <!-- MINDFORGE:EVIDENCE:END -->
  ```

- **幂等核心**：`re.escape(START) + r".*?" + re.escape(END)` (DOTALL)
  splice 替换；不存在则按"原文末换行情况"决定 separator 后追加
- **profile 必须先存在**，否则 `EvidenceError` + exit 2 + 友好提示
  （本命令故意**不自动创建** profile）
- 卡片排序键 `(c.id or stem).lower(), c.rel_path` —— 让幂等性不依赖 dict 插入顺序
- 默认仅 `human_approved`；`--include-drafts` 才含 `ai_draft`
- `--dry-run` 完整打印将要写入的内容，**不**写盘
- **永远不写入**：raw_text / prompt / completion / api_key /
  原始 `## Source Excerpt`

### 1.3 本地 telemetry（M5.7）

详见 [M5_7_TELEMETRY_PROTOCOL.md](./M5_7_TELEMETRY_PROTOCOL.md)。要点：

- 默认开 (`enabled: true`)、永久 `local_only`
- 写入 `<state.workdir>/telemetry.jsonl`，已加入 `.gitignore`
- 字段白名单 10 项；`record_event` 二次过滤兜底
- `mindforge telemetry status` / `telemetry summary` 命令
- 写盘失败 swallow，不影响业务命令
- `enabled: false` → 整个函数零开销零文件创建

---

## 2. 测试覆盖（新增 22 / 总 209 全过）

`tests/test_v0_2_3.py` 22 用例 5 大块：

1. **多 project 兼容**：单 project 的 markdown / json 与 v0.2.2 字节级一致
2. **多 project 分组**：11 段都出现、顺序正确、target 来自 first-found profile
3. **多 project dedup**：重复卡片只归第一个匹配项目（path 级 set）
4. **多 project 降级**：缺 profile 的项目独立降级，其他不受影响
5. **多 project JSON v2**：`mode: "multi_project"` + `project_count` 正确
6. **update-evidence dry-run**：不写盘
7. **update-evidence 创建 + 更新**：marker 不存在时追加 / 存在时替换
8. **update-evidence 幂等**：第二次运行 `will_change=False`、无写盘
9. **update-evidence 不漏 secret**：6 条正则在 START/END 之间均不匹配
10. **update-evidence 不修改 Knowledge Cards**：cards 文件 mtime 不变
11. **telemetry 字段白名单**：所有 `command_completed` 事件只含 10 字段
12. **telemetry 不漏内容**：6 条正则审计 telemetry.jsonl 全文 0 匹配
13. **telemetry disabled**：`enabled: false` 时不创建文件、不写事件
14. **telemetry status / summary CLI** 输出可预期
15. **evidence 模块单测**：`update_evidence_block` / `_splice_block` /
    `EvidenceError`（缺 profile）

旧用例（v0.2.0 / v0.2.1 / v0.2.2）全部通过：**209 passed**。

---

## 3. /tmp 沙箱 smoke 摘要

8 步走过：单 project / 多 project markdown / 多 project json /
update-evidence dry-run / update-evidence write / update-evidence 重跑
（"已是最新，未写盘"）/ telemetry status / telemetry summary。

证据：

- `telemetry.jsonl` 6 行事件，**0** 个匹配 `SECRET|sk-smoke`
- profile 文件 START/END marker 之间 0 泄漏
- profile 文件人手部分（含 `SECRET=sk-smoke-must-not-leak`）原样保留

---

## 4. 安全 & 范围契约（继续坚守）

- ❌ 不调用任何 LLM（真实或 fake）
- ❌ 不读取 `.env` / `runs/` / `state.json` 作为知识来源
- ❌ 不读取 `00-Inbox/` 任何 raw source
- ❌ 不修改 Knowledge Cards
- ❌ 不修改原始 source 文件
- ❌ 不自动 approve
- ❌ 不上传 telemetry
- ❌ 不做 RAG / embedding / Obsidian 插件 / 自动复习调度
- ❌ 不进入 M5.1 PDF/Docx，也不进入 M5.4 RAG spike

---

## 5. 下一步候选（不预先承诺）

| 候选 | 价值 | 风险 |
|---|---|---|
| **CLI polish**（错误信息 / `--help` 文案 / shell completion） | ⭐⭐⭐ 立刻提升手感 | 低 |
| **M5.1 PDF/Docx adapter** | ⭐⭐⭐ 真实 PKM 价值 | 容易被难解析的 PDF 拖进 OCR 工程 |
| **M5.2 WebClip / ChatExport adapter** | ⭐⭐ | ChatExport 容易把 secret 带进 raw_text，需要入口脱敏 |

建议：**先用满 1–2 周 v0.2.3**（多 project context + evidence + telemetry），
让 telemetry summary 自己告诉我们最常用的命令是哪几个，再决定下一站。
