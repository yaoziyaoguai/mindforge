# V0.13 行业模式映射 (Industry Pattern Map)

> 本文档基于离线知识整理，不调用网络抓取，不引用未经核实的 URL；
> 所有结论均标记为 **离线判断 (offline-judgement)**，仅用于 MindForge
> real-capable opt-in 路径设计参考，不作为权威产品对照。

## 1. 调研范围

| 类别 | 代表 | 关注维度 |
| --- | --- | --- |
| Agent 框架 | OpenAI Agents SDK · LangChain · LangGraph · Dify | guardrails / human-in-the-loop / interrupt / structured output / provider 切换 |
| 本地优先 (local-first) | Obsidian (+ AI plugins) · Logseq · Tana · Anytype | vault ownership / 显式写入 / plugin permissions / local↔cloud 模型切换 |
| 第二大脑 (second brain) | Readwise Reader · Cubox · Capacities · Notion AI · Mem | capture → review → approve → recall 闭环 / AI draft vs permanent / approval boundary |
| CLI 知识工具 | 通用 markdown / shell-first 工具 | dry-run / preview / 显式写入 / 无后台索引 |

## 2. 共性模式 (cross-cutting)

| 模式 | 出现产品 | MindForge 是否对照 |
| --- | --- | --- |
| 默认安全 fake / mock provider | Dify (provider 配置完成前不可调用), LangGraph 测试 | ✅ `active_profile: fake` |
| 显式 opt-in 真实 provider | OpenAI Agents SDK (env+model 必显式), Dify (provider 配置 UI), Obsidian AI plugins (按钮启用) | ✅ profile 切换 + 本轮新增 `--allow-real` flag |
| 真实输出仅落 draft / preview, 不直接成 approved | Readwise Reader (highlights → review → save), Cubox (preview → 整理 → 归档), Logseq (AI draft → 用户接受) | ✅ Real LLM smoke 输出仅落 `ai_draft_preview` 类 artifact |
| 显式 human approval gate | OpenAI Agents SDK (`HumanApproval` guardrail), LangGraph (`interrupt`), Dify (Human Input node), Obsidian (UI 确认) | ✅ MindForge ApprovalService + `human_approved` 仅由人产生 |
| 无后台索引 / 无隐式上传 | Obsidian, Logseq, Anytype | ✅ Local-first Privacy Contract v2 |
| Capability matrix 公开声明 | Dify (model provider 状态页), OpenAI (tool catalog) | ✅ `V0_12_CAPABILITY_MATRIX.md` §8 readiness 列 |
| Secret 不打印 | 几乎所有合规框架 | ✅ `provider_readiness.inspect_provider_config` 仅返回 `api_key_present: bool` |
| 真实 ingestion 单独门 | Readwise / Cubox 显式登录 + 范围确认 | ✅ Cubox/Obsidian deferred ingestion gates 文档 |

## 3. 借鉴 (adopted)

| 来源 | 借鉴点 | MindForge 落点 |
| --- | --- | --- |
| OpenAI Agents SDK | guardrails 拦截 + structured output | preview packet contract + `ReviewableArtifact` 提案 |
| LangGraph | interrupt / checkpoint 把人类决策建模成显式节点 | Human Decision Gate Map (privacy contract 内) |
| Dify | provider 配置与 ingestion 显式分离 | `--allow-real` flag + Cubox/Obsidian deferred gates |
| Obsidian | vault 写入永远显式 | `human_approved` 永远只能人产生; 真实 LLM 输出永不写 vault |
| Readwise / Cubox | capture 与 review 解耦 | preview packet 与 ai_draft 类型化区分 |

## 4. 拒绝 (rejected — 不引入)

| 模式 | 拒绝原因 |
| --- | --- |
| 后台自动 embedding / RAG 索引 | 违反 local-first 隐式上传禁令 (LangChain 默认行为) |
| Plugin marketplace 任意执行 | 违反 custom strategy runtime 禁令 (Dify plugin / Obsidian community plugins 安全模型) |
| Auto-approve / auto-merge | 违反 human approval gate 不可绕过 (某些 Agentic IDE 默认行为) |
| 默认远端模型 | 违反 fake-default (Notion AI / Mem 默认云端) |
| Semantic merge 无人确认 | 违反 ReviewableArtifact 边界 (Mem 自动合并风险) |

## 5. 推迟 (future — 仅记录方向)

| 方向 | 当前状态 | 启用前置 |
| --- | --- | --- |
| 真实 Cubox API ingestion | docs-only proposal (本轮新增 deferred gates 文档) | 测试账号 / sample-folder-only / item cap / no-persist |
| 真实 Obsidian vault 写入 | docs-only | 显式 dry-run preview → 用户确认 → 单文件写 |
| ReviewableArtifact protocol 实现 | proposal-only | 至少 3 类 artifact 落地后再抽象 |
| 多 provider routing 审计 | capability matrix 一行占位 | 出现真实多 provider 切换需求后 |
| 真实 dogfooding (个人资料) | 未启用 | Cubox + Obsidian 写入 gate 全部就绪后 |

## 6. MindForge 差异化 (differentiation)

1. **Profile-level lazy provider 构建**：仅 `active_profile` 涉及的 alias
   被实例化，未启用 alias 不会因缺 api_key 报错 — 比 Dify provider 配置
   更轻；比 LangChain 默认 eager 实例化更安全。
2. **Real ≠ Approved 的硬隔离**：真实 LLM 输出在类型层面就被标记为
   `ai_draft_preview`/`preview_packet`，无任何代码路径能将其升格为
   `human_approved`；这一边界由 AST 级 import 守卫与 ReviewableArtifact
   提案双重保护。
3. **Synthetic-only smoke**：真实 provider 烟测只接受硬编码 synthetic
   prompt，无用户输入面 — 避免误把私人资料喂给云端模型。
4. **Capability matrix 即文档即测试**：`docs/V0_12_CAPABILITY_MATRIX.md`
   既是用户文档，也由 `tests/test_v013_*` 系列做 token 断言，确保不被
   静默回退。
5. **Local-first Privacy Contract v2 单一源**：避免多份隐私声明漂移；
   `human_approved` / `written` / `network` / `secret` 四类边界集中描述。

## 7. 离线判断声明 (offline-judgement disclaimer)

- 本文档不通过网络获取任何官方文档；所有产品行为描述基于已公开知识
  与社区常识，**可能与最新版本细节存在偏差**。
- 不引用未经核实的 URL；如未来需要权威化对照，应单独发起一次有联网
  访问的调研，并把结果合入本文档对应行。
- 本文档仅服务于 MindForge real-capable opt-in 路径设计，不替代各产品
  自身的官方安全声明。
