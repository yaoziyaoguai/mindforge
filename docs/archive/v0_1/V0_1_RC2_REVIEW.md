# MindForge v0.1.0-rc2 — M3 复盘（Explicit Human Approval Workflow）

> 本文是 v0.1.0-rc2 tag 对应的复盘记录，承接 [`V0_1_RC1_REVIEW.md`](./V0_1_RC1_REVIEW.md) §4
> "进入 M3 的条件"。完整协议见 [`M3_HUMAN_APPROVAL_PROTOCOL.md`](./M3_HUMAN_APPROVAL_PROTOCOL.md)。

---

## 1. M3 完成了什么

| 范畴 | 交付 |
|---|---|
| 协议 | `docs/M3_HUMAN_APPROVAL_PROTOCOL.md`（状态转移 / 退出码 / 审计字段 / 反向断言 / 12 项测试矩阵） |
| 实现 | `src/mindforge/approver.py`（纯函数 `approve_card`） + `src/mindforge/cli.py` 新增 `approve` 命令 |
| 数据 | `ItemState` 新增 `approved_at` / `approval_method`；`run_logger` 新增 3 个事件 + 5 个白名单字段 |
| 测试 | `tests/test_approve.py` 17 用例（含反向断言），rc1 基线 106 → rc2 总数 **123 passed** |
| 文档 | `MINDFORGE_PROTOCOL.md` §5.4 / `ROADMAP.md` / `V0_1_RC1_REVIEW.md` §4 全部对齐到 M3 |

最终命令形态：

```
mindforge approve --card 20-Knowledge-Cards/agent-runtime/20260428--xxx.md \
                  --config configs/mindforge.yaml
```

---

## 2. `mindforge approve` 状态转移规则

