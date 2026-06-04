# MindForge 本地控制台设计系统

轻量级设计系统文档 —— 设计原则 + token 参考 + 组件使用规范 + 页面结构规则。
P3 Design System Foundation, 2026-05-28。

---

## 产品定位

MindForge 本地控制台是 MindForge 的本地优先 Web 界面。它是一个单用户、仅在本机的个人知识工作台，用于配置、检查、审阅、批准、拒绝和召回自己的知识卡片，而不需要停留在 CLI 中。

它不是 SaaS 产品，不是管理仪表盘，也不是营销网站。它应该像一个安静的本地工具，放在用户自己的文件之上：透明、在可写操作时尽可能可逆、在可能改变长期记忆的写操作时保持显式。

## 设计原则

- **Calm（安静）**：默认表面安静、可读、低戏剧性。UI 避免营销文案、繁忙的渐变和装饰性动画。
- **Trustworthy（可信）**：每个页面都显示它正在读取的本地状态和下一步将发生的操作。
- **Beginner-safe（新手友好）**：空状态解释下一步命令或本地操作，而不是假设用户有 CLI 经验。
- **Review-focused（审阅优先）**：草稿被视为等待人类判断的工作，不是需要盖章的生成内容。
- **Local-first（本地优先）**：产品语言、状态标签和安全栏强调数据保留在本地。所有远程调用必须 opt-in。
- **Reversible（可逆）**：尽可能使用户操作可逆。审批操作可以撤销，导入可以删除，配置可以重置。

## 产品人格

MindForge 的 Web 界面应该感觉像一个**安静的编辑性知识工作台**。用户在 MindForge 中的体验应该像是在安静的图书馆中翻阅精心编排的卡片目录——不是繁忙的 SaaS 仪表盘，不是炫目的 AI demo，不是拥挤的笔记应用。

**应该是什么样的**：
- 纸质感、克制的色彩
- 编辑性排版权威
- 充足的留白
- 温暖的中性色调

**不应该是什么样的**：
- SaaS 管理面板（数据密集、冷色调、无穷表格）
- AI 聊天机器人界面（对话气泡、紫色渐变、闪烁动画）
- Notion 克隆（虽然是借了温暖纸质感，但 MindForge 是编译器而非画布）
- Obsidian 克隆（不做图数据库 UI、不做图谱优先、不做本地文件浏览器）
- 闪亮的落地页风格（渐变 CTA、3 列图标网格、装饰性 blob）
- 黑暗终端 UI（虽然 local-first，但用户不是开发者/运维人员）

## 字体

| 用途 | 字体 | 回退 |
|------|------|------|
| 标题 | Source Serif 4 | Georgia, serif |
| 正文 | DM Sans | system sans-serif |
| 代码 / 文件路径 | JetBrains Mono | monospace |

## 颜色 Token

| Token | 值 | 用途 |
|-------|-----|------|
| `--surface` | `#FAF8F5` | 页面背景（微暖纸质感） |
| `--card-bg` | `#FFFFFF` | 卡片背景 |
| `--card-shadow` | 4 层渐变 | 卡片深度（来自 Variant B） |
| `--text-primary` | `#1A1A1A` | 正文 |
| `--text-secondary` | `#555555` | 次要文本 |
| `--draft-border` | `#E8A44A`（amber）| ai_draft 状态指示 |
| `--approved-border` | `#4CAF50`（green） | human_approved 状态指示 |
| `--danger` | `#C62828` | 删除/拒绝操作 |
| `--safe` | `#2E7D32` | 确认/安全操作 |

## 卡片样式

- **border-radius**: 10px
- **shadow**: 4 层阴影堆叠（来自 Variant B）
- **status accent**: 左侧 3px 彩色边框（amber = draft, green = approved）
- **padding**: 充足（16-24px）

## 组件使用规范

### 侧边栏导航

按 pipeline 分组：
1. **Sources → Review → Library**（主路径）
2. **Recall / Wiki**（工具）
3. **Graph / Sensemaking**（折叠的 Lab 分组）

### 空状态

每个空状态都应该：
- 解释当前页面是做什么的
- 提供下一步操作建议
- 使用温暖、鼓励性的语言

### 安全栏

Web 界面顶部应显示安全摘要：
- 当前 provider 状态（fake vs real）
- API key 是否已配置
- 是否有待审批的草稿

## 页面结构规则

- **Library 页面**：卡片列表 + 详情，不是表格
- **Review 页面**：草稿审阅，不是批量操作
- **Recall 页面**：搜索结果 + 解释面板
- **Wiki 页面**：运行时 Topic View，不是 LLM 合成
- **Setup 页面**：配置表单，不是仪表盘
