---
type: feat
status: active
created: 2026-05-22
---

# MindForge Real LLM Opt-in Dogfood Plan

## Summary

设计一条**批量、端到端、可重复**的真实 LLM opt-in dogfood 路线。在已有 fake dogfood 基础上，新增多份非敏感样本、真实 LLM 配置模板、以及一个统一的 dogfood 脚本——默认 preflight 模式（安全），`--real-llm --confirm-cost` 显式 opt-in 进入真实 LLM 批量端到端 smoke。

**核心原则**：真实 LLM 调用必须显式 opt-in，fake provider 是默认安全路径，human_approved 必须人工 confirm。

## Problem Frame

当前 fake dogfood（`examples/dogfood/mindforge.dogfood.yaml` + `scripts/dogfood_smoke.sh`）已验证 MindForge 在零网络、零密钥路径下能跑通完整知识加工闭环。下一步需要验证：**使用真实 LLM（OpenAI / Anthropic / compatible）时，同样的管线是否仍然正确** —— 包括 ai_draft 质量、insufficient_content 判断、review 展示、approve/reject 流程、recall 检索。

fake dogfood 无法验证的维度：
- 真实 LLM 输出的 ai_draft JSON schema 是否符合 Card 写入预期
- insufficient_content / low-signal 判断在真实模型上的表现
- 中英文混合内容的处理质量
- 批量处理时模型调用是否稳定
- 真实 API 调用的错误处理和重试

## Scope Boundaries

### In Scope
- 多份非敏感 sample markdown（≥6 份，覆盖短/长/结构化/技术笔记/低价值/中英混合）
- 真实 LLM dogfood 配置模板（`examples/dogfood/mindforge.real-llm.example.yaml`）
- 统一 dogfood 脚本 `scripts/real_llm_dogfood.sh` — 默认 preflight 模式（安全，不调 LLM），`--real-llm --confirm-cost` 启用真实 LLM 批量端到端 smoke
- 端到端验证：scan → process → ai_draft → review → approve/reject → library → index rebuild → recall
- Dogfood friction log 模板
- 配套文档

### Deferred for Later
- 真实 LLM 的 Wiki 合成验证
- 多 provider 并行对比
- 性能/延迟基准测试
- 真实 LLM 回归测试套件

### Outside Scope
- RAG / embedding / vector DB
- Web UI 改动
- 自动 approve / 自动 human_approved
- 真实私人资料处理
- 真实 Obsidian vault 写入
- 新增 Python 依赖
- 修改 provider/approval/recall 管线代码

## Requirements

| ID | Requirement |
|----|-------------|
| R1 | 提供 ≥6 份非敏感 sample markdown，覆盖短/长/结构化/技术笔记/低价值/中英混合场景 |
| R2 | 提供真实 LLM dogfood 配置模板，用户只需填入 api_key_env、base_url 和 model |
| R3 | 提供 preflight 脚本，验证配置就绪但不调用真实 LLM |
| R4 | 提供 real-run smoke 脚本，需 `--real-llm --confirm-cost` 显式 opt-in |
| R5 | 端到端覆盖 scan → process → ai_draft → review → approve/reject → library → index rebuild → recall |
| R6 | human_approved 必须人工 `approve --confirm`，脚本不得自动 approve |
| R7 | 所有数据写入 /tmp，不接触真实 Obsidian vault |
| R8 | 脚本不读取 .env 或 secrets 文件，由用户通过 shell 环境变量传入 API key |

## Key Technical Decisions

### K1: 配置模板使用 openai_compatible

选择 `type: openai_compatible` 作为配置模板的默认类型。理由：
- OpenAI-compatible API 是最大公约数（覆盖 OpenAI、Ollama、vLLM、多数第三方代理）
- Anthropic-compatible 作为注释中的可选替代方案
- 与 `configs/mindforge_example.yaml` 的示例风格一致

### K2: 一份脚本，两种模式

preflight 和 real-run 合并为一个脚本 `scripts/real_llm_dogfood.sh`：
- **默认模式（无 flag）**: preflight only — config 校验、provider readiness、sample 验证
- **real-run 模式（`--real-llm --confirm-cost`）**: 完整批量端到端 pipeline

理由：避免两个脚本的代码重复；默认安全（不传 flag 绝不调 LLM）；双 flag 设计确保用户不会误触发。

### K3: 批量处理，不做单篇逐一验证

一次 `scan` + 一次 `process` 处理全部 6+ 份样本，而非逐篇处理。理由：
- 更接近真实使用场景（用户一次性导入多篇笔记）
- 验证批量处理稳定性
- 减少重复 scan/index 操作

### K4: Friction log 而非自动化断言

