# MindForge Web UI 后端差距日志

最后更新: 2026-06-02

本文档用于防止参考图片重新设计暗示尚不存在的后端能力。

## Batch 1: Shell、Home、Setup

| 页面/类型 | 参考图片的 UI 期望 | 当前后端/API 支持程度 | 当前 UI 行为 | 所需后端工作 | 优先级 | 当前 UI 可否安全展示？ | 原因 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Home / Welcome Desk | Sources、AI Drafts、Ready for Review、Approved Knowledge 的概览卡片 | 部分支持 | 当 `/api/workflow/summary` 存在时显示真实数据；否则回退到 `/api/home/status` 工作区/vault/安全计数 | 如果产品需要更丰富的来源新鲜度或按阶段增量，添加显式的首页仪表盘摘要字段 | P1 | 是 | 显示的计数来自已有状态 API，或为明确的最小回退值；未渲染伪造卡片。 |
| Home / Welcome Desk | 知识流：Import -> AI Draft -> Human Review -> Approved Knowledge -> Export | 产品语义层面完整支持，按步骤的实时活动部分支持 | 使用真实产品状态和链接的静态说明性流程图 | 可选的按步骤实时状态端点，供未来 UI 展示进度详情 | P2 | 是 | 流程图解释当前生命周期边界；未声明超出已有状态的实时管线自动化。 |
| Home / Welcome Desk | 首次运行配置真实模型卡片 | provider readiness/status 支持，一键设置不支持 | 状态卡片和 CTA 仅跳转到 Setup | 状态无需后端工作；未来改进可返回推荐设置预设 | P2 | 是 | 侧边栏/首页卡片是状态展示和导航，非隐藏的 provider 激活操作。 |
| 侧边栏 | Demo 模式/配置真实模型卡片 | 部分支持 | 使用 `SafetySummary.provider_state`；CTA 导航到 `/setup` | 可选的更丰富的 provider readiness 原因摘要 | P2 | 是 | 仅区分 demo 和就绪 provider，不修改 provider 模式。 |
| Setup / 模型配置 | Provider -> Connection -> Model -> Validate/Test 引导 | 部分支持 | 引导使用 `ConfigStatusResponse.provider` 和 `/api/config/editable`；现有表单仍通过当前 API 保存 | 如果未来 UI 需要服务端编写的步骤，后端可暴露首次运行设置向导形状 | P2 | 是 | 引导是对现有可编辑配置/就绪状态的 UI 组织层。 |
| Setup / 模型配置 | 验证/测试已配置的 provider | 部分支持 | `Validate Config` 调用现有 `validateSetupConfig`；未触发真实 LLM smoke/test | 如果产品需要端点/认证验证但不生成内容，添加显式非生成式 readiness 测试端点 | P1 | 是 | UI 将 Validate/Test 标记为配置验证，并声明不会发生真实 LLM 调用。 |
| Setup / 模型配置 | Provider 预设：Qwen / OpenAI-compatible / Anthropic-compatible / Custom | 部分支持 | OpenAI-compatible 和 Anthropic-compatible 显示为受支持映射；Qwen 和 Custom 标记为手动端点配置 | 仅在后端支持 provider 特定默认值和验证时才添加一等 provider 预设 | P2 | 是 | 预设是说明性卡片，非伪造的一键集成。 |
| Setup / 模型配置 | API key 显示 | 支持 | 输入为只写；已配置的 key 仅通过可编辑配置中的存在/掩码状态显示 | Batch 1 无需后端工作 | P0 | 是 | 保留 secret 边界；不显示明文 API key。 |
| Setup / 模型配置 | 配置完成 -> 跳转到 Sources/Drafts | 导航支持，上下文推荐部分支持 | 保存/验证后引导文本指向 Sources；无自动跳转 | 可选的 next-action 端点可根据当前状态建议 Sources 还是 Drafts | P3 | 是 | 引导仅为文案和导航；无伪造的完成状态。 |

