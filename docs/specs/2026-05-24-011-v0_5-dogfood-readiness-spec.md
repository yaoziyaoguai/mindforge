---
title: MindForge v0.5 — Dogfood Readiness Spec
type: feat
status: spec
date: 2026-05-24
roadmap: V0_5_DOGFOOD_READINESS
parent: 2026-05-24-010-v0_5-next-phase-planning-review.md
---

# v0.5: Dogfood Readiness

## 1. Background

v0.3-v0.4 建立了完整的知识质量层、关系体验层和 Web 交互层。基础设施已经足够支撑真实使用，但 dogfood 就绪仍有缺口：

- Setup 页面缺少模型快速配置引导和连接测试
- 假→真实切换缺乏显式确认门
- 缺少端到端 fake dogfood 自动化验证
- 密钥管理 UX 可改进（masking、validation 反馈）
- 狗粮操作手册分散在多个文档

**v0.5 的核心命题**：不新增后端能力，打磨 setup 到 approve 的完整 dogfood 链路，让用户能安全、自信地从 fake 模式过渡到真实 LLM 使用。

## 2. Goals

1. **Setup UX 完善** — 模型快速配置模板（Anthropic / OpenAI / OpenRouter 一键填充）、API key 验证反馈（connection test）、key masking/visibility toggle
2. **安全确认门** — 假→真切换需要显式确认步骤，而非纯信息横幅；真实模式激活前展示 cost warning + safety checklist
3. **Fake Dogfood 自动化** — `scripts/fake_dogfood.sh` 端到端脚本覆盖 scan → triage → distill → review → approve → wiki rebuild → recall 全链路
4. **Dogfood Runbook** — 统一操作手册 `docs/dogfood-runbook.md`（合并 dogfood.md + real-llm-dogfood.md + 新增安全检查清单）
5. **Web Smoke 覆盖 dogfood 路径** — 补充 Setup 页面的 browser smoke 和 product copy 测试
6. **安全护栏加固** — 审计并加固 secret store 安全语义、provider switching 边界、real environment detection

**Dogfood Readiness Definition**: v0.5 的"就绪"标准是——用户能通过 Web UI 完成以下完整路径而无需阅读源码：(1) 从模板配置模型 → (2) 填入 API key → (3) 通过安全检查清单 → (4) 激活真实模式 → (5) 运行一次完整 scan→approve→wiki→recall 流程。同时，`scripts/fake_dogfood.sh` 为开发者提供一键自动化验证。

## 3. Non-Goals

- 不做真实 LLM 调用（fake provider 始终是默认安全路径）
- 不读取 .env / secrets
- 不修改 approval 语义（human_approved 必须显式人工确认）
- 不引入 auto approve
- 不做 RAG / embedding / vector DB
- 不做 mail storage / email
- 不处理真实私人资料
- 不写真实 Obsidian vault
- 不新增大型依赖
- 不加密 secret store（那是 v0.6+ 的安全增强）

## 4. Safety Constraints (inviolable)

以下约束在本 spec 所有 implementation units 中必须保持不变：

| # | 约束 | 验证方式 |
|---|------|---------|
| S1 | AI 只创建 ai_draft，绝不自动 human_approved | code review + test |
| S2 | human_approved 必须显式人工确认 | code review |
| S3 | Fake provider 始终为默认安全路径 | code review + smoke |
| S4 | 真实 LLM 调用仅为 opt-in，需显式用户配置 | code review |
| S5 | API key 绝不写入 YAML config | code review + test |
| S6 | API key 绝不泄露到 API 响应、DOM、console、日志 | code review + smoke |
| S7 | Secret store 与 config 物理分离 | code review |
| S8 | 不做 RAG / embedding / vector DB | code review |
| S9 | 不读取 .env 文件 | code review |
| S10 | 不破坏 explicit approval 语义 | code review + test |

## 5. Implementation Units

### U1: Setup UX Polish — Model Quick-Start & Connection Test

**Goal**: 让用户能快速配置模型而不需要了解 provider type、base_url 等概念。

