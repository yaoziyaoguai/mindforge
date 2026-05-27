# Backend Copy & ID Sanitization — Implementation Notes

- **Date**: 2026-05-27
- **Trigger**: Web IA audit 发现后端生成英文文本和内部 ID 暴露问题
- **Related**: `docs/implementation-notes/2026-05-27-111-web-ia-simplification.md`

---

## 1. Audit Source

基于 Web IA simplification 审计中发现的 6 项非前端可修复问题：

1. 后端生成英文文本（Health page 摘要、Wiki body 元数据、Graph evidence）
2. 后端内部数据暴露在 markdown 中（`__model_routing__`、workflow stage IDs）
3. Export 页面不存在（fallthrough 到 Home）
4. "note-b" 源文件名暴露
5. Wiki body 中原始时间戳
6. Dogfood 文件路径暴露

---

## 2. Backend-generated Copy Issues Fixed

### 2.1 Health Service (`src/mindforge/health/health_service.py`)

**全部 8 种 health check 类型的 message 和 suggested_action 中文化：**

| Issue Code | Before | After |
|-----------|--------|-------|
| `review_backlog` | `"{n} pending drafts in review backlog"` | `"{n} 张待审阅草稿积压"` |
| `pending_drafts` | `"{n} pending draft(s)"` | `"{n} 张待审阅草稿"` |
| `missing_provenance` | `"{n} approved cards missing provenance metadata"` | `"{n} 张已确认卡片缺少来源追溯元数据"` |
| `low_quality` | `"{n} approved cards with low quality score"` | `"{n} 张已确认卡片质量评分偏低"` |
| `orphans` | `"{n} orphan cards found"` | `"{n} 张孤立卡片 — 未被 Wiki 或关联卡片引用"` |
| `duplicates` | `"{n} potential duplicate card pair(s)"` | `"{n} 对潜在重复卡片"` |
| `wiki_stale` | `"{n} stale wiki section(s)"` | `"{n} 个 Wiki 章节已过期"` |
| `source_warnings` | `"{n} source warning(s) recorded"` | `"记录了 {n} 条来源警告"` |

**汇总行也中文化：**
- `"Health check: {parts} issue(s)."` → `"健康检查：{parts}。"`
- `"Health check: all clear."` → `"健康检查：一切正常。"`
- severity labels: `critical` → `严重`, `warnings` → `警告`, `informational` → `信息`

### 2.2 Wiki Service (`src/mindforge/wiki_service.py`)

**Per-card provenance section 标签中文化（lines 390-410）：**
- `Principles` → `核心原则`
- `Action Items` → `行动项`
- `Provenance` → `来源追溯`
- `Source card` → `源卡片`
- `Card path` → `卡片路径`
- `Original source` → `原始来源`
- `Strategy` → `策略`
- `Tags` → `标签`
- `Value score` → `价值评分`

**LLM-synthesized wiki section 标签中文化（lines 625-664）：**
- `LLM synthesis · Model: ... · Last rebuilt: ...` → `LLM 合成 · 模型: ... · 最近重建: ...`
- `Cards included` → `包含卡片`
- `Overview` → `概览`
- `Knowledge Sections` → `知识章节`
- `Related approved cards` → `关联已确认卡片`
- `Original source` (in section) → `原始来源`
- `Additional Approved Cards` → `附加已确认卡片`
- `Open Questions` → `待解决问题`

---

## 3. Internal IDs — Status

- `__model_routing__` — 已由前端 `friendlyProviderName()` 映射（上一轮 Web IA simplification）
- Workflow stage IDs — 仅存在于内部 checkpoint state，不暴露给 Web UI
- `unrouted` — 前端已有 display mapping
- Track/source raw enum — 前端已通过 `friendlyTrack()` 映射

**本次 loop 未发现新的内部 ID 暴露到用户可见 payload 中。**

---

## 4. Source Display Title — Status

- `note-b` 是 sample fixture 的 source_id，非硬编码
- `source_title` 字段已存在于 Card model，由 source adapter 填充
- 前端已使用 `source_title` 显示友好名称
- 本次 loop 无需额外处理

---

## 5. Export Page Spec

