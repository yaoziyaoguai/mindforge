# 用户指南

MindForge 完整功能说明。

---

## 概念模型

MindForge 的核心概念：

| 概念 | 说明 |
|------|------|
| **Workspace** | MindForge 的工作目录，包含 vault 和本地 config |
| **Vault** | 本地知识库目录，存放 source 文件和生成的知识卡片 |
| **Source** | 原始文件，AI 处理的输入 |
| **ai_draft** | AI 生成的草稿卡片，仅供预览 |
| **human_approved** | 你显式审批后的正式知识卡片 |
| **Run** | 一次 source 处理任务，包含多个 step |
| **Wiki** | 基于已审批卡片 LLM synthesis 生成的结构化 topic page |

---

## Workspace 管理

### 初始化

```bash
mindforge init
```

在当前目录创建 MindForge workspace。Workspace 路径记录在 `~/.mindforge/current_workspace.json`，之后在任意目录运行命令都会自动定位。

### 状态查看

```bash
mindforge status
```

显示 workspace 路径、vault 状态、draft 数量等。

### 诊断

```bash
mindforge doctor
```

检查环境、配置和潜在风险。troubleshooting 入口，不是 first-run 主路径。

---

## Source 管理

### 添加 Source

```bash
# 持续监听（文件变化时自动重新处理）
mindforge watch add <path>

# 一次性导入
mindforge import <path>
```

Source 放在 `vault/00-Inbox/` 下即可，无需预建子目录。

### 路径规则

- **Web Add Source**：必须绝对路径。`~/Documents/note.md` 自动展开。
- **CLI**：支持相对路径，按 cwd → project-root → active-vault 自动解析。
- 路径不存在时返回错误。

### 支持的格式

| 格式 | 状态 |
|------|------|
| Markdown (`.md`) | 已支持 |
| TXT (`.txt`) | 已支持 |
| HTML (`.html`) | 已支持 |
| DOCX (`.docx`) | 已支持 |
| PDF (`.pdf`) | 文本型已支持 |
| Legacy `.doc` | 不支持 |

### 监听频率

`watch add` 默认 **manual** 频率，不自动扫描。通过 CLI `--every` / `--frequency` 或 Web UI（Setup → Add Source 的 Frequency 下拉，Sources → Edit frequency）设置。可选：`manual` / `hourly` / `daily` / `weekly` / `every 1h` / `every 6h` / `every 12h` / `every 24h`。查看频率：`mindforge watch status`。详见 [Source 管理](sources.md)。

### 停止监听

在 Web **Sources** 页面操作。Stop watching 不删除 source 文件。

### Source Location / 来源追溯

每张卡片在 Library 详情页展示来源追溯信息：

- **Source Location**: 卡片内容在原始 source 文件中的位置（Section 标题 + 段落序号）
- **Provenance 字段**: source_id、source_path、source_type、adapter_name 完整保留

Source Location 用于支持 Related Cards 的相邻位置关系发现和 Knowledge Health 的 provenance 完整性检查。

---

## 模型配置

### 模型池

`llm.models` 下可配置多个模型，每个有独立的 model id、type、base URL、model name。

### 默认模型

`llm.default_model` 指定所有 workflow step 默认使用的模型。

### Model Routing

可选的 per-step 模型分配：

```yaml
llm:
  routing:
    triage: main
    distill: main
    link_suggestion: main
    review_questions: main
    action_extraction: main
```

缺失的 step fallback 到 default_model。

### 超时与重试

- `timeout_seconds`：单次 HTTP request timeout（默认 120s）
- `max_retries`：单次 call 有限 retry（默认 1）

详细说明见 [模型配置](model-setup.md)。

---

## Provider Readiness

**Provider Readiness** 诊断面板报告哪些模型 alias 可用、被阻塞或需要配置：

- **就绪 (Ready)**: 模型已配置有效 API key 和 endpoint
- **阻塞 (Blocked)**: 缺少 API key、endpoint 不可达或协议不兼容
- **未知 (Unknown)**: 尚未配置

