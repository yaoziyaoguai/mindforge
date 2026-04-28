# v0.4.1 复盘 — Review Polish + Onboarding

## 范围
- `review schedule --format ical [-o file]`：本地 .ics 导出，RFC 5545 极简
  VEVENT，UID 用 `card.id@mindforge.local` → 用户重复导入不会出现重复事件。
  **不**接系统日历、**不**联网、**不**请求权限。
- `review weekly [--format markdown|json] [-o file]`：周报，frontmatter
  结构化汇总；section：Overdue / Due this week / Reviewed this week /
  Forgotten or partial / Suggested focus tracks（按 backlog × forgotten 加权
  纯计数）/ Project distribution / Next week preview。**不**调 LLM。
- `mindforge doctor`：新增 review hint —— overdue 提示 `review backlog`，
  本周内 due 提示 `review schedule --days 7`。
- 新增文档：`docs/ROADMAP_PROGRESS.md`、`docs/GETTING_STARTED.md`、
  `docs/USER_GUIDE.md`、`docs/V0_4_REVIEW_SCHEDULING_PROTOCOL.md` 已含 ical 段落。
- 测试 10 项：iCal stdout / 写文件 / UID 稳定 / weekly markdown 结构 /
  weekly JSON schema / weekly 不改卡 / weekly 不发 HTTP / doctor overdue hint /
  doctor due-this-week hint / iCal+weekly telemetry 不泄漏。
- 版本：`0.4.0 → 0.4.1`。

## 不做（明示）
- 不接系统日历；用户自己导入；
- 不调 LLM；不读 .env；不联网；不引 embedding；
- 不做后台调度 / 桌面提醒 / 邮件；
- 不改 status；不自动 approve；不写 raw source；
- weekly suggested focus 是**纯计数**，不预测 / 不语义推断；
- PDF/Docx 不做 OCR（继续保持 v0.2.5 边界）。

## 测试 / 质量
- pytest: **327 passed, 2 skipped**（v0.4.0 的 317 + 10 新）
- ruff: clean
- git diff --check: clean
- 真实 smoke：doctor / schedule json / schedule ical / weekly markdown / recall hybrid 全绿

## PDF/Docx 现状
- v0.2.5 已经把 `PdfAdapter` / `DocxAdapter` 落到 lazy import + extras
  `mindforge[pdf,docx,docs]`；
- 扫描件 PDF → `PdfNoTextError` 不降级；
- v0.4.1 不再扩 PDF/Docx 能力，避免不必要的依赖膨胀；后续若要做大文件
  / 多语言段落策略，列入 backlog。

## 兼容性
- `review schedule` 默认行为不变；新增 `ical` 是第三个 `--format`；
- `review weekly` 是新命令；
- `_render_ics` / `_ics_escape` 是 cli 内部 helper，不进 public API；
- doctor 新 hint 仅追加，不改既有行为。

## 下一步建议
1. **真实 dogfooding 1–2 周**（强烈推荐）：v0.4.1 的产品边界已收敛，
   再加更多代码不如先验证产品假设；
2. 如果想继续推进：可做 `mindforge init --interactive` + 错误信息中文化全
   覆盖；
3. M5.1 PDF/Docx 完善（`--max-pages`、空页跳过）按 dogfooding 真实需求决定；
4. M6 RAG/embedding 仅 docs/POC，不入主干。