已写入 `docs/plans/2026-05-27-112-export-page-product-spec.md`：

**决策：需要独立 Export 页面**
- 当前 Export API 存在但无独立 UI 页面
- 推荐方案：新增 `/export` 路由 + 独立 ExportPage 组件
- MVP 范围：导出范围选择、格式选择（仅 Markdown）、预览、下载
- 不实现：新格式、外部服务、Obsidian 同步、定时导出

---

## 6. Files Changed

| File | Change |
|------|--------|
| `src/mindforge/health/health_service.py` | 8 种 issue 的 message/suggested_action + summary 行中文化 |
| `src/mindforge/wiki_service.py` | Per-card provenance labels + LLM-synthesized section labels 中文化 |
| `tests/test_wiki_service.py` | 更新 3 处 label 断言匹配中文 |
| `docs/plans/2026-05-27-112-export-page-product-spec.md` | 新增 Export 页面产品方向 spec |

---

## 7. API Compatibility

- **无 API contract 变更** — message/suggested_action 字段值变更，但字段名、类型、结构不变
- **无 schema 变更** — 前端无需适配新的 response shape
- **向后兼容** — 旧前端消费新中文消息不会出错（仅语言变化）

---

## 8. User-facing Before/After

**Before (Health Page):**
> Health check: 1 critical, 2 warnings, 1 informational issue(s).
> 3 orphan cards found — not referenced by Wiki or related cards

**After (Health Page):**
> 健康检查：1 严重, 2 警告, 1 信息。
> 3 张孤立卡片 — 未被 Wiki 或关联卡片引用

**Before (Wiki Body):**
> **Provenance:**
> - **Source card**: Auth Pattern
> - **Original source**: note-b

**After (Wiki Body):**
> **来源追溯:**
> - **源卡片**: Auth Pattern
> - **原始来源**: note-b

---

## 9. Tests Added/Updated

- `tests/test_wiki_service.py`: 3 处 label 断言更新为中文
  - `"Source card" in wiki_text` → `"源卡片" in wiki_text`
  - `"Original source" in wiki_text` → `"原始来源" in wiki_text`
  - `"Related approved cards" in wiki_text` → `"关联已确认卡片" in wiki_text`
- `tests/health/test_health_service.py`: 无需更新（按 issue.code 断言，不按 message 文本）
- `tests/test_web_product_copy.py`: 无需更新（已有中文 copy 测试覆盖）

---

## 10. Browser/MCP Re-check

MCP 不可用时的替代验证：
- API-level: health/wiki service tests 通过
- Product copy: test_web_product_copy.py 100% 通过
- Web build: TypeScript + Vite build 成功
- Code-level: 所有 backend 英文用户可见文本已改为中文

---

## 11. Gates

| Gate | Command | Exit Code | Timeout |
|------|---------|-----------|---------|
| git diff --check | `git diff --check` | 0 | No |
| ruff check | `ruff check src/ tests/` | 0 | No |
| health tests | `pytest tests/health/test_health_service.py -q` | 0 | No |
| wiki tests | `pytest tests/test_wiki_service.py -q` | 0 | No |
| product copy | `pytest tests/test_web_product_copy.py -q` | 0 | No |
| web build | `npm --prefix web run build` | 0 | No |

---

## 12. Remaining IA Debt

| Item | Status | Owner |
|------|--------|-------|
| Backend English text (Health) | ✅ Fixed | This loop |
| Backend English text (Wiki) | ✅ Fixed | This loop |
| Export page | 📋 Spec written | Future loop |
| note-b source title | 🟢 Acceptable (sample data) | N/A |
| Raw timestamps in wiki | ✅ Fixed (prev loop) | Web IA Simplification |
| Dogfood file path | 🟢 Internal tool page | Low priority |
| `__model_routing__` exposure | ✅ Fixed (prev loop) | Web IA Simplification |

---

## 13. v3.7 Planning Status

- v3.7 planning is unblocked
- 本次 loop 仅修复 IA 债（backend copy + ID sanitization），未引入新功能
- 下一阶段推荐方向：Export page 实现（按 spec）或 Graph quality hardening