## Batch 2: Sources、Drafts、Review

| 页面/类型 | 参考图片的 UI 期望 | 当前后端/API 支持程度 | 当前 UI 行为 | 所需后端工作 | 优先级 | 当前 UI 可否安全展示？ | 原因 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Sources / Adapter 目录 | Cubox、Web Clipper、RSS Feed 适配器卡片，带 Browse/Connect 按钮 | 不支持 | Cubox/WebClipper/RSS 显示为"即将推出"——不可点击或伪造连接 | 实现 CuboxAdapter、WebClipperAdapter、RSSAdapter，包含 source registry 和导入管线 | P2 | 是 | 未实现的适配器明确标注"即将推出"；无伪造数据或伪造连接流程。 |
| Sources / Adapter 目录 | 本地文件适配器，带来源计数 | 支持 | 显示"Active"徽章；来源计数反映实际的 `watched_sources` 长度 | 无 | P0 | 是 | 唯一已实现的适配器显示来自 `/api/sources` 的真实计数。 |
| Sources / 导入方式 | 监听导入、一次性 CLI、粘贴/文件夹描述 | 部分支持 | 显示说明卡片；监听指向现有 sources 页面；CLI/Paste 为信息性 | 显示无需后端工作；LibraryPage 已存在 paste/folder 导入 | P1 | 是 | 卡片解释现有导入路径；无伪造能力。 |
| Sources / 监听来源列表 | 带状态、路径、指标、操作的来源卡片 | 支持 | 来自 `/api/sources` 的真实数据；可展开详情带指标；process/copy/frequency 操作 | 无 | P0 | 是 | 所有展示数据来自现有 API；操作使用真实后端端点。 |
| Sources / 空状态 | 空监听来源列表，带添加 CTA | 支持 | 当 `watched_sources` 为空时显示空状态；CTA 跳转到 `/setup` | 无 | P0 | 是 | 正确处理空数据。 |
| Drafts / 表格列表 | 含标题、状态、来源、评分的 AI Draft 表格 | 支持 | 来自 `/api/drafts` 的真实数据；仅显示 `ai_draft` 状态项；状态徽章始终为"AI Draft" | 无 | P0 | 是 | 仅筛选 `ai_draft` 状态；不在草稿表中显示 `human_approved`。 |
| Drafts / 空状态 | 空草稿列表，带添加来源 CTA | 支持 | EmptyState 组件，链接到 `/sources` | 无 | P0 | 是 | 正确处理空数据。 |
| Drafts / 预览面板 | 草稿正文预览 + 操作（发送审阅、查看详情、移入回收站） | 部分支持 | 正文预览已显示；移入回收站使用真实 `moveDraftToTrash` API；发送审阅为占位（后端不支持直接提交） | 如果产品希望草稿被标记为待人工审阅但无需审批，添加显式"提交审阅"端点 | P2 | 是 | Send to Review 按钮已存在但禁用（尚无后端支持）；Trash 使用真实 API。 |
| Review / 左侧列表 | 带搜索、状态徽章、来源信息、价值评分的草稿列表 | 支持 | 来自 `/api/drafts` 的真实数据；仅筛选 `ai_draft`；搜索为客户端过滤 | 无 | P0 | 是 | 所有数据来自现有 API；搜索为客户端过滤。 |
| Review / 右侧面板 | 草稿正文预览 + 审批面板（复选框、带两步确认的 Approve、Reject） | 支持 | 来自 `getDraftDetail` 的正文预览；Approve 使用真实 `approveDraft` API 带两步确认；Reject 使用真实 `rejectDraft` API | 无 | P0 | 是 | Approve/Reject 使用真实后端；两步确认防止意外审批；无自动审批。 |
| Review / 统计行 | AI Drafts 计数、Approved 计数 | 支持 | 计数来自真实的 `/api/drafts` 数据 | 无 | P0 | 是 | 来自 API 响应的真实计数。 |
| Review / 空状态 | 无待审草稿，带引导 | 支持 | 当不存在 `ai_draft` 项时显示空状态 | 无 | P0 | 是 | 正确处理空数据。 |
| Review / 安全提示 | "无批量审批，无自动审批"消息 | 支持 | 审批面板中的静态安全提示 | 无 | P0 | 是 | 文本仅为 UI 消息；无功能性声明。 |

