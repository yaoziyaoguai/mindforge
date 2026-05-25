# Product Main Path Dogfood Plan

**日期**: 2026-05-25
**状态**: proposed
**基于**: v4.2.1 partial remediation closure (all four PARTIAL findings closed, gate clean)
**参考**: `docs/plans/2026-05-25-087-post-stabilization-direction.md`

---

## Goal

用 50-100 个非敏感本地资料验证 MindForge 产品主路径是否真实可用：

```
Source / Import → ai_draft → Review → explicit approval → human_approved
→ Library → Recall / Wiki → Export
```

这不是功能扩张，而是用真实使用来暴露 onboarding、import、review、search、wiki、export、empty state、error state 的问题。

---

## Non-Goals

- 不实现 v4.3
- 不新增 Graph / Sensemaking / Entity / Community 能力
- 不调用真实 LLM / Cubox / Upstage / 外部服务（除非用户显式 opt-in）
- 不处理私人敏感资料、公司机密资料
- 不写真实 Obsidian vault
- 不做 RAG answering / embedding / vector DB / GraphRAG
- 不新增大型依赖
- 不做抽象优先的 service/schema 大拆分
- 不修改 explicit approval / human_approved 安全语义
- Graph / Sensemaking 只能作为 lab/internal evidence support 观察

---

## Sample 资料策略

### 数量：50-100 个文件

### 类型分布

| 类型 | 建议数量 | 说明 |
|------|---------|------|
| Markdown 笔记 | 30-40 | 技术笔记、阅读摘录、项目记录 |
| TXT 纯文本 | 10-15 | 简短备忘、命令行输出记录 |
| HTML 本地文件 | 5-10 | 保存的网页、文档导出 |
| PDF（文本型） | 5-10 | 非扫描件论文、报告 |
| DOCX | 5-10 | 课程资料、工作文档 |
| 多种混合目录 | — | 模拟真实文件组织 |

### 内容规则

- 非敏感：公开资料、学习笔记、技术文档、开源项目文档
- 不涉及：个人身份信息、财务数据、公司内部资料、密码/密钥
- 可来源：公开论文、开源 README、Wikipedia 导出、个人学习笔记

### 获取方式

1. **synthetic 优先**：用脚本生成非敏感示例资料（fake knowledge cards, fake notes）
2. **redacted 其次**：对已有公开资料做脱敏/裁剪
3. **用户提供**：用户确认非敏感范围后提供真实资料（仅当用户明确 opt-in）

---

## Dogfood Phases

### Phase 1: Fake/Local Dry-Run（默认起始点）

不使用真实 LLM，使用 fake provider 完成全路径：

1. 初始化临时 workspace（非真实 vault 目录）
2. 生成 50-100 synthetic 非敏感 source 文件
3. 用 fake provider import + process（生成 ai_draft）
4. Review + explicit approve
5. Library 浏览、搜索、查看卡片详情
6. Wiki rebuild（fake/safe fallback）
7. Export 已审批卡片

### Phase 2: Real LLM Opt-In（需用户显式触发）

如果用户在 Web Setup 中显式配置真实 API key 并 opt-in：

1. 使用已配置的真实模型 re-process 部分 source
2. 比较 fake vs real ai_draft 质量
3. 验证 real LLM wiki rebuild
4. 验证 provider readiness / safety boundaries

### Phase 3: Dogfood Report

汇总 Phase 1 + Phase 2 结果：
- 每步成功率
- 失败原因分类
- 用户困惑点
- 阻塞性 bug
- 推荐修复优先级

---

## User Journey Test Plan

### Import Journey

| Step | Check | Expected |
|------|-------|----------|
| 添加单个 source 文件 | Web Setup / CLI | 成功添加，显示 pending |
| 添加 source 目录 | Web Setup / CLI | 递归扫描，显示文件数 |
| Process now | Web / CLI | run 创建，进入 processing |
| 查看 run 状态 | `mindforge runs list/show` | 显示 step、进度、summary |
| 不支持的格式 | 导入 .doc 旧格式 | 友好提示转换 |

### Review Journey

| Step | Check | Expected |
|------|-------|----------|
| 查看 ai_draft 列表 | Web Drafts / CLI approve list | 按 source 分组，显示标题 |
| 查看 draft 详情 | Web / CLI | 显示 5 段处理结果 |
| 审批单张卡片 | Web / CLI approve --confirm | status → human_approved |
| 拒绝卡片 | Web Trash | 卡片进入 Trash |
| 恢复卡片 | Web Trash restore | 卡片恢复到 ai_draft |

### Library Journey

| Step | Check | Expected |
|------|-------|----------|
| 浏览已审批卡片 | Web Library | 显示标题、tag、source、日期 |
| 查看卡片详情 | 点击卡片 | 显示 body、source provenance、related cards |
| Related cards | 卡片详情 | 显示确定性关系（same source/tag/wiki_section）|
| 搜索卡片 | Web Recall / CLI recall | BM25 返回相关结果 |
| 空状态 | 搜索无结果 | 显示友好 empty state |
| 导出卡片 | Library export | JSON/OPML/Zip 导出成功 |

### Wiki Journey

