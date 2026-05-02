# Cubox Dry-Run Dogfood Guide

> 用本地 Cubox JSON export 做一次**预检**，验证 MindForge 能正确识别、
> 去重、并展示你打算交给后续流程的"原始材料"。
>
> 全程**不联网、不读 `.env`、不调真实 Cubox API、不调 LLM、不写 Obsidian
> vault、不生成 `human_approved`、不自动 approve**。

## 这个命令是什么 / 不是什么

**是**：

- 一个对**本地 JSON 文件**的只读预检入口；
- Cubox web → Settings → Export 导出的 JSON 文件的"哈希去重 + 计数 +
  抽样标题"展示器；
- 验证 mapping、dedup、source 安全边界的最小 dogfood 路径。

**不是**：

- 不是 Cubox 真实 API 客户端（`fetch_inbox` 显式 `NotImplementedError`）；
- 不是 ai_draft / 卡片生成入口（不会写任何卡片）；
- 不是 review / approve 入口（不会标记任何东西为 `human_approved`）；
- 不是 Obsidian 写入入口（不写 vault 任何文件）。

## 准备一份 export

两条路径任选其一：

1. **真实 export**：Cubox web → Settings → Export → JSON。**不要把真实
   导出文件提交到本仓库**——它包含你的私人收藏正文与可能的私人 URL；
2. **示例 fixture**：仓库自带 `tests/fixtures/sample_cubox_api_export.json`
   是 2 条**完全虚构**的样本数据，可直接用来熟悉命令。

## 跑命令

human-readable summary（默认）：

```bash
mindforge cubox dry-run --export tests/fixtures/sample_cubox_api_export.json
```

机器可读 JSON 一行：

```bash
mindforge cubox dry-run --export tests/fixtures/sample_cubox_api_export.json --json
```

限制 sample 标题展示条数（默认 3）：

```bash
mindforge cubox dry-run --export tests/fixtures/sample_cubox_api_export.json --limit 5
```

## summary 字段

| 字段 | 含义 |
|---|---|
| `items_seen` | export 中解析到的 item 总数 |
| `yielded` | 经 `SourceMux` 去重后保留的 SourceDocument 数 |
| `deduped` | 因 `content_hash` 重复被丢弃的 SourceDocument 数 |
| `by_source` | 每个 `source_type` 实际产出的数量；Cubox export 路径下固定为 `{cubox_api: N}` |
| `sample` | 至多 `--limit` 条 `{source_id_short, title}`，**不含**正文/URL/作者/标签/凭据 |

## 错误与边界场景

| 场景 | 退出码 | 提示 |
|---|---|---|
| `--export` 路径不存在 | `2` | `Cubox export 文件不存在：<path>` |
| JSON 解析失败 | `2` | `Cubox export JSON 解析失败：<path>（<msg> @ line N）` |
| 顶层不是 array | `2` | `Cubox export 内容非法：Cubox export 顶层必须是 array …` |
| 空数组 `[]` | `0` | `items_seen=0 yielded=0 deduped=0` |
| 同 `content_hash` 重复 | `0` | `deduped > 0`；`by_source` 仅记 yielded |

## 安全保证（与测试一一对应）

| 保证 | 守护测试 |
|---|---|
| 命令存在且可发现 | `test_cubox_group_appears_in_help` / `test_cubox_dry_run_appears_in_cubox_help` |
| `--export` 必填，不偷读 env | `test_cubox_dry_run_requires_export_arg` |
| missing file / malformed JSON 友好报错 | `test_cubox_dry_run_missing_file_user_friendly_error` / `test_cubox_dry_run_malformed_export_user_friendly_error` |
| summary 不泄露 token / body / URL / email | `test_cubox_dry_run_summary_does_not_leak_token_or_body` |
| 不联网 | `test_cubox_dry_run_does_not_open_network` |
| 不读 `.env` | `test_default_path_does_not_read_dotenv` + `test_parse_export_does_not_read_dotenv` |
| presenter 不调 LLM / approval / vault writer | `test_presenter_module_exists_and_has_no_forbidden_imports` |
| 核心 pipeline 不反向依赖 dry-run | `test_core_modules_do_not_import_dry_run_presenter` |
| 凭据不入 SourceDocument metadata | `test_source_document_metadata_does_not_carry_credential` / `test_parse_export_metadata_excludes_credential_fields` |

## 架构边界（一图速览）

```
mindforge cubox dry-run --export <path>
      │
      ▼
cubox_cli.cubox_dry_run         ← 薄 CLI adapter（解析 args / 处理用户错误）
      │
      ├── CuboxApiAdapter.parse_export(Path)   ← Cubox JSON → SourceDocument（mapping）
      │
      ├── SourceMux.feed(ScanResult)           ← 跨源去重（content_hash）
      │
      └── cubox_dryrun_presenter.render_*      ← 展示（text / json）

不参与本命令：
  Scanner（vault inbox 扫描的另一条 use-case 入口）
  KnowledgeStrategy / Pipeline（生成 ai_draft，需另走 `mindforge process`）
  ApprovalDecision / approval_service（审批，需另走 `mindforge approve`）
  vault writer / workspace（写 Obsidian，需另走 `mindforge obsidian`）
```

## 不要做的事

- 不要把真实 Cubox export 文件提交到仓库；
- 不要在 dry-run 输出基础上"自动 approve"或"自动写 vault"——这些路径
  仍然要走 `mindforge process` / `mindforge approve` / `mindforge
  obsidian`，并且 `human_approved` 必须显式确认；
- 不要试图通过 `--export` 传一个 URL 来触发 fetch——本命令只接受**本地
  文件**，未来真实 fetch 走独立 opt-in 通道。

## 下一步

当你确认 dry-run summary 看起来合理：

1. 想生成 ai_draft 卡片？走 `mindforge process --profile fake`（仍然不
   接真实 LLM，只用 FakeProvider）；
2. 想审阅候选 ai_draft？走 `mindforge approve list` / `mindforge
   approve show`；
3. 想跨源批量去重日常 inbox？把 `cubox_api` 加入 `configs/mindforge.yaml`
   的 `sources.enabled` 后，走 `mindforge scan`；`SourceMux` 是 opt-in，
   接入位置由调用方显式决定。

详见 [`USER_GUIDE.md`](./USER_GUIDE.md) 与 [`SECURITY.md`](./SECURITY.md)。