**Scope**:
- Model quick-start templates: "Anthropic Claude", "OpenAI", "OpenRouter" 一键填充按钮
- 每个 template 预填 type、base_url、model 字段，用户只需填 API key
- API key format validation：本地格式检查（长度、前缀、字符集），不发送外部 HTTP 请求
- Fake 模式下的 key 验证返回 N/A（fake provider 不需要 key）
- Key visibility toggle (show/hide) 在输入框中
- Key presence 指示器（已填写 / 未填写）

**Files**: `web/src/pages/SetupPage.tsx`, `web/src/components/SetupModelForm.tsx` (可能 new), `web/src/api/setup.ts`, `src/mindforge_web/routers/config.py`, `src/mindforge_web/services/web_config_service.py`

**Test scenarios**:
- Template 按钮正确填充各字段
- Connection test API 返回正确验证状态
- Fake 模式下 connection test 被跳过或返回 N/A
- Key toggle 切换可见性
- Key 元数据在 API 响应中被 mask

**Note**: Connection test 在 v0.5 不发送真实 HTTP 请求到外部 API。它做本地验证：检查 key 格式、检查 key 存在于 secret store、检查 model 配置完整性。真正的外部验证是 v0.6+ 的工作。

### U2: Safety Confirmation Gate — Fake→Real Transition

**Goal**: 假→真模式切换必须有显式确认步骤，而非纯信息横幅。

**Scope**:
- 在 Setup 页面添加 "Activate Real LLM" 确认对话框
- 对话框内容：cost warning（API 调用会产生费用）、safety checklist（确认已理解安全模型）、explicit opt-in checkbox
- 改造现有蓝色安全横幅：假模式下显示"Safe Mode: Fake Provider"，真模式下显示"Live Mode: Real LLM Active"（红色/amber 色调）
- Real mode 激活需要两步：先保存 API key → 再 confirm activation dialog
- `mode` 存储在 state.json 中（`provider_mode: fake | real`），跨 server 重启持久化
- 后端不自动切换 mode；mode 由用户显式 API 调用触发（`POST /api/config/provider-mode`）

**Files**: `web/src/pages/SetupPage.tsx`, `web/src/components/SafetyBanner.tsx` (可能 new), `src/mindforge_web/schemas.py`, `src/mindforge_web/routers/config.py`

**Test scenarios**:
- Fake 模式下 SafetyBanner 显示 safe mode 信息
- Activation dialog 三个步骤都完成才能激活
- 未填 API key 时 activation 按钮 disabled
- mode 切换反映在 ProviderStatus API 中

### U3: Fake Dogfood Automation Script

**Goal**: 一键运行完整的 fake dogfood 流程验证。

**Scope**:
- `scripts/fake_dogfood.sh` — 端到端 fake 狗粮脚本
- 流程：创建临时 dogfood workspace → 初始化 config（fake profile）→ 导入 samples → scan → 验证 drafts 生成 → 验证 card 结构 → 验证 wiki rebuild → 验证 recall 搜索 → 清理
- 每个步骤输出 PASS/FAIL
- 退出码 0 = 全部通过，非 0 = 失败步骤数
- 不读取 .env，不调用真实 LLM
- 使用 `examples/dogfood/samples/` 下的样本文件

**Files**: `scripts/fake_dogfood.sh` (NEW)

**Test scenarios**:
- 脚本在 clean 环境可运行
- 所有步骤 PASS
- 退出码 0
- 不产生副作用（使用 tmp 目录）

### U4: Dogfood Runbook

**Goal**: 统一操作手册，覆盖 fake → real 完整狗粮路径。

**Scope**:
- `docs/dogfood-runbook.md` — 合并并取代 `docs/dogfood.md` + `docs/real-llm-dogfood.md`
- 章节：Quick Start (fake)、Setup Real LLM、First Scan & Review、Approve & Wiki、Ongoing Use、Safety Checklist、Troubleshooting
- 保留原有 dogfood 文档作为参考（添加 "Merged into dogfood-runbook.md" 说明）
- Runbook 中的所有命令必须是可复制粘贴执行的

**Files**: `docs/dogfood-runbook.md` (NEW), `docs/dogfood.md` (amend header), `docs/real-llm-dogfood.md` (amend header)

