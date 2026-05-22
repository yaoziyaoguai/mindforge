# Engineering Workflow

MindForge 日常开发流程。本文档固定 SPEC/Plan 优先、TDD/SDD、implementation-notes、exit-code gate、fast lane commit/push main、仅高风险才 PR 的工程纪律。

---

## 原则

1. **SPEC/Plan 优先** — 任何非 trivial 改动（>3 文件、涉及架构决策、影响多页面/多模块）必须先写 spec 或 plan 文档，再写代码。
2. **TDD/SDD** — 先定义期望行为（测试用例或 spec 断言），再实现。不写"看起来能跑"的代码。
3. **Implementation Notes** — 实现过程中产生的非显而易见决策、边界权衡、已知限制，写入 plan 文档或 commit message body，不靠口头传递。
4. **Exit Code Gate** — 任何 commit 前必须通过 build + diff check，exit code 非 0 不得 commit。
5. **Fast Lane Main** — 个人项目走 fast lane：直接在 main 上 commit + push，不创建 feature 分支，不开 PR。
6. **高风险才 PR** — 仅以下情况走 PR 流程：多人协作、跨团队改动、破坏性 API 变更、安全敏感路径（auth/approval/secret handling）。

---

## Phase 0: 从请求到 Plan

### 0.1 判断是否需要 Plan

| 改动规模 | 动作 |
|----------|------|
| 单文件小修（typo、文案、一行修复） | 跳过 plan，直接实现 → Phase 2 |
| 2-3 文件，改动明确（如中文化、状态文案映射） | 轻量 plan：在 commit message body 写清改动范围 + 红线 |
| 3+ 文件，架构决策，跨模块 | 完整 plan：写入 `docs/plans/` |

### 0.2 完整 Plan 流程

1. **需求澄清**: 如需求模糊，先跑 `/ce-brainstorm` 产出一个 requirements doc (`docs/brainstorms/`)
2. **技术方案**: 跑 `/ce-plan`，基于 requirements doc 产出 implementation plan (`docs/plans/`)
3. **Plan Review**: 跑 `/ce-doc-review` 对 plan 做多角色审查（coherence、feasibility、security、scope）
4. **Plan 批准**: plan 必须包含明确的 scope boundary、implementation units、test scenarios、verification criteria

### 0.3 Plan 文档结构

每个 plan 至少包含：
- problem frame 和 scope boundary
- requirements traceability（回溯到原始需求或 brainstorm doc）
- implementation units（含 repo-relative file paths）
- test scenarios（具体到每个 unit 的 happy path / edge case / error path）
- dependencies 和 sequencing
- risks 和 non-goals

---

## Phase 1: 实现

### 1.1 TDD/SDD 执行顺序

```
1. 写测试（RED）       → 基于 plan 中的 test scenarios
2. 跑测试 → 确认 FAIL   → 测试因缺少实现而失败
3. 写最小实现（GREEN）  → 只写通过测试所需的代码
4. 跑测试 → 确认 PASS   → 全部通过
5. 重构（IMPROVE）      → 保持测试绿，改善结构
6. 验证覆盖率 ≥ 80%     → pytest --cov
```

### 1.2 Implementation Notes

实现过程中记录：
- **设计意图**: 为什么这样实现，而不是另一种方式
- **边界权衡**: 选择了哪种取舍，放弃了什么
- **已知限制**: 当前未覆盖的场景、需要后续跟进的 TODO

记录方式：
- 关键代码用中文注释（解释 WHY，不解释 WHAT）
- 非 trivial 决策写入 commit message body
- 大决策更新回 plan 文档

### 1.3 编码红线

硬性禁止（任何改动都不得触碰）：
- 读取 `.env`、secrets
- 调用真实 LLM（除非显式 opt-in dogfood）
- 处理真实私人资料
- 写真实 Obsidian vault
- 改 approval 后端语义
- 自动 approve
- 改 recall/BM25 语义
- 引入 RAG/embedding/vector DB
- 新增依赖（除非 plan 明确批准）
- 大重写架构（除非 plan 明确批准）

---

## Phase 2: Exit Code Gate

### 2.1 前端改动

```bash
npm --prefix web run build
echo "EXIT_CODE_web_build=$?"
```

`tsc -b && vite build` 必须 exit code = 0。timeout 不算通过。

### 2.2 后端改动

```bash
ruff check src tests
pytest -q
```

两者必须 exit code = 0。

### 2.3 通用检查

```bash
git diff --check
echo "EXIT_CODE_diff_check=$?"
```

必须 exit code = 0（无空白冲突）。

### 2.4 Gate 失败处理

- exit code 非 0 → 停止，修复，重新验证
- build timeout → 证据不足，不能声称通过，需排查原因
- 禁止跳过 gate 直接 commit

---

## Phase 3: Commit & Push

### 3.1 Fast Lane（默认）

适用条件（全部满足即可走 fast lane）：
- 个人项目，无其他活跃贡献者
- 改动在 `web/src/` 或 `docs/` 范围内
- 不改后端 `src/` 语义
- 不改 API contract（破坏性）
- 不触碰安全敏感路径

```bash
# 1. 同步 main
git pull --ff-only origin main

# 2. 确认 gate 通过（Phase 2）

# 3. 确认只改了预期文件
git diff --name-only

# 4. Commit
git add <files>
git commit -m "type: description"

# 5. Push
git push origin main

# 6. 验证对齐
git status --short
git rev-list --left-right --count @{u}...HEAD
# 期望输出: 0  0
```

### 3.2 Commit Message 格式

```
<type>: <中文描述>

<可选 body — 写清为什么改、边界在哪里>

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

### 3.3 PR 流程（高风险）

触发条件（满足任一即走 PR）：
- 改 `src/mindforge/` 后端核心逻辑
- 改 API contract（新增/删除/重命名字段、改 endpoint 签名）
- 改 approval 流程
- 改 secret handling
- 改 provider/model 配置语义
- 多人协作冲突风险
- 破坏性 UI 架构变更

PR 命令: `gh pr create --title "..." --body "..."`，base 为 `main`。

---

## Phase 4: 验证

### 4.1 Post-Merge Audit

重要改动合入 main 后，跑一次独立审计：

```
/ce-code-review
```

审计报告必须覆盖 commit scope、架构红线、build exit code、P0-P4 问题清单。

### 4.2 浏览器冒烟测试

前端改动（尤其是 UX 变更）必须经过浏览器手动冒烟：

1. 启动 Web: `.venv/bin/mindforge web --port 8766 --no-open`
2. 用 Browser MCP / Playwright 打开，验证关键路径
3. 检查 console error、network 4xx/5xx、API key 泄露
4. 记录 P0-P4 发现

### 4.3 验证检查清单

- [ ] `npm --prefix web run build` exit code = 0
- [ ] `git diff --check` exit code = 0
- [ ] 只改了预期文件（`git diff --name-only`）
- [ ] 浏览器冒烟通过（前端改动）
- [ ] `pytest -q` 通过（后端改动）
- [ ] `ruff check src tests` 通过（后端改动）
- [ ] 无 console error
- [ ] 无 API key/secret 泄露
- [ ] main 与 origin/main 对齐（`0 0`）

---

## 参考

- [Testing And Smoke Guide](testing.md) — 本地 push gate、dogfood smoke、real LLM dogfood
- [Release Process](release-process.md) — 版本号、发布检查清单
- [Contributing](contributing.md) — 开发环境、代码标准、项目约定
- [Design System](design-system.md) — Web 设计 token、Tailwind 语义色板