## 后端 -> 前端矩阵: Batch 1

| 后端/API 能力 | 路由/服务/API 文件 | 当前前端覆盖 | 现在暴露？ | 如否，原因 | 未来 UI 切片 | 优先级 |
| --- | --- | --- | --- | --- | --- | --- |
| Home 状态，含安全/工作区/vault/provider/recall 摘要 | `web/src/api/home.ts`，`/api/home/status` | Home 概览、SafetyBar、侧边栏 provider 卡片 | 是 | 不适用 | Batch 2 页面稳定后增加更丰富的空状态 | P0 |
| 工作流摘要，含已处理 source、ai_draft、human_approved 计数 | `web/src/api/workflow.ts`，`/api/workflow/summary` | Home 概览卡片 | 是 | 不适用 | 可为按阶段流程活动徽章提供数据 | P1 |
| 可编辑的配置和掩码后的 secret 元数据 | `web/src/api/config.ts`，`/api/config/editable` | Setup 引导和现有模型表单 | 是 | 不适用 | 改进 provider 预设表单默认值 | P0 |
| Provider 模式 opt-in/opt-out | `web/src/api/config.ts`，provider mode 端点 | 仅现有 Setup 激活对话框 | 仅在 Setup 中暴露，但可以 | 侧边栏/首页不得隐式激活真实模式 | 将 opt-in 确认保留在 Setup 中 | P0 |
| 配置验证 | `web/src/api/config.ts`，`/api/config/validate` | Setup 引导 Validate Config 和现有 Validate 按钮 | 是 | 不适用 | 添加更清晰的验证结果面板 | P1 |
| Lab/内部 graph/sensemaking/dogfood 路由 | 现有应用路由/页面 | 仅折叠的 Lab | 不在主路径暴露 | 产品边界说明 Graph/Sensemaking/Entity/Community 为 lab/internal，非主要工作流 | 如有需求，单独重新设计 Lab | P3 |

## 后端 -> 前端矩阵: Batch 2

| 后端/API 能力 | 路由/服务/API 文件 | 当前前端覆盖 | 现在暴露？ | 如否，原因 | 未来 UI 切片 | 优先级 |
| --- | --- | --- | --- | --- | --- | --- |
| 草稿列表，含 ai_draft/human_approved 筛选 | `web/src/api/drafts.ts`，`/api/drafts` | DraftsPage 表格 + ReviewPage 列表 | 是 | 不适用 | 大批量草稿的服务端分页 | P1 |
| 草稿详情，含正文和 frontmatter | `web/src/api/drafts.ts`，`/api/drafts/:id` | DraftsPage 预览 + ReviewPage 预览 | 是 | 不适用 | ReviewPage 详情面板中的完整正文视图 | P1 |
| 草稿审批 (approve/reject) | `web/src/api/approval.ts`，`/api/drafts/:id/approve`，`/api/drafts/:id/reject` | ReviewPage 审批面板 | 是 | 不适用 | 在 UI 中添加拒绝原因字段 | P1 |
| 草稿正文保存/编辑 | `web/src/api/drafts.ts`，PATCH `/api/drafts/:id` | DraftsPage CardWorkspace（现有） | 是 | 不适用 | ReviewPage 中的内联正文编辑器 | P2 |
| 草稿移入回收站 | `web/src/api/trash.ts`，`/api/drafts/:id/trash` | DraftsPage 回收站按钮 | 是 | 不适用 | ReviewPage 中也添加回收站操作 | P2 |
| 监听来源列表，含指标 | `web/src/api/sources.ts`，`/api/sources` | SourcesPage 监听来源区域 | 是 | 不适用 | 来源级别的下钻页面 | P2 |
| 来源扫描/处理 | `web/src/api/sources.ts`，`/api/sources/:id/scan` | SourcesPage "立即处理"按钮 | 是 | 不适用 | 后台扫描进度指示器 | P2 |
| 来源频率更新 | `web/src/api/sources.ts`，`/api/sources/:id/frequency` | SourcesPage 频率选择器 | 是 | 不适用 | 无 | P0 |
| 来源删除/停止监听 | `web/src/api/sources.ts`，`/api/sources/:id` | SourcesPage "停止监听"按钮 | 是 | 不适用 | 无 | P0 |
| Cubox adapter | 未实现 | SourcesPage "即将推出"卡片 | 否 | 后端 CuboxAdapter 未实现 | 实现 Cubox 导入管线 | P2 |
| Web Clipper adapter | 未实现 | SourcesPage "即将推出"卡片 | 否 | 后端 WebClipperAdapter 未实现 | 实现 Web Clipper 集成 | P2 |
| RSS Feed adapter | 未实现 | SourcesPage "即将推出"卡片 | 否 | 后端 RSSAdapter 未实现 | 实现 RSS Feed 导入 | P2 |