real-run 模式生成 structured friction log（markdown 模板），供人工填写观察结果，而非对 LLM 输出内容做自动化断言。理由：
- 真实 LLM 输出是非确定性的，无法做精确字符串匹配
- 人工 review 是 dogfood 的核心价值 —— 发现 AI 行为的意外模式
- Friction log 可积累为后续改进的输入

### K5: API key 通过 shell 环境变量传入

脚本不读取 .env 或 secret store，由用户在调用前 `export` 环境变量。理由：
- 保持脚本对 secret 管理的完全无知
- 用户自行决定 key 的来源（shell export、secret manager、CI variable）
- 与 `load_cfg(read_env=False)` 的安全语义一致

## Implementation Units

### U1. Batch non-sensitive sample markdowns

**Goal**: 创建 6+ 份非敏感 sample markdown，覆盖端到端 dogfood 需要的多样化输入场景。

**Requirements**: R1

**Dependencies**: None

**Files**:
- Create: `examples/dogfood/samples/short-note.md`
- Create: `examples/dogfood/samples/long-technical.md`
- Create: `examples/dogfood/samples/bullet-notes.md`
- Create: `examples/dogfood/samples/tech-learning.md`
- Create: `examples/dogfood/samples/low-signal.md`
- Create: `examples/dogfood/samples/mixed-zh-en.md`

**Approach**: 每份 sample 是带 YAML frontmatter 的独立 markdown 文件，内容为非敏感合成数据。命名采用 kebab-case，中文内容使用简体中文。所有 sample 的 `tags` 中包含 `dogfood` 和 `real-llm`。

**Sample 覆盖矩阵**:

| 文件 | 场景 | 长度 | 语言 | 预期行为 |
|------|------|------|------|----------|
| `short-note.md` | 简短笔记 | ~80 词 | 中文 | 正常生成 ai_draft |
| `long-technical.md` | 长技术文档 | ~500 词 | 中文 | 正常生成 ai_draft，summary 应覆盖要点 |
| `bullet-notes.md` | 结构化 bullet 笔记 | ~120 词 | 中文 | 正确处理列表结构 |
| `tech-learning.md` | 技术学习笔记 | ~250 词 | 中文 | 提取技术概念和 learning track |
| `low-signal.md` | 信息不足 | ~30 词 | 中文 | 可能触发 insufficient_content |
| `mixed-zh-en.md` | 中英混合 | ~200 词 | 中英混合 | 正确处理代码/术语 |

**Patterns to follow**: `scripts/dogfood_smoke.sh` 中内嵌的 sample markdown 的 frontmatter 格式。

**Test scenarios**:
- Covers R1: 验证 6 份 sample 文件均存在且包含有效 YAML frontmatter
- Happy path: 每份 sample 可被 `PlainMarkdownAdapter` 正确解析
- Edge case: `low-signal.md` 内容极短，验证 process 不会 crash
- Edge case: `mixed-zh-en.md` 含代码块和英文术语，验证 frontmatter 解析正确

**Verification**: 所有 sample 文件存在，YAML frontmatter 有效，`mindforge scan --config <real-llm-config>` 能扫描到全部 6 份文件。

---

### U2. Real-LLM dogfood config template

**Goal**: 创建真实 LLM dogfood 配置模板，用户只需填入 API key 环境变量名和 base_url 即可使用。

**Requirements**: R2

**Dependencies**: None

**Files**:
- Create: `examples/dogfood/mindforge.real-llm.example.yaml`

**Approach**: 以 `examples/dogfood/mindforge.dogfood.yaml` 为结构基础，将 `llm.models` 中的 provider 从 `type: fake` 改为 `type: openai_compatible`，添加 `api_key_env` 和 `base_url` 占位符。保留 /tmp 路径、BM25 search、手动 approve、telemetry disabled 等安全设置。

关键差异点：
```yaml
# fake dogfood config:
llm:
  default_model: fake-main
  models:
    fake-main:
      type: fake
      provider: fake
      base_url: "fake://"

# real-llm dogfood config:
llm:
  default_model: real-main
  models:
    real-main:
      type: openai_compatible
      provider: openai_compatible
      base_url: "https://your-endpoint.example.com/v1"  # ← 用户填入
      model: "your-model-name"                            # ← 用户填入
      api_key_env: "YOUR_API_KEY_ENV_VAR"                 # ← 用户填入
      timeout_seconds: 120
      max_retries: 2
```

注释中提供 `anthropic_compatible` 的替代配置示例。

**Patterns to follow**:
- `examples/dogfood/mindforge.dogfood.yaml` — 结构模板
- `configs/mindforge_example.yaml` — 多 provider 示例风格
- `src/mindforge/assets/configs/llm.example.yaml` — env var 配置模式

