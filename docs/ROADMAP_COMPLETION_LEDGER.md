# Roadmap Completion Ledger

> Single-page status table for MindForge Roadmap. 任何想"我现在能不
> 能开始做 X"的贡献者请先看这里。规则: **本仓库内不会自动越过任
> 何 future gate。**

最近一次更新: v0.14 future-gate Pack push 之后 (HEAD = `dc14b8c`)。

## Status buckets

| Bucket | 含义 | 谁可以触发 | 输出契约 |
| --- | --- | --- | --- |
| `pushed` | 已合并到 `origin/main` 并通过质量门 | 任何贡献者 (按现有命令) | 见各能力文档 |
| `local-complete` | 完成本地, 未 push, 等下次 review | 当前 session 维护者 | 见各 commit message |
| `future-gated` | 必须先过 [V0_14_FUTURE_GATES.md](V0_14_FUTURE_GATES.md) 中的对应 gate 才能落地 | 命名 human authorizer | 永不自动 produce `human_approved` |
| `release-gated` | 必须 named human authorizer + CHANGELOG freeze + signed marker | 命名 human authorizer | 创建 git tag / public release |
| `forbidden` | 永远不实现 (与产品定位冲突) | 无 | n/a |

## Capability ledger

### v0.7 - v0.12 — Architecture & Strategy Layer

| 能力 | Bucket |
| --- | --- |
| process / approve / recall / review CLI | `pushed` |
| presenter / approval / review / recall service 抽取 | `pushed` |
| KnowledgeStrategy seam + StrategyDefinition + registry | `pushed` |
| 默认 fake provider, `active_profile=fake` | `pushed` |
| Source plugin (deterministic, in-process) | `pushed` |
| Custom strategy (declarative-only, no executable) | `pushed` |

### v0.13 — Real-capable, fake-safe fallback

| 能力 | Bucket | 关键文件 |
| --- | --- | --- |
| Real LLM provider opt-in skeleton | `pushed` | `provider_readiness.py` / `real_smoke.py` |
| `mindforge provider readiness` / `smoke` CLI | `pushed` | `provider_cli.py` |
| Synthetic-only real LLM smoke (DashScope qwen verified once) | `pushed` | `real_smoke.py` |
| `mindforge dogfood preflight` 安全分类 | `pushed` | `dogfood_safety.py` |
| Preflight UX hint (allowed → fake-safe; refused → demo-vault) | `pushed` | `dogfood_safety.py` |
| 闭环文档 (closure ledger / readiness evidence / real-safe journey) | `pushed` | `docs/V0_13_*.md` |
| Stage 5 boundary tests (closure 不变量) | `pushed` | `tests/test_v013_stage5_*.py` |

### v0.14 / v1.0 — Future Gate Specifications

| Gate | Bucket | 触发条件 (摘自 [V0_14_FUTURE_GATES.md](V0_14_FUTURE_GATES.md)) |
| --- | --- | --- |
| G1 Real Cubox Ingestion | `future-gated` | sample-folder + item-cap + dry-run-first + no-persist |
| G2 Real Obsidian Formal-Note Write | `future-gated` | `--commit-write` + `--diff-preview` + per-write 确认 + auto backup |
| G3 `human_approved` Production UX | `future-gated` (UX only) | 永不更改 `approver.approve_card` 是唯一晋升路径的不变量 |
| G4 Custom Executable Strategy Runtime | `future-gated` | out-of-process sandbox + capability-restricted env + 不能 produce `human_approved` |
| G5 RAG / Embedding / Semantic Merge | `future-gated` | local-only 默认; remote embedding 必须 explicit opt-in; semantic merge 只 produce suggestion |
| G6 Public Release / Git Tag | `release-gated` | named human authorizer + CHANGELOG freeze + signed marker; **任何自动化都不能创建 tag** |

### Permanently forbidden

这些不会出现在任何 future gate; 出现即与产品定位冲突。

| 行为 | 理由 |
| --- | --- |
| 默认启用 real provider | 用户不付钱也能开箱安全 |
| 仅 env 变量出现就激活 real provider | env presence ≠ explicit opt-in |
| 测试依赖真实 secret 才能 pass | CI 不应该需要付费 key |
| `cat .env` / 打印 / 提交 secret | 隐私底线 |
| 自动 approve / 程序生成 `human_approved` | 审核权专属人类 |
| 扫描 `Path.home()` / 真实 Obsidian vault | 隐私底线 |
| `subprocess` 执行用户提供的 strategy | 任意代码执行 |
| importlib 加载任意 plugin module | 任意代码执行 |
| 自动 `git tag` / `git push --tags` / `--force` | release 权专属人类 |

## Completion claim

- **v0.13 stage-complete locally and pushed**: 所有 v0.13 stage
  (Stage 1-5) commits 已经在 `origin/main`。
- **v0.14 future-gate Pack pushed**: future gate 规格 + evidence
  cookbook + 仓库级守卫已经在 `origin/main` (HEAD = `dc14b8c`)。
- **Roadmap closure pushed**: ledger + G1-G6 forbidden-impl guard +
  README/GETTING_STARTED/cookbook cross-links 已经在 `origin/main`
  (HEAD = `c052cc1`)。
- **Safe-completable scope is exhausted**: 没有任何进一步动作可以
  在不打开 future gate / release gate 的前提下推进 Roadmap。详见
  [ROADMAP.md](ROADMAP.md) §Roadmap Completion Status 段落。

## How a future contributor opens a gate

1. 阅读 [V0_14_FUTURE_GATES.md](V0_14_FUTURE_GATES.md) 中对应 gate
   的 6 段规格。
2. 在 ROADMAP 增加专属 RFC section (不直接落代码)。
3. 在新 PR / 新 stage 中实现; 同时把 `future-gated` → 一个新的
   stage bucket; 更新本 ledger。
4. 触发 release / tag 之前必须经过 G6 完整流程。
5. 不允许通过删除 boundary 测试来"绕过" gate; boundary 测试本身就
   是 gate。
