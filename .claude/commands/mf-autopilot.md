# MindForge Autopilot

当用户运行 `/mf-autopilot` 时，Agent 必须按以下规则自主推进工程工作，不在每个 milestone 完成后停下来问用户。

---

## 0. Roadmap-authorized execution mode

Roadmap / SPEC / Plan / implementation notes 是 Autopilot 的执行授权来源。

只要工作属于 MindForge Roadmap / SPEC / Plan / implementation notes 中已经确立的产品方向，Autopilot 就可以自动推进，**不因 backend / API / schema / service / strategy / tests / Web / docs 改动而停止**。

### 产品大方向（不可变）

MindForge 是个人 AI 学习记忆库 / 本地知识工作台。

### 允许自动推进的全部范围

| 层级 | 范围 |
|------|------|
| Backend service | service 层实现、strategy / policy / presenter 层实现 |
| Web API | API schema 扩展、endpoint 新增/修改（需 spec 授权） |
| 数据模型 | schema 扩展、字段新增、类型定义 |
| 知识质量 | Card Quality、Wiki Quality（非 embedding/RAG 方案） |
| 关系与导航 | Related Cards API（轻量/确定性的）、Source Location/Provenance |
| 知识健康 | Knowledge Health checks、维护报告 |
| 图谱 | Local Graph Preview（确定性图，非 vector/embedding） |
| Web 前端 | UX/UI/i18n/copy/Wiki/Library/Card UI |
| 测试 | Python tests、contract tests、fake dogfood、browser smoke |
| 脚本 | `scripts/` 下的检查/辅助脚本 |
| 文档 | docs/specs/plans/implementation notes/roadmap |

### Backend/API work 许可条件

Backend/API/work 自动允许，当且仅当：

1. 属于活跃 Roadmap / SPEC / Plan 范围
2. 保持 MindForge 产品大方向不变
3. 不触碰全局硬红线
4. 附带 tests 和 implementation notes
5. 通过对应 gate

### 不视为停止条件的普通工作

以下属于正常可执行工作，**不触发停止**：

- backend service 实现
- Web API schema 扩展
- Python tests
- 前后端集成
- strategy / policy / presenter / service 层实现
- 轻量 Related Cards API
- 确定性关系图谱
- Source provenance/location 改进
- Knowledge health checks
- Card quality / Wiki quality 工作
- docs/spec/roadmap 更新

---

## 1. 建立工程事实

首先执行并读取以下命令的输出：

```bash
pwd
git status --short
git branch --show-current
git fetch origin
git rev-list --left-right --count @{u}...HEAD || true
git log --oneline -20
```

**安全同步规则：**
- 如果不是 clean main，或 main 与 origin/main 不对齐（非 `0 0`），先处理安全同步
- 只能 `git pull --ff-only origin main`
- 不能 merge commit，不能 rebase，不能 `git reset --hard`

### 1.1 Stale Window / Old Commit Reconciliation

用户或系统可能在终端中提到另一个窗口的 commit（例如旧分叉窗口的 `7f28d54 upstream 0 1 push failed`）。这些信息**不得直接当作当前主线事实**。

必须遵守以下规则：

1. **以当前 repo 证据为唯一真理来源。** 旧窗口/旧会话的 commit hash 必须用 `git log --all`、`git branch -a`、实际文件系统（`rg`/`ls`）重新验证。
2. **不得 cherry-pick 不可见 commit。** 如果 `git log --all` 中找不到该 hash，当作不存在处理。
3. **不得修改 remote / proxy / global git config。** 只使用当前 repo 已配置的 remote。
4. **如果旧 commit 内容缺失但仍有价值**，必须基于当前 repo evidence 重新创建，而不是依赖旧窗口的记忆。
5. **如果当前主线已覆盖旧内容**（通过正常 git history 追溯确认），记录为 `superseded/absorbed`，不重复创建。
6. **如果用户提供旧窗口的文件路径或内容**，验证后可以采纳为参考，但实现仍必须基于 `HEAD` 的 code truth。

---

## 2. 读取工程宪法和状态

每个 `/mf-autopilot` run 必须先读取以下文件（按顺序）：

1. **`docs/dev/CURRENT_PROJECT_STATE.md`** — 项目当前状态（第一入口）
2. **`docs/dev/progress-ledger.md`** — 进度跟踪
3. **`docs/dev/HANDOFF.md`** — 如果存在，读取上一次的 handoff 上下文
4. **`docs/dev/engineering-workflow.md`** — 工程工作流规范
5. `docs/design/roadmap/` 下最新 roadmap 文件（如需）
6. `docs/plans/` 下最新 active plan 文件（如需）
7. `docs/specs/` 下最近最新的 spec 文件（如需）
8. `docs/implementation-notes/` 下最新的 notes / handoff 文件（如需）
9. `docs/dev/copy-policy.md`（如需）

前 3-4 个文件是所有 task type 的必读项。剩余文件按 task type 按需读取。

---

## 3. 按 Task Type 选择入口

`/mf-autopilot` 必须根据当前 task type 选择合适的 loop 起点，**不一定每次从 spec → implementation 从头开始**。

### Task Type 判断

Agent 必须根据用户指令和当前 repo 状态判断 task type：

| Task Type | 触发信号 |
|-----------|---------|
| `bug_fix` | 用户报告 bug / test failure / gate 失败 / 行为异常 |
| `docs_cleanup` | 用户要求清理文档 / 归档 / 更新 docs |
| `ui_ux_polish` | 用户要求 UI 改进 / 设计 QA / 视觉调整 |
| `architecture_refactor` | 用户要求架构改进 / 重构 / 拆分巨石 |
| `feature_implementation` | 用户要求新功能 / 完整 milestone |
| `audit_only` | 用户要求审查 / 审计 / 不改产品代码 |
| `dogfood` | 用户要求 dogfood run / 验证 |
| `design_review` | 用户要求设计审查 / 视觉对比 |
| `autopilot_governance` | 用户要求修复 /mf-autopilot 自身规则或治理机制 |

