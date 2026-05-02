# Workspace / Obsidian Human-Approved Merge — Planning Doc (Stage 7)

> **状态：仅规划，不实现**。本文档不引入 production code，不写真实
> Obsidian vault，不自动 approve，不自动 merge。它只把"未来如何把
> ai_draft → human_approved → 长期知识工作台"这条路径的设计意图、
> 接口边界、安全约束与必备测试**显式写下来**，避免该流程被代码层悄
> 悄发明。

---

## 1. 边界一句话

`ai_draft` 是 LLM 的产物；`human_approved` 是**人类**的产物。
任何把 `ai_draft` 自动晋升为 `human_approved` 的代码路径都视为架构
违反。

---

## 2. ai_draft → human_approved 的合法路径

仓库现有路径（`approver.approve_card` / `approver.apply_decision`）：

1. 用户在 Obsidian / 编辑器中**人工阅读** ai_draft 卡片；
2. 用户决定 approve（或 reject / defer / append_as_evidence /
   link_to_existing / merge_candidate / split 等 7 个 first-class
   `ApprovalDecision` 之一）；
3. 用户**显式调用** `mindforge approve <card-id-or-path>`；
4. CLI → `approval_service` → `approver.approve_card` 原子改写
   frontmatter `status: ai_draft` → `status: human_approved`，
   并在 `state.json` 中标注 `approval_method=explicit_cli`、
   `approved_at=<utc-iso>`；
5. **没有任何自动晋升路径**。

未来扩展（仍受同一边界保护）：

- explicit GUI / Obsidian plugin click → 同样必须落到
  `approve_card` 同一原子写入入口；
- explicit batch approve（如 `approve --bulk`）必须显式列出每张卡，
  不允许"approve-all-pending"这种隐式批量。

---

## 3. workspace writer 接口（仅规划）

未来"把 human_approved card 同步到正式 Obsidian vault"是一类**新的
write 路径**。它**不**等同于现有的 `CardWriter`：后者写的是
`ai_draft`（process 阶段产出），位置是 mindforge 自己的 cards 目录；
本路径写的是 human_approved 派生物，可能落到用户长期 vault 的特定
folder（例如 `vault/inbox/approved/`）。

设计草案（**未实现**，只供未来 TDD 参照）：

```python
class WorkspaceWriter(Protocol):
    """把已批准的 card 同步到用户长期工作区的写入边界。

    所有实现必须遵守：
    - 输入是只读的 ApprovalEffect（kind="approved"）；
    - 输出是 WorkspaceMergePlan（dry-run）或 WorkspaceMergeResult；
    - 不可写未 human_approved 的 card；
    - 不可创建状态为 ai_draft 的 vault 文件；
    - 不可触发 approve/reject 等业务动作；
    - 不可读 .env / 不可联网 / 不可调真实 LLM；
    - 必须支持 dry-run：所有写入路径必须先经过 plan 阶段。
    """

    def plan_merge(self, effect: ApprovalEffect) -> WorkspaceMergePlan: ...

    def execute_merge(self, plan: WorkspaceMergePlan) -> WorkspaceMergeResult: ...
```

---

## 4. command / workflow 草案（仅规划）

| 命令（草案） | 输入 | 输出 | 默认安全行为 |
| --- | --- | --- | --- |
| `mindforge workspace plan-merge --card <path>` | 已 human_approved 卡片 | `WorkspaceMergePlan`（dry-run 摘要） | 永远不写真实 vault |
| `mindforge workspace execute-merge --plan <id>` | plan id | `WorkspaceMergeResult` | 必须 `--confirm` 显式确认；否则退出 |
| `mindforge workspace status` | — | 列出 pending merge plans | 只读 |

**不允许**的命令模式：

- `mindforge workspace auto-merge` — 自动合入禁止；
- `mindforge workspace approve-and-merge` — 把 approve 与 merge 串成一步禁止；
- `mindforge workspace sync-all` — 批量隐式合入禁止。

