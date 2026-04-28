# MindForge User Guide — v0.4.3

> 这是一份"工作手册"：每条命令、每个产物、每条边界都在这里查得到。
> 入门请先看 [`GETTING_STARTED.md`](./GETTING_STARTED.md)。
> 文档总览见 [`DOCS_INDEX.md`](./DOCS_INDEX.md)。
> 找不到命令？运行 **`mindforge commands`**（按场景分组）。
> 不知道下一步？运行 **`mindforge next`**（基于 vault 状态推荐）。

## 1. 命令地图

| 命令 | 用途 | 副作用 |
|---|---|---|
| `mindforge init [--vault PATH] [--interactive] [--dry-run] [--force]` | 一键铺 vault 骨架 + configs + `.env.example` | 写文件（仅 vault + configs） |
| `mindforge commands` | 按场景列出全部命令 + 一句中文用途 | 只读（纯静态） |
| `mindforge next [--format text\|json]` | 基于 vault 状态推荐下一步 | 只读 |
| `mindforge doctor` | 健康检查 + 下一步建议 | 只读 |
| `mindforge version` | 元数据 | 只读 |
| `mindforge scan` | 扫 inbox，建 SourceDocument，刷 state.json | 只读 source；写 state |
| `mindforge process [--limit N] [--file P]` | 跑 5-stage pipeline（默认 fake provider） | 写 Knowledge Cards + state + runs |
| `mindforge approve list/--card/--source-id/--all` | 把卡片晋升 human_approved | 仅写 frontmatter `status` |
| `mindforge index rebuild / status / info [--json]` | BM25 索引维护 | 写 `.mindforge/index/bm25.json` |
| `mindforge recall --query "..." [--ranking bm25|hybrid] [--explain] [--weight-*]` | 本地词法 + 多路融合检索 | 只读卡片 frontmatter + 白名单 body |
| `mindforge review due/mark/schedule/backlog/stats/weekly` | 复习计划与执行 | 仅 `mark` 写 4-5 字段 |
| `mindforge project list/context/update-evidence` | 项目上下文 + evidence 区块 | `update-evidence` 写 30-Projects 受控区块 |
| `mindforge vault index/links/refresh` | Obsidian 友好度（自动 _index/_link_candidates） | 仅写 _index.md 系列 |
| `mindforge llm ping/inspect [--profile]` | 真实 provider 体检 | 实际网络（仅 ping） |
| `mindforge telemetry status/summary` | 本地 telemetry 摘要 | 只读 |

全局 flag：
- `--config PATH` / `-c`：指定 mindforge.yaml；
- `--vault PATH`：临时覆盖 `vault.root`，**不**改 yaml；
- `--debug`：打开完整 traceback（默认压制）。

Shell completion:

```bash
mindforge --install-completion zsh
mindforge --show-completion bash
```

Completion 只影响 shell 命令补全，不改变 `--vault` / `--debug` / `--config`
的语义，也不会读取 vault 或 `.env`。

## 2. 关键产物

| 路径 | 性质 | 谁写 | 谁读 |
|---|---|---|---|
| `00-Inbox/<sub>/*` | **只读**原始材料 | 用户/外部工具 | scanner / adapters |
| `20-Knowledge-Cards/<track>/*.md` | AI 加工产物（默认 ai_draft） | writer / approve / review mark | recall / review / project context |
| `30-Projects/<name>.md` | 用户主笔记 + 受控 evidence 区块 | 用户 + `update-evidence` | project context |
| `.mindforge/state.json` | scan/process 状态机 | scanner / processor | scan / status / doctor |
| `.mindforge/runs/*.jsonl` | 每次 run 的事件链路 | RunLogger | telemetry summary（白名单） |
| `.mindforge/index/bm25.json` | BM25 索引 | index rebuild | recall |
| `.mindforge/telemetry.jsonl` | 本地 only telemetry | 全局 hook | telemetry status/summary |
| `40-Reviews/*.md` 或 `/tmp/*.ics` | 周报 / iCal 导出 | review weekly / schedule | 用户手动消费 |

## 3. 安全契约（不可放宽）

1. **不读 `.env` 内容**：`doctor` 仅检查 `.env` 是否在 `.gitignore`；
2. **不调真实 LLM**：默认 `active_profile=fake`；切真实前必须 `mindforge llm ping`；
3. **不联网**：BM25 / hybrid / iCal / weekly / project context 全部本地；
4. **不修改 raw source**：所有 inbox 文件只读；
5. **不自动 approve**：人工把 `status` 改成 `human_approved` 才算长期记忆；
6. **telemetry 字段白名单**：仅 10 项元数据，**绝不**记录 query / title / body；
7. **`review mark --note`** 强约束：单行 ≤200 字符；多行/超长 fail-fast；
8. **iCal 仅本地导出**：不接系统日历，不请求权限；
9. **PDF/Docx 只做最小文本**：不做 OCR、不做表格、不做图片解析；
10. **`update-evidence`** 只写 START/END 区块，**不**写 raw_text / prompt / completion。

## 4. 错误处理（v0.4.1）

| 场景 | 现象 | 处置 |
|---|---|---|
| `mindforge.yaml` 不存在 | 友好中文提示，建议 `mindforge init` | exit 2 |
| vault 目录缺失 | doctor 给 init 提示；命令本身降级 | exit 0/2 |
| 卡片 frontmatter 损坏 | `review mark` exit 3，错误说明在哪行 | exit 3 |
| BM25 索引 stale / 配置漂移 | recall 自动用当前配置内存重建一次 + 警告；建议 `index rebuild` | exit 0 |
| optional 依赖缺失（pypdf/python-docx） | `OptionalDependencyError("pip install mindforge[pdf]")` | exit 1 |
| LLM provider 错配 | `mindforge llm ping` 显式失败；`process` 提前 fail-fast | exit 1 |
| `.env` 存在但未 gitignore | doctor 红色警告 | exit 0（仅警告） |

未传 `--debug` 时一律压制 traceback，仅打印简短中文错误 + 建议命令。

## 5. 典型工作流

### 5.1 每日 5 分钟
```
mindforge scan
mindforge process --limit 10
mindforge approve list                  # 决定是否晋升
mindforge review backlog                # 看欠了多少
```

### 5.2 周末复盘
```
mindforge review weekly --output ~/MindForgeVault/40-Reviews/$(date +%F).md
mindforge review schedule --days 7 --format ical -o /tmp/next-week.ics
mindforge project context <project> --target claude-code -o /tmp/context.md
```

### 5.3 项目召回（Claude Code / Copilot 协作）
```
mindforge recall --query "agent runtime checkpoint" --ranking hybrid --explain
mindforge project context my-first-agent --target claude-code
```

## 6. 不支持（明示边界，避免误用）

- ❌ 不做 RAG / embedding / 向量库
- ❌ 不做 Obsidian 插件
- ❌ 不做浏览器插件
- ❌ 不做 OCR / 扫描件 PDF
- ❌ 不做云端同步
- ❌ 不做后台调度 / 系统通知（review schedule 只是导出）
- ❌ 不做 SM-2 / FSRS（区间走配置 `cfg.review.intervals`）
- ❌ 不做自动复习提醒 / 邮件 / 桌面通知

如果未来要做，遵循 [`M5_BACKLOG.md`](./M5_BACKLOG.md) 里的"先 spike，再决策"流程。