在 Web **Setup** 页面的 Provider Readiness 面板查看。诊断绝不会返回原始 API key 值 — key 始终被遮蔽（仅显示最后 4 位）。

---

## Processing Workflow

### 知识生命周期

每张卡片按明确定义的生命周期流转，可在 **Home** 页面查看：

```
Source → ai_draft → human_approved
                      ├── Library (浏览/检索)
                      ├── Wiki (LLM synthesis)
                      └── Recall (BM25 检索)
```

Home 页面按 source 分组展示卡片，显示每个阶段的数量。点击任一 source 可查看完整的 Source-to-Card 生命周期时间线。

### 处理步骤

处理一个 source 经历五个固定 step：

| Step | 说明 |
|------|------|
| **Triage** | 评估 source 价值，给出 track / value_score |
| **Distill** | 提取核心知识，生成卡片主体 |
| **Link Suggestion** | 建议相关主题和链接 |
| **Review Questions** | 生成复习和自测问题 |
| **Action Extraction** | 提取可跟进 action items |

每个 step 可分配不同模型。在 Web Setup 的 Processing Workflow 区域查看每个 step 的 prompt 和模型配置。

### 查看运行状态

```bash
mindforge runs list              # 列出所有 run
mindforge runs show <run_id>     # 查看 run 详情和当前 step
```

如果 triage 判定 source 价值低，run 会标记为 skipped。真实模型处理需要时间，`running` 持续几分钟是正常的。

---

## 审批

### CLI 审批

```bash
mindforge approve list                  # 列出待审批 ai_draft
mindforge approve show --card 1         # 查看草稿摘要
mindforge approve show --card 1 --show-content  # 查看完整内容
mindforge approve 1 --confirm           # 显式审批
```

### Web 审批

在 **Review** 页面查看 AI 草稿，点击 **Approve** 并二次确认。

### 审批语义

- `ai_draft`：AI 生成的草稿，仅供预览，不进入 Library
- `human_approved`：你显式审批后的正式知识，进入 Library，可被 Recall 检索，参与 Wiki 生成
- **没有自动审批**。所有 approve 路径必须显式确认

---

## Card Quality

每张知识卡片在生成时会经过确定性质量评估，结果写入卡片 frontmatter。

### 评分维度

| 维度 | 说明 |
|------|------|
| **Completeness** | 内容是否包含标题、正文、来源引用等必要元素 |
| **Structure** | 是否有清晰的分段和层级结构 |
| **Provenance** | 是否完整保留了 source_id、source_path、source_type、adapter_name |

### 质量等级

- **high** — 各项指标良好
- **medium** — 基本可用，部分维度可改进
- **low** — 存在明显不足，建议重新生成或拆分

Web Library 页面每张卡片右上角显示对应颜色的质量徽章。低质量卡片会触发 Knowledge Health 警告。

## Library

浏览和管理已审批知识卡片：

```bash
mindforge library list           # 列出所有已审批卡片
mindforge library show <ref>     # 查看单张卡片详情
```

### Related Cards

每张卡片详情页展示 Related Cards 面板。关系基于确定性字段匹配计算，不依赖 embedding 或向量检索：

- **同源 (same_source)**: 来自同一 source 文件
- **同标签 (same_tag)**: 共享 tags
- **同 Wiki Section (same_wiki_section)**: 归属同一 Wiki 章节
- **同批次 (same_review_batch)**: 同一批次处理
- **相邻位置 (source_location_neighbor)**: 同一 source 中的相邻段落

每种关系类型最多展示 5 条，按关联强度降序排列。

### Community Browser

Web **Library** 页面支持社区浏览视图 — 知识卡片按共享 tags、sources、wiki sections 分组为确定性主题社区。社区检测纯结构化计算，不使用 LLM 或 embedding。每个社区展示其成员卡片和连接理由。

### Local Graph Preview