**Verification**: 文档审查通过（命令可执行、安全检查清单完整、fake 路径无需外部依赖）

### U5: Web Smoke & Product Copy for Dogfood Path

**Goal**: Setup 页面和相关 dogfood 路径的 browser smoke 和 product copy 覆盖。

**Scope**:
- 补充 `tests/test_web_product_copy.py`：Setup 页面文案覆盖
- 补充 browser smoke：Setup 页面三步导航、model form 交互、safety banner 显示
- 验证 Setup 页面在 fake 模式下的所有文案和状态

**Files**: `tests/test_web_product_copy.py`, `web/src/lib/i18n.ts`

**Test scenarios**:
- Setup 页面所有 i18n key 在 zh/en 下存在
- Setup 页面加载无 console error
- Model form 添加/删除模型正常
- Safety banner 正确显示

**i18n keys needed** (zh + en):
- `setup.template.*` — 模板相关文案
- `setup.connection_test.*` — 连接测试文案
- `setup.safety_banner.*` — 安全横幅文案
- `setup.activation_dialog.*` — 激活对话框文案

### U6: Safety Hardening Audit

**Goal**: 审计并加固安全边界。

**Scope**:
- 审计 `_is_real_environment()` — 确保 demo/dogfood vault 不会被误判为真实环境
- 审计 secret store 访问路径 — 确保只在必要时读取
- 审计 API 响应中的 key 脱敏 — 确保 `/api/config/status` 等端点不泄露 key
- 审计 provider switching 边界 — 确保 fake→real 切换不会在配置持久化时泄露 key
- 加固 `model_setup_readiness()` — 确保 fake 模式下不要求 key
- 如果发现 P0/P1 安全问题，修复
- **硬约束**：审计代码路径时不打开 `.mindforge/secrets.json` 文件。审计 secret store 访问模式（谁调用 `SecretStore.get()`、在什么条件下调用），而非审计密钥内容。

**Files**: `src/mindforge_web/services/web_facade.py`, `src/mindforge_web/services/web_config_service.py`, `src/mindforge/secret_store.py`, `src/mindforge/model_setup_readiness.py`

**Test scenarios**:
- `/api/config/status` 不包含原始 key
- Fake 模式下 provider status 不要求 key
- `_is_real_environment()` 对 dogfood vault 返回 False
- Secret store 只在 llm 调用时读取原始 key

## 6. Verification

### Gate Matrix

| Unit | ruff | pytest | npm build | product copy | git diff | browser smoke |
|------|------|--------|-----------|-------------|----------|---------------|
| U1 Setup UX | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| U2 Safety Gate | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| U3 Fake Dogfood | — | — | — | — | ✓ | — |
| U4 Runbook | — | — | — | — | ✓ | — |
| U5 Smoke/Copy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| U6 Safety Audit | ✓ | ✓ | — | — | ✓ | — |

### Browser Smoke Checklist (post all units)

- [ ] `/setup` — 三步导航、model form 添加/删除、template 按钮、connection test 按钮、safety banner 显示
- [ ] `/setup` — activation dialog 弹出、checklist 完整、确认按钮行为正确
- [ ] `/library` — 卡片浏览正常
- [ ] `/wiki` — wiki 渲染正常
- [ ] `/health` — health report 渲染正常
- [ ] `/drafts` — drafts 列表正常
- [ ] 0 console errors
- [ ] 0 API 5xx

## 7. Stop Conditions

以下条件触发 HARD_STOP 并需要用户介入：
- 需要读取 `.mindforge/secrets.json` 中的真实 key
- 需要调用真实 LLM API 验证 connection
- 需要修改 approval 语义
- 需要引入加密库或安全框架依赖
- 发现 P0 安全问题无法在 2 轮回退内修复

## 8. References

- Parent review: `docs/specs/2026-05-24-010-v0_5-next-phase-planning-review.md`
- v0.4 spec: `docs/specs/2026-05-24-009-v0_4-knowledge-relationship-experience-spec.md`
- Existing dogfood: `docs/dogfood.md`, `docs/real-llm-dogfood.md`
- Engineering workflow: `docs/dev/engineering-workflow.md`
- Autopilot: `.claude/commands/mf-autopilot.md`