### 各 Task Type 的 Loop 入口

#### bug_fix
```
repo facts → bug context → reproduce/inspect → fix → targeted gates → notes → progress ledger → commit/push
```

#### docs_cleanup
```
repo facts → docs inventory → code-truth check → cleanup/rewrite/archive → docs gates → progress ledger → commit/push
```

#### ui_ux_polish
```
repo facts → browser/MCP audit → P1/P2 fix → product copy/build gates → progress ledger → commit/push
```

#### architecture_refactor
```
repo facts → architecture audit → target design → boundary tests → small slice → gates → progress ledger → commit/push
```

#### feature_implementation
```
repo facts → spec/plan → self-review → implementation → gates → notes → progress ledger → commit/push
```

#### audit_only
```
repo facts → read evidence → report → no production code → docs gates → progress ledger → commit/push (if docs changed)
```

#### dogfood
```
repo facts → dogfood plan → isolated workspace → run → report → fix P1/P2 → gates → progress ledger → commit/push
```

#### design_review
```
repo facts → browser/MCP screenshots → compare → report → progress ledger → commit/push (if docs changed)
```

#### autopilot_governance
```
repo facts → read governance rules → identify gaps → update rules → docs gates → progress ledger → commit/push
```

### 入口选择规则

1. 不论从哪个入口开始，都必须: **落文档 → 更新 progress ledger → 跑 gate → commit/push**
2. 如果无法判断 task type，读取 `CURRENT_PROJECT_STATE.md` §6 找推荐 next loop
3. 如果仍然无法判断，更新 `CURRENT_PROJECT_STATE.md` 后 `HARD_STOP_PRODUCT_DECISION`

---

## 4. 自动判断当前阶段 (Legacy — 仍可用于 feature_implementation 类型)

Agent 必须根据工程事实和文档判断当前处于哪种状态：

| 状态 | 条件 | 动作 |
|------|------|------|
| **A** | 有已写好的 spec 但未实现 | 自审 spec → 通过后实现 |
| **B** | 有 implementation 但未 review / smoke | 做 post-merge review / browser smoke |
| **C** | 有 P0/P1/P2 | 按 evidence 回退修复，最多 2 轮 |
| **D** | 只有 P3/P4 | 能低风险修就修；不能修则记录到 notes，不阻塞主线 |
| **E** | 一个 milestone 已完成 | 不要停。读取 plan/roadmap/notes，自动判断下一阶段最有价值的 milestone，写 spec 或直接进入实现 |
| **F** | 没有明确下一阶段 | 读取 roadmap 找最近 planned milestone。若 roadmap 也无，写 next-phase planning review，不要乱实现 |
| **G** | context 低于 15% | 不要硬做实现。必须写 handoff 文档 → commit → push → 明确告知用户新会话继续 `/mf-autopilot` |

---

## 5. 自动跑完整 Loop

只要没有触发停止条件，Agent 必须自己完成以下循环（feature_implementation 的完整路径；其他 task type 使用 §3 的对应入口）：

```
spec / plan
  → self-review（对照 spec checklist 自审）
  → implementation（按 spec 的 implementation units 逐个实现）
  → implementation notes（记录非显而易见的决策、边界权衡、已知限制）
  → code review（对照 spec 检查 scope、红线、正确性）
  → gate（真实运行 exit code gate）
  → browser / API smoke
  → commit + push main
  → 更新 progress ledger
  → 判断下一阶段
  → 继续下一轮
```

**关键纪律：**
- 不在每个 milestone 完成后停下来问用户
- 不在 gate 通过后停下来问用户是否 commit
- 不在 commit 后停下来问用户是否继续
- 只有触发 §7 的停止条件时才停

### 5.1 Auto-continue contract

如果最终报告能写出明确的下一步行动，Autopilot 必须立即进入下一步，不得停止。

明确的下一步行动包括但不限于：
- "继续 U2"
- "下一个 milestone 是 X"
- "实现下一个 roadmap item"
- "写下一个 spec"
- "跑下一个 smoke"
- "继续 docs cleanup batch 2"

禁止输出"下一步是 X"然后停止。

**spec 写完不是停止点** — 如果 spec 通过 review，必须立即进入实现。
**docs 写完不是停止点** — 如果 docs 清理计划写好，必须立即执行 batch 1。
**commit/push 不是停止点，是检查点。** commit/push 后，Autopilot 必须：
1. 重新建立工程事实（git status、branch、log）
2. 按需重新读取 `CURRENT_PROJECT_STATE.md`、`progress-ledger.md`、活跃 roadmap/spec/notes
3. 判断是否存在 hard-stop
4. 如无 hard-stop，继续下一轮

### 5.2 Progress update template

每个 loop 结束必须更新 progress-ledger.md，使用以下固定模板：

```markdown
### YYYY-MM-DD: <简短标题>

- **Commit**: `<hash>` 或 `<start-hash>` → `<end-hash>`
- **Workstream**: <active workstream name>
- **Task type**: <bug_fix | docs_cleanup | ui_ux_polish | architecture_refactor | feature_implementation | audit_only | dogfood | design_review | autopilot_governance>
- **Outcome**: <1-2 句话描述结果>
- **Docs/notes**: <新建的 docs/implementation-notes 路径>
- **Gates**: <gate 命令 + exit codes>
- **Next**: <推荐的 next loop>
- **Workstream changed**: yes / no
```

Minor bug fix 至少追加一行：
```markdown
- YYYY-MM-DD: <描述> (`<hash>`)
```

同时检查 `CURRENT_PROJECT_STATE.md`：
- HEAD 是否已更新
- §3 (capabilities) 是否有变化
- §5 (open debts) 是否有变化
- §6 (next loops) 是否需要调整

### 5.3 Active Workstream / Loop Queue Rules

**每次 `/mf-autopilot` 运行必须识别当前 active workstream：**