**Test scenarios**:
- Covers R2: 验证配置模板可被 `mindforge doctor --config` 解析
- Happy path: 替换占位符后可正常加载
- Edge case: `api_key_env` 未设置时 doctor 报告 `needs_setup`

**Verification**: `python -c "from src.mindforge.config import load_mindforge_config; load_mindforge_config(Path('examples/dogfood/mindforge.real-llm.example.yaml'))"` 不抛出异常，doctor 报告 provider 状态为 `needs_setup`（key 不存在时预期行为）。

---

### U3. Real-LLM dogfood documentation

**Goal**: 编写真实 LLM dogfood 完整文档，覆盖前提条件、配置步骤、批量端到端命令序列、friction log 模板。

**Requirements**: R3, R4, R5, R6, R7, R8

**Dependencies**: U1, U2 (引用 sample 和 config 路径)

**Files**:
- Create: `docs/real-llm-dogfood.md`

**Approach**: 参考 `docs/dogfood.md` 的结构，扩展为真实 LLM 场景。文档分为以下章节：

1. **前提条件** — Python >= 3.11, pip install -e ., API key, 网络连接
2. **安全边界** — 显式 opt-in、手动 approve、/tmp 隔离
3. **配置步骤** — 复制 config template → 填入 api_key_env / base_url / model
4. **Preflight 检查** — 运行 `./scripts/real_llm_dogfood.sh` 验证配置就绪
5. **批量端到端命令序列** — 完整的手动命令序列（供不想用脚本的用户）
6. **Real-run smoke** — `./scripts/real_llm_dogfood.sh --real-llm --confirm-cost`
7. **Friction log 模板** — 结构化的观察记录模板
8. **常见问题**

Friction log 模板包含以下观察维度：
- 每份 sample 的 ai_draft 质量（summary 准确性、concepts 提取、action_items 合理性）
- insufficient_content 触发情况
- review_questions 是否有意义
- 处理耗时
- API 调用次数
- 错误/重试情况
- 意外行为

**Patterns to follow**: `docs/dogfood.md` — 结构和风格

**Test scenarios**:
- Test expectation: none — 纯文档，无行为变更

**Verification**: 文档中每条命令可被复制粘贴执行，路径引用与 U1/U2/U4 产出一致。

---

### U4. Dogfood script（preflight + real-run）

**Goal**: 创建统一 dogfood 脚本，默认 preflight 模式（安全，不调 LLM），`--real-llm --confirm-cost` 启用真实 LLM 批量端到端 smoke。

**Requirements**: R3, R4, R5, R6, R7, R8

**Dependencies**: U1, U2

**Files**:
- Create: `scripts/real_llm_dogfood.sh`

**Approach**: 单一 bash 脚本（`set -euo pipefail`），遍历参数分叉：

**Preflight 模式（默认，无 flag）**:
```
[P1] 环境检查（python, mindforge, config 文件存在）
[P2] Provider readiness 检查（mindforge doctor --config）
[P2a] API key 环境变量检查：解析 config 中的 api_key_env 字段，用 `[ -n "${VAR_NAME+set}" ]` 验证变量存在且非空
[P3] Sample 文件验证（6+ 份 sample 存在且 frontmatter 有效）
[P4] /tmp 路径可写性检查
[P5] 输出 readiness 报告（opt_in_state, blockers, 下一步提示）
```
不读取 .env，不调用 LLM（不创建出站 HTTP 连接到 LLM API），不读取 secrets 文件。

**Real-run 模式（`--real-llm --confirm-cost`）**:
```
[S0] 解析 flag：遍历所有参数，确认 --real-llm 和 --confirm-cost 均存在（顺序无关），否则拒绝
     同时从 config YAML 解析 llm.models 中的 model type，确认至少一个非 fake，否则拒绝
[S1] 清理 /tmp 残留
[S2] 创建 workspace 目录结构
[S3] 复制 sample markdowns 到 inbox
[S4] scan
[S5] process（真实 LLM 调用）
[S6] 验证 ai_draft 已生成（approve list --format json）
[S7] 验证安全边界（ai_draft 未被自动提升，library 仍为空）
[S8] 展示 review 列表
[S9] 交互式 approve — 脚本暂停，提示用户手动执行 approve 命令
     （脚本不自动执行 approve，用户必须在另一个终端或脚本暂停后手动操作）
[S10] 轮询等待用户完成 approve：每 5 秒运行 approve list --format json，直到无 ai_draft 卡片或超时（5 分钟）
[S11] 验证 library 中有已审批卡片
[S12] index rebuild
[S13] recall 检索验证（对每份 sample 的关键词检索）
[S14] 生成 friction log 模板文件
```

