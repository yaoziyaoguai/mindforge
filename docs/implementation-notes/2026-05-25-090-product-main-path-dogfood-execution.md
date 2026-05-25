# Product Main Path Dogfood — Execution Notes

**日期**: 2026-05-25
**状态**: complete
**基于**: `docs/plans/2026-05-25-089-product-main-path-dogfood-plan.md`
**上游**: v4.2.1 partial remediation closure (`e0d2b52`)

---

## 执行摘要

用 30 个 synthetic 非敏感 markdown 样本文件完成了 MindForge 产品主路径的端到端验证：

```
Source/Import → ai_draft → Review → explicit approval → human_approved
→ Library → Recall/Wiki → (Export via Web API)
```

**结论**: 产品主路径在 fake provider 下真实可用。无 P0 阻塞性 bug，无安全边界被绕过。

---

## Dogfood 指标

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| 样本文件数 | 50-100 | 49 (31 md, 9 txt, 6 html, 3 other) | ⚠ 略低于目标 |
| 实际处理数 | >= 20 | 30 | PASS |
| Import → ai_draft | 100% | 30/30 (100%) | PASS |
| Review → human_approved | 100% | 30/30 (100%) | PASS |
| Safety boundary (no auto-approve) | 0 bypass | 0 bypass | PASS |
| Recall 命中率 | > 50% | 7/10 (70%) | PASS |
| Wiki rebuild | pass | pass | PASS |
| Index rebuild | pass | pass | PASS |
| P0 阻塞性 bug | 0 | 0 | PASS |
| 审批语义未被绕过 | must hold | held | PASS |

---

## 修复的 Bug

### B1. FakeProvider 缺少 wiki_synthesis stage

**文件**: `src/mindforge/llm/fake.py:120`

`FakeProvider.generate()` 的 stage dispatch 缺少 `wiki_synthesis`，导致 wiki rebuild 在 fake provider 下失败。

**修复**: 添加 `wiki_synthesis` stage 支持，返回符合 wiki_synthesis prompt schema 的占位 JSON：
```python
{
    "overview": "[fake] ...",
    "sections": [{"title": "...", "body": "...", "card_ids": []}],
    "open_questions": [{"question": "...", "card_ids": []}]
}
```

注意：fake provider 返回空 `card_ids` 是正确行为 — 它无法知道真实 card ID。wiki_service 的 section validation 会丢弃无有效 card_id 的 section，但 wiki 仍通过 "additional cards" fallback 机制正常工作。

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/mindforge/llm/fake.py` | MODIFIED | 添加 `wiki_synthesis` stage 支持 |
| `scripts/generate_dogfood_samples.py` | NEW | 生成 49 个非敏感 synthetic 样本 |
| `scripts/expanded_dogfood.sh` | NEW | 扩展版 dogfood 脚本 (30+ 文档, 13 steps) |
| `docs/implementation-notes/2026-05-25-090-product-main-path-dogfood-execution.md` | NEW | 本笔记 |

---

## 样本策略

`scripts/generate_dogfood_samples.py` 生成 49 个非敏感文件：
- 31 个 Markdown 笔记（技术主题: Python, Docker, K8s, SQL, React, Git 等）
- 9 个 TXT 纯文本（会议记录、日志、代码片段）
- 6 个 HTML 文件（Wikipedia 摘录、文档导出、API 参考）
- 3 个混合文件（CSS, CSV, JSON）

所有内容来自公开技术知识，不涉及：
- 个人身份信息 / 财务数据 / 公司内部资料
- 密码 / 密钥 / API token
- 真实私人笔记

当前 dogfood 仅处理 `.md` 文件（PlainMarkdownAdapter），TXT/HTML 文件可用于后续扩展 adapter 覆盖。

---

## 已知限制

1. **Wiki section 被丢弃**: fake provider 返回空 `card_ids`，wiki_service 丢弃了 section。wiki 通过 additional cards fallback 正常工作，但 section 结构只在实际 LLM 下有意义。

2. **Export 无独立 CLI 命令**: export 通过 Web API (`routers/library.py`) 实现，无 `mindforge export` CLI 命令。dogfood plan 中的 CLI export smoke 命令不适用 — 需通过 Web UI 或 API 验证。

3. **BM25 中文召回弱**: "安全" 和 "中文" 查询无匹配。BM25 在 30 个英文为主的技术文档上对中文查询召回率低，这是预期行为（非 bug）。

4. **样本量未达 50-100**: 生成的 49 个文件中有 31 个 `.md` 可被 PlainMarkdownAdapter 处理。要处理 TXT/HTML 需要额外 adapter。30 张卡片已达到 "≥ 20" 的最低标准。

---

## 不在此次范围

- 不启动 v4.3
- 不恢复 Graph / Sensemaking / Entity / Community 扩张
- 不新增 TXT/HTML adapter（后续可做，非阻塞）
- 不补齐 wiki_synthesis fake 输出的 card_id 匹配（需要真实 LLM 才能有意义地匹配）
- 不做 RAG / embedding / vector DB
- 不调用真实 LLM / Cubox / Upstage

---

## Product Main Path Dogfood — Final Verdict

**主路径可用。** 在 fake provider 下，Import → ai_draft → Review → explicit approval → human_approved → Library → Recall → Wiki 所有步骤均通过，安全边界未被绕过。