1. **读取 `CURRENT_PROJECT_STATE.md` §6** 和 **`progress-ledger.md` §2**，交叉验证 active workstream。
2. **如果两处不一致** — 以 `CURRENT_PROJECT_STATE.md` 为准，并立即更新 `progress-ledger.md` §2 使其一致。
3. **默认只能有一个 active workstream。** 如果有多个候选，按 priority 选择第一个，其余保持 pending。不得同时展开多个 active workstream。
4. **如果用户明确切换方向**（例如 "现在不要做 docs cleanup，做 autopilot 升级"）— 必须更新:
   - `CURRENT_PROJECT_STATE.md` §6（推荐 next loops 排序）
   - `progress-ledger.md` §2（active workstream）
5. **commit/push 不是切换 workstream 的触发条件。** Workstream 切换优先级：
   - **前一个 workstream 全部完成（所有 batch done + 无 remaining debt）→ 自动切换，不需要等用户确认。** 从 `CURRENT_PROJECT_STATE.md` §6 的推荐 next loop 中选取第一个作为新 workstream。
   - 用户明确指令切换方向 → 覆盖自动切换，以用户指令为准。
   - 前一个 workstream 未完成 → 不得切换，除非用户明确指令。
6. **如果 workstream 完成并切换** — 在 progress-ledger §2 标记旧 workstream 为 done，记录新 workstream。新 workstream 的第一步如果是 plan/spec 编写、boundary tests、audit 等在 §5.7 auto-continue 表中的动作，必须直接进入，不得因 "新 workstream" 而停止。

### 5.4 Stop reason must use HARD_STOP_<CODE>

停止原因必须使用 §7（Stop Conditions）中定义的 `HARD_STOP_<CODE>` token。如果 §7 中无一适用，Autopilot 必须继续。

### 5.5 Context policy

根据 context 剩余比例决定行为：

| Context | 行为 |
|---------|------|
| ≥ 15% | 正常执行，可开始新实现单元 |
| < 15% | **不得开启新 loop。** 不开始大型新实现单元（除非小且边界清晰）。完成当前 loop 后写 handoff。 |
| < 10% | 只完成当前变更、跑 minimal gates、commit/push。不得开启新工作。 |
| < 5% | 立即写 handoff、跑最小 gate、commit/push、停止并输出 `HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN` |

不要仅因为 milestone 完成就停止。不要因为 context 低就停在口头报告——必须写 handoff 文档落地。

### 5.6 Low-Context Handoff Protocol

当 context 不可持续时（< 15%），handoff **必须落文档**，不只是终端报告。

**Handoff 文件位置:** `docs/dev/HANDOFF.md`（固定位置，后续 session 的第一读取目标之一）。

**HANDOFF.md 必须包含:**

```markdown
# Handoff — <date>

## Repo Snapshot
- HEAD: <hash>
- Branch: main
- Working tree: clean / dirty
- vs origin/main: <left> <right>

## Active Workstream
- Workstream: <name>
- Status: <in-progress / blocked / done>

## Last Completed Loop
- Task type: <type>
- Outcome: <1 sentence>
- Commit: <hash>

## In-Progress Files
- <file1> (staged / unstaged / pending)
- <file2>

## Gates Last Run
- <command>: exit <N>

## Next /mf-autopilot Instruction
\`\`\`
/mf-autopilot

继续 <workstream>。
上次在 <exact file> 完成了 <exact thing>。
下一步: <concrete next action>。
\`\`\`

## Hard Stops / Warnings
- <any active hard-stop conditions>
- <context remaining estimate>
```

**Handoff 写入规则:**
1. context < 15%: 完成当前 loop 后写 HANDOFF.md，commit/push。
2. context < 10%: 完成当前变更后立即写 HANDOFF.md，不开始新的代码改动。
3. context < 5%: 放弃当前变更（stash if needed），立即写 HANDOFF.md，commit/push。
4. 新 session 启动时，`/mf-autopilot` 的 §2 必读文件列表包含 `docs/dev/HANDOFF.md`（如果存在）。
5. 如果 HANDOFF.md 存在且新 loop 成功启动，新 loop 的 commit 应删除 HANDOFF.md（或标记为 resolved）。

### 5.7 Auto-Continue Decision Table

每个 loop 完成后，必须根据下一步的行动类型决定是自动继续还是停止。

**Auto-continue without asking user（直接继续，不询问）:**

| 下一步行动 | 说明 |
|-----------|------|
| audit（审计） | 只读审计，不改产品代码 |
| plan/spec 编写 | 只写文档，不改产品代码 |
| implementation notes 编写 | 只写文档，不改产品代码 |
| docs cleanup（在已批准规则内） | 清理/归档/更新文档 |
| browser/MCP QA | 只读验证，不改产品代码 |
| targeted P1/P2 fix | 小范围修复，边界清晰 |
| tests/gates | 只跑测试和 gate |
| small safe implementation slice（已由当前 plan 授权） | plan 已覆盖的实现单元 |
| architecture_refactor plan/spec only | 只写重构方案，不动代码 |
| architecture boundary tests | 只写测试，不动实现 |
| low-risk schema/service cleanup（已由 plan 覆盖） | plan 已批准的清理 |
| 更新 CURRENT_PROJECT_STATE / progress-ledger / HANDOFF | 治理文档维护 |
| start next workstream spec/plan（前一个 workstream 已完成） | 当前 workstream 完结后，CPS §6 推荐的下一 workstream 的 spec/plan/boundary-tests/audit 编写 |

**Must ask user / HARD_STOP_PRODUCT_DECISION（必须停止询问）:**

| 触发条件 | 说明 |
|---------|------|
| real API key needed | 需要真实 API key / secrets |
| real LLM/Cubox/Upstage required | 需要调用真实外部 AI 服务 |
| real private user data needed | 需要处理真实私人资料 |
| real Obsidian vault write needed | 需要写真实 Obsidian vault |
| large archive/delete batch without exact rules | 大范围删除但无明确规则 |
| large architecture implementation without plan/review | 无 plan 的大架构实现 |
| new heavy dependency | 新增大型框架 / 重依赖 |
| product direction conflict | 产品方向有歧义或冲突 |
| restoring Graph/Sensemaking/Entity/Community expansion | 重新扩张已收缩的 lab/internal 能力 |
| irreversible or destructive action | 不可逆或破坏性操作 |

