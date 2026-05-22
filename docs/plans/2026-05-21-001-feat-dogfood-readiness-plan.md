---
title: "feat: Non-sensitive dogfood readiness — fake-provider end-to-end loop"
type: feat
status: active
date: 2026-05-21
---

# feat: Non-sensitive Dogfood Readiness Plan

## Summary

确认并补齐 MindForge 在 fake/safe local 路径下跑通完整非敏感 dogfood 闭环的能力：非敏感 markdown → import/process → ai_draft → review → approve/reject → recall/search。当前核心管线已就位但缺少三个小补丁——一个可直接使用的 dogfood config（fake provider）、一个一键 smoke 脚本、以及对应的文档入口。本轮只补这三个缺口，不改管线逻辑。

---

## Problem Frame

MindForge 已完成稳定性收口（4 个 push 上的 commit，全量 pytest=0、ruff=0、diff-check=0），现在需要验证它能否在完全不依赖真实 LLM、不读 .env、不接触私人资料的前提下跑通完整知识加工闭环。当前已有所有必要组件（FakeProvider、PlainMarkdownAdapter、approval 安全边界、BM25 recall），但缺少一个把组件串起来的 dogfood 配置和一键入口。

---

## Requirements

- R1. 用户能在不配置任何 API key 的前提下跑通完整 dogfood 闭环
- R2. dogfood 闭环覆盖：import → process → ai_draft → review → approve → recall/search
- R3. 所有步骤不调用真实 LLM、不读 .env、不接触私人资料
- R4. ai_draft 不会被自动提升为 human_approved
- R5. 提供可重复执行的一键 smoke 脚本
- R6. 有对应文档入口说明 dogfood 使用方法

---

## Scope Boundaries

- 不新增 CLI 命令
- 不修改 provider / adapter / approval / recall 管线逻辑
- 不修改 `src/mindforge/assets/configs/mindforge.yaml`（那是 init 模板，不是 dogfood config）
- 不改 Web UI
- 不新增依赖
- 不做 RAG / embedding / vector DB

### Deferred to Follow-Up Work

- Demo provider 生成更丰富非 `[fake]` 前缀的占位内容：属于后续 product decision，需先确定语义边界
- `mindforge dogfood` 子命令：当前用脚本已足够，CLI 集成留到有明确用户需求时再做

---

## Context & Research

### Relevant Code and Patterns

- `src/mindforge/llm/fake.py` — FakeProvider，确定性、零网络、零密钥
- `src/mindforge/sources/markdown_adapter.py` — PlainMarkdownAdapter，处理 .md 文件
- `src/mindforge/approval_cli.py` + `src/mindforge/approve_presenter.py` — approve 安全边界，必须 `--confirm`
- `src/mindforge/recall_index_cli.py` — BM25 本地检索 + `index rebuild`
- `src/mindforge/cli.py` — 所有 CLI 命令注册入口
- `examples/fixture-vault/` — 已有合成 sample vault（含 ai_draft + human_approved 卡片）
- `tests/test_onboarding_smoke.py` — 10 步 CLI smoke test（pytest，非独立脚本）
- `scripts/check.sh` — 已有 push gate 脚本，dogfood smoke 脚本应遵循相同模式

### Institutional Learnings

- `docs/internal/product-contracts.md`：fake provider 是默认安全路径，real provider 只能 opt-in
- `docs/internal/ROADMAP_COMPLETION_LEDGER.md`：声明 "MindForge is clean enough for long-term local use on non-sensitive or project-only data"
- `docs/internal/V0_3_DEVELOPMENT_RULES.md`：禁止自动 mutation，禁止新增依赖

### External References

无（本轮不需要外部研究）。

---

## Key Technical Decisions

- **Dogfood config 放在 `examples/dogfood/` 而非覆盖默认 config**：默认 config 是 `init` 模板，修改它会改变新用户 onboarding 行为。Dogfood config 是独立文件，通过 `--config` 传入，不干扰生产路径
- **Smoke 脚本用 bash 而非 pytest**：`test_onboarding_smoke.py` 已覆盖 pytest 路径；bash 脚本面向想快速手动验证的开发者，互补不替代
- **Sample data 复用 `examples/fixture-vault/`**：已存在、已验证、非敏感；不需要新建
- **不改 FakeProvider 输出内容**：`[fake]` 前缀是安全特性——它让 fake 输出一眼可辨，防止误认为真实 AI 生成内容