| 当前 status | approve 行为 | exit | state.json | runs/*.jsonl |
|---|---|---|---|---|
| `ai_draft` | 写 `status=human_approved` + `approved_at` + `approval_method=explicit_cli` | 0 | 同步 3 个字段 | `approval_started` + `approval_completed` |
| `human_approved` | **幂等**：不动文件、不刷 timestamp、不写 state | 0 | 不变 | `approval_started` + `approval_completed`（带 `idempotent=true`） |
| `raw` / `triaged` / `skipped` / `failed` / 未知 | 拒绝 | 4 | 不变 | `approval_started` + `approval_failed` |
| frontmatter 缺 status / YAML 损坏 | 拒绝 | 3 | 不变 | `approval_started` + `approval_failed` |
| 卡片文件不存在 | 拒绝 | 2 | 不变 | `approval_started` + `approval_failed` |

硬约束：
- 卡片正文 1 字节不动；
- 16 个原 frontmatter 字段全部保留；
- 源文件（`00-Inbox/**`）byte 级不变；
- 全程不调 LLM、不需 `.env`、不读 `active_profile`。

---

## 3. 为什么 `human_approved` 必须来自显式 CLI

如果允许其他路径写入这个状态（例如：人手编辑文件 + 下次 `scan` 自动回写、
LLM 高 value_score 自动晋升、prompt 输出 status 字段被信任…），就会形成
**反向污染回路**：未来 M4 recall / project memory 把 AI 推测当成"我确认
过的事实"返回给下一轮 LLM 调用，自我强化幻觉。

显式 CLI 入口的好处是：
1. **审计点唯一**：所有晋升都在 `runs/*.jsonl` 留下 `approval_completed`
   事件，可追溯、可回放；
2. **意图明确**：`approval_method` 字段在 v0.1 硬编码为 `"explicit_cli"`，
   不接受参数注入，杜绝"AI 帮我自动批准"这条路；
3. **可组合**：未来扩展（`--revoke` / 批量 / Web UI）都通过命令的扩展实现，
   而不是放宽闸门规则。

→ M3 的设计裁定（与 rc1 §4 原计划"反向同步"的差异）：v0.1 不实现"人工
编辑 frontmatter → 下次 scan 自动识别"那条隐式路径，**留待 v0.2 评估**。

---

## 4. 为什么 `mindforge process` 仍然只能生成 `ai_draft`

结构上的三道隔离：

1. **模板层**：`templates/knowledge_card.md.j2` 第 4 行 `status: ai_draft`
   是**硬编码**字符串，**不**接受 LLM 输出的任何 status 字段；
2. **代码层**：`mindforge.processors.Pipeline` 与 `mindforge.approver` 互相
   零依赖（grep 可证）；
3. **测试层**：`tests/test_approve.py::test_process_pipeline_never_writes_human_approved`
   作为反向断言：跑完 fake provider 端到端后，所有卡片 `status` 与 state.json
   均不得包含 `human_approved`。该测试是 v0.1 → v0.2 之间的硬质量门。

---

## 5. runs / state 如何审计 approval

### 5.1 `runs/<run_id>.jsonl`

每次 `mindforge approve` 执行写一个新的 jsonl，事件序列：

```
{"event":"run_started","command":"approve",...}
{"event":"approval_started","card_path":"..."}
{"event":"approval_completed","card_path":"...","status":"human_approved",
  "prev_status":"ai_draft","approval_method":"explicit_cli",
  "approved_at":"2026-04-28T16:40:21+08:00","idempotent":false}
{"event":"run_finished",...}
```

字段全部经 `run_logger._ALLOWED_FIELDS` 白名单校验，**不会**包含卡片正文 /
source 原文 / prompt 全文 / api_key。

### 5.2 `state.json`

```json
"plain_markdown::00-Inbox/ManualNotes/n1.md": {
  "status": "human_approved",
  "approved_at": "2026-04-28T16:40:21+08:00",
  "approval_method": "explicit_cli",
  ...
}
```

向前兼容：旧 state.json（rc1 之前生成）缺这两个字段时按 `None` 解析，不
触发 schema migration。

---

## 6. 质量门

```
$ pytest                  → 123 passed in ~3.3s
$ ruff check src tests    → All checks passed!
$ git status -s           → 干净
```

rc1 基线 106 → rc2 总数 123（+17 用例）。

---

## 7. 当前不能 push 的注意事项

- 本地 tag：`v0.1.0-rc1`、`v0.1.0-rc2`；远端**未**同步，`git push` /
  `git push --tags` 由人决定时机；
- `.env` / `MINDFORGE_*` 真实 API key 不在仓库；smoke 工作流见
  `docs/SMOKE_M2_8.md`，未来跑真实 LLM 之前请确认本地 .env 不会被 commit；
- M3 实现路径**不需要**任何真实 provider 调用，已通过 fake-provider E2E
  + httpx 拦截测试证明。

---

## 8. 与 rc1 §4 计划相比的偏差

| rc1 计划 | rc2 实际 | 原因 |
|---|---|---|
| 反向同步：人手改 frontmatter → scan 自动回写 | 改为显式 `mindforge approve --card` | 反 AI 污染闸门必须有清晰审计入口；隐式回写无法在 jsonl 留痕 |
| 协议写在 `MINDFORGE_PROTOCOL.md` | 独立成 `M3_HUMAN_APPROVAL_PROTOCOL.md`，主协议加链接 | 单独成文便于单独评审、单独迭代；不污染主协议结构 |
| approval_method 字段 | 硬编码 `"explicit_cli"`，不接受参数 | 防止参数注入伪造审计 |

---

## 9. 进入 M4 之前的状态确认

- v0.1.0-rc2 tag 已打（本地）✅
- 所有 v0.1 stop rules（rc1 §7）+ M3 反向断言全部通过 ✅
- 下一步：**只做 M4 设计调研，不实现**。详见
  [`docs/M4_RECALL_REVIEW_DESIGN.md`](./M4_RECALL_REVIEW_DESIGN.md)。