**Low-context override（context 不足时覆盖正常决策）:**

| Context | 行为 |
|---------|------|
| < 15% | 不得开启新的大型实现单元。Plan/spec/docs/handoff 在边界小且清晰时可继续 |
| < 10% | 只完成当前变更、跑 minimal gates、commit/push。不得开启新工作 |
| < 5% | 立即写 HANDOFF.md、跑最小 gate、commit/push、停止并输出 `HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN` |

### 5.8 Self-routing after final report

每次 final report 之前必须执行以下自路由流程：

1. **parse own completed loop outcome** — 解析刚完成的 loop 结果
2. **identify next recommended loop** — 从 `CURRENT_PROJECT_STATE.md` §6 和当前进度识别下一步
3. **classify next loop task type** — 判断下一 loop 的 task type（`bug_fix` / `docs_cleanup` / `ui_ux_polish` / `architecture_refactor` / `feature_implementation` / `audit_only` / `dogfood` / `design_review` / `autopilot_governance`）
4. **check hard-stop table** — 对照 §5.7 的 Auto-Continue Decision Table
5. **check context policy** — 对照 §5.5 和 §5.7 的 low-context override
6. **decide and COMMIT — 必须输出标准化 ACTION token，不得只描述不执行:**
   - 如果 auto-continue allowed → 输出 `ACTION: CONTINUE_NEXT_LOOP. Next: <具体下一步描述>`，然后**立即进入下一步执行**，不得在 final report 后停止
   - 如果 not allowed → 输出 `ACTION: HARD_STOP_<CODE>. Reason: <具体原因>`，然后更新所有 state docs、按需写 HANDOFF.md、停止
   - 如果 context < 15% 但当前 loop 已完成 → 输出 `ACTION: HANDOFF_AND_STOP. Reason: context low, handoff written`，然后写 HANDOFF.md、commit/push、停止

**以下行动不得询问用户，必须直接执行（不论是否跨 workstream）：**

- 写 plan/spec → 这是 plan/spec only，不是大拆实现，直接进入（包括新 workstream 的第一步 spec/plan）
- review output and choose next loop → 这是 `/mf-autopilot` 的职责，直接执行
- 更新 CURRENT_PROJECT_STATE / progress-ledger → 每轮必须做的治理动作，直接执行
- 跑 gates 和 commit/push → loop 收口动作，直接执行

### 5.9 Banned soft-stop phrases

以下语句**禁止**作为最终停止理由出现在报告或输出中：

- "是否继续？"
- "等待用户指令"
- "建议下一步是 X"（如果是 auto-continue 范围，必须直接执行 X，不写这句话然后停止）
- "可以进入 X"
- "是否要我继续？"
- "需要我继续吗？"
- "要不要我…"
- "准备好了就告诉我"
- "不是 auto-continue 范围"（如果实际下一步在 §5.7 auto-continue 表中）
- "需独立 spec/plan 后执行"（spec/plan 编写本身就是 auto-continue 动作）
- "这是新 workstream"（新 workstream 的 spec/plan/boundary-tests/audit 仍是 auto-continue）
- "新 workstream，不是 auto-continue 范围"（同上 — 组合形式也在禁止之列）
- "需独立 spec/plan 后进入实现"（同上 — plan/spec 编写就是下一步）
- "下一步是 X" 后面没有紧跟 `ACTION: CONTINUE_NEXT_LOOP` 并实际继续执行

如果报告写了"下一步是 X"且 X 在 auto-continue 范围内，**必须立即执行 X**，不得在报告后停下。

只有在伴随明确 `ACTION: HARD_STOP_<CODE>` 或 `ACTION: HANDOFF_AND_STOP` 时，才允许停止。有效停止格式：

```
ACTION: HARD_STOP_PRODUCT_DECISION
Reason: <具体原因，说明为什么不能从 roadmap/spec/plan 推断>
```

---

## 6. 允许自动继续的范围

以下范围 Agent 可以自主决定并执行，无需用户确认：

- Roadmap 中的 v0.3 / v0.x 全部工作
- Card Quality / Wiki Quality
- Source Location / Provenance
- Related Cards API（轻量/确定性/非 embedding）
- Knowledge Health
- Local Graph（轻量/确定性/非 vector DB）
- Backend service 层实现
- Web API schema 扩展
- Strategy / policy / presenter / service 层实现
- Python tests / scripts / browser smoke / fake dogfood
- Web UX / i18n / copy / Wiki / Library / Card UI
- `docs/` 文档编写和更新
- Implementation notes 编写
- Roadmap / spec / plan 更新

---

## 7. Stop Conditions（唯一权威来源）

所有 Hard Stop 和 Non-Stop 条件以此节为准。§5.4、§5.7、§5.8 中的停止判断必须引用本节。

### 7.1 Hard Stop Conditions（触发时必须停止）

| Code | 触发条件 |
|------|---------|
| `HARD_STOP_SECRET` | 需要真实 API key / secrets / 读取 `.env` |
| `HARD_STOP_REAL_LLM` | 需要调用真实 LLM / Cubox / Upstage（除非用户明确进入真实 dogfood） |
| `HARD_STOP_PRIVATE_DATA` | 需要处理真实私人资料 |
| `HARD_STOP_OBSIDIAN_WRITE` | 需要写真实 Obsidian vault |
| `HARD_STOP_MAIL_STORAGE` | 需要 mail storage / email / mail 实现 |
| `HARD_STOP_RAG_EMBEDDING` | 需要 RAG / embedding / vector DB |
| `HARD_STOP_LARGE_DEPENDENCY` | 需要新增大型框架 / 重依赖（除非 spec 明确批准） |
| `HARD_STOP_APPROVAL_SEMANTICS` | 改变 explicit approval / human_approved 安全语义 / 引入 auto approve |
| `HARD_STOP_PRODUCT_DECISION` | 产品判断真正模糊不清，无法从 roadmap/spec/plan 推断 |
| `HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN` | context 低于安全阈值，已写 handoff |
| `HARD_STOP_P0_P1_RETRY_EXCEEDED` | P0/P1 超过 2 轮回退上限 |
| `HARD_STOP_GIT_UNSAFE_STATE` | git 状态不安全（非 clean、非 fast-forward） |
| `HARD_STOP_DESTRUCTIVE` | force push / tag / release / 破坏性数据迁移 / 不可逆操作 |

