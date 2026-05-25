# Workspace Data Layout

MindForge workspace 数据模型、schema 版本、文件布局和迁移策略。

---

## 数据目录结构

```
workspace/
├── mindforge.yaml              # 主配置文件（version/vault/llm/sources）
├── vault/                      # 知识库根目录
│   ├── 00-Inbox/               # 源文件目录（按 source type 分子目录）
│   │   ├── ManualNotes/        # PlainMarkdownAdapter 源文件
│   │   └── ...
│   ├── 20-Knowledge-Cards/     # 知识卡片目录（按 track 分子目录）
│   │   ├── agent-runtime/      # track 子目录
│   │   └── ...
│   ├── 30-Wiki/                # Wiki 输出
│   ├── 40-Logs/                # 运行日志
│   └── 90-Archive/             # 归档目录
│       └── Skipped/            # 跳过的源文件
├── .mindforge/                 # 本地运行时数据（gitignored）
│   ├── state.json              # 处理状态（runs、source tracking）
│   ├── secrets.json            # API key 存储（不进 git）
│   ├── index.jsonl             # BM25 词法索引
│   ├── runs/                   # 运行记录
│   └── backups/                # state 备份
└── exports/                    # 导出文件
```

---

## Schema 版本

### Config Version

`mindforge.yaml` 顶层 `version` 字段（float）：
- `0.7` — 当前稳定版本（vault.root、cards_dir、state_dir）
- 向后兼容：缺失字段有合理默认值

### Card Schema Version

每张 Knowledge Card 的 frontmatter 中 `schema_version` 字段（str）：
- 记录卡片创建时的 schema 版本
- 格式：如 `"0.7"`、`"1.0"`
- 用于迁移检测：旧 schema 卡片在读/写时可能需要转换

### Lexical Index Version

`index.jsonl` header 中 `SCHEMA_VERSION`：
- 当前值：`"0.3.1"`
- 用于索引重建触发检测

---

## Knowledge Card 数据模型

每张卡片是一个 Markdown 文件，包含 YAML frontmatter + Markdown body。

### 核心字段（CardSummary 白名单）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 卡片唯一标识（通常来自文件名） |
| title | str | 卡片标题 |
| path | Path | 绝对路径 |
| rel_path | str | 相对 vault root 路径 |
| status | str | ai_draft / human_approved / trashed |
| track | str | 知识分类（对应子目录） |
| tags | tuple[str] | 标签集合 |
| source_type | str | 来源类型（plain_markdown 等） |
| source_id | str | 来源文件标识 |
| source_path | str | 来源文件路径 |
| adapter_name | str | 处理适配器名称 |
| source_location_index | int | 在源文件中的位置索引 |

### 审批字段

| 字段 | 类型 | 说明 |
|------|------|------|
| approved_at | datetime | 审批时间（approver 写入） |
| reviewed_at | datetime | 最后一次审阅时间 |
| review_count | int | 审阅次数 |
| last_review_result | str | 最近审阅结果 |

### 质量字段

| 字段 | 类型 | 说明 |
|------|------|------|
| quality_score | int | 质量评分（0-100） |
| quality_level | str | high / medium / low |
| value_score | int | 价值评分 |

### 溯源字段

| 字段 | 类型 | 说明 |
|------|------|------|
| profile | str | 使用的 model profile |
| provider | str | LLM provider 类型 |
| strategy_id | str | 策略标识 |
| strategy_version | str | 策略版本 |
| prompt_version | str | prompt 版本 |
| run_id | str | 关联的运行 ID |

### 字段安全分级

- **白名单（可曝光到 API/搜索）**: id, title, status, track, tags, source_type, wiki_sections, quality_level
- **内部（卡片详情页可展示）**: body, source_path, adapter_name
- **机密（不返回给前端）**: 无 — API key 在 secret store 中，卡片的 frontmatter 不含 key

---

## 数据所有权原则（Local-first）

1. **用户拥有全部数据** — 所有文件在本地 `vault/` 目录下，纯 Markdown + YAML
2. **无隐藏状态** — 卡片数据是 human-readable Markdown，不是数据库 blob
3. **可导出** — JSON/OPML/Zip 多格式导出，完整保留 frontmatter
4. **可迁移** — 复制 `vault/` + `mindforge.yaml` 到新位置即可重建工作区
5. **无供应商锁定** — 无专有格式、无云同步依赖

---

## 迁移策略

### Version N → N+1

迁移触发条件：
- `mindforge.yaml` version 低于当前支持版本
- 卡片 `schema_version` 与当前 schema 不匹配

迁移步骤：
1. 读取旧版本数据
2. 应用字段映射/默认值填充
3. 写入新版本格式
4. 更新 version 标记
5. 保留原始文件备份（`.mindforge/backups/`）

### 当前迁移需求

当前版本 0.7，无活跃迁移。未来可能触发迁移的场景：
- vault 目录结构变更（如 cards_dir 重命名）
- frontmatter 字段新增/重命名
- status 状态机扩展