---

## Open Questions

### Resolved During Planning

- 是否需要新增 CLI 命令？→ 不需要，现有命令足够
- 是否需要新增 sample data？→ 不需要，`examples/fixture-vault/` 已足够
- 是否需要改默认 config？→ 不需要，dogfood config 独立放置

### Deferred to Implementation

- Dogfood config 中 vault root 指向哪里？→ 实现时用 `/tmp/mindforge-dogfood-vault`，与 testing.md 的 smoke 指南一致
- Smoke 脚本是否需覆盖 wiki rebuild？→ 实现时判断：wiki rebuild 走 fake provider 可产出占位内容，加入会增加脚本运行时间但完整性更好；初始版本可先不加，标注为 optional

---

## Implementation Units

### U1. Dogfood config — fake provider YAML

**Goal:** 创建一个开箱即用的 dogfood config，预配置 fake provider，无需 API key

**Requirements:** R1, R3

**Dependencies:** None

**Files:**
- Create: `examples/dogfood/mindforge.dogfood.yaml`

**Approach:**
- 从 `src/mindforge/assets/configs/mindforge.yaml` 的结构出发，只改 `llm` 块
- `default_model: fake-main`
- `models` 下配置一个 `type: fake` 的模型，`routing` 所有 stage 指向该模型
- `vault.root` 指向 `/tmp/mindforge-dogfood-vault`
- `state.workdir` 指向 `/tmp/mindforge-dogfood-state`（避免污染项目根目录 `.mindforge`，见 `config.py:802` workdir 解析起点为 `Path.cwd()`）
- `telemetry.enabled: false`
- 文件头加注释说明这是 dogfood 专用、不含 secret、不连接外部服务
- 放在 `examples/dogfood/` 而非 `src/mindforge/assets/`——避免和 init 模板混淆
- 注意：`default_model` + `models` + `routing` 是现代 config 格式，不能同时使用 `profiles`（遗留格式），否则 profiles 会被 parser 静默忽略（见 `config.py:990` 的格式路由）

**Patterns to follow:**
- `src/mindforge/assets/configs/mindforge.yaml` — 结构参照，llm 块替换为 fake
- `tests/test_v0_2_6.py:221-224` — 验证 `default_model` 存在时 `profiles` 不出现在输出中，parser 格式互斥

**Test scenarios:**
- Happy path: `mindforge status --config examples/dogfood/mindforge.dogfood.yaml` 不报错
- Happy path: `mindforge scan --config ...` 正常扫描 inbox
- Happy path: `mindforge process --config ...` 使用 fake provider 生成 ai_draft，不发起 HTTP 请求
- Error path: 不存在的 config 路径返回清晰错误

**Test expectation:** `test_onboarding_smoke.py` 已有覆盖，不需要新增测试文件；dogfood smoke 脚本（U3）作为手动验证入口

**Verification:**
- `mindforge doctor --config examples/dogfood/mindforge.dogfood.yaml` exit_code=0
- `mindforge status --config ...` 显示 fake profile 信息

---

### U2. Dogfood 文档

**Goal:** 为开发者提供 dogfood 闭环的文档入口，说明如何零配置跑通完整链路

**Requirements:** R6

**Dependencies:** U1

**Files:**
- Create: `docs/dogfood.md`

**Approach:**
- 简短说明 dogfood 的目标：验证管线在 fake provider 下能跑通
- 列出前置条件（Python >=3.11、已 `pip install -e .`）
- 给出命令序列草案
- 明确说明 fake provider 不调用真实 LLM、不读 .env
- 指向 `scripts/dogfood_smoke.sh` 一键脚本
- 中文书写，与现有 docs 风格一致
- 不重复 README 的完整功能说明——只聚焦 dogfood 闭环

**Patterns to follow:**
- `docs/dev/testing.md` — 简洁、命令驱动、有安全说明
- `README.md` 的 "快速开始" 节——命令格式和注释风格

**Test scenarios:**
- 文档本身不需要测试；但文档中的命令序列应可逐条执行

**Verification:**
- 按文档步骤操作，能跑通完整 dogfood 闭环

