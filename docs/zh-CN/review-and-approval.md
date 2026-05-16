# 审阅与审批

AI 生成的是草稿（`ai_draft`），仅供预览。必须显式审批才能成为正式知识（`human_approved`）。

---

## 核心原则

**审批永远是显式确认。没有自动 approve。**

---

## 卡片状态

| 状态 | 含义 |
|------|------|
| `ai_draft` | AI 生成的草稿，仅供预览。不进入 Library，不参与 Recall，不进入 Wiki |
| `human_approved` | 你显式审批后的正式知识。进入 Library，可被 Recall 检索，参与 Wiki 生成 |

---

## CLI 审批

```bash
# 列出待审批草稿
mindforge approve list

# 查看草稿摘要
mindforge approve show --card 1

# 查看完整草稿内容
mindforge approve show --card 1 --show-content

# 显式审批
mindforge approve 1 --confirm
```

---

## Web 审批

1. 打开 Web 控制台，进入 **Review** 页面
2. 查看 AI 生成的草稿内容
3. 确认后点击 **Approve**
4. 二次确认后草稿进入 `human_approved`

---

## Processing Workflow

处理每个 source 经历五个固定 step：

| Step | 说明 |
|------|------|
| Triage | 评估 source 价值，给出 track / value_score |
| Distill | 提取核心知识，生成卡片主体 |
| Link Suggestion | 建议相关主题和链接 |
| Review Questions | 生成复习和自测问题 |
| Action Extraction | 提取可跟进 action items |

每个 step 可分配不同模型（model routing），在 Web Setup 中配置。

---

## 安全边界

- AI 草稿不会自动成为正式知识
- 未审批内容不进入 Library / Recall / Wiki
- 审批后编号失效，需重新 `approve list` 查看
- Triage 判定低价值的 source 会被 skip，不会生成草稿