## Batch 3: Library、Wiki、Export

### 参考图片 -> 后端矩阵

| 页面/类型 | 参考图片的 UI 期望 | 当前后端/API 支持程度 | 当前 UI 行为 | 所需后端工作 | 优先级 | 当前 UI 可否安全展示？ | 原因 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Library / 筛选标签 | 所有知识、按来源、按轨道、收藏夹、最近浏览 | 部分支持 | 全部/按来源/按轨道具客户端在真实数据上运行；收藏夹/最近浏览禁用（无后端） | 添加收藏夹/书签端点和最近浏览跟踪 | P2 | 是 | 已实现的标签能筛选真实的 human_approved 卡片；禁用的标签明确标记。 |
| Library / 表格 | 含标题、来源、日期、状态、标签的知识表格 | 支持 | 来自 `/api/library/cards` 的真实数据；仅显示 `human_approved` | 无 | P0 | 是 | 所有列来自现有 API；LibraryCardResponse 包含 title、source_type、created_at、status、tags。 |
| Library / 详情面板 | 右侧卡片正文详情面板 | 支持 | 使用 `getLibraryCardDetail` API；显示正文、来源、溯源信息 | 无 | P0 | 是 | 每张选中卡片调用真实 API。 |
| Library / Graph 探索 | Graph 可视化按钮 | 不支持 | 已从 LibraryPage 移除——Graph 为 lab/internal，非主路径 | Library 无需后端工作；graph 作为独立页面存在 | P3 | 是 | 已移除以保护产品边界；graph 非主路径。 |
| Library / 社区面板 | 知识社区面板 | 不支持 | 已从 LibraryPage 移除——Community 为 lab/internal | 无 | P3 | 是 | 已移除以保护产品边界；community 非主路径。 |
| Library / 收藏夹 | 收藏/星标知识 | 不支持 | 筛选标签禁用；表格中的星标图标仅为视觉，无后端 | 添加收藏夹/书签端点 | P3 | 是 | UI 元素存在但无功能；无伪造数据。 |
| Library / 最近浏览 | 最近浏览跟踪 | 不支持 | 筛选标签禁用；无后端跟踪 | 添加每卡片的浏览计数跟踪 | P3 | 是 | 筛选标签禁用，带 Coming Soon 标签。 |
| Wiki / 筛选标签 | 所有页面、收藏夹、最近、最近更新 | 部分支持 | 所有页面在真实 wiki 章节上运行；收藏夹/最近/最近更新禁用 | 添加 wiki 页面收藏、浏览跟踪、更新时间戳 | P3 | 是 | 所有页面筛选真实 wiki 章节；禁用的标签标记为 Coming Soon。 |
| Wiki / 页面列表 | 带卡片计数的章节列表 | 支持 | 来自 `/api/wiki/page` 的真实数据；带卡片计数的章节 | 无 | P0 | 是 | 章节数据来自现有 wiki API。 |
| Wiki / 质量指标 | 覆盖率、忠实度、未使用、陈旧、缺口 | 支持 | 来自 `/api/wiki/quality` 的真实数据；在可折叠详情中显示 | 无 | P0 | 是 | 所有指标来自真实 API。 |
| Wiki / 重建 | LLM + 确定性重建 | 支持 | `POST /api/wiki/rebuild` 带模式参数 | 无 | P0 | 是 | 现有重建端点。 |
| Wiki / 新页面 | 手动创建新 wiki 页面 | 不支持 | 按钮已显示但无后端支持 | 添加 wiki 页面创建端点 | P2 | 是 | 按钮为占位；无伪造能力。 |
| Export / 格式卡片 | Markdown、ZIP、PDF、HTML、Word、JSON | 部分支持 | Markdown/ZIP 已启用并可工作；PDF/HTML/Word/JSON 标记为 Coming Soon | 实现 PDF/HTML/Word/JSON 导出格式 | P2 | 是 | 仅已实现格式可工作；Coming Soon 卡片已禁用。 |
| Export / 范围 | 全部 / 按标签 / 按轨道 | 支持 | 在已审批卡片上实现真实筛选；标签/轨道下拉菜单由 API 填充 | 无 | P0 | 是 | 筛选在真实 human_approved 数据上工作。 |
| Export / 下载 | Markdown 下载、ZIP 下载 | 支持 | 使用 `/api/knowledge/export` 和 `/api/knowledge/export/download` | 无 | P0 | 是 | 真实下载端点。 |
| Export / 选项 | 包含元数据、目录、标签、frontmatter | 不支持 | 选项复选框已显示但尚未发送到后端 | 将导出选项添加到导出 API 请求体 | P2 | 是 | 选项 UI 已准备；后端集成待完成。 |
| Export / 最近导出 | 最近导出历史 | 不支持 | 区域未显示（无后端跟踪） | 添加导出历史跟踪 | P3 | 是 | 已省略而非伪造。 |

