# M3 · Human Approval 协议（v0.1 → v0.2 之间的硬约束）

> 本文是 MindForge **唯一**对"`ai_draft → human_approved` 状态转移"具
> 约束力的文档。任何代码、CLI、UI 行为都必须以本文协议为准。
>
> 设计哲学：**"AI 是草稿手，你是主人"**。MindForge 的反 AI 污染机制
> 全部寄托在这一道闸门上 — 没有显式人工动作，AI 永远不可能晋升知识。

---

## 1. 为什么必须有这道闸门？

`ai_draft` 与 `human_approved` 在数据上只是 frontmatter 的一个字段，但
在**记忆契约**上是两类不同的东西：

| 状态 | 含义 | 谁可以写 |
|---|---|---|
| `ai_draft` | AI 加工草稿，**不**代表本人长期记忆，可能含幻觉、可能跑偏 | LLM pipeline（`mindforge process`） |
| `human_approved` | 本人**显式**确认进入长期记忆候选；可被未来 review / recall / project memory hooks 召回 | **仅** `mindforge approve` CLI |

如果允许 AI 自动晋升，那么：
- 一年后 vault 里全是看似"我已确认"的 AI 复读机内容；
- 任何后续基于 `human_approved` 的召回（M4 recall / project memory）都会
  把 AI 推测当我的真实理解返回给 AI，形成**自我强化的幻觉回路**；
- 复盘时无法区分"我确认过的事实"与"AI 当时这么写的草稿"。

→ 因此 `ai_draft → human_approved` 是 MindForge 的**第一道反污染闸门**，
必须 100% 由显式人工动作触发，**绝不**允许 prompt 注入、阈值规则、
LLM 自评、value_score 高分自动晋升等任何自动机制。

---

## 2. 状态转移（v0.1 → v0.2 阶段）

```
        ┌─────────┐  mindforge process  ┌──────────┐
  raw ─▶│ triaged │─────────────────────▶│ ai_draft │  (Card frontmatter status)
        └─────────┘                      └─────┬────┘
                                               │ mindforge approve --card <path>
                                               │ （唯一允许的晋升路径）
                                               ▼
                                        ┌────────────────┐
                                        │ human_approved │
                                        └────────────────┘
                                               │
                                               │ mindforge approve --card <path> --revoke
                                               │ （v0.2.1+ 才考虑，本协议留待将来）
                                               ▼
                                          (back to ai_draft)
```

允许的转移（M3 范围）：
- `ai_draft` → `human_approved`：**仅** `mindforge approve` 触发
- `human_approved` → `human_approved`：**幂等**成功（不写新 timestamp）

不允许的转移（必须 fail-fast）：
- `raw` / `triaged` / `skipped` / `failed` / 任何未知 status → `human_approved`
- LLM pipeline → `human_approved`（**结构上**保证：`mindforge process` 永远只
  写 `ai_draft`）
- 通过编辑 yaml / 改 state.json 直接绕过 approve（不在协议保护范围内，但
  会在审计层面被发现 — state.json 缺 `approved_at` / `approval_method`）

---

## 3. 命令契约：`mindforge approve --card <path>`

### 3.1 签名

```
mindforge approve --card <path-to-knowledge-card.md>
                  [--config <mindforge.yaml>]
```

v0.1 不实现：`--source-id` / `--track` / `--all-pending` 等批量形式；
M3 严格"一卡一确认"，避免误批量。

### 3.2 行为

1. 加载 `--config`（仅为定位 `state.workdir` / `vault.cards_dir`）；**不**调用 `load_dotenv` 之外的任何 env 读取，**不**实例化 LLM provider；
2. 读取 `<card>` 的 frontmatter（`python-frontmatter`）；
3. 校验：
   - card 文件必须存在；不存在 → exit 2；
   - frontmatter 必须包含 `status` 字段；缺失 → exit 3；
   - YAML 必须可解析；解析失败 → exit 3；
4. 按当前 `status` 决定动作：
   - `ai_draft` → 改写 frontmatter，加 `approved_at` / `approval_method: explicit_cli`，原子写回；同步更新 state.json 对应 item；exit 0；
   - `human_approved` → **幂等**（不修改文件、不刷新 timestamp、不重复写 state）；exit 0；
   - 其他（`raw` / `triaged` / `skipped` / `failed` / 未知）→ 拒绝；exit 4；
5. 全程**不**调用 LLM、**不**改正文、**不**改原始 source 文件、**不**触发 `mindforge.processors`。

### 3.3 卡片 frontmatter 变更（最小集）

approve 成功后 frontmatter 仅追加 / 修改下列字段：

```yaml
status: human_approved
approved_at: "2026-04-28T16:40:21+08:00"   # ISO-8601 with tz
approval_method: explicit_cli              # 永远是 explicit_cli（v0.1）
```

**不**改：`id` / `title` / `track` / `source_*` / `prompt_version` /
`stage_models` / `run_id` / `value_score` / `confidence` / 卡片正文。

