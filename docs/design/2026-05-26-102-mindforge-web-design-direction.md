# MindForge Web 设计方向

**日期**: 2026-05-26
**状态**: proposed
**输入**: /design-consultation — awesome-design-md reference survey
**参考仓库**: https://github.com/VoltAgent/awesome-design-md

---

## A. 执行摘要

### MindForge Web 应该是什么样的

一个安静、温暖、编辑性的知识工作台。用户在 MindForge 中的体验应该像是在一个安静的图书馆中翻阅精心编排的卡片目录——不是繁忙的 SaaS 仪表盘，不是炫目的 AI demo，不是拥挤的笔记应用。

界面应该退后，让知识卡片成为主角。色彩应该是纸质的、克制的，排版应该有编辑权威。每一次审查和批准的操作都应该感觉慎重而自然，不是机械的点击。

### 不应该是什么样的

- 不是 SaaS 管理面板（数据密集、冷色调、无穷的表格）
- 不是 AI 聊天机器人界面（对话气泡、紫色渐变、闪烁的动画）
- 不是 Notion 克隆（虽然从 Notion 借了温暖纸质感，但 MindForge 是编译器而非画布）
- 不是 Obsidian 克隆（不做图数据库 UI、不做图谱优先、不做本地文件浏览器）
- 不是闪亮的落地页风格（渐变 CTA、3 列图标网格、装饰性 blob）
- 不是黑暗终端 UI（虽然 local-first，但用户不是开发者/运维人员）

### 推荐主方向

**"Calm Editorial Knowledge Compiler"（安静的编辑性知识编译器）**

温和纸质感 + 编辑性排版权威 + 精确的审批工作流 + 克制的 AI 产品润色

### 备选方向

**"Warm Library Catalog"（温暖的图书馆目录）** — 更接近 Notion 的温暖极简路线，弱化 serif，强卡片感

### 为什么这个方向适合审批优先的知识编译器

MindForge 的核心路径是 `Source → ai_draft → Review → explicit approval → human_approved → Library → Recall/Wiki → Export`。用户的核心行为是：**阅读**（来源材料、草稿卡片）、**判断**（是否批准）、**检索**（召回、Wiki）。这些行为的 UX 基础是长文本阅读的舒适度、对内容判断的可信度、以及操作的安全感。一个温暖的、编辑性的、纸质感的设计强化了"这是你的知识，值得认真对待"的信号。

---

## B. 产品个性 — 7 个设计形容词

### 1. Calm（安静）

**UI 含义**: 色彩不喧闹，无闪烁动画，页面加载后没有意外的布局跳动。状态切换使用淡入淡出而非弹出。卡片之间呼吸充足。用户能专注阅读而非被界面争夺注意力。

### 2. Editorial（编辑性）

**UI 含义**: 排版有层次，serif 标题传递权威感，正文行高宽松（1.5-1.6），卡片像是被编辑过的出版物条目。不是 wiki 的随意感，不是聊天机器人的口语感。

### 3. Trustworthy（可信）

**UI 含义**: 审批按钮设计谨慎但不隐藏。状态标签（ai_draft、human_approved）使用经过推敲的颜色——不像是随手填的 CSS 变量。来源溯源（provenance）清晰可见。安全边界说明有体面的排版对待。

### 4. Warm（温暖）

**UI 含义**: 暖色调中性色（yellow-brown undertone），不使用冷蓝灰。白色不是 #fff 纯白而是微暖。阴影柔和多层而非硬边。圆角舒适（8-12px），不锐利。

### 5. Local-First（本地优先）

**UI 含义**: 不使用云端加载动画，不展示 "Syncing..." 旋转图标。本地文件路径用 mono 字体呈现，但不用终端美学。安全说明（不写 vault、不调真实 LLM）以体面的 callout 呈现，非刺眼的 alert。

### 6. Focused（聚焦）

**UI 含义**: 每个页面核心操作不超过 3 个。侧边栏导航精简——只展示主路径页面，lab/internal 功能折叠或隐藏。卡片列表不塞满元数据。

### 7. Quietly Intelligent（安静地智能）

**UI 含义**: AI 生成的内容（ai_draft summary、inference、review questions）以微妙的风格差异呈现——比如稍淡的背景色或 serif 引用样式——暗示"这是 AI 的建议，待你确认"。不是 "AI 生成！✨" 的喧闹，而是安静的提醒。