### 后端 -> 前端矩阵: Batch 3

| 后端/API 能力 | 路由/服务/API 文件 | 当前前端覆盖 | 现在暴露？ | 如否，原因 | 未来 UI 切片 | 优先级 |
| --- | --- | --- | --- | --- | --- | --- |
| Library 卡片列表，含状态筛选 | `web/src/api/library.ts`，`/api/library/cards` | LibraryPage 表格列表 | 是 | 不适用 | 服务端分页 + 收藏排序 | P0 |
| Library 卡片详情 | `web/src/api/library.ts`，`/api/library/cards/:id` | LibraryPage 详情面板 | 是 | 不适用 | 丰富的溯源可视化 | P0 |
| Library 批量操作 (export、tag、track) | `web/src/api/library.ts`，批量端点 | LibraryPage 批量操作栏 | 是 | 不适用 | 无 | P0 |
| Wiki 状态 | `web/src/api/wiki.ts` (via fetch)，`/api/wiki/status` | WikiPage 状态栏 | 是 | 不适用 | 无 | P0 |
| Wiki 页面内容 | `web/src/api/wiki.ts` (via fetch)，`/api/wiki/page` | WikiPage 章节列表 | 是 | 不适用 | 带目录的完整页面导航 | P0 |
| Wiki 质量指标 | `web/src/api/wiki.ts` (via fetch)，`/api/wiki/quality` | WikiPage 质量可折叠面板 | 是 | 不适用 | 无 | P0 |
| Wiki 重建 | `web/src/api/wiki.ts` (via fetch)，`/api/wiki/rebuild` | WikiPage 重建按钮 | 是 | 不适用 | 无 | P0 |
| Wiki 相关章节 | `web/src/api/wiki.ts` (via fetch)，`/api/wiki/related-sections` | 已获取但未在 UI 中展示 | 否 | 新设计中无明确 UI 位置 | 在详情视图中添加相关章节侧边栏 | P2 |
| 知识导出 (markdown) | `web/src/api/library.ts` (via fetch)，`/api/knowledge/export` | ExportPage 预览 + 下载 | 是 | 不适用 | 无 | P0 |
| 知识导出下载 (zip) | `web/src/api/library.ts` (via fetch)，`/api/knowledge/export/download` | ExportPage 下载 | 是 | 不适用 | 无 | P0 |
| 导出选项 (metadata、TOC、tags、frontmatter) | 导出 API 中尚不支持 | ExportPage 选项复选框 | 否 | 后端导出 API 不接受选项 | 将选项添加到导出请求体 | P2 |

