# MindForge v0.2.2 · M5.3 复盘

> 范围：**Better project context**（项目级 profile + Knowledge Cards
> 混合数据源 + target-aware suggested prompt）。
> 上一轮：[V0_2_1_REVIEW.md](./V0_2_1_REVIEW.md)
> 协议：[M5_3_PROJECT_CONTEXT_PROTOCOL.md](./M5_3_PROJECT_CONTEXT_PROTOCOL.md)
> 后续 backlog：[M5_BACKLOG.md](./M5_BACKLOG.md)

---

## 1. v0.2.2 增量能力清单

### 1.1 项目 profile（项目级稳定上下文）

- 路径：`<vault.root>/<vault.projects_dir>/<project_name>.md`
- `vault.projects_dir` 默认 `30-Projects`（v0.2.1 不需要改 yaml）
- **只读 frontmatter**；项目笔记正文永不被读取（避免误抓 secret / 草稿）
- 支持字段：`description / default_target / principles / known_risks / preferred_workflow`
- 文件不存在 → 不报错，自动降级为 cards-only，并在输出顶部声明
- 路径越界保护：拒绝 `project_name = "../../etc/passwd"` 类输入（exit 2）

### 1.2 `project context` 命令新增

| 新参数 | 含义 |
|---|---|
| `--target {claude-code\|copilot\|codex\|generic}` | 目标助手；不传则用 profile.default_target，再退化 generic |
| —（无新参数，但行为变化） | `--format json` 输出 `version: 2` schema |
| —（无新参数，但行为变化） | markdown 始终包含 `## Excluded Content` 段 |

target 解析顺序（`§2.2`）：CLI > profile.default_target > `generic`。

### 1.3 markdown 段落（顺序固定，缺数据用降级文案，**绝不**空标题）

```
# Project Context · <name>
> Generated ... target: <target> ...

## Source Notice                    ← project_profile_found / path / card_count
## Project Profile                  ← description + preferred_workflow
## Project-Level Principles         ← profile 优先级最高
## Card-Level Principles (supplementary)   ← from [card-id] 来源透明
## Project-Level Known Risks
## Card-Level Known Risks (supplementary)
## Related Learning Tracks
## Knowledge Cards (sorted by review_after asc, then value_score desc)
## Action Items                     ← --include-actions（默认 ON）
## Review Due                       ← --include-review-due（默认 ON）
## Suggested Prompt for <target>    ← --include-next-step-prompt（默认 ON）
## Excluded Content (safety guarantee)   ← 始终输出
```

### 1.4 Suggested Prompt 模板（**固定文本，绝不调 LLM**）

| target | 风格 |
|---|---|
| `claude-code` | 先看 runtime_observer / state / 真实 events，再决定改不改代码 |
| `copilot` | 先 plan，再小步实现 + 验证命令；不确定的设计先给 2–3 个选项 |
| `codex` | 高质量补丁 + 测试；root cause 与请求不一致先汇报再继续 |
| `generic` | plan → patch → test → report；破坏性操作先确认 |

模板尾部按需追加项目级 `principles` / `preferred_workflow`（字符串拼接）。

### 1.5 JSON v2 schema 新增字段

```
project_profile_found / project_profile_path / project_description /
preferred_workflow / project_level_principles / card_level_principles /
project_level_known_risks / card_level_known_risks / suggested_prompt /
excluded_content / target / include_next_step_prompt
items[].principles / items[].known_risks
```

> v0.2.0/v0.2.1 既有字段语义不变；下游用 `if "project_level_principles" in payload`
> 这种 forward-compatible 写法即可。

### 1.6 RunLogger 字段扩展

`_ALLOWED_FIELDS` 新增 `target` / `project_profile_found`（仅 metadata，
**不**记录 profile 正文 / principles 文本 / suggested prompt 内容）。

---

## 2. 安全边界（v0.2.2 仍是"安全召回 + 安全拼装"层）

