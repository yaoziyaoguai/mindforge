# Topic View API 契约（v0.5）

稳定 API 契约，供前端和其他消费者开发使用。

## 接口端点

### `GET /api/topics`

列出所有包含 `human_approved` 卡片的 topic 名称。

**响应**（`TopicListResponse`）：
```json
{
  "topics": ["Python", "React"]
}
```

- 无卡片时返回 `{"topics": []}`
- 只包含有 `human_approved` 卡片的 topic；仅含 `ai_draft` 的 topic 不出现在列表中

### `GET /api/topics/{topic_name}`

获取指定 topic 的运行时视图。

**响应**（`TopicViewResponse`）：
```json
{
  "topic": "React",
  "total_approved_cards": 2,
  "type_counts": {"concept": 1, "claim": 1},
  "cards": [
    {
      "id": "card-1",
      "title": "React Hooks",
      "knowledge_type": "concept",
      "relations": [{"type": "supports", "target_id": "card-2"}],
      "tags": ["react", "hooks"],
      "summary": "React hooks are a fundamental pattern...",
      "human_note": "Approved with corrections",
      "approval_state": "human_approved",
      "value_score": 5,
      "source_title": "React Docs",
      "source_type": "web_page",
      "track": "React",
      "created_at": "2026-05-10T00:00:00",
      "approved_at": "2026-06-01T12:00:00"
    }
  ]
}
```

### 卡片字段

| 字段 | Type | Nullable | 描述 |
|-------|------|----------|-------------|
| `id` | `string` | yes | 卡片唯一 ID |
| `title` | `string` | yes | 卡片标题 |
| `knowledge_type` | `string` | no | 知识类型，默认 `"concept"` |
| `relations` | `list[object]` | no | 语义关系列表 |
| `tags` | `list[string]` | no | 标签列表 |
| `summary` | `string` | no | 安全摘要（从 approved body 提取，不调 LLM） |
| `human_note` | `string` | yes | 审批时的人工备注 |
| `approval_state` | `string` | no | 始终为 `"human_approved"` |
| `value_score` | `int` | yes | 价值评分 |
| `source_title` | `string` | yes | 来源标题 |
| `source_type` | `string` | yes | 来源类型 |
| `track` | `string` | yes | 所属 track/topic |
| `created_at` | `string` | yes | ISO 8601 创建时间 |
| `approved_at` | `string` | yes | ISO 8601 审批时间 |

### 错误行为

- **未知/空 topic**：`404 Not Found`，返回 `{"detail": "Topic 'X' not found or has no approved cards"}`
- **topic 下无已审批卡片**：`404 Not Found`（同上）

### 已知限制

- **基于路径的 topic 名称编码**：`GET /api/topics/{topic_name}` 使用 FastAPI 路径参数。包含 `/` 的 topic 名称（如 `"Programming/Python"`）在不转义的情况下无法在标准 URL 路径中编码。未来版本可能改用查询参数（如 `GET /api/topics?name=...`）或使用 URL 安全的 slug 编码来支持 topic 名称中的 `/`。作为后续事项跟踪。

### 审批边界

- 只有 `status: human_approved` 的卡片出现在视图中
- `ai_draft`、`trashed` 等状态的卡片被严格排除
- `summary` 从已审批卡片 body 的 `## AI Summary` section 安全提取，不调用 LLM