## Batch 4: Fake 模式 QA 发现 (2026-06-02)

### QA 矩阵

| 页面 | 可打开 | Demo 模式可见 | 按钮可工作 | 空状态正确 | 产品边界安全 | 评分 |
| --- | --- | --- | --- | --- | --- | --- |
| Home | 是 | 是（侧边栏 + safety bar） | 导航链接、CTA 均可工作 | 不适用（有 demo 数据） | 是——无伪造的真实 provider 激活 | 9/10 |
| Setup | 是 | 是（Demo / Fake Provider 区域） | 添加模型、验证在填写前禁用 | 不适用 | 是——API key 仅掩码显示，validate 警告无真实 LLM 调用 | 9/10 |
| Sources | 是 | 是（safety bar） | "立即处理"可工作，Cubox/WebClipper/RSS 禁用 | 不适用（有 1 个本地文件来源） | 是——source 与 provider 明确分离 | 9/10 |
| Drafts | 是 | 是 | "浏览草稿"链接可工作 | 是——空状态带跳转来源的 CTA | 是——仅显示 ai_draft，无自动混合 | 8/10 |
| Review | 是 | 是 | 不适用（空） | 是——显示引导文本 | 是——无 Approve All，无自动审批 | 8/10 |
| Library | 是 | 是 | 详情面板、导出、搜索、筛选、排序均可工作 | 不适用（有 6 张 demo 卡片） | 是——仅显示 human_approved | 9/10 |
| Wiki | 是 | 是 | 搜索、章节展开/折叠可工作 | 是——提示需要模型进行 LLM 综合 | 是——无 RAG/向量 DB 声明 | 8/10 |
| Export | 是 | 是 | 预览、下载可工作，格式卡片正确 | 不适用（有 6 张已审批卡片） | 是——PDF/HTML/Word/JSON 禁用，选项可折叠为 Coming Soon | 9/10 |

### 发现并已修复的问题

1. **缺少 i18n key `library.col_title`**——Library 表头显示原始 key "library.col_title" 而非"标题"。已通过添加中英文对应项修复。
2. **缺少 i18n key `nav.review`**——侧边栏显示原始 key "nav.review" 而非"人工审阅"。已通过添加中英文对应项修复。
3. **缺少 i18n key `shared.safety_notice`**——导出页面的安全区域显示原始 key。已通过添加中英文对应项修复。

### Fake 模式主路径状态

- Source → Process: "立即处理"在 Local Files adapter 上触发 ✓
- Process → Drafts: 后台处理已启动；在 fake 模式下草稿可能需要时间显示
- Drafts → Review: 当无草稿存在时 Review 页面正确显示空状态 ✓
- Library → Export: 6 张 demo 卡片通过 Markdown 预览和下载成功导出 ✓

### 截图

- `tmp/fake-qa-home.png`
- `tmp/fake-qa-setup.png`
- `tmp/fake-qa-sources.png`
- `tmp/fake-qa-drafts.png`
- `tmp/fake-qa-review.png`
- `tmp/fake-qa-library.png`
- `tmp/fake-qa-wiki.png`
- `tmp/fake-qa-export.png`
- `tmp/fake-qa-library-fixed.png`（i18n 修复后）