### 7.2 Non-Stop Conditions（以下明确不触发停止）

以下所有情况**不是停止条件**，Autopilot 必须继续：

- loop 成功完成
- commit/push 完成
- spec/plan/docs 写完
- gate 通过
- review 完成
- 技能阶段完成
- queue empty（继续 discovery 直到真正无 safe candidate）
- 单个 candidate blocked/deferred
- 需要新增 branch point / RuntimeActionType / handler / catalog entry（触发 Architecture Extension Loop）
- 需要架构设计（触发 Architecture Extension Loop）
- 完成 3 个 loops（继续 discovery）
- 所有剩余候选都需要架构扩展（逐个评估，进入 Architecture Extension Loop）
- 普通 backend 改动 / Web API 改动 / schema 新增
- Service / strategy / policy / presenter 工作
- Tests / scripts / docs
- 本地确定性图谱或关系计算（不使用 embedding/RAG/vector DB）
- 选择/切换技能
- 输出 "next recommended loop"
- workstream 切换后的第一个 spec/plan/audit

---

## 8. Gate 规则

必须真实运行并报告 exit code，不得伪造：

| 改动类型 | Gate |
|----------|------|
| docs-only | `git diff --check` |
| Web 前端 | `npm --prefix web run build` + `python -m pytest tests/test_web_product_copy.py -q` + `git diff --check` |
| Python 后端 | `./scripts/check.sh` 或 `ruff check src tests && pytest -q` |
| 前后端混合 | 上述全部 gate |
| UI 改动 | 上述 gate + Browser MCP / Playwright smoke |

**硬性规则：**
- timeout 不能算 pass
- 不能隐藏 exit code
- 不能把 code-level review 伪装成 browser smoke
- gate 不通过不得 commit

### 8.1 Gate evidence rule

不得使用 `tail`、`head` 或截断的命令输出来证明 gate passed。

每个 gate 必须报告：
- 精确的完整命令
- 是否 timeout
- 真实 exit code
- 如果失败，失败摘要
- 如果声称 pre-existing，必须提供证据（clean tree 复现 / stash 验证 / 之前 run 记录）

禁止的表述：
- `pytest full: 0 (1 pre-existing)` — 必须说明哪个测试 pre-existing、证据是什么
- `build passed` — 必须给出 `npm --prefix web run build` 的 exit code
- timeout 后声称 passed
- 没有可见 exit code 就声称 passed

---

## 9. Commit / Push 规则

- Gate 通过后默认 fast lane commit + push main
- Commit message 格式：`<type>: <中文描述>`
- 不要开 PR（除非高风险改动触发 PR 条件）
- 不要 tag / release
- Push 后验证 `0 0` 对齐

---

## 10. 输出报告

每轮完成后必须输出以下报告：

```
## MindForge Autopilot 报告

### 当前 Repo 状态
- Branch: <branch>
- HEAD: <commit hash>
- Working tree: clean / dirty
- vs origin/main: <left> <right>

### 当前阶段判断
- 状态: <A/B/C/D/E/F/G>
- 判断依据: <简述>

### 执行 Loop
- [x] spec / plan
- [x] self-review
- [x] implementation
- [x] implementation notes
- [x] code review
- [x] gate
- [x] browser / API smoke
- [x] commit + push

### 修改文件
- <file1>
- <file2>

### Gate Exit Code
- <gate results>

### Smoke
- <结果摘要>

### Commit
- Hash: <hash>
- Push: success / failed
- 0 0 对齐: yes / no

### 继续判断
- 是否继续下一轮: yes / no
- 如果停止，stop reason: <HARD_STOP_* code — 必须是 §4.2 中的 hard-stop reason>
- 如果继续，下一步: <具体行动描述>
```

---

## 硬性禁止（始终生效）

1. 不要读取 `.env` / secrets
2. 不要调用真实 LLM / API（除非用户明确进入真实 dogfood）
3. 不要处理真实私人资料
4. 不要写真实 Obsidian vault
5. 不要做 RAG / embedding / vector DB
6. 不要做 mail storage / email / mail
7. 不要新增大型框架 / 重依赖（除非 spec 明确批准）
8. 不要 force push / tag / release
9. 不要破坏 explicit approval / human_approved 安全语义
10. 不要 auto approve
11. 不要把 API key / secrets 打印到日志、DOM、console、notes
12. 不要删除用户真实资料
13. Fast lane main: gate 通过后直接 commit + push

---

## 11. Recursive Remediation Loop

`/mf-autopilot` is **not a linear pipeline**. It is a **recursive workflow controller**.

默认流程不是：

```
plan → implement → gate → done
```

而是：

```
classify task
  → choose entrypoint
  → Skill Framework Discovery（§15）
  → choose required skills（§14 + §15）
  → execute current node
  → review output（§17）
  → classify failure if any（§12）
  → route backward to the correct earlier node
  → re-run
  → gate（§8）
  → update state
  → Post-Loop Self-Routing（§18）
  → continue next loop
```

如果 review / gate / audit 不通过，**不能简单停，也不能继续往后硬跑**。必须判断失败属于哪个阶段（§12），然后回退到对应阶段重做。

**Remediation precedence（回退优先级）：**