- ❌ 不调 LLM（含 fake / 真实）
- ❌ 不读 `.env`
- ❌ 不读 `runs/` / `state.json` 作为知识来源
- ❌ 不读 `00-Inbox/**` raw source
- ❌ 不读项目笔记**正文**，只读 frontmatter
- ❌ 不修改 `30-Projects/**`、`20-Knowledge-Cards/**` 任何文件
- ❌ 不索引 / embedding / 向量化
- ✅ 仅读卡片 frontmatter 白名单 + body 段落抽取（与 v0.2.0/v0.2.1 一致）
- ✅ 仅读项目 profile frontmatter 白名单
- ✅ runs jsonl 仅记 metadata（target / project_profile_found / project_name / count / output_format）

---

## 3. Smoke 结果（隔离 /tmp + fake fixture）

| # | 命令 | exit | 备注 |
|---|---|---|---|
| 1 | `project context my-first-agent`（profile 提供 default_target=claude-code） | 0 | target=claude-code |
| 2 | `... --target copilot` | 0 | CLI 覆盖 profile |
| 3 | `... --target codex` | 0 | "高质量补丁 + 测试" 在输出中 |
| 4 | `... --target generic --format json` | 0 | JSON `version: 2` 通过解析 |
| 5 | `... --output /tmp/.../ctx.md` | 0 | 文件落盘 |
| 6 | `project context no-such-project`（无 profile） | 0 | 显示 `using Knowledge Cards only` |
| 7 | `... --target gpt99` | 2 | 错误打印合法集合 |

✅ 7/7；6 条凭据正则审计 0 hit；profile 正文塞的 `SECRET=sk-...` 0 泄漏；repo 根未污染。

---

## 4. 测试 / Lint / Diff

| 项 | 结果 |
|---|---|
| `pytest` | **187 passed**（v0.2.1 161 → +26 M5.3 用例） |
| `ruff check src tests` | clean |
| `git diff --check` | clean |

新增覆盖（`tests/test_m5_3.py`）：
- profile loader：缺失文件降级 / frontmatter 白名单 / 非法 default_target 静默丢弃 / 路径穿越拒绝
- `resolve_target` 三段路由 + invalid 报错
- 端到端 markdown：项目级优先 + 卡片级补充 + Excluded Content + 不漏 SECRET
- 无 profile 降级文案 / 不空标题
- target 覆盖 + runs jsonl 含 metadata
- invalid `--target` / invalid `--format` 各 exit 2
- JSON v2 schema：profile-found 与 cards-only 两态
- target-specific 措辞参数化 4 用例
- Suggested prompt 包含项目级 principles / preferred_workflow
- 凭据 6 正则反向断言（markdown / json / runs jsonl 三处）
- 拦截 httpx.Client.send：永不发请求；`.env` 在场也不被加载
- 卡片级**永不覆盖**项目级（顺序固定 + `from [card-id]` 来源透明）
- 所有结构化数据缺失时仍不出现空标题（正则反向断言）
- `--output` 与 `--target` 联合使用 / 父目录缺失 exit 2

---

## 5. 明确不做（仍坚守 v0.1 立柱）

- ❌ embedding / RAG / 向量检索
- ❌ Obsidian 插件
- ❌ AI 自动 approve / 自动写 ai_inference 进项目笔记
- ❌ 多 project 联合上下文（v0.2.x 后续考虑）
- ❌ 自动维护 `30-Projects/<name>.md` 追加块（v0.2.x 后续考虑）
- ❌ 任何 LLM 调用 / 自动复习调度 / token-aware routing
- ❌ 改写 `00-Inbox` / `20-Knowledge-Cards` / `30-Projects` 文件

→ 全部归到 [M5_BACKLOG.md](./M5_BACKLOG.md)。

---

## 6. 下一步建议

按推荐优先级：

1. **真实使用 1–2 周** — 用 `mindforge project context my-first-agent --target claude-code --output /tmp/ctx.md` 喂给 Claude Code，记录 prompt pack 的真实可用度。
2. 如果痛点是"想一次拉多个 project 的联合上下文" → 进入 **M5.3 后续**（多 project 联合）。
3. 如果痛点是"想自动追加到 30-Projects/<name>.md 的'已审核证据栏'" → 进入 **M5.3 后续**（幂等追加块）。
4. 如果想看自己用了哪些命令 → [**M5.7** Telemetry](./M5_BACKLOG.md#m57--real-usage-telemetry-without-content-leakage)。
5. **不**建议优先级：M5.4（RAG）/ M5.5（Obsidian 插件） — 极易过度工程。
