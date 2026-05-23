# UI Copy Policy

MindForge Web 的用户界面文案本地化策略。本条适用于所有面向用户的 Web UI 文本。

## 核心规则

### 1. 用户可见 UI copy 必须本地化

所有用户可见的 UI 文本（标题、说明、按钮、状态标签、操作文案）必须通过 `web/src/lib/i18n.ts` 的 `t(key)` 函数获取，支持 zh/en 切换。

```tsx
// CORRECT
<h1>{t("home.title")}</h1>

// WRONG — 硬编码文案
<h1>首页</h1>
```

### 2. 技术标识符降级展示

后端 internal status code、model ID、strategy ID 等机器可读标识符，在前端仅作为次要信息展示（小字、灰色、括号内），满足开发排查需要。用户侧主展示使用 `friendlyStatus()` 等 display mapping 函数。

### 3. 用户内容不翻译

以下内容属于用户数据或专有标识，**禁止翻译**：
- 卡片正文（body）、卡片标题
- source title、source path
- 用户自定义的 model ID、run_id
- 产品名 "MindForge"、算法名 "BM25"
- adapter 名称

### 4. 格式名保留原文，周围说明必须本地化

- Markdown、PDF、HTML、JSON 等格式名作为专有名词，保留原名
- 格式名周围的说明性文本（"支持格式：Markdown, PDF, HTML"）必须本地化
- 技术标识同理：BM25、LLM、API key 保留原名，说明文案本地化

### 5. NextAction action_key 契约

后端 `NextAction` schema 包含可选字段 `action_key: str | None`：
- `action_key` 是稳定的 machine-readable identifier，不对应具体语种的文案
- 前端通过 `nextActionLabel(action_key, locale)` 做 display mapping
- 缺 `action_key` 时，安全 fallback 到 `action.label`
- 禁止用 `action.label` 做字符串匹配判断语言

### 6. 后端不翻译，前端处理 display mapping

后端 API 返回 machine-readable identifiers。前端负责 human-readable labels。
多语言切换是纯前端关注点，不应耦合到 API contract。

## 防回归清单

以下场景容易引入中英混用，变更时必须检查：

| 场景 | 危险信号 | 正确做法 |
|------|---------|---------|
| 新增 NextAction | label 硬编码英文 | 添加 action_key + nextActionLabel() 映射 |
| 新增状态标签 | 直接展示 status code | 通过 friendlyStatus() 或 statusLabel() 映射 |
| 新增页面 | 未注册 i18n key | 在 i18n.ts 的 zh/en 两处添加 key |
| 操作按钮文案 | 直接用英文 label | 使用 `t()` 包装 |
| 空状态提示 | 硬编码混合文案 | 使用 EmptyState 组件 + 传入 locale |
| 格式/技术说明 | 周围中文夹杂英文名词 | 名词保留，说明本地化 |

## 已有 display mapping 函数

| 函数 | 用途 |
|------|------|
| `friendlyStatus(status, locale?)` | ai_draft → "待确认" / "Pending Review" |
| `statusLabel(status, locale?)` | ok → "正常" / "OK" |
| `nextActionLabel(key, locale?)` | init_vault → "初始化知识库" / "Initialize vault" |
| `workflowStepLabel(stepId, locale?)` | triage → "初筛" / "Triage" |
| `strategyStatusLabel(status, locale?)` | default workflow → "默认工作流" |
| `sourceStatusLabel(status, locale?)` | active → "监控中" / "Watching" |
| `sourceRunStatusLabel(status, locale?)` | running → "处理中" / "Running" |
| `sourceDueStatusLabel(status, locale?)` | overdue → "已逾期" / "Overdue" |

## 测试覆盖

`tests/test_web_product_copy.py` 包含回归测试，验证：
- 所有 StatusLabel 映射 key 有对应 i18n entry
- 所有 NextAction action_key 有对应 display mapping
- i18n 中不存在硬编码的中英混用模式