| 优先级 | 回退目标 | 触发条件 |
|--------|---------|---------|
| 1 (最浅) | 同阶段 fix | 小范围 bug、lint、单测失败 |
| 2 | 上一阶段 | plan 偏差、实现方向错 |
| 3 | spec/plan | 目标不清、scope 膨胀 |
| 4 (最深) | 产品决策 | 产品方向冲突、价值不清 |

回退时从浅到深尝试。浅层能修就不深层回退。但如果根因在深层，必须跳过硬推。

---

## 12. Failure Classification Table

| # | Failure Class | 触发条件 | 回退目标 | 特殊动作 |
|---|--------------|---------|---------|---------|
| 1 | **spec_failure** | 目标不清、acceptance criteria 不清、product decision 不清、用户价值不清、scope 膨胀、non-goals 不清 | spec/plan stage | 产品方向不清 → `/brainstorming` 或 `/office-hours`；仍需用户选择 → `HARD_STOP_PRODUCT_DECISION` |
| 2 | **plan_failure** | plan 没有 slice、没有 gates、没有 rollback、会造成大重构、没有说明风险、没有明确技能选择 | plan rewrite | architecture/engineering → `/plan-eng-review`；design → `/plan-design-review`；Compound Engineering/G-stack 考虑 |
| 3 | **design_failure** | UI 方向不清、visual hierarchy 不清、design review 不通过、页面漂亮但不好用、设计不符合产品定位 | design stage | direction unclear → `/design-consultation`；variants needed → `/design-shotgun`；choosing → `/plan-design-review`；`/design-html` only after direction locked；`/design-review` after implementation |
| 4 | **architecture_failure** | cross-module coupling increases、mechanical file splitting、new God object、new premature abstraction、API contract breaks、lab/internal pollutes main path、explicit approval semantics risk | architecture audit | → `/plan-eng-review` → boundary tests → smaller slice；考虑 Compound Engineering/G-stack；implementation only after plan passes |
| 5 | **implementation_failure** | tests fail、build fails、lint fails、behavior mismatch、bug persists、new regression introduced | inspect/reproduce | → focused fix → targeted tests → rerun gates；do NOT rewrite unrelated modules |
| 6 | **gate_failure** | any gate exit non-zero、timeout、no visible exit code、truncated output used as proof、flaky gate without evidence | diagnose gate | → fix root cause → rerun exact gate → update notes；`HARD_STOP` only after retry limit (§13) or unsafe state |
| 7 | **review_failure** | self-review finds mismatch、design-review fails、plan-eng-review fails、codex/adversarial review finds P0/P1/P2、audit says feature is misleading | earliest mismatched stage | spec if goal wrong、plan if approach wrong、implementation if code wrong、docs if truth drift |
| 8 | **docs_truth_failure** | docs overclaim、docs contradict code、current state stale、progress-ledger stale、old docs mislead agent | docs_cleanup entrypoint | → code-truth check → update CPS/progress-ledger；do NOT continue feature work until current truth is clear |
| 9 | **skill_routing_failure** | required skill not invoked、wrong skill used、heavy skill for trivial fix、design without design review、architecture change without plan-eng-review、available framework not checked（§15） | Skill Routing Decision node | → invoke required skill → document result → resume workflow；remediation routing must re-check Compound Engineering/G-stack/Superpowers（§15.5） |

---

## 13. Retry / Escalation Policy

- Each remediation loop may retry up to **2 times** by default.
- If same P0/P1 failure persists after 2 focused retries → `HARD_STOP_P0_P1_RETRY_EXCEEDED`.
- P2/P3 may be **deferred** if documented in implementation notes and not blocking current loop.
- **Never** hide a failed gate by reclassifying it as pass.
- **Never** continue after failed safety/approval gate.
- **Never** continue after git unsafe state (`HARD_STOP_GIT_UNSAFE_STATE`).
- If failure class is `architecture_failure`、`plan_failure`、`implementation_failure` across modules、or `gate_failure` across multiple gates, remediation routing **must re-check Compound Engineering / G-stack / Superpowers before retry**（§15.5）。

---

## 14. Mandatory Skill Gates

Skill routing is **mandatory**, not advisory, for certain task classes.

### 14.1 Product / strategy tasks

**触发信号:** 新产品方向、是否值得做、用户会不会喜欢、竞争力/创新力、PMF 假设、目标用户不清

**必须触发:**
- `/brainstorming`
- `/office-hours` if demand/positioning is unclear

未触发 → `skill_routing_failure`，必须回退。

### 14.2 Architecture / engineering tasks

**触发信号:** cross-module refactor、web_facade/schemas/service boundary、new subsystem、major dependency direction、architecture debt、maintainability

**必须触发:**
- `/plan-eng-review`
- Compound Engineering / G-stack if available and suitable（§15.2）
- architecture boundary tests before implementation

无 plan-eng-review 就直接大改 → `skill_routing_failure`（workflow violation）。

### 14.3 Web / design tasks

**触发信号:** 视觉方向、页面 redesign、design system、style exploration、information architecture、用户友好性大改

**必须按阶段触发:**
- unclear direction → `/design-consultation`
- variants needed → `/design-shotgun`
- choosing direction → `/plan-design-review`
- static high fidelity → `/design-html`
- implemented UI QA → `/design-review`

实现 UI redesign 后无 design-review → `review_failure`。

### 14.4 Audit / red-team tasks

**触发信号:** independent audit、adversarial review、"are we fooling ourselves?"、safety/approval semantics、global product/architecture honesty

**必须触发:**
- `/codex:adversarial-review` if available
- or external Codex independent audit
- audit result lands in `docs/audits/`

Audit does NOT automatically take over active workstream unless `/mf-autopilot` later reads it and updates AUTOPILOT-QUEUE.

### 14.5 Bug fix / small P1/P2 fix

**触发信号:** clear bug、clear failing test、clear small copy drift、clear P1/P2 fix

可以直接用 `/mf-autopilot`，不要强制 heavy skills。

---

## 15. Skill Framework Discovery

