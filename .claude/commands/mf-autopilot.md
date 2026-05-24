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

---

## 2. 读取工程宪法和路线

必须读取以下文件（按顺序）：

1. `docs/dev/engineering-workflow.md`
2. `docs/design/roadmap/` 下最新 roadmap 文件
3. `docs/plans/` 下最新 active plan 文件
4. `docs/specs/` 下最近最新的 spec 文件
5. `docs/implementation-notes/` 下最新的 notes / handoff 文件
6. `docs/dev/copy-policy.md`

---

## 3. 自动判断当前阶段

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

## 4. 自动跑完整 Loop

只要没有触发停止条件，Agent 必须自己完成以下循环：

```
spec / plan
  → self-review（对照 spec checklist 自审）
  → implementation（按 spec 的 implementation units 逐个实现）
  → implementation notes（记录非显而易见的决策、边界权衡、已知限制）
  → code review（对照 spec 检查 scope、红线、正确性）
  → gate（真实运行 exit code gate）
  → browser / API smoke
  → commit + push main
  → 判断下一阶段
  → 继续下一轮
```

**关键纪律：**
- 不在每个 milestone 完成后停下来问用户
- 不在 gate 通过后停下来问用户是否 commit
- 不在 commit 后停下来问用户是否继续
- 只有触发 §6 的停止条件时才停

### 4.1 Auto-continue contract

如果最终报告能写出明确的下一步行动，Autopilot 必须立即进入下一步，不得停止。

明确的下一步行动包括但不限于：
- "继续 U2"
- "下一个 milestone 是 X"
- "实现下一个 roadmap item"
- "写下一个 spec"
- "跑下一个 smoke"

禁止输出"下一步是 X"然后停止。

**commit/push 不是停止点，是检查点。** commit/push 后，Autopilot 必须：
1. 重新建立工程事实（git status、branch、log）
2. 按需重新读取活跃 roadmap/spec/notes
3. 判断是否存在 hard-stop
4. 如无 hard-stop，继续下一轮

### 4.2 Stop reason must be explicit

如果 Autopilot 停止，必须输出以下其中一个 stop reason：

- `HARD_STOP_SECRET` — 需要真实 API key / secrets
- `HARD_STOP_REAL_LLM` — 需要调用真实 LLM / Cubox / Upstage
- `HARD_STOP_PRIVATE_DATA` — 需要处理真实私人资料
- `HARD_STOP_OBSIDIAN_WRITE` — 需要写真实 Obsidian vault
- `HARD_STOP_MAIL_STORAGE` — 需要 mail storage / email / mail
- `HARD_STOP_RAG_EMBEDDING` — 需要 RAG / embedding / vector DB
- `HARD_STOP_LARGE_DEPENDENCY` — 需要新增大型框架 / 重依赖
- `HARD_STOP_APPROVAL_SEMANTICS` — 改变 explicit approval / human_approved 安全语义
- `HARD_STOP_PRODUCT_DECISION` — 产品判断真正模糊不清，无法从 roadmap/spec/plan 推断
- `HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN` — context 低于安全阈值，已写 handoff
- `HARD_STOP_P0_P1_RETRY_EXCEEDED` — P0/P1 超过 2 轮回退上限
- `HARD_STOP_GIT_UNSAFE_STATE` — git 状态不安全（非 clean、非 fast-forward）

如果以上无一适用，Autopilot 必须继续。

### 4.3 Context policy

根据 context 剩余比例决定行为：

| Context | 行为 |
|---------|------|
| ≥ 15% | 正常执行，可开始新实现单元 |
| < 15% | 不开始大型新实现单元（除非小且边界清晰） |
| < 10% | 只完成当前单元、跑 gate、写 notes/handoff、commit/push |
| < 5% | 立即写 handoff、跑最小 gate、commit/push、停止并输出 `HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN` |

不要仅因为 milestone 完成就停止。不要因为 context 低就停在口头报告——必须写 handoff 文档落地。

---

## 5. 允许自动继续的范围

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

## 6. 全局硬红线（始终生效）

只有以下情况才停止并询问用户：

1. 需要真实 API key / secrets
2. 需要读取 `.env` / secrets
3. 需要调用真实 LLM / Cubox / Upstage（除非用户明确进入真实 dogfood 并在 Web 里自己配置 API key）
4. 需要处理真实私人资料
5. 需要写真实 Obsidian vault
6. 需要 mail storage / email / mail 实现
7. 需要 RAG / embedding / vector DB
8. 需要新增大型框架 / 重依赖（除非先写 spec 明确说明必要性）
9. 需要 force push / tag / release
10. 需要破坏性数据迁移
11. 改变 explicit approval / human_approved 核心安全语义
12. 引入 auto approve
13. P0/P1 无法在 2 次回退内关闭
14. 同一问题超过回退上限（2 轮）
15. 产品判断真正模糊不清，无法从 roadmap/spec/plan 推断

### 不视为停止条件

以下**不**触发停止：

- 普通 backend 改动
- 普通 Web API 改动
- 普通 schema 新增
- Service / strategy / policy / presenter 工作
- Tests / scripts / docs
- Roadmap 定义的 v0.3 工作
- 活跃 spec 要求的前后端集成
- 本地确定性图谱或关系计算（不使用 embedding/RAG/vector DB）

---

## 7. Gate 规则

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

### 7.1 Gate evidence rule

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

## 8. Commit / Push 规则

- Gate 通过后默认 fast lane commit + push main
- Commit message 格式：`<type>: <中文描述>`
- 不要开 PR（除非高风险改动触发 PR 条件）
- 不要 tag / release
- Push 后验证 `0 0` 对齐

---

## 9. 输出报告

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
