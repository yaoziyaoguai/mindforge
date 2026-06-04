# MindForge 归档计划

日期：2026-06-05
状态：软归档 — 已暂停的学习项目

## 1. 归档类型

此为**软归档**（也称为"暂停"或"学习项目保留"）。具体来说：

- **不是** GitHub 硬归档（仓库未在 GitHub 上归档）
- **不是** 代码删除（所有代码保留在仓库中）
- **不是** 目录重组（不移动任何文件或目录）
- **不是** git 标签（本次提交不创建 `archive/vX-final` 或 `paused/YYYY-MM-DD` 标签）
- **不是** 推送到远程（变更仅在本地提交）
- 代码**仍然可以在本地运行** — 没有任何破坏
- 项目**可以从任何方向在未来重新启动**

**软归档的含义**：我们停止积极投入新功能和产品开发。仓库作为学习产物、复盘参考和未来实验的潜在起点保留。

## 2. 当前状态

| 项目 | 状态 |
|------|--------|
| 分支 | `main` |
| HEAD | `e02c9fc` |
| 领先 origin/main | 0 |
| 落后 origin/main | 11（提交后将更新） |
| 脏跟踪变更 | 无 |
| 未跟踪文件 | `pictures/`、`setup.png`、`tmp/`、`uv.lock`、`docs/specs/*_v2.md`、`docs/superpowers/brainstorms/*`、`docs/superpowers/reviews/*` |
| 战略文档存在 | 是 — `docs/specs/mindforge_strategic_repositioning.md`、brainstorm、review |
| 复盘文档存在 | 是 — `docs/postmortem/mindforge-postmortem.md`、`mindforge-lessons-for-vibe-coding.md`、`mindforge-archive-plan.md` |
| 验证协议存在 | 是 — `docs/product/validation-protocol.md`（从未执行） |

### 不再积极推进的方向

- 独立 Web 知识库产品
- Knowledge Library UI 打磨
- Wiki / Topic Browser 开发
- 关系面板 / 图谱类 UI
- Knowledge Card v2 实现
- Distill Prompt v2 实现
- Obsidian 导出实现
- Agent Memory Infrastructure 实现
- 任何形式的新功能开发

## 3. 停止投资清单

以下领域将不再获得投入。代码**不会被删除** — 其保留在仓库中供参考。

| 领域 | 原因 |
|------|--------|
| **独立 Web 知识库产品** | 未经验证的用户场景；已有工具可覆盖 |
| **Knowledge Library UI 打磨** | UI 问题是表面问题；根本原因在产品方向 |
| **Wiki / Topic Browser** | 没有经用户验证需求的功能 |
| **关系面板 / 图谱类 UI** | 无价值闭环的实验功能；同标签不等于知识图谱 |
| **Knowledge Card v2 实现** | Schema 变更依赖产品形态，而产品形态已不再推进 |
| **Distill Prompt v2 实现** | Prompt 优化解决提取质量，不是产品方向 |
| **Obsidian 导出实现** | 依赖 Obsidian 优先的方向，该方向未经验证 |
| **Agent Memory Infrastructure 实现** | 依赖 agent memory 方向，该方向未经验证 |
| **新功能开发** | 所有新功能需要先验证产品方向 |

## 4. 保留资产清单

以下资产被保留，可在未来项目中复用：

| 资产 | 位置 | 可复用性 |
|-------|----------|-------------|
| **源码管线** | `src/mindforge/ingestion_*.py`、`src/mindforge/import_cli.py` | 高 — 文件导入可复用 |
| **FakeProvider** | `src/mindforge/llm/fake.py` | 高 — 演示/测试模式 |
| **审批优先设计** | `src/mindforge/approval_*.py` | 高 — 适用于任何 AI 输出工作流 |
| **ai_draft / human_approved 边界** | `src/mindforge/cards.py`、`src/mindforge/approver.py` | 高 — 工程契约 |
| **本地优先约束** | `src/mindforge/config.py`、`src/mindforge/secret_store.py` | 高 — 隐私优先设计 |
| **测试** | `tests/` | 中 — 测试模式参考 |
| **文档** | `docs/` | 高 — 文档方法论 |
| **规范文档** | `docs/specs/` | 高 — SPEC 写作模式 |
| **复盘** | `docs/postmortem/` | 高 — 未来项目的学习参考 |
| **验证协议** | `docs/product/validation-protocol.md` | 高 — 终止标准方法论 |
| **工程工作流** | CLAUDE.md、`.claude/` | 高 — SDD/TDD/review/audit 工作流 |
| **可迁移经验** | 本文档 + 复盘 | 高 — 避免重复错误 |

## 5. README 状态更新

以下 README 文件已更新，顶部添加了项目状态横幅：

- `README.md` — 中文

### 中文横幅

```
> **项目状态：Paused / Soft Archived**
> MindForge 当前作为一次 vibe coding 学习项目与复盘样本保留。独立 Web 知识库产品方向不再继续积极推进；代码仍保留用于学习、复盘和未来可能的实验。详细复盘见 [docs/postmortem/](docs/postmortem/)。
```

### 英文横幅

```
> **Project Status: Paused / Soft Archived**
> MindForge is currently preserved as a vibe-coding learning project and postmortem artifact. The standalone Web knowledge-base product direction is no longer actively pursued. The code remains available for reference, learning, and possible future experiments. See [docs/postmortem/](docs/postmortem/) for details.
```

这些横幅放在标题之后、原始内容之前。原始 README 内容保持原样不变。

## 6. 标签决策

**本次提交不创建标签。**

理由：
- 软归档不需要标签
- 标签意味着一个发布里程碑，而这不是
- 如果将来需要标签，可以按需添加：
  - `git tag archive/v0.7-final` — 作为最终发布标记
  - `git tag paused/2026-06-05` — 作为暂停时间戳

## 7. GitHub 归档决策

**目前不建议进行 GitHub 硬归档。**

理由：
- 代码可能仍有学习价值
- 未来实验可能从此代码库重新启动
- GitHub 归档会将仓库设为只读，并标记为"已废弃"
- 软归档（状态横幅 + 复盘）已满足当前需求

**如果将来决定永久停止**，可以考虑 GitHub 归档：
- GitHub Settings → Archive this repository
- 这将使仓库变为只读，并添加"Archived"徽章

## 8. 如果将来重新启动

在编写任何重启 MindForge 的代码之前，必须满足以下条件：

1. **明确的目标用户**：谁会精确地使用它？不是"个人知识管理者" — 要具体。

2. **明确的实际场景**：他们解决的精确问题是什么？不是"组织知识" — 要具体。

3. **3-5 次真实的 dogfood 会话**：真实用户（或你自己）的真实使用，不是假设的场景。

4. **知识提取价值已验证**：有证据表明 AI 提取的知识比好的摘要具有更多的复用价值。

5. **CLI / Markdown 已被证明不足**：有证据表明更简单的形式（脚本、CLI、Obsidian 插件）无法解决问题，从而证明 Web 投入是合理的。

6. **重启 SPEC 已编写**：一份定义重启方向、范围和验收标准的新 SPEC 文档 — 在**任何**实现**之前**。

重启应遵循 vibe coding 启动清单（见 `docs/postmortem/mindforge-lessons-for-vibe-coding.md`）：一句话场景 → 手动验证 → CLI/脚本验证 → 真实 dogfood → 然后决定 Web/后端/架构。
