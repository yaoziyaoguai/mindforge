# Sample Workspace Validation Path

日期: 2026-05-28
用途: 在 User Validation 之前验证 demo workspace 和所有主路径页面在 auto-fallback fake provider 下正常工作。

---

## 前置条件

- MindForge 零配置启动: `.venv/bin/mindforge web --port 8766 --no-open`
- 未配置任何真实模型 (auto-fallback to fake LLM)
- 浏览器打开 `http://localhost:8766`

---

## Validation Checklist

### 1. QuickStartWizard 流程

| Step | Check | 预期 |
|------|-------|------|
| 1.1 | 首页显示 QuickStartWizard | Welcome + 3 步向导 |
| 1.2 | Step 1 "了解" | 展示 MindForge 核心概念 |
| 1.3 | Step 2 "创建" | 提供 "Create Demo Workspace" 按钮 |
| 1.4 | 点击 "Create Demo Workspace" | 创建成功，跳转 Step 3 |
| 1.5 | Step 3 "探索" | 列出可探索的页面 |
| 1.6 | 完成后 | 首页展示 demo 卡片 + demo badge |
| 1.7 | Console 无 error | 无 4xx/5xx, 无 JS error |

### 2. Demo Cards 验证

| Check | 预期 |
|-------|------|
| 2.1 | 至少 6 张 demo 卡片 | 6 张卡片在 Library 可见 |
| 2.2 | 卡片状态 = human_approved | approval_method = demo_sample |
| 2.3 | 卡片有标题/正文/tags/track | 内容完整可渲染 |
| 2.4 | 卡片不显示 "demo" 以外的异常标签 | 无 stale/fake/failed 标记 |
| 2.5 | 卡片不携带真实私人数据 | 所有内容为 synthetic |

### 3. 主路径页面可用性

| Page | Check | 预期 |
|------|-------|------|
| 3.1 Home | 加载 | 显示卡片分组 + QuickStartWizard (如首次) |
| 3.2 Setup | 加载 | 显示 "demo mode" + provider 配置为空 |
| 3.3 Sources | 加载 | 显示 Import 选项 + source list (空) |
| 3.4 Review | 加载 | 显示 "暂无待审阅卡片" (如无新导入) |
| 3.5 Library | 加载 | 显示 demo 卡片列表，筛选/排序可用 |
| 3.6 Recall | 加载 | 搜索框可用，搜索 "知识" 返回结果 |
| 3.7 Wiki | 加载 | "生成 Wiki" 可用，生成后内容非空 |
| 3.8 Export | 加载 | 格式选择和下载按钮可用 |

### 4. Recall 功能验证

| Check | 预期 |
|-------|------|
| 4.1 | 搜索 "AI" | 返回包含 AI 相关内容的卡片 |
| 4.2 | 搜索不存在的内容 | 返回空状态 + explain zero hits |
| 4.3 | explain 面板可用 | 点击展开，显示匹配字段/分数 |

### 5. 页面引导验证

| Page | Check | 预期 |
|------|-------|------|
| 5.1 Home | OnboardingHint 显示 | 首页引导横幅 |
| 5.2 Setup | OnboardingHint 显示 | 配置页引导 |
| 5.3 Sources | OnboardingHint 显示 | 导入页引导 |
| 5.4 Review | OnboardingHint 显示 | 审阅页引导 |
| 5.5 Library | OnboardingHint 显示 | 知识库引导 |
| 5.6 Recall | OnboardingHint 显示 | 检索页引导 |
| 5.7 Wiki | OnboardingHint 显示 | Wiki 引导 |
| 5.8 Export | OnboardingHint 显示 | 导出页引导 |

### 6. Console Error Check

| Check | 预期 |
|-------|------|
| 6.1 | No console.error | 0 errors |
| 6.2 | No console.warn (except known) | 无意外 warning |
| 6.3 | No network 4xx | 所有 API call 成功 |
| 6.4 | No network 5xx | 后端正常响应 |
| 6.5 | 无 API key/secret 泄露 | 检查所有 console log 和 DOM |

### 7. i18n 验证

| Check | 预期 |
|------|------|
| 7.1 | 中文界面完整 | 所有页面文案为中文 |
| 7.2 | 英文切换可用 | 切换后所有文案为英文 |
| 7.3 | Onboarding text 完整 | zh = 33 keys, en = 33 keys |

---

## Execution

### Method 1: Browser MCP Smoke (preferred)

使用 Chrome DevTools MCP 自动执行以上 checklist。

```bash
# 启动应用
.venv/bin/mindforge web --port 8766 --no-open

# 在另一个终端使用 browser MCP：
# 1. navigate http://localhost:8766
# 2. take_snapshot
# 3. 按 checklist 逐项验证
```

### Method 2: Manual Browser Smoke

在浏览器中手动打开 `http://localhost:8766`，按 checklist 逐项验证。

---

## Results

| 日期 | 方法 | 结果 | 备注 |
|------|------|------|------|
| ________ | Browser MCP / Manual | PASS / FAIL | ________ |

---

## Failure Handling

如果任何 check 失败:
1. 记录失败项和实际表现
2. 判定是否 block User Validation (P0 = block, P1 = block, P2 = can proceed with note)
3. 修复 P0/P1 后重新跑
