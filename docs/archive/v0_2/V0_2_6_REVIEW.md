# MindForge v0.2.6 Review

> v0.2.6 = 日用化版本。重点是"新用户能 init / 能日常 approve / 能自查"，
> 不是堆功能。仍然不调用真实 LLM、不读 .env、不上传 telemetry。

## 增量

### 1. `mindforge init`（新）

- 创建 vault 骨架（`00-Inbox/{Cubox,WebClips,ChatExports,PDFs,Docs,ManualNotes}` /
  `20-Knowledge-Cards/` / `30-Projects/` / `80-Reviews/` / `90-System/` /
  `_attachments/`）
- 拷贝 `configs/{mindforge.yaml,learning_tracks.yaml,llm.example.yaml}` 到目标 project_root
- 创建 `.env.example`（**不**创建真实 `.env`）
- 自动改写新 yaml 中的 `vault.root` 指向本次 `--vault`，避免 doctor 体验割裂
- `--dry-run` 仅打印 plan
- `--force` 仅覆写 MindForge 自带的模板文件，**不**碰用户已建的目录/卡片
- 多次运行幂等

### 2. Approve workflow polish

- `mindforge approve --card <path>`：保留向后兼容，仍是最安全主路径
- `mindforge approve --source-id <id>`：通过 state.json 反查 card_path 再批准
- `mindforge approve --all`：默认拒绝，必须 `--dry-run` 预览或 `--confirm` 真正执行；可选 `--limit N`
- `mindforge approve list [--status … --project … --track … --format table|json]`：
  默认列出 ai_draft；输出仅安全字段（title / path / status / track / projects /
  source_type / created_at / value_score）；**不**读卡片正文
- 仍只允许 `ai_draft → human_approved`；其他状态拒绝；`human_approved` 幂等

### 3. Doctor 增强

新增 actionable hints：
- vault 缺目录 → 建议 `mindforge init --vault <path>`
- `active_profile` 不在 `llm.profiles` → 提示检查 yaml
- 无卡片 → 建议 `scan && process`
- 有 ai_draft 堆积 → 建议 `approve list`
- `active_profile` 非 fake → 建议先 `llm ping` 校验环境变量

仍**不**读 .env 内容、**不**发 HTTP。

### 4. 文档

- 新增 `docs/ONBOARDING_SMOKE.md`：5 分钟新用户全链路，**全程 fake provider**
- 新增本文 `docs/V0_2_6_REVIEW.md`
- 更新 `README.md` / `docs/ROADMAP.md` / `docs/V0_2_FINAL_REVIEW.md`

## 测试

- 255 passed, 2 skipped (pypdf/python-docx 未装时跳过真实抽取)
- 新 `tests/test_v0_2_6.py` 15 例覆盖：init dry-run/真实/幂等/--force / approve 向后兼容 /
  approve list 默认/过滤/JSON 安全字段 / approve --all dry-run/无 confirm 拒绝/有 confirm 限量 /
  approve --source-id 反查 / approve 无参友好提示 / doctor action items（草稿堆积 + vault 缺失）

修复了一个潜在测试污染：`--vault` 全局 flag 写入 `MINDFORGE_VAULT_OVERRIDE` env，
未传时**必须**从 env 清除，否则跨 CliRunner 调用会泄漏。

## 不做的事（仍坚守）

- ❌ 真实 LLM
- ❌ `.env` 内容读取
- ❌ telemetry 上传
- ❌ 自动 approve
- ❌ 修改原始 source
- ❌ 修改 Knowledge Card 正文（approve 仅改 frontmatter）
- ❌ RAG / embedding / OCR / Obsidian 插件
- ❌ 自动复习调度

## 下一步

- v0.2 系列已五连发（v0.2.0–v0.2.6），全部本地未 push
- 下一步候选：approve workflow 再增强（按 track 批量、approve 历史）/ `mindforge logs` /
  v0.3 进入 BM25 lexical recall