### 3.4 state.json 同步

成功 approve 后，对应 `ItemState` 字段更新：

```
status: "human_approved"
approved_at: <iso datetime>
approval_method: "explicit_cli"
last_run_id: <approve 命令本次的 run_id>
```

如果 state.json 中找不到对应 item（极少见 — 例如有人手工把卡片复制到
另一个 vault），则**只**更新 card 文件，并在 runs jsonl 写一条
`approval_completed` 事件中标 `state_missing: true`（白名单允许的字段
之一），不视为错误。

### 3.5 退出码契约

| Exit | 含义 |
|---|---|
| 0 | approve 成功 OR 已是 human_approved（幂等） |
| 2 | card 文件不存在 / 配置错 |
| 3 | frontmatter 缺 status / YAML 损坏 |
| 4 | status 不在允许晋升的集合中 |

---

## 4. 审计要求（runs/*.jsonl + state.json）

### 4.1 新增事件（runs/*.jsonl）

| 事件名 | 何时 emit | 关键字段 |
|---|---|---|
| `approval_started` | 命令进入业务逻辑前 | `path`（card 绝对/相对路径） |
| `approval_completed` | 成功（含幂等情况） | `path` / `status`（最终值，必定 `human_approved`）/ `approval_method` / `state_missing`（仅在 state 找不到时为 true） |
| `approval_failed` | 任何 exit != 0 的失败 | `path` / `error_message` / `status`（拒绝时记录拒绝前的 status） |

**禁止**：jsonl 中**不得**记录 card 正文、AI summary、source_excerpt、
prompt 全文、completion 全文、api_key、Authorization。所有字段仍走
`run_logger._ALLOWED_FIELDS` 白名单。

### 4.2 state.json 新增字段（ItemState）

```
approved_at: datetime | None      # 仅 approve 成功时 set
approval_method: str | None       # v0.1 仅 "explicit_cli"
```

向后兼容：旧 state.json 缺这两个字段时按 None 解析；不触发 schema migration。

---

## 5. 反向断言（如何**结构上**保证 AI 不能自动 human_approved）

下列约束都通过测试覆盖：

1. **代码层面**：`approve` 函数与 `mindforge.processors.Pipeline` **零依赖**；
   `Pipeline` 不 import `approver`，反之亦然；
2. **生成路径层面**：`Writer` 渲染 Knowledge Card 模板时 `status` 字段
   **硬编码**为 `ai_draft`（模板里直接写 `status: ai_draft`，**不**接受
   AI 输出的 status 字段）；
3. **CLI 层面**：`mindforge process` 命令绝不会写 `status: human_approved`
   到任何 card；
4. **Approver 层面**：`approve` 永远只能从 `ai_draft` 晋升，且 `approval_method`
   字段在 v0.1 是固定字符串 `"explicit_cli"`，**不**接受参数注入；
5. **测试层面**：专门有 `test_process_never_writes_human_approved` 等
   反向断言用例，跑 fake provider 端到端确认**所有**生成的卡片初始
   status 都是 `ai_draft`。

---

## 6. v0.1 → v0.2 之间的边界（不在 M3 最小范围）

下列功能**不**在本协议覆盖，留给后续：

- ❌ `mindforge approve --revoke`（human_approved → ai_draft 回退）；
- ❌ 批量 approve（`--all-pending` / `--track <id>` 等）；
- ❌ 反向同步：检测人**手工**编辑 card frontmatter 后自动回写 state.json；
- ❌ approve 时附加 human_note 模板自动追加；
- ❌ 任何 LLM 辅助 approve 决策（"AI 看一眼帮你判断要不要批准"）— **永久禁止**。

---

## 7. 测试覆盖矩阵（M3 必须通过）

| # | 用例 | 预期 |
|---|---|---|
| 1 | ai_draft card → approve | exit 0；status 改为 human_approved，approved_at / approval_method 写入；state.json 同步 |
| 2 | approve 不修改正文 | card body 字符串相等 |
| 3 | approve 不修改 source 文件 | source 文件 byte 级相等 |
| 4 | approve 零 env | 清掉所有 MINDFORGE_* 仍 exit 0 |
| 5 | approve 不调 LLM | 拦截 httpx.Client.post 抛 AssertionError 仍 exit 0 |
| 6 | human_approved 幂等 | 第二次 approve exit 0；timestamp 不变；state.json 不二次刷新 |
| 7 | raw / failed / skipped / 未知 → 拒绝 | exit 4；card 不变 |
| 8 | YAML 损坏 → 拒绝 | exit 3；card 不变 |
| 9 | card 不存在 → 拒绝 | exit 2 |
| 10 | runs jsonl 仅白名单字段 | approval_started / completed 字段全在白名单 |
| 11 | state.json 含 approved_at / approval_method 且无敏感字段 | 序列化 round-trip 通过 |
| 12 | **process 命令绝不会写 human_approved** | 跑 fake E2E，所有卡片初始 status == ai_draft |