卡片详情页展示以当前卡片为中心的 1-hop 局部图谱，可视化展示卡片与 source、tag、wiki section 之间的关系。纯确定性计算，不做全局图谱展开。

### Multi-hop Relations

Related Cards 支持多跳导航 — 从一张卡片可以探索其相关卡片，再探索这些卡片的相关卡片，形成可解释的溯源路径。每一跳展示关系类型和证据。所有关系和社区检测均为确定性计算，不使用 embedding、GNN 或向量数据库。

---

## Recall

本地 BM25 词法检索：

```bash
mindforge recall --query "关键词"
```

当前基于 BM25 词法匹配，不做语义检索。不支持 RAG / embedding / 向量数据库。

---

## Knowledge Health

```bash
mindforge health
```

Knowledge Health 是只读维护报告，会检查 review backlog、低质量卡片、缺少 provenance、重复候选、孤立卡片、stale wiki 等，并给出建议。它不会自动修改卡片、source 或 Wiki。

---

## Wiki

### 生成

```bash
mindforge wiki status            # 查看 Wiki 状态
mindforge wiki rebuild           # LLM synthesis 重建
mindforge wiki show              # 查看 Wiki 内容
```

Web **Wiki** 页面点击 **Generate Wiki**。

### 工作原理

- Wiki 只从 `human_approved` cards 生成
- LLM-first synthesis：调用 LLM 对已审批卡片做综合归纳和重写
- 不会绕过审批读取 raw source
- 必须手动触发，不会自动运行

### 配置

```yaml
wiki:
  mode: llm                 # LLM-first synthesis
  model: main               # 使用的 model id
  auto_rebuild_on_approve: false  # 是否在 approve 时自动重建
```

### Troubleshooting 回退

Web Wiki 页面的 **Advanced** 区域提供 Safe fallback rebuild（确定性模板重建），用于没有可用模型时的应急回退。这不是推荐的 Wiki 生成路径。

### Wiki Quality

Wiki 页面底部展示 Quality Bar，显示当前 Wiki 的质量指标：

| 指标 | 说明 |
|------|------|
| **Coverage** | 已审批卡片中被 Wiki 引用的比例 |
| **Faithfulness** | Wiki 内容忠实反映源卡片的程度 |
| **Staleness** | 是否有已审批卡片未被 Wiki 覆盖（过期） |
| **Knowledge Gaps** | 检测 Wiki 章节之间的知识断层 |

Quality Bar 在每次 Wiki rebuild 时自动更新，数据以嵌入式 JSON 存储在 Wiki 文件末尾。

---

## Web 控制台

`mindforge web --open` 启动后访问 `http://127.0.0.1:8765`：

| 页面 | 用途 |
|------|------|
| **Home** | 状态总览、安全摘要、知识生命周期视图 |
| **Setup** | 配置模型、管理 Processing Workflow、Provider Readiness 检查 |
| **Sources** | 管理 source、Process now、Import、文件夹导入 |
| **Review** | 查看 AI 草稿、审批或移入 Trash |
| **Library** | 浏览已审批知识卡片、Related Cards、Community Browser、Local Graph Preview |
| **Recall** | 本地 BM25 词法检索 |
| **Wiki** | LLM synthesis Wiki 生成、Wiki Quality Bar |
| **Health** | 知识健康诊断、维护建议 |
| **Dogfood** | 工作区使用报告、指标面板 |
| **Trash** | 安全回收站，支持 Restore |

当前 Web 控制台没有独立的 **Import/Export** 页面。文件夹导入和 source
导入入口在 **Sources**；卡片选择和 JSON/OPML/Zip 导出入口在 **Library**。

端口被占用时换端口：

```bash
mindforge web --port 8766 --open
```

---

## Import & Export

MindForge 支持安全本地导入导出，显式审批不可绕过。

### 导入

所有导入仅创建 `ai_draft` — 显式审批从不会被绕过。

