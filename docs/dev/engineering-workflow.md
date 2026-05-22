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
7. **文档即合约** — 所有 plan/spec/specification 文档生成后必须经过 `/ce-doc-review`（或等价审查）通过，才能进入实现阶段。审查未通过的文档不得作为实现依据，必须先修文档。
8. **仓库事实优先** — 仓库内 SPEC / Plan / implementation-notes / tests / commit message 才是工程事实来源。不依赖临场散装 prompt 或聊天上下文作为持久工程知识。跨会话关键决策必须沉淀到仓库文档。
9. **可回退闭环** — 工程流程不是线性流水线。每一步都可以根据证据回到上游阶段修正，而不是硬着头皮继续。Agent 必须主动判断该回到哪一步，不能等用户每次手动指挥。

---

## 可回退工程闭环

MindForge 工程流程不是一条从 SPEC → TDD → Implementation → Review → Done 的线性流水线。它是一个可以自我纠偏的闭环系统。

### 大 Loop

完整的工程闭环，每一步的输出都是下一步的输入，但任何一步发现问题都可以回到上游：

```
SPEC / Plan
    ↓
Document Review  ──→ 不通过 → 回到 SPEC/Plan
    ↓ 通过
TDD / Test Design
    ↓
Test Review  ──→ 不合理 → 回到 TDD
    ↓ 通过
Implementation
    ↓
Implementation Review  ──→ 偏离 → 回到 Implementation 或 TDD
    ↓ 通过
Debug / Remediation  ──→ 根因在上游 → 回到 SPEC/Plan 或 TDD
    ↓ 通过
Exit Code Gate  ──→ 不通过 → 回到 Implementation
    ↓ 通过
Commit / Push
```

### 每一步的小 Loop

每个阶段内部也有自己的回退循环：

| 阶段 | 小 Loop | 回退触发条件 |
|------|---------|-------------|
| SPEC/Plan | 写 → 审查 → 修正 → 再审查 | Plan review 发现 scope 不清、需求矛盾、遗漏边界 |
| TDD | 写测试 → 验证 FAIL → 写实现 → 验证 PASS → 重构 | 测试设计不合理、覆盖不足、过度耦合实现细节 |
| Implementation | 实现 → 自测 → 对照 plan 检查 | 实现发现规格缺失、需求本身有误、plan 不完整 |
| Review | 审查 → 发现问题 → 修正 → 再审查 | 实现偏离 plan、引入越界改动、破坏红线 |
| Debug | 查证据 → 定位根因 → 修正 → 回归验证 | 根因在设计层而非代码层、需要改上游文档 |

### Agent 自我纠偏规则

Coding Agent 在流程中必须遵循以下判断规则：

1. **不机械前进** — 完成当前步骤不等于"可以进入下一步"。必须先验证当前步骤的输出是否合格。
2. **证据驱动回退** — 回退到上游必须有具体证据：log、状态、测试失败、文档矛盾、review 发现。不凭直觉回退。
3. **不回退过远** — 能修测试就修测试，不回到 SPEC；能补实现就补实现，不回到 TDD。回退距离与问题根因匹配。
4. **不绕过 gate** — 回退后重新经过受影响的所有 gate，不能因为"之前通过过"就跳过。
5. **不为通过而修 case** — 不能为了让测试变绿而削弱断言、删除覆盖、放宽边界。测试失败先怀疑实现，再怀疑测试，最后怀疑 spec。
6. **不忽略 plan 错误** — 实现过程中发现 plan 本身有问题，必须回到 SPEC/Plan 修正文档，不能在代码里"将就一下"。
7. **Debug 必须查根因** — 不能把 debug 变成表面补丁。必须查日志、状态、事件链、真实证据。根因在上游时，回到上游修正，不在表面贴膏药。

### Implementation Notes 中的回退记录

每次发生跨阶段回退，implementation notes 必须记录：

- **回退到哪一步** — SPEC/Plan、TDD、Implementation、Review 中的哪一个
- **为什么回退** — 发现了什么具体证据或矛盾
- **修改了什么** — 哪个上游文档、测试文件、或实现代码被修改
- **如何验证修正** — 回退修正后跑了什么检查确认问题已解决