---

### U3. Dogfood smoke 脚本

**Goal:** 提供一键 dogfood smoke 脚本，覆盖 markdown import → process → approve → recall 闭环

**Requirements:** R1, R2, R3, R4, R5

**Dependencies:** U1

**Files:**
- Create: `scripts/dogfood_smoke.sh`

**Approach:**
- 使用 bash，`set -euo pipefail`，与 `scripts/check.sh` 风格一致
- 在 `/tmp` 下创建临时 workspace（脚本开头 `rm -rf` 清理上次残留），脚本结束后不清理（方便检查产出）
- 步骤：清理旧 workspace → 创建目录结构 → 写入 sample markdown（包含可搜索关键词如 "checkpoint runtime 非敏感测试"）→ scan → process → 检查卡片 status=ai_draft（验证 R4：未自动提升为 human_approved）→ approve list → approve --confirm → 确认卡片 status=human_approved → index rebuild → recall --query "checkpoint runtime"
- 每步打印清晰标题，失败时打印预期 vs 实际
- 中文注释说明安全边界（不联网、不读 .env、fake provider）
- exit code 明确：任何一步失败则非零退出
- 不依赖 `examples/fixture-vault/`（那是 Obsidian vault 结构），直接在 `/tmp` 创建简单 markdown

**Patterns to follow:**
- `scripts/check.sh` — bash 风格、`set -euo pipefail`、带编号步骤、中文注释

**Test scenarios:**
- Happy path: `./scripts/dogfood_smoke.sh` exit_code=0，完整链路通过
- Error path: 缺少 `mindforge` 命令时给出清晰提示

**Verification:**
- `./scripts/dogfood_smoke.sh` 成功执行，exit_code=0
- process 后输出中确认卡片 status=ai_draft（未被自动提升）
- approve 后卡片 status 变为 human_approved
- recall --query "checkpoint runtime" 返回已审批卡片，结果非空

---

## System-Wide Impact

- **Interaction graph:** 无回调/中间件变更。dogfood config 和 smoke 脚本都是独立新增文件
- **Error propagation:** 无影响——不改管线逻辑
- **State lifecycle risks:** smoke 脚本在 `/tmp` 下操作，不与真实 workspace 交互
- **API surface parity:** 无 CLI 变更
- **Integration coverage:** smoke 脚本本身就是集成验证
- **Unchanged invariants:** FakeProvider、PlainMarkdownAdapter、approval service、recall index——所有管线组件不变

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| dogfood config 的 vault.root 硬编码 `/tmp` 路径在某些环境不可写 | 脚本在 `/tmp` 下创建，如果 `/tmp` 不可写则脚本提前失败并给出提示 |
| FakeProvider 输出 `[fake]` 前缀内容，对初次 dogfood 用户可能造成困惑 | docs/dogfood.md 和脚本注释明确说明这是预期行为 |
| smoke 脚本可能与已有 test_onboarding_smoke.py 产生竞态 | smoke 脚本使用独立 `/tmp` 路径，不与 pytest tmp_path 重叠 |
| `--config` 是 fake/real LLM 之间的唯一未设防边界——忘记传 `--config` 则静默回退到默认 config（可能使用真实 provider） | smoke 脚本开头检查 `MINDFORGE_CONFIG` 或验证当前 provider 为 fake；docs/dogfood.md 明确说明必须传 `--config` |

---

## Documentation / Operational Notes

- `docs/dogfood.md` 新增，作为 dogfood 的统一文档入口
- `docs/dev/testing.md` 可能需要在 "Local Push Gate" 旁边加一行指向 `scripts/dogfood_smoke.sh`
- 不需要改 README——dogfood 是开发者/维护者工具，不是用户功能

---

## Sources & References

- `src/mindforge/llm/fake.py` — FakeProvider 实现
- `src/mindforge/assets/configs/mindforge.yaml` — 默认 config 模板
- `examples/fixture-vault/` — 已有合成 sample vault
- `tests/test_onboarding_smoke.py` — 已有 CLI smoke test
- `scripts/check.sh` — push gate 脚本（dogfood smoke 脚本的风格参考）
- `docs/dev/testing.md` — 已有测试文档
- `docs/internal/product-contracts.md` — 安全契约