| 方式 | 说明 |
|------|------|
| **Web Add Source** | 添加单个文件为 source 以供处理 |
| **Markdown 文件夹导入** | 扫描文件夹，将所有 `.md` 文件导入为 draft |
| **批量粘贴导入** | 以 `---` 分隔多篇文档批量导入 |

导入去重检测在创建新 draft 前进行精确标题匹配和模糊 Jaccard 相似度检查。验证在导入前运行，提前捕获结构性问题。

> **注意**: 文件夹导入和批量粘贴仅处理 fake/sample/dry-run 安全数据。不暗示支持真实私人资料导入。

### 导出

多格式导出知识卡片：

| 格式 | 说明 |
|------|------|
| **JSON** | 完整卡片数据，包含 metadata 和 relations |
| **OPML** | 大纲格式，兼容思维导图工具 |
| **Zip** | 流式 zip 包，包含 `cards.md` + `manifest.json` |

所有导出保留 provenance 数据和审批状态。使用 Web **Library** 页面的导出控件预览后再下载。

### 安全

- 所有导入进入 `ai_draft` — 不会自动审批
- 磁盘上的 source 文件不会被导入修改
- 导出绝不会包含 API key 或 secret store 数据
- 验证在导入前运行；无效文件被拒绝并给出明确信息

---

## Dogfood（使用报告）

**Dogfood** 页面提供工作区使用分析和基础设施状态：

| 区域 | 说明 |
|------|------|
| **活动摘要** | 总 source 数、卡片数、wiki 数、run 数随时间变化 |
| **参与度指标** | 审批率、审阅周转时间、处理吞吐量 |
| **基础设施** | Provider 就绪状态、存储统计、索引健康 |
| **建议** | 基于检测模式的操作建议（stale 卡片、未使用 source 等） |

Dogfood 报告完全本地运行 — 无遥测、无外部分析。

---

## Trash

被删除的知识卡片进入 Trash，支持 Restore 恢复。在 Web **Trash** 页面操作。

---

## 安全边界

| 原则 | 说明 |
|------|------|
| API key 不进 Git | `.mindforge/` 已 gitignore，key 只存 local secret store |
| API key 不进前端 | API 只返回 masked 值 |
| 不自动审批 | 所有 approve 路径必须显式确认 |
| Wiki 不从 raw source 生成 | 未审批内容不进入 Wiki |
| Source 文件保护 | Stop watching + Move to Trash 都不动 source 文件 |
| 真实模型必须 opt-in | 需配置模型 + API key + 显式触发 |

---

## Troubleshooting

| 现象 | 检查 |
|------|------|
| 模型无法生成 draft | Web Setup 中为该 model 添加 API key |
| run skipped by triage | source 被 triage 判定为低价值，检查 `runs show` |
| running 持续几分钟 | 真实模型处理需要时间，检查 `runs show` 看当前 step |
| provider timed out | 检查 endpoint / network / proxy；长文档可拆分或调高 `timeout_seconds` |
| already processed | source 已处理过，不会重复生成 draft |
| approve number ref expired | 审批后编号失效，重新 `approve list` |
| Web port already in use | 换端口 `mindforge web --port 8766 --open` |
| `mindforge: command not found` | `source .venv/bin/activate && pip install -e .` |

**不要将 API key 粘贴到聊天、issue、logs 或文档中。**

---

## 已知限制

- 适合非敏感资料小规模使用，暂不建议处理私人/工作敏感资料
- 长文档可能需要拆分或调高 `timeout_seconds`
- 大目录处理耗时较长
- 不支持 RAG answering、embedding、向量数据库、语义检索
- 图谱和社区检测为纯确定性计算 — 不使用 embedding、GNN 或向量数据库
- 嵌入式图数据库 (Kuzu) 仅限 spike 阶段，未进入生产路径
- 独立 Graph 和 Sensemaking 路由属于 lab/internal；主产品路径只暴露 Library
  中的 Local Graph Preview。当前正式支持的图节点类型是 `card`、`source`、
  `tag`、`wiki_section`。
- 不支持 Obsidian plugin
- 不支持自动审批