记录方式：写入 commit message body 或更新 plan 文档。关键回退决策同时更新两处。

### 用户介入的边界

正常运转的闭环中，Agent 应能自我驱动完成"发现问题 → 回到正确阶段 → 修正 → 再验证"的完整循环。用户介入主要发生以下场景：

| 场景 | 说明 |
|------|------|
| 流程卡住 | Agent 无法判断该回到哪一步，或回退后反复失败 |
| 风险升级 | 发现的问题涉及安全、隐私、数据完整性，需人工确认 |
| 产品判断 | 需求取舍、优先级冲突、scope 变更等非技术决策 |
| 外部确认 | 需要真实 secret、真实 API key、真实外部服务调用确认 |
| 架构分歧 | plan 和实现之间的分歧无法通过现有规则解决，需要设计决策 |

如果流程正常运转，用户不应每次手动指挥"回到 plan"或"重新跑 review"。Agent 应该根据证据主动判断并执行回退。

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

### 0.4 技能命令

MindForge 开发使用 Compound Engineering / G-Stack / Superpowers 技能体系。优先使用技能命令，不默认发散装 prompt。

| 阶段 | 技能 | 用途 |
|------|------|------|
| 需求澄清 | `/ce-brainstorm` | 产出 requirements doc（`docs/brainstorms/`） |
| 技术方案 | `/ce-plan` | 基于 requirements 产出 implementation plan（`docs/plans/`） |
| 方案审查 | `/ce-doc-review` | 对 plan/spec 做多角色审查（coherence、feasibility、security、scope） |
| 设计/UX 审查 | `plan-design-review` | 设计文档、UX 规范审查 |
| 全局路线审查 | `gstack:geo_review` | 跨里程碑架构/产品路线审计 |
| 代码审查 | `/ce-code-review` | 对 commit/PR 做 post-merge 或多角色代码审查 |
| 实现执行 | `/ce-work` | 按已通过 review 的 SPEC/Plan 执行 TDD 实现 |

技能调用顺序：`/ce-brainstorm` → `/ce-plan` → `/ce-doc-review` → `/ce-work`。`/ce-code-review` 在 commit 后或 PR 前独立运行。`plan-design-review` 和 `gstack:geo_review` 按需触发。

---

## Phase 1: 实现

大型 plan 推荐通过 `/ce-work` 调度执行（自动 TDD → 实现 → 验证）；小型改动手动按 1.1 的 TDD 循环执行。

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

推荐使用 `./scripts/check.sh` 作为统一本地 push gate（等价于 full pytest + ruff + git diff --check）。该脚本不读取 `.env`、不调用真实 provider。前端改动需额外运行 `npm --prefix web run build`。详见 [Testing Guide](testing.md)。

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

### 2.4 纯文档改动 Gate

仅修改 `docs/` 文件、不改代码时：
- 至少运行 `git diff --check`
- 若文档影响可执行流程、CLI 命令、release 步骤或 testing 指南，按影响范围运行对应验证
- 不要求所有纯文档改动都 full pytest

### 2.5 Gate 失败处理

- exit code 非 0 → 停止，修复，重新验证
- build timeout → 证据不足，不能声称通过，需排查原因
- 禁止跳过 gate 直接 commit

---

## Phase 3: Commit & Push

### 3.1 Fast Lane（默认）

适用条件（全部满足即可走 fast lane）：
- 个人项目，无其他活跃贡献者
- 改动在 `web/src/`、`docs/`、`tests/`（仅前端测试）范围内
- 不改后端 `src/` 语义
- 不改 API contract（破坏性）
- 不触碰安全敏感路径
- 不改 CI / release / packaging 配置
- 非架构重构
- 非大范围 Web 重设计

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
- 改 workspace/runtime state 路径安全
- 涉及真实数据或隐私
- 多人协作冲突风险
- 破坏性 UI 架构变更
- 改 CI / release / packaging
- 架构重构

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