---

## C. 设计灵感调研

从 awesome-design-md 的 58 个 DESIGN.md 中，分析了以下与 MindForge 相关的设计家族：

### 1. Warm Paper Knowledge（Notion + Claude）

**参考**: Notion（warm neutrals, whisper borders, pill badges）, Claude（parchment canvas, serif headlines, terracotta accent）

**可借用的**:
- Notion 的暖色中性色系统（#f6f5f4 暖白、#31302e 暖黑、#615d59 暖灰）
- Notion 的 whisper border (1px solid rgba(0,0,0,0.1))
- Notion 的多层柔和阴影（4-5 层叠加，单层透明度 <0.05）
- Claude 的 serif headline + sans body 排版分层
- Claude 的 ring shadow 系统（0px 0px 0px 1px）
- 两者共有的温暖纸张底色哲学

**应避免的**:
- 直接复制 NotionInter 字体或 Notion Blue (#0075de)
- Claude 的手绘插图风格（MindForge 不是 AI 对话产品）
- Claude 的深色/浅色 section 交替（MindForge 是 app 而非 marketing page）

**适合度**: 9/10 — 最接近 MindForge 的产品本质

### 2. Developer Infrastructure Precision（Vercel + Stripe）

**参考**: Vercel（black/white precision, Geist font, gallery-like emptiness）, Stripe（navy headings, signature purple, technical luxury）

**可借用的**:
- Stripe 的排版精确性——font-weight 300 用于大标题（优雅但不浮夸）
- Vercel 的 "every element earns its pixels" 哲学
- Stripe 的 "技术但温暖" 的品牌感

**应避免的**:
- Vercel 的极端极简（对知识阅读太冷）
- Stripe 的紫蓝渐变系统
- Geist 字体的使用（那属于 Vercel 品牌）

**适合度**: 6/10 — 过于冷感，但排版纪律值得学习

### 3. Local-First Terminal（Ollama）

**参考**: Ollama（radical minimalism, pure white void, terminal-native）

**可借用的**:
- "strip away everything unnecessary" 的极简态度
- local-first 的诚实表达

**应避免的**:
- 过度的白（缺少温暖感）
- 终端美学（MindForge 用户不一定是开发者）
- 无阴影、无装饰的极端减法（知识阅读需要适度的视觉层次）

**适合度**: 5/10 — 精神契合但视觉过冷

### 4. Premium AI Platform（Claude + Superhuman）

**参考**: Claude（已分析）, Superhuman（luxury envelope, twilight purple gradient）

**可借用的**:
- Superhuman 的 "单一戏剧性色彩姿态 + 其余克制" 策略
- Claude 的配色克制纪律（只用一种品牌色，通过暖色系统传递品牌）

**应避免的**:
- Superhuman 的紫色渐变（太像 SaaS marketing）
- 任何过度 premium/luxury 的暗示（MindForge 是工具，不是奢侈品）

**适合度**: 7/10 — 品牌策略优秀但需要降调

### 5. Dark Technical Console（Supabase + Sentry）

**参考**: Supabase（dark emerald, code-editor aesthetic）, Sentry（dark dashboard, pink-purple accent）

**可借用的**:
- 暗色模式的 dark surface 处理参考

**应避免的**:
- 全部深色模式（知识阅读在浅色背景下更舒适）
- 数据密集仪表盘布局
- 代码编辑器美学（不适合知识卡片阅读）

**适合度**: 3/10 — 不适合知识工作台

### 6. Creative / Playful（Figma + Linear + Raycast）

**参考**: Figma（vibrant multi-color）, Linear（ultra-minimal purple accent）, Raycast（gradient accents）

**可借用的**:
- Linear 的键盘导航哲学
- Raycast 的功能性优雅

**应避免的**:
- Figma 的多彩（MindForge 不需要像创意工具那么活泼）
- Linear 的工程感（MindForge 用户不全是工程师）

**适合度**: 5/10 — 部分方法可借鉴但不适合整体方向

### 7. Enterprise / Corporate（IBM + HashiCorp）

**参考**: IBM（Carbon design system, structured blue）, HashiCorp（enterprise-clean, black and white）

**可借用的**: 系统的设计 token 组织方式

**应避免的**: 企业软件感、冷蓝灰、过度结构化的布局

**适合度**: 2/10 — 和 MindForge 的产品气质相反

---

## D. 推荐方向：安静的编辑性知识编译器

### 色彩方向

**主色调**: 暖纸色系（warm paper palette）

| Role | Color | Usage |
|------|-------|-------|
| Page Background | `#faf9f5` (Warm Paper) | 主页面底色 |
| Surface | `#ffffff` | 卡片、面板表面 |
| Surface Alt | `#f3f1eb` (Warm Sand) | 交替区域、选中状态 |
| Primary Text | `#1c1b18` (Warm Ink) | 标题、正文 |
| Secondary Text | `#5e5c56` (Warm Gray 600) | 描述、元数据 |
| Tertiary Text | `#8a8880` (Warm Gray 400) | 占位符、禁用态 |
| Border | `1px solid rgba(0,0,0,0.08)` | 卡片、分割线 |
| Brand Accent | `#2d7d5f` (Forest Green) | 主 CTA、链接、品牌色 |

**品牌色选择说明**: Forest Green（森林绿，#2d7d5f）而非 Notion Blue 或 Claude Terracotta。绿色传达**成长**（知识成长）、**安全**（审批安全）、**自然**（本地优先）。它是一个既不像 SaaS 蓝、也不像 finance 紫、也不像 AI 橙的独立选择。它在暖色纸张上形成优雅的对比，同时保持克制。

**语义色**:
- `ai_draft`: `#b8860b` (Dark Goldenrod) — 温暖的琥珀色，传达 "AI 草稿，待确认"
- `human_approved`: `#2d7d5f` (Forest Green) — 与品牌色一致，传达 "已确认，安全"
- `lab/internal`: `#8a8880` (Warm Gray) — 中性灰，不喧宾夺主
- `warning`: `#cc7a00` (Warm Amber) — 温暖的警告色
- `error`: `#c04040` (Warm Red) — 不刺眼的红色

### 浅色/深色模式策略

- 默认浅色模式（知识阅读优先）
- 深色模式为独立设计：warm charcoal 底色（#1c1b18），warm paper 文字色，降低饱和度 15%
- 不简单的颜色反转，深色模式需要降低暖色的 chroma

### 排版方向

**Serif for editorial authority, Sans for UI utility**

| Role | Font | Rationale |
|------|------|-----------|
| Display/Heading | **Source Serif 4** (Google Fonts) | 开源 serif，编辑性权威感，接近 Claude 的 Anthropic Serif 精神 |
| Body/UI | **DM Sans** (Google Fonts) | 温暖几何感 sans，支持 tabular-nums，接近 Notion 的 warm sans |
| Code/Paths | **JetBrains Mono** (Google Fonts) | 代码和文件路径展示，清晰可读 |

**排版层级**:

| Level | Font | Size | Weight | Line Height | Usage |
|-------|------|------|--------|-------------|-------|
| Display | Source Serif 4 | 36px | 500 | 1.15 | 页面主标题 |
| H1 | Source Serif 4 | 28px | 500 | 1.2 | Section 标题 |
| H2 | Source Serif 4 | 22px | 500 | 1.25 | 卡片标题 |
| H3 | DM Sans | 18px | 600 | 1.3 | 子标题 |
| Body L | DM Sans | 16px | 400 | 1.6 | 知识卡片正文 |
| Body | DM Sans | 15px | 400 | 1.5 | 标准正文 |
| Body S | DM Sans | 14px | 400 | 1.45 | 元数据、描述 |
| Caption | DM Sans | 12px | 500 | 1.35 | 标签、badge |
| Code | JetBrains Mono | 13px | 400 | 1.5 | 路径、代码 |

**设计原则**: serif 仅用于标题——为每条知识赋予编辑权威。sans 处理所有 UI 文本。不混用。

### 间距密度

**Base unit**: 4px（比 8px 更灵活，适合阅读型界面的微调）

| Token | Value | Usage |
|-------|-------|-------|
| 2xs | 4px | 紧凑内边距 |
| xs | 8px | 标准内边距、标签 padding |
| sm | 12px | 卡片内边距、按钮 padding-x |
| md | 16px | 卡片 padding、列表项间距 |
| lg | 24px | Section 间距、卡片间距 |
| xl | 32px | 页面 section 间距 |
| 2xl | 48px | 主区域间距 |
| 3xl | 64px | 页面顶部/底部留白 |

**密度哲学**: 舒适但不高档。卡片和 section 之间有充足的呼吸空间，但列表和元数据保持紧凑以支持扫描。这不是 Apple 的奢侈留白，也不是 Linear 的紧凑工程感。

### 卡片风格

- 白色表面 (#ffffff)，带 whisper border (1px solid rgba(0,0,0,0.08))
- 圆角 10px（标准卡片）、14px（featured 卡片）
- 多层柔和阴影（Notion 风格）:
  ```
  rgba(0,0,0,0.03) 0px 2px 12px,
  rgba(0,0,0,0.015) 0px 1px 4px,
  rgba(0,0,0,0.008) 0px 0.4px 1.5px
  ```
- hover 时阴影轻微加深
- 知识卡片内部：标题（serif）、summary（sans body L）、元数据行（caption）、状态 badge

### 审查队列风格

- 队列项为全宽卡片列表（非棋盘格）
- 每项：source 名 → ai_draft 标题 → 价值分数 → 预览片段 → 操作按钮
- 已批准的卡在队列中灰色降低对比度（淡出处理）
- Approve/Reject 按钮明确但不喧宾夺主——Forest Green approve + 暖红 reject

### 知识库布局

- 顶部 filter bar（已实现在 v4.4 A5 中）
- 卡片采用 1-3 列响应式网格（取决于屏幕宽度）
- 排序选择器较轻量级
- 空状态：温暖的引导性说明文字（"你的知识库还是空的。导入第一个来源或从示例工作区开始。"）

### 召回/搜索结果风格

- 搜索结果以卡片 + 匹配解释面板的形式呈现
- 命中项突出显示匹配字段（title、tags、body）
- 零结果：不展示空列表，而是给解释性信息（"没有卡片匹配你的查询。BM25 词法检索基于精确词匹配。"）
- 搜索框显著、温暖、邀请输入

### Wiki/导出呈现

- Wiki 内容呈现为编辑性长文——serif 标题、宽松行高、分节
- 导出预览：展示选中的格式和卡片数，安全说明体面呈现
- "不写 Obsidian vault" 以体面的 callout 样式呈现（非刺眼警告）

### 图标策略

- 使用 Lucide Icons（已在项目中）—— 一致、克制、线条风格
- 品牌/语义图标不使用 emoji（除了状态标签中的小指示符）
- AI draft indicator：小琥珀色点 + serif 风格 "ai draft" 标签

### 动效/微交互规则

- 页面切换：无动画（SPA 即时切换）
- 状态变化：opacity transition 150ms ease-out
- 卡片 hover：shadow transition 200ms ease-out
- 审批操作：按钮点击后短暂的确认状态（200ms），然后卡片淡出
- 无滚动驱动动画
- 无入场动画（知识工具不需要 "wow" 效果）
- 动效哲学：只帮助理解状态变化，不制造娱乐感

---

## E. 已拒绝的方向

以下方向明确拒绝，不进入后续设计阶段：

| 方向 | 拒绝原因 |
|------|---------|
| SaaS Admin Dashboard | 冷色调、数据密集、表格优先——与知识阅读体验对立 |
| Graph-First Cyberpunk UI | 图谱不是主路径，不要让它定义视觉语言 |
| Generic AI Chatbot UI | 对话气泡、紫色渐变、闪烁光标——MindForge 不是聊天产品 |
| Notion Clone | 虽然借了温暖纸质感，但 MindForge 是编译器而非空白画布 |
| Obsidian Clone | 图数据库 UI、本地文件浏览器——MindForge 自有审批流核心差异 |
| Flashy Landing-Page Style | 渐变 CTA、3 列图标网格、装饰性 blob——不适合应用内 UI |
| Over-Dark Terminal UI | 知识阅读在浅色背景下更舒适，深色模式应是选项而非默认 |
| Heavy Animated AI Demo Style | 滚动驱动动画、打字机效果——和 "安静的知识工具" 气质冲突 |

---

## F. 逐页设计目标

### 1. First-Run / Onboarding

- **用户目标**: 从空工作区到达第一张 approved 卡片
- **情感调性**: 被引导、被欢迎、不困惑
- **布局方向**: 单列居中引导面板，步骤式进度指示器
- **关键状态**: 完全为空、有模型配置、有第一个来源
- **Copy 语调**: 温暖指示性（"从这里开始"），不傲慢（"你必须先做这个"）
- **不要做**: 不要展示所有可能操作的 dashboard（用户在空 workspace 不需要看到 10 个菜单）

### 2. Source / Import

- **用户目标**: 理解导入方式并添加知识来源
- **情感调性**: 清晰、可选择
- **布局方向**: import 方式卡片（watch、one-shot、paste），provenance 预览
- **关键状态**: 无来源、导入中（dry-run）、导入完成、导入失败
- **Copy 语调**: 信息性，解释每种方式的安全边界
- **不要做**: 不要做成文件管理器或上传页面

### 3. Review Queue

- **用户目标**: 逐个审查 AI 草稿并做出明确的批准/拒绝决定
- **情感调性**: 慎重、可信、有控制感
- **布局方向**: 全宽队列列表，每项可展开查看详情，操作按钮在底部
- **关键状态**: 队列为空、有待审草稿、已有批准记录
- **Copy 语调**: 中性编辑性——告知但不催促
- **不要做**: 不要做成一键批量批准（破坏 explicit approval 语义）

### 4. Card Detail

- **用户目标**: 深度阅读一张知识卡片的所有内容
- **情感调性**: 沉浸式阅读
- **布局方向**: 宽阅读列（max-width: 720px），serif 标题，宽松行高正文
- **关键状态**: ai_draft 预览、human_approved 完成态、溯源展开
- **Copy 语调**: 卡片自身内容优先，元数据轻量呈现
- **不要做**: 不要做成 wiki 编辑器或笔记编辑器

### 5. Approval Confirmation

- **用户目标**: 确认批准操作并看到状态变更
- **情感调性**: 确定但需确认——不轻率
- **布局方向**: 内联确认面板（当前 ApprovalPanel 已有），状态时间线展示
- **关键状态**: 批准前、confirm 按钮、批准后（时间线更新）
- **Copy 语调**: 确认性的——"这将被纳入你的知识库"
- **不要做**: 不要 auto-approve，不要一键跳过确认

### 6. Library

- **用户目标**: 浏览、筛选、排序已批准的知识卡片
- **情感调性**: 浏览图书馆目录的满足感
- **布局方向**: 顶部 filter bar → 统计卡片行 → 响应式卡片网格
- **关键状态**: 卡片列表、筛选激活态、空结果
- **Copy 语调**: 安静的目录感——"X 张卡片，按 Y 排序"
- **不要做**: 不要做成 Airtable 风格数据库，不要做成 notes 应用

### 7. Recall / Search

- **用户目标**: 通过关键词检索找到相关知识卡片
- **情感调性**: 精确、可解释
- **布局方向**: 搜索框（显著）→ 结果计数 → 命中列表 → 解释面板（可折叠）
- **关键状态**: 有结果、零结果、搜索结果解释展开
- **Copy 语调**: 信息性 + BM25 边界说明（当前已实现在 U5）
- **不要做**: 不要伪装成语义搜索，不要用 AI 聊天回答替代搜索结果

### 8. Wiki

- **用户目标**: 从已批准卡片中阅读合成的知识百科
- **情感调性**: 编辑性长文阅读
- **布局方向**: 宽阅读列（max-width: 720px），serif 标题，分节
- **关键状态**: 内容加载中（fake provider 下为占位内容）、完整渲染
- **Copy 语调**: 百科条目感——客观、有结构
- **不要做**: 不要做成聊天式 FAQ 或 RAG 问答

### 9. Export

- **用户目标**: 以选定格式导出知识卡片
- **情感调性**: 可信、可预测
- **布局方向**: 格式选择 → 卡片选择（可选）→ 安全说明 → 导出按钮 → 结果
- **关键状态**: 格式选择、导出中、完成
- **Copy 语调**: 明确的能力说明（"导出 markdown、JSON、OPML"，"不写 Obsidian vault"）
- **不要做**: 不要暗示可以导出到所有可能的服务

### 10. Provider Readiness

- **用户目标**: 检查 LLM provider 配置状态
- **情感调性**: 技术性但友好
- **布局方向**: 检查清单（已配置/未配置）
- **Copy 语调**: 帮助性——"配置模型以开始处理知识"
- **不要做**: 不要泄露 API key 或 secret 信息

### 11. Settings / Current Limitations

- **用户目标**: 理解产品当前能力和限制
- **情感调性**: 诚实、透明
- **布局方向**: 分节的能力/限制说明
- **Copy 语调**: 事实性——"当前支持 X，不支持 Y"
- **不要做**: 不要过度承诺未来能力

### 12. Lab/Internal Graph Page

- **用户目标**: （如保留可见）探索 4 种 NodeType 的本地图谱
- **情感调性**: 实验性、受限制的
- **布局方向**: 图谱画布 + LAB badge + 限制说明
- **Copy 语调**: 实验性——"这是实验室功能，仅支持 4 种节点类型"
- **不要做**: 不要暗示这是主路径功能，不要暴露 8 种 NodeType 选择器

---

## G. 设计系统 Token（候选）

以下 token 为候选定义，不在本轮实现。

### Color Roles
```
--color-bg: #faf9f5
--color-surface: #ffffff
--color-surface-alt: #f3f1eb
--color-text-primary: #1c1b18
--color-text-secondary: #5e5c56
--color-text-tertiary: #8a8880
--color-border: rgba(0, 0, 0, 0.08)
--color-accent: #2d7d5f
--color-accent-hover: #236b4f
```

### Status Colors
```
--color-status-draft: #b8860b
--color-status-approved: #2d7d5f
--color-status-lab: #8a8880
--color-warning: #cc7a00
--color-error: #c04040
```

### Surface Levels
```
--surface-flat: 0
--surface-raised: 0px 2px 12px rgba(0,0,0,0.03), 0px 1px 4px rgba(0,0,0,0.015)
--surface-overlay: 0px 4px 24px rgba(0,0,0,0.06)
```

### Border Radius
```
--radius-sm: 4px
--radius-md: 8px
--radius-lg: 12px
--radius-xl: 16px
--radius-full: 9999px
```

### Spacing Scale
```
--space-2xs: 4px
--space-xs: 8px
--space-sm: 12px
--space-md: 16px
--space-lg: 24px
--space-xl: 32px
--space-2xl: 48px
--space-3xl: 64px
```

### Typography Scale
```
--font-serif: 'Source Serif 4', Georgia, serif
--font-sans: 'DM Sans', -apple-system, sans-serif
--font-mono: 'JetBrains Mono', monospace

--text-display: 36px / 1.15 / 500
--text-h1: 28px / 1.2 / 500
--text-h2: 22px / 1.25 / 500
--text-h3: 18px / 1.3 / 600
--text-body-lg: 16px / 1.6 / 400
--text-body: 15px / 1.5 / 400
--text-body-sm: 14px / 1.45 / 400
--text-caption: 12px / 1.35 / 500
--text-code: 13px / 1.5 / 400
```

---

## H. 组件清单

### 核心组件（主路径）

| Component | Purpose | Visual Role | States | Design Risks |
|-----------|---------|-------------|--------|-------------|
| **AppShell** | 应用外框：sidebar + header + 内容 | 安静的框架，不争抢注意力 | loaded, loading, error | 不要过度设计侧边栏 |
| **Sidebar** | 主导航：主路径页面 + 折叠的 lab 区域 | 精简、安静、功能明确 | collapsed/expanded (lab section) | 不要加入未稳定功能 |
| **PageHeader** | 页面标题 + 描述 + 可能的操作 | serif 标题建立编辑权威 | default, with actions | 保持标题一致层级 |
| **KnowledgeCard** | Library/Drafts 中的卡片条目 | 纸质感表面，whisper border，多层阴影 | default, hover, selected | 不要塞入过多元数据 |
| **ReviewQueueItem** | 审查队列中的可展开项 | 全宽卡片，清晰的 draft→review→approve 流程 | pending, reviewing, approved, rejected | 批准操作需明确 guard |
| **ApprovalPanel** | 卡片详情中的审批面板 | 关键安全 UI，状态时间线 | pre-approval, post-approval | 不能做成自动批准 |
| **ProvenanceBlock** | 来源溯源信息 | 轻量信息块，mono 字体路径 | collapsed, expanded | 不要过度复杂化 |
| **RecallResult** | 搜索命中结果 | 卡片式，匹配字段高亮 | hit, no-hit, explain expanded | BM25 边界需诚实表达 |
| **WikiSection** | Wiki 内容分节 | 编辑性长文布局 | loaded, loading | 不要做成 RAG 回答 |
| **ExportPreview** | 导出预览 + 安全说明 | 清晰格式选择 + 安全 callout | format selected, exporting, done | 安全说明必须可见 |

### 辅助组件

| Component | Purpose | Visual Role | States | Design Risks |
|-----------|---------|-------------|--------|-------------|
| **EmptyState** | 各页面的空状态引导 | 温暖的引导语，邀请行动 | per-page variants | 不要写成营销语 |
| **LabFeatureBanner** | lab/internal 页面的实验性标识 | 中性灰色 banner，不喧宾夺主 | visible | 不能看起来像 error |
| **SafetyNotice** | 安全边界说明 | 体面的 callout，非刺眼 alert | visible | 不能被忽略 |
| **CurrentLimitationsNotice** | 当前限制说明 | 诚实的限制列表 | visible | 不要过度承诺 |

---

## I. 实施路线图

### Stage 0 — Design Direction Lock（本轮）
- 本设计方向文档
- 实施计划文档
- **无产品 UI 变更**

### Stage 1 — Design Shotgun（建议下一步 /design-shotgun）
- 生成 3-5 个视觉变体（静态原型）
- 基于本设计方向的核心 token
- 仅静态 HTML/CSS 原型

### Stage 2 — Design Review（建议 /plan-design-review）
- 选择一个方向
- 识别风险
- 确认 token 候选

### Stage 3 — Design System Foundation
- 实现 design tokens（CSS 变量）
- AppShell + Sidebar 布局重设计
- 排版层级落地
- 基础组件（Button、Card、Badge、EmptyState）
- **不改变产品逻辑**

### Stage 4 — Core Page Redesign
- Review Queue（最关键——审批体验是核心差异化）
- Library（卡片布局 + filter bar polish）
- Card Detail（阅读体验优化）
- Recall/Search（结果呈现 polish）
- Wiki/Export（长文阅读 + 导出体验）

### Stage 5 — Design QA
- 视觉一致性 pass
- 可访问性 pass（contrast、focus、tab order）
- Product copy pass
- 响应式 pass
- 使用 /design-review 验收

---

## J. 自动运行实施护栏

### 显式约束

1. **不改变后端逻辑**——设计层只改 CSS/HTML/React 组件外观
2. **不恢复 Graph/Sensemaking 扩张**——lab 页面只做最小样式调整
3. **不做 RAG/embedding/vector DB**
4. **不调用真实 LLM**
5. **不新增大型前端依赖**——（如需新字体，Google Fonts 的 <link> 即可）
6. **不复制参考站点的品牌标识**——配色、字体、插图均为独立选择
7. **不做一次性全量重设计**——每个 stage 独立 commit/push
8. **每个 stage 必须有 tests/build/gates**
9. **commit/push 在每次连贯变更后执行**

### 品牌保护

- **Forest Green (#2d7d5f)** 是我们的品牌色选择，不与任何参考站点冲突
- **Source Serif 4 + DM Sans** 是开源字体组合，不属于任何公司的品牌系统
- **暖纸色系**是设计选择，不是 Notion 的专有属性

---

## 自我评审

| Check | Verdict |
|-------|---------|
| 设计方向是否过于通用？ | No — "Calm Editorial Knowledge Compiler" 是特定于审批知识编译器的方向 |
| 是否太像 Notion/Obsidian/Linear？ | No — 借了 Notion 的温暖纸质感但定位不同（编译器 vs 画布） |
| 是否适合审批优先的知识编译？ | Yes — 审查队列和审批面板是核心设计目标 |
| 是否让 Review/Approval 成为中心？ | Yes — Review Queue 在 page-by-page targets 中优先级最高 |
| 是否过度强调 Graph/Sensemaking？ | No — Graph 只在 lab 页面列表中，明确为实验性质 |
| 是否制造了实施风险？ | No — 分 5 stage 递增，每阶段可独立验证 |
| 是否尊重 local-first 和安全边界？ | Yes — SafetyNotice、CurrentLimitationsNotice 是显式组件 |
| 是否能驱动多阶段 auto-run？ | Yes — 每个 stage 有明确的交付物和 gate |