### 关口

- `git diff --check`: 通过 (exit 0)
- `web/ npm run build`: 通过 (tsc -b && vite build completed in 4.72s)
- `main` 与 `origin/main` 同步: 是 (push 后 0 0)
- `pictures/` 未暂存: 是（仅 untracked）
- 工作树: 干净（仅 untracked pictures/、tmp/）

## Batch 5: Setup / Source 流程 UX 修复 (2026-06-02)

### 问题摘要

用户报告 Setup/Sources/模型配置流程中的 UX 问题：
1. Sources 页面的"新来源"按钮跳转到 Setup 页面，而非内联添加来源
2. "添加模型"按钮无明显视觉反馈
3. 侧边栏的 Demo Mode 是可点击按钮，仅导航到 /setup（循环）
4. "验证配置"名称暗示真实 LLM 连接测试，但仅检查本地配置
5. Qwen 显示为独立 provider 卡片，而非 OpenAI-compatible 示例
6. Setup 页面文案过于工程化

### 已做修改

| 修改 | 修改的文件 | 后端影响 |
| --- | --- | --- |
| Sources 的"新来源"打开内联 SourceAddPanel | `SourcesPage.tsx` | 无——使用现有 `addWatchedSource` API |
| "添加模型" → "配置模型"，带滚动到表单的反馈 | `SetupPage.tsx`，`i18n.ts` | 无 |
| Demo Mode → 状态 chip（不可点击） | `Sidebar.tsx`，`i18n.ts` | 无 |
| "验证配置" → "检查配置"，带 tooltip | `SetupPage.tsx`，`i18n.ts` | 无 |
| Provider 类型收敛为 4 种：OpenAI native、Anthropic native、OpenAI-compatible、Custom | `SetupPage.tsx`，`i18n.ts` | 无——仅 UI 预设 |
| 工程化 chip 整合为单条安全提示 | `SetupPage.tsx`，`i18n.ts` | 无 |
| Sources 页面描述更新为引用内联添加 | `SourcesPage.tsx`，`i18n.ts` | 无 |

### 后端差距评估

无需后端修改。所有修改均为使用现有 API 的前端 UX 改进：
- 来源添加：现有 `POST /api/sources` 端点
- 模型配置：现有 `POST /api/config` 端点
- 验证：现有 `POST /api/config/validate` 端点（已仅为本地，无 LLM 调用）
- Provider 模式：现有模式切换端点（未改动）

### 资源

Batch 1 和 Batch 2 中未添加外部资源。

## Batch 6: Review / Library / Wiki / Lab UX 修复 (2026-06-03)

### 问题摘要

用户通过真实浏览器试用报告的 UX 问题：
1. "人工审阅"和"审阅草稿"侧边栏标签看起来重复，用户混淆其区别
2. Library 首次点击卡片后显示空详情面板（交互 bug）
3. 卡片详情内容在狭窄的侧面板中过于拥挤（最大 50% 宽度，70vh 高度）
4. 当已审批知识存在但 Wiki 未生成时，Wiki 默认状态不清晰
5. Lab/Graph/Sensemaking 视觉样式与主 Web 不一致

### 已做修改

| 修改 | 修改的文件 | 后端影响 |
| --- | --- | --- |
| 从主侧边栏导航移除 `/drafts`；移至 Lab 区域 | `Sidebar.tsx` | 无 |
| Library 空状态 CTA 从 `/drafts` 更新为 `/review` | `LibraryPage.tsx` | 无 |
| 在 Library 中添加 `detailLoading` 状态；显示加载指示器而非空白 | `LibraryPage.tsx` | 无 |
| Library 详情面板网格从 `1fr 1fr` 加宽为 `2fr 3fr` | `LibraryPage.tsx` | 无 |
| Library 详情面板最大高度从 `70vh` 增加为 `85vh` | `LibraryPage.tsx` | 无 |
| 为已有 Wiki 但无章节时添加 Wiki 空状态（显示刷新 CTA + 已审批计数） | `WikiPage.tsx` | 无 |
| 优化 SensemakingPage 头部/标签/LAB 横幅，使用主 Web 设计 token | `SensemakingPage.tsx` | 无 |

