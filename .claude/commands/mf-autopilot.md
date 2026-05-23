# MindForge Autopilot

当用户运行 `/mf-autopilot` 时，Agent 必须按以下规则自主推进工程工作，不在每个 milestone 完成后停下来问用户。

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
2. `docs/plans/2026-05-22-002-feat-web-ux-improvement-plan.md`
3. `docs/specs/` 下最近最新的 spec 文件
4. `docs/implementation-notes/` 下最新的 notes / handoff 文件
5. `docs/dev/copy-policy.md`

---

## 3. 自动判断当前阶段

Agent 必须根据工程事实和文档判断当前处于哪种状态：

| 状态 | 条件 | 动作 |
|------|------|------|
| **A** | 有已写好的 spec 但未实现 | 自审 spec → 通过后实现 |
| **B** | 有 implementation 但未 review / smoke | 做 post-merge review / browser smoke |
| **C** | 有 P0/P1/P2 | 按 evidence 回退修复，最多 2 轮 |
| **D** | 只有 P3/P4 | 能低风险修就修；不能修则记录到 notes，不阻塞主线 |
| **E** | 一个 milestone 已完成（spec + impl + notes + review + gate + smoke 全部通过） | 不要停。读取 plan/notes，自动判断下一阶段最有价值的 milestone，写 spec 或直接进入实现 |
| **F** | 没有明确下一阶段（plan 中无 planned milestone、无 spec 草稿） | 写 next-phase planning review / spec，不要乱实现 |
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
  → browser smoke（前端改动必须浏览器冒烟）
  → commit + push main
  → 判断下一阶段
  → 继续下一轮
```

**关键纪律：**
- 不在每个 milestone 完成后停下来问用户
- 不在 gate 通过后停下来问用户是否 commit
- 不在 commit 后停下来问用户是否继续
- 只有触发 §6 的停止条件时才停

---

## 5. 允许自动继续的范围

以下范围 Agent 可以自主决定并执行，无需用户确认：

- `docs/` 文档编写和更新
- Web UX 改进（`web/src/` 范围内的组件、样式、布局）
- i18n / copy 新增和修改
- Library / Wiki / Card UI 功能
- Browser smoke 测试
- Fake dogfood（不调用真实 LLM 的功能验证）
- Product copy 合同测试（`tests/test_web_product_copy.py`）
- 低风险 Web 前端 polish
- Implementation notes 编写
- Roadmap / spec 更新
- Plan 状态更新

---

## 6. 必须停下 Ask User 的范围

只有以下情况才停止并询问用户：

- 需要真实 API key / secrets
- 需要读取 `.env` / secrets
- 需要调用真实 LLM / Cubox / Upstage
- 需要处理真实私人资料
- 需要写真实 Obsidian vault
- 需要 mail storage / email / mail 实现
- 需要 RAG / embedding / vector DB
- 需要新增大型框架 / 重依赖
- 需要改变 provider / approval / human_approved / recall / BM25 语义
- 需要新增后端 API 且 spec 没有授权
- P0/P1 无法在 2 次回退内关闭
- 同一问题超过回退上限（2 轮）
- 需要产品判断（需求取舍、优先级冲突、scope 变更）

---

## 7. Gate 规则

必须真实运行并报告 exit code，不得伪造：

| 改动类型 | Gate |
|----------|------|
| docs-only | `git diff --check` |
| Web 前端 | `npm --prefix web run build` + `python -m pytest tests/test_web_product_copy.py -q` + `git diff --check` |
| Python 后端 | `./scripts/check.sh` 或相关 pytest |
| UI 改动 | 上述 gate + Browser MCP / Playwright smoke |

**硬性规则：**
- timeout 不能算 pass
- 不能隐藏 exit code
- 不能把 code-level review 伪装成 browser smoke
- gate 不通过不得 commit

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
- [x] browser smoke
- [x] commit + push

### 修改文件
- <file1>
- <file2>

### Gate Exit Code
- npm build: <exit code>
- pytest: <exit code>
- git diff --check: <exit code>

### Browser Smoke
- <结果摘要>

### Commit
- Hash: <hash>
- Push: success / failed
- 0 0 对齐: yes / no

### 继续判断
- 是否继续下一轮: yes / no
- 如果停止，stop reason: <原因>
```

---

## 硬性禁止（始终生效）

1. 不要读取 `.env` / secrets
2. 不要调用真实 LLM / API
3. 不要处理真实私人资料
4. 不要改 provider / approval / recall / BM25 语义
5. 不要做 RAG / embedding
6. 不要新增大型框架 / npm 依赖
7. 不要 tag / release / PR
8. Fast lane main: gate 通过后直接 commit + push
