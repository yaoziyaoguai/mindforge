---
title: "v1.5 I3: Obsidian Binding Design Doc"
type: design-doc
status: draft
date: 2026-05-25
parent: v1.5 Safe Integration & Import/Export Expansion
priority: P2
---

# Obsidian Binding Design Doc

## 现状

MindForge 当前通过 CLI 与 Obsidian 交互：

- `mindforge obsidian next` — 查看 staged export 状态和推荐下一步（只读导航）
- `mindforge obsidian export` — 将 approved cards 导出到 staging 目录（dry-run）
- `mindforge obsidian manifest` — 生成导出清单供 manual inspection

**硬边界**：不写真实 Obsidian vault，不做 formal note write，不做 plugin。

参考实现：`src/mindforge/obsidian_workflow.py`、`src/mindforge/safety_policy.py`

## "Binding" 是什么

"Binding" 指 MindForge 与 Obsidian vault 之间的**可选、显式、单向**数据通道：

- **方向**：MindForge → Obsidian（导出），不做 Obsidian → MindForge（导入）
- **触发**：用户显式操作，永不自启
- **范围**：仅 `human_approved` 卡片，不碰 `ai_draft`

不做的：
- Obsidian plugin
- 自动双向同步
- 后台守护进程
- 写 `.obsidian/` 配置目录

## 三层安全模型

### Layer 1: Staged Export（当前已实现）

```
MindForge cards_dir  ──copy──>  staged_export_dir/
                                    ├── manifest.json
                                    ├── card-1.md
                                    └── card-2.md
```

- 输出到独立 staging 目录（不在 Obsidian vault 内）
- 用户 manual inspection 确认后才手动复制到 vault
- 不写 vault，不碰 `.obsidian/`

### Layer 2: Vault-Aware Export（未来可选）

```
staged_export_dir/  ──user confirms──>  {vault}/Knowledge-Cards/
                                            ├── card-1.md
                                            └── card-2.md
```

**前置条件**：
- 用户在 `configs/mindforge.yaml` 中显式配置 `obsidian.vault_path`
- 配置项不在 Web UI 中暴露（仅 CLI/config 文件）
- 每次写入前展示 diff preview，用户确认后才执行
- 写入目标限制在 `{vault}/Knowledge-Cards/` 子目录内

**安全约束**：
- 永不创建目录（vault 必须已存在，目标子目录必须已存在）
- 永不覆盖已有文件（同名冲突 → 跳过 + 警告）
- 永不删除 vault 中的文件
- 永不修改 frontmatter 以外的 metadata
- 导出的卡片文件名使用 `{card_id}.md` 格式

### Layer 3: Native Integration（远期愿景，不在当前 roadmap）

- Obsidian 社区插件（独立仓库）
- 不做

## 配置设计

```yaml
# configs/mindforge.yaml — obsidian 段（可选）
obsidian:
  # 是否启用 vault-aware export（默认 false）
  enabled: false
  # Obsidian vault 根路径（绝对路径）
  vault_path: ""
  # 导出目标子目录（相对于 vault_path）
  target_dir: "Knowledge-Cards"
  # 导出前是否要求用户确认（始终 true，不可配置关闭）
  require_confirmation: true
```

**Web UI 行为**：
- 即使配置了 obsidian 段，Web UI 的导出面板仍只做浏览器下载
- Obsidian vault 写入仅通过 CLI 触发
- 这是安全隔离，不是技术限制

## CLI 命令设计

```bash
# Staged export（当前已有）
mindforge obsidian export --card-ids id1,id2 --output-dir ./staged/

# 新增：vault-aware export（需 obsidian.enabled = true）
mindforge obsidian publish --card-ids id1,id2 --dry-run   # 预览
mindforge obsidian publish --card-ids id1,id2             # 执行

# 新增：查看 vault 绑定状态
mindforge obsidian status
```

## 不在范围内

- Obsidian → MindForge 导入（反向通道）
- 实时文件监听（watch mode）
- 双向同步 / 冲突解决
- Obsidian 插件（独立仓库，不在 MindForge monorepo）
- Web UI 触发 vault 写入
- 写 `.obsidian/` 配置、模板、插件目录
- 处理 `_attachments`、图片、附件

## 与现有安全策略的关系

本设计不改变 `safety_policy.py` 中的任何边界：

- `no_formal_obsidian_note_write` — 只有在用户显式执行 `obsidian publish` 时豁免，且仅写入用户指定的 vault
- `no_obsidian_plugin` — 不变
- `human_approved_gate` — 仅导出 approved 卡片，不变

## 实现优先级

| Layer | 状态 | 备注 |
|-------|------|------|
| Layer 1: Staged Export | 已实现 | `obsidian_workflow.py` |
| Layer 2: Vault-Aware Export | P2，待 spec | 需配置段 + CLI 命令 + 安全门 |
| Layer 3: Native Plugin | 不做 | 独立仓库 |

## 参考

- `src/mindforge/safety_policy.py` — 现有安全边界定义
- `src/mindforge/obsidian_workflow.py` — 现有 staged workflow
- `src/mindforge/obsidian_cli.py` — 现有 CLI 命令
- `src/mindforge/obsidian_stage.py` — 现有 staging 逻辑