### 根因：Library 首次点击详情为空 bug

**位置：** `LibraryPage.tsx:166-172`（修复前）

**因果链：**
1. 用户点击第一张卡片 → 调用 `selectCard(ref)`
2. `setSelected(ref)` 更新选中状态
3. `setDetail(null)` **同步清除**详情状态
4. 详情面板渲染（条件：`selected &&`）——面板出现但 `detail` 为 null
5. 面板内部：`!error && detail`——detail 为 null，**无内容渲染**
6. `useEffect` 触发异步 `getLibraryCardDetail()`——请求已发出
7. 面板保持空白直到响应返回
8. 第二次点击正常工作，因为第一次请求已完成并缓存了详情

**修复：** 在 `selectCard()` 中将 `setDetail(null)` 替换为 `setDetailLoading(true)`。在详情面板中添加加载指示器。

### 后端差距评估

| 能力 | 状态 | 可安全展示？ | 说明 |
| --- | --- | --- | --- |
| Library 完整详情 API (`getLibraryCardDetail`) | **已支持** | 是 | 真实 API，可正常工作 |
| Wiki 基于已审批知识自动生成 | **需要手动重建** | 是 | 用户必须点击"生成 Wiki"或"刷新 Wiki"；无自动触发 |
| Wiki 相关页面/历史/空间 | **部分支持** | 是 | `/api/wiki/related-sections` 存在但未在 UI 中展示 |
| Graph / Sensemaking 当前支持 | **lab/internal，仅确定性** | 是 | 仅 BFS + 集合操作；无 LLM/embedding/向量 DB |
| Review / Drafts 重复入口 | **IA 历史** | 已解决 | 合并为单个 `/review` 入口；`/drafts` 移至 Lab |

### 资源

未添加外部资源。

### 端点诊断与就绪语义

- 当前 readiness 状态已从 "Ready" 改为 "Configured / Not verified"（配置已保存 / 尚未测试连接），仅代表本地配置已保存，不代表外部提供商网络可达。
- 真正的 "Test Connection"（测试连接）功能尚未实现。
- `base_url` 格式要求：用户需要填写服务根路径（如包含 `/v1`），不应包含 `/chat/completions`，系统会自动拼接。
- 真实连接失败可能来自 endpoint、network、proxy、key、model 多种原因，现在会在 UI 和日志中统一提示"模型连接失败。请检查 base URL、网络代理、provider 类型、model name 或 API key。"

### Batch 7: Setup 模型保存 UX 修复

**用户报告：** "配置完模型的时候，第一次点模型配置部分的保存没有反应，按全局的保存的才保存"

**根因：** `saveModelEdit()` 存在两个问题：
1. 验证失败时使用 `setMessage()` 显示绿色成功消息，视觉上与成功提示无区别，用户误以为"无反应"
2. `await save()` 未包裹在 try/catch 中，API 错误抛出 unhandled rejection，React 可能抑制状态更新
3. `if (!form || !editing) return` 零反馈退出

**修复：**
- 所有验证错误改用 `setSaveError()`，显示在红色错误横幅中
- 添加 try/catch 包裹 `await save()`，捕获 save 抛出的错误并静默处理（save 已设置 saveError）
- 添加 missing i18n key `setup.validation.form_not_loaded`
- 顺便修复 i18n.ts 中 pre-existing 语法错误（line 1553 转义引号）

**修改的文件：**
- `web/src/pages/SetupPage.tsx` — saveModelEdit error handling
- `web/src/lib/i18n.ts` — new i18n key + fix escaped quotes bug