---

## 5. 安全约束（实现前必须满足）

实现 workspace writer 之前，下列硬约束必须用测试固化：

1. **status 守门**：writer 拒绝 `status != "human_approved"` 的 card；
2. **dry-run 优先**：默认 plan-only，execute 必须显式参数；
3. **无 secret**：writer 不读 `.env`、不调 OPENAI/ANTHROPIC env；
4. **无网络**：writer 不发起任何 HTTP/Socket 请求（本地文件操作）；
5. **无 LLM**：writer 不依赖 `mindforge.llm.*`；
6. **无 source 反向依赖**：writer 不感知 `cubox_*` / `source_mux` /
   `scanner` / `sources.cubox_*`；
7. **审计日志**：每一次 execute_merge 必须 emit 结构化事件到既有
   RunLogger（`event=workspace_merge`，字段必须显式登记到
   `_ALLOWED_FIELDS`）；
8. **原子写**：与 approver 一致使用 `_atomic_write` 模式；
9. **idempotent**：重复 execute 同一 plan 不重复写文件，必须能报告
   "already_merged"；
10. **冲突可见**：vault 中已有同 id 文件时必须 abort+报告，不允许
    silent overwrite。

---

## 6. 仍未实现 / 仍未承诺的事

- ❌ **真实 Obsidian vault 写入**（不实现）；
- ❌ **自动 approve**（永远不会做）；
- ❌ **批量 auto-merge**（永远不会做）；
- ❌ **真实私人资料处理**（不在 workspace writer 范围）；
- ❌ **RAG / embedding / semantic merge**（不在 workspace writer
  范围）；
- ❌ **Web UI / TUI / Obsidian plugin 自动同步**（不在 workspace
  writer 范围）；
- ❌ **跨设备同步 / 云端 vault**（不在 workspace writer 范围）。

如果未来需要触碰上述任一项，必须**先**写 protocol 文档（类似
`docs/M3_HUMAN_APPROVAL_PROTOCOL.md`），再 TDD 实现。

---

## 7. 后续实现前必须先写的测试

实现 workspace writer 第一行 production code 之前，下列测试必须先
存在并 Red：

1. `test_workspace_writer_rejects_non_human_approved_card`
2. `test_workspace_writer_default_is_plan_only`
3. `test_workspace_writer_execute_requires_explicit_confirm`
4. `test_workspace_writer_does_not_read_dotenv`
5. `test_workspace_writer_does_not_open_socket`
6. `test_workspace_writer_does_not_import_llm_or_source`
7. `test_workspace_writer_emits_audit_event_to_run_logger`
8. `test_workspace_writer_atomic_write_pattern`
9. `test_workspace_writer_repeat_execute_is_idempotent`
10. `test_workspace_writer_aborts_on_target_file_collision`

---

## 8. Stop Conditions

实现 workspace writer 时，遇到以下任一情况必须立即停下来 Ask User：

- 需要读 `.env`；
- 需要联网；
- 需要调 LLM；
- 需要在 ai_draft → human_approved 之外引入新 status；
- 需要让 writer 知道 source 类型（cubox / pdf / 其他）；
- 需要批量 auto-merge / silent overwrite；
- 需要新增重依赖（fsevents / pywatchdog / Obsidian SDK 等）；
- 测试失败且需要扩大 production 修改才能通过。

---

## 9. 与现有文档的关系

- `docs/M3_HUMAN_APPROVAL_PROTOCOL.md`：approval 业务语义的源头协议
  （已存在）；本文 §2/§5 复用其语义，不重写；
- `docs/OBSIDIAN_BINDING.md`：现有 Obsidian 集成（read-only scan 与
  mindforge cards 目录）；workspace writer 是其**增量扩展**而不是
  重写；
- `docs/ARCHITECTURE_MAP.md`：本文档落地后应在该 map 中追加一节
  "Workspace Writer Boundary"。