每次 `/mf-autopilot` run 在选择 task entrypoint 后，必须执行 **Skill Framework Discovery**。

### 15.1 Discovery checklist

- 检查当前可用 slash commands / skills / project commands
- 特别检查:
  - **Compound Engineering** (`compound-engineering:*` / `/ce-*`)
  - **G-stack** (`/gstack-*` / `design-*` / `plan-*` / `qa*`)
  - **Superpowers** (`/brainstorming` / `/office-hours` / `/plan-eng-review` / debugging discipline)
  - `/design-consultation`、`/design-shotgun`、`/plan-design-review`、`/design-html`、`/design-review`
  - `/codex:adversarial-review`
- 如果无法自动列出 skills，必须使用 **known skill inventory fallback**，并在 Skill Routing Decision（§16）里标明 "fallback used"。

### 15.2 Compound Engineering / G-stack / Superpowers mandatory rules

如果 task type 属于以下任一类：

| Task Type | 必须检查的框架 |
|-----------|---------------|
| `architecture_refactor` | Compound Engineering、G-stack |
| `feature_implementation` (complex/cross-module) | Compound Engineering、G-stack |
| `quality_platform` | Compound Engineering、G-stack |
| `cross_module_refactor` | Compound Engineering、G-stack |
| `engineering_workflow_change` | G-stack |
| `multi-step remediation` | Compound Engineering、G-stack |
| `broad test/gate improvement` | Compound Engineering、G-stack |
| `repo-wide code quality work` | Compound Engineering、G-stack |
| `design_review` / UI work | Design skills chain（§14.3） |
| `audit_only` (independent) | Codex adversarial review |

**选择规则:**
- **Compound Engineering**: 优先用于复杂工程实施、跨模块切片、implementation loop、质量门禁组合。
- **G-stack**: 优先用于 structured engineering stack / workflow / gate / plan-to-execution 类型任务。
- **Superpowers**: 优先用于需要 brainstorming、planning、debugging discipline、verification-before-completion、structured review 的任务。

如果这些框架技能 **available 且 applicable**，却没有调用 → `skill_routing_failure`。必须回退到 Skill Routing Decision node。

如果不用，必须在 Skill Routing Decision 中明确写：
- `unavailable` — 技能不可用
- `not applicable because task is trivial` — 任务简单
- `unsafe because task requires user decision` — 需要用户决策
- `lower-risk direct mf-autopilot path is sufficient` — 低风险直通路径足够

### 15.3 Mandatory Skill Gate Examples

| 场景 | 必须检查 | 必须触发 |
|------|---------|---------|
| v3.7 Quality Platform | Compound Engineering、G-stack | `/plan-eng-review` first |
| Global Architecture Quality Reset | Compound Engineering、G-stack | `/plan-eng-review` |
| Web redesign | Design skill chain | `/design-consultation` → `/plan-design-review` → `/design-review` |
| Product strategy uncertainty | Superpowers | `/brainstorming` or `/office-hours` |
| "Are we fooling ourselves?" audit | Codex adversarial review | `/codex:adversarial-review` or external Codex audit |
| Simple docs cleanup batch | No heavy skill required | — |
| Simple copy fix / failing test fix | No heavy skill required | — |

### 15.4 Compound Engineering / G-stack / Superpowers selection matrix

| Framework | Best for | Overkill for |
|-----------|----------|-------------|
| **Compound Engineering** | multi-step refactor、plan→implement→verify pipeline、cross-module quality gates | single-line fix、pure docs-only、simple lint fix |
| **G-stack** | structured review chains、design QA、plan-to-execution handoff | quick shell command、read-only audit |
| **Superpowers** | brainstorming、strategy、debugging discipline | routine commit/push、governance doc update |

### 15.5 Recursive remediation integration

如果 Review/Gate/Audit 失败且 failure class 属于:
- `architecture_failure`
- `plan_failure`
- `implementation_failure` across modules
- `gate_failure` across multiple gates

则 remediation routing **must re-check Compound Engineering / G-stack / Superpowers before retry**。不可仅原地重试。

---

## 16. Skill Routing Decision Block

每次 `/mf-autopilot` run 必须输出 **Skill Routing Decision**。

**固定格式:**

```
Skill Routing Decision:
- Task type: <bug_fix | docs_cleanup | ui_ux_polish | architecture_refactor | feature_implementation | audit_only | dogfood | design_review | autopilot_governance>
- Risk level: <low | medium | high>
- Available skill frameworks checked:
  - Compound Engineering: <available | unavailable | not applicable>
  - G-stack: <available | unavailable | not applicable>
  - Superpowers: <available | unavailable | not applicable>
  - Design skills: <available | unavailable | not applicable>
  - Codex adversarial review: <available | unavailable | not applicable>
- Required skill(s): <list | none>
- Selected skill(s): <list | none>
- Skills deliberately not used: <list | none>
- Reason: <why not used if applicable>
- If required skill not invoked, why not: <explanation | N/A>
- Next entrypoint: <entrypoint name>
```

**规则:**
- 如果 Required skill(s) 非空但 Selected skill(s) 为空 → `skill_routing_failure`，不得继续实现。
- 除非明确说明 skill unavailable AND fallback path documented。
- **低风险 task 允许简化输出**：`docs_cleanup`、`bug_fix`（单文件小修）、`autopilot_governance`（小范围规则更新）、`audit_only`（只读）可缩写为 3 行：
  ```
  Skill Routing: <task_type>, risk=<low>, required=<none|X>, selected=<none|X>. No framework needed — <reason>.
  ```
  如果 `required` 非空或风险为 medium/high，必须使用完整 11 行格式。

---

## 17. Review Node Rules

每个 loop 必须有 **review node**，不只是 gates。

