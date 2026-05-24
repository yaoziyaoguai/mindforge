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

## Processing Workflow

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

### Local Graph Preview

卡片详情页展示以当前卡片为中心的 1-hop 局部图谱，可视化展示卡片与 source、tag、wiki section 之间的关系。纯确定性计算，不做全局图谱展开。

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
| **Home** | 状态总览、安全摘要、下一步建议 |
| **Setup** | 配置模型、管理 Processing Workflow、添加 source |
| **Sources** | 管理 source、Process now、Import |
| **Review** | 查看 AI 草稿、审批或移入 Trash |
| **Library** | 浏览已审批知识卡片 |
| **Trash** | 安全回收站，支持 Restore |
| **Recall** | 本地 BM25 词法检索 |
| **Wiki** | LLM synthesis 生成 Wiki |

端口被占用时换端口：

```bash
mindforge web --port 8766 --open
```

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
- 当前不支持 RAG、embedding、向量数据库、semantic merge
- 不支持 Obsidian plugin
- 不支持自动审批