| Step | Check | Expected |
|------|-------|----------|
| 查看 Wiki 状态 | Web Wiki / CLI wiki status | 显示 last rebuilt、card count |
| Rebuild Wiki | Web / CLI wiki rebuild | 生成结构化 topic pages |
| 浏览 Wiki | Web Wiki | 显示 sections、references、source links |
| Wiki 引用 | 查看 reference | 链接回 Library 卡片 |
| Safe fallback | Advanced → Safe rebuild | 应急回退可用 |
| 空状态 | 无 approved cards 时 | 友好提示 |

### Export Journey

| Step | Check | Expected |
|------|-------|----------|
| 选择卡片 | Library 多选 | 选中计数更新 |
| 导出 JSON | 选择 JSON 格式 → 导出 | 下载 JSON 文件 |
| 导出 OPML | 选择 OPML 格式 → 导出 | 下载 OPML 文件 |
| 导出 Zip | 选择 Zip 格式 → 导出 | 下载含 .md 文件的 Zip |

---

## CLI/API Smoke Plan

```bash
# Workspace 初始化
mindforge init --workspace /tmp/mindforge-dogfood

# Source 管理
mindforge watch add <sample-dir> --every manual
mindforge watch status
mindforge import <sample-file>

# Processing
mindforge runs list
mindforge runs show <run_id>

# Review & Approve
mindforge approve list
mindforge approve show --card <ref>
mindforge approve <ref> --confirm

# Library
mindforge library list
mindforge library show <ref>

# Recall
mindforge recall --query "knowledge"
mindforge recall --query "学习"

# Wiki
mindforge wiki status
mindforge wiki rebuild
mindforge wiki show

# Export
mindforge export --format json --output /tmp/export-test/

# Health
mindforge health
mindforge doctor

# Status
mindforge status
mindforge version
```

---

## Web Smoke Plan

用 Browser MCP / Playwright 验证以下页面可访问且无 console error：

| 页面 | 检查项 |
|------|--------|
| Home (`/`) | Dashboard 加载、safety summary 显示、next actions 列表 |
| Setup (`/setup`) | 模型配置、source 添加、workflow 展示 |
| Sources (`/sources`) | Watched sources 列表、status 显示、process now 按钮 |
| Drafts (`/drafts`) | Draft 列表、展开预览、approve 按钮 |
| Library (`/library`) | Card grid、card detail、related cards、GraphExplorer（lab/internal）|
| Recall (`/recall`) | 搜索框、搜索结果、empty state |
| Wiki (`/wiki`) | Wiki 状态、rebuild 按钮、wiki 内容 |
| Trash (`/trash`) | Trash 列表、restore 按钮 |
| Health (`/health`) | Health report、maintenance suggestions |
| Dogfood (`/dogfood`) | Report 加载（internal） |

---

## Success Criteria

- [ ] 完成一次完整路径：Import → Review → Approve → Library → Recall → Wiki → Export
- [ ] 每个步骤至少处理 20 张卡片
- [ ] 无 P0 阻塞性 bug（应用崩溃、数据丢失、secret 泄露）
- [ ] P1 bug（功能不可用、错误状态无反馈）≤ 3 个
- [ ] 所有 Web 页面可加载、无 console error
- [ ] 所有 CLI 命令正常退出
- [ ] 审批语义未被绕过（ai_draft 不能直接进入 Library）
- [ ] 不产生任何真实 secret / API key / 私人资料写入
- [ ] Graph/Sensemaking 不出现在主路径结论中（除非作为 lab/internal 观察项）

---

## Stop Conditions

立即停止并报告：

- [ ] 需要读取 .env / secret store / 真实 API key
- [ ] 需要调用真实 LLM / Cubox / Upstage（除非用户显式 opt-in Phase 2）
- [ ] 需要处理私人敏感资料
- [ ] 需要写真实 Obsidian vault
- [ ] 发现 P0 安全风险
- [ ] 审批语义被绕过
- [ ] repo 不在 clean main 或 upstream 不对齐

---

## Suggested First Implementation Loop

1. 创建临时 dogfood workspace：`/tmp/mindforge-dogfood`
2. 生成 50 个 synthetic 非敏感 source 文件（用脚本/Markdown 模板）
3. `mindforge init` → `mindforge watch add` → `mindforge watch scan`
4. 在 fake provider 模式下完成 import → process → review → approve
5. 记录每一步的 friction points
6. 不修 bug（除非阻塞 dogfood）— 只记录
7. 产出 Phase 1 dogfood report

---

## What Must NOT Be In Main Path

以下能力不得出现在 dogfood 主路径验证中，仅可作为 lab/internal 观察项：

| 能力 | 原因 | 允许的观察方式 |
|------|------|--------------|
| Graph / GraphExplorer | lab/internal, 仅 4 NodeType | Library 页内嵌入口，不影响主路径 |
| Sensemaking Workspace | lab/internal, heuristic-only | 独立路由 /sensemaking，不影响主路径 |
| Entity Resolution | lab, candidate-only | 不作为审批/检索依据 |
| Community / Topic | partial lab | Library community browser 可用但不在主路径 |
| Extension Plugin | lab, architecture placeholder | 不使用、不验证 |