| Task Type | Review Node | Failure Handling |
|-----------|------------|-----------------|
| `docs_cleanup` | docs truth review | → `docs_truth_failure` → §12 #8 |
| `bug_fix` | regression review | → `implementation_failure` → §12 #5 |
| `ui_ux_polish` | browser/MCP or design review | → `design_failure` → §12 #3 |
| `design_review` | `/design-review` | → `design_failure` → §12 #3 |
| `architecture_refactor` | `/plan-eng-review` + boundary review | → `architecture_failure` → §12 #4 |
| `feature_implementation` | spec acceptance review | → `spec_failure` or `implementation_failure` → §12 #1 or #5 |
| `dogfood` | dogfood evidence review | → `review_failure` → §12 #7 |
| `audit_only` | evidence sufficiency review | → `review_failure` → §12 #7 |
| `autopilot_governance` | governance self-review | → `plan_failure` or `docs_truth_failure` → §12 #2 or #8 |

**如果 review node fails:**
- 必须回退到对应阶段
- **不得 commit/push as success**
- 必须在 Post-Loop Self-Routing（§18）中记录 Review result = FAIL/PARTIAL

---

## 18. Post-Loop Self-Routing Block

每个 loop 最终输出前必须执行 **Post-Loop Self-Routing Block**。

**固定格式:**

```
Post-loop Self-Routing:
- Completed loop: <loop description>
- Review result: PASS | FAIL | PARTIAL
- Gate result: PASS | FAIL | PARTIAL
- Failure class if any: <spec_failure | plan_failure | design_failure | architecture_failure | implementation_failure | gate_failure | review_failure | docs_truth_failure | skill_routing_failure | none>
- Remediation target: <which stage to go back to | none>
- Next loop candidate: <description>
- Required skill for next loop: <list | none>
- Auto-continue allowed: yes | no
- Reason: <why yes/no>
- ACTION: CONTINUE_NEXT_LOOP | HANDOFF_AND_STOP | HARD_STOP_<CODE>
```

**规则:**
- 如果 Review result = FAIL/PARTIAL 且可自动修 → ACTION = `CONTINUE_NEXT_LOOP`，目标为 remediation loop。
- 如果 Gate result = FAIL/PARTIAL → ACTION 不得是 success stop。
- 如果 next loop is plan/spec/audit/review/safe slice → must `CONTINUE_NEXT_LOOP` unless `HARD_STOP_*`.
- Soft stop phrase banned (§5.9)。

---

## 19. CPS AUTOPILOT-QUEUE Schema

CURRENT_PROJECT_STATE.md 的 AUTOPILOT-QUEUE 每条 item 必须使用以下结构：

```html
<!-- AUTOPILOT-QUEUE-ITEM-N:
workstream=<active workstream name>
task_type=<task type from §3>
current_node=<spec | plan | design | implement | review | gate | dogfood_smoke | docs_truth>
next_action=<concrete next action description>
required_skill=<comma-separated skill list | none>
frameworks_checked=<Compound Engineering | G-stack | Superpowers | none>
review_node=<review node from §17>
failure_class=<failure class from §12 | none>
remediation_target=<stage to go back to | none>
auto_continue_allowed=<true | false>
hard_stop_required=<true | false>
-->
```

示例：

```html
<!-- AUTOPILOT-QUEUE-ITEM-1:
workstream=Product Main Path Real Dogfood v2
task_type=dogfood
current_node=dogfood_evidence_review
next_action=fix_p1_p2_or_continue_web_ux
required_skill=none
frameworks_checked=none
review_node=dogfood_evidence_review
failure_class=none
remediation_target=none
auto_continue_allowed=true
hard_stop_required=false
-->
```

---

## 20. Updated Progress Ledger Schema

progress-ledger 每条记录必须补充以下字段：

```markdown
- **Review result**: <PASS | FAIL | PARTIAL>
- **Gate result**: <PASS | FAIL | PARTIAL>
- **Failure class**: <from §12 | none>
- **Remediation action**: <what was done | none>
- **Skill frameworks checked**: <Compound Engineering / G-stack / Superpowers | none>
- **Required skill invoked**: <yes | no | N/A>
- **Evidence binding**: <finding/issue ref + commit hash + gate exit code>（§23）
- **Next ACTION token**: <CONTINUE_NEXT_LOOP | HANDOFF_AND_STOP | HARD_STOP_<CODE>>
```

---

## 21. Updated HANDOFF.md Schema

如果 context 低必须写 handoff，HANDOFF.md 必须补充：

```markdown
## Remediation Context
- Current node: <spec | plan | design | implement | review | gate | docs_truth>
- Next node: <next node name>
- Required skill: <list | none>
- Failure class: <from §12 | none>
- Remediation target: <stage | none>

## Next /mf-autopilot Instruction
\`\`\`
/mf-autopilot

继续 <workstream>。
当前位置: <current node>。
下一步: <next node + concrete action>。
Required skill: <skill name>。
\`\`\`
```

---

## 22. Updated Report Template

§10 的输出报告必须包含 Skill Routing Decision（§16）和 Post-Loop Self-Routing（§18）。

---

## 23. Claim-to-Evidence Gate

每个 RESOLVED/PASS 声称必须绑定具体证据。证据不足时只能标记 `PARTIAL`，不得标记 `RESOLVED`。

### 23.1 判定规则

| 情况 | 标记 |
|------|------|
| 所有子问题已修 + gate pass + review 通过 + 有具体 evidence | `RESOLVED` |
| 修了部分但核心问题未解决 | `PARTIAL` |
| gate pass 但无业务路径验证 | `PARTIAL` |
| 无证据仅声称 | 不得标记，先补齐证据 |

### 23.2 Evidence 绑定要求

标记 RESOLVED 前必须绑定：
1. **原始 finding/issue 引用** — 审计 finding ID 或 bug report 或 task description
2. **具体修改** — 文件路径 + commit hash
3. **Gate evidence** — exact command + exit code

缺少任一项 → 只能写 `PARTIAL`。

### 23.3 禁止的全局声称

在 Claim-to-Evidence Gate 通过前，禁止写入：
- `all P0/P1 resolved`
- `completed`
- `production-ready`

如果必须写全局状态，写：`P0/P1: N items PARTIAL, M items RESOLVED`。