关键安全设计：
- `--real-llm` 和 `--confirm-cost` 必须同时出现，缺一不可（遍历参数，顺序无关）
- config 验证：如果所有 model type 均为 fake，即使 flag 正确也拒绝执行
- [S9] 不自动执行 approve，脚本暂停并提示用户手动操作
- [S10] 轮询检测 approve 完成（非简单 read -p），防止未 approve 时误继续
- 所有 assert 失败立即 `exit 1`
- 不读取 .env 或 secrets 文件

**Patterns to follow**:
- `scripts/dogfood_smoke.sh` — `set -euo pipefail`、step 标记、assert_contains 辅助函数
- `scripts/check.sh` — 多段验证模式

**Test scenarios**:
- Covers R3: preflight 模式无网络调用，exit=0 当配置有效
- Covers R4: real-run 模式缺少 flag 时立即拒绝并 exit=1
- Covers R5: real-run 模式覆盖完整端到端链路
- Covers R6: 脚本不包含自动 approve 逻辑，[S9] 处暂停提示用户手动操作
- Covers R7: 所有路径在 /tmp 下
- Covers R8: 不 source .env、不读取 secrets.json
- Happy path: `./scripts/real_llm_dogfood.sh` → preflight 通过
- Happy path: `./scripts/real_llm_dogfood.sh --real-llm --confirm-cost` → 完整 pipeline
- Edge case: `--real-llm` 单独使用（无 `--confirm-cost`）→ 拒绝
- Edge case: `--confirm-cost` 单独使用 → 拒绝
- Error path: config 不存在 → preflight 检测并报错

**Verification**:
1. Preflight 模式 EXIT_CODE=0（在已配置环境）
2. `./scripts/real_llm_dogfood.sh --real-llm` → EXIT_CODE=1（缺少 --confirm-cost）
3. `./scripts/real_llm_dogfood.sh --confirm-cost` → EXIT_CODE=1（缺少 --real-llm）
4. Real-run 模式完整执行 EXIT_CODE=0（需要真实 API key 环境）

---

### U5. Update testing.md

**Goal**: 在 `docs/dev/testing.md` 中添加真实 LLM dogfood 引用。

**Requirements**: None（文档维护）

**Dependencies**: U3, U4

**Files**:
- Modify: `docs/dev/testing.md`

**Approach**: 在现有 "Dogfood Smoke" 章节下方添加 "Real LLM Dogfood" 子章节，引用 `docs/real-llm-dogfood.md` 和 `scripts/real_llm_dogfood.sh`。保持与 fake dogfood 章节一致的格式。

**Patterns to follow**: `docs/dev/testing.md` 中现有 "Dogfood Smoke" 章节格式

**Test scenarios**:
- Test expectation: none — 纯文档，无行为变更

**Verification**: 文档引用路径正确，命令可复制执行。

---

## System-Wide Impact

- **无生产代码变更** — 仅新增文档、配置模板、sample 数据和脚本
- **无依赖变更** — 不需要新的 Python 包
- **无 API 合约变更** — CLI 接口不变，config schema 不变
- **安全边界保持** — fake provider 默认路径不受影响，real provider opt-in 路径为增量

## Risks & Dependencies

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| 用户未设置 API key 环境变量 | High | Low | Preflight 检测并报告 `needs_setup` |
| 真实 LLM 输出格式不符合 Card schema | Medium | Medium | Friction log 记录，人工判断 |
| 批量处理时 API 限流 | Low | Medium | Config 中 `max_retries: 2`，脚本中用 sleep 间隔 |
| 用户误将真实 config 用于私人资料 | Low | High | 文档强调 /tmp 隔离，config 模板中 vault.root 固定为 /tmp |
| `--confirm-cost` 被用户绕过 | Low | Medium | 双 flag 设计，缺少任一则拒绝；文档强调安全边界 |

## Verification

1. `scripts/real_llm_dogfood.sh`（preflight）在干净环境中 EXIT_CODE=0
2. `scripts/real_llm_dogfood.sh --real-llm` 拒绝执行（缺少 --confirm-cost）
3. `scripts/real_llm_dogfood.sh --confirm-cost` 拒绝执行（缺少 --real-llm）
4. `scripts/check.sh` 仍通过（pytest + ruff + diff --check）
5. Fake dogfood smoke（`scripts/dogfood_smoke.sh`）仍通过
6. 所有 6 份 sample markdown YAML frontmatter 有效
7. Real-LLM config template 可被 config parser 正确加载
8. Doctor 对 real-LLM config 报告正确的 readiness 状态
