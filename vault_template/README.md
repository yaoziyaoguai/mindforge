# MindForge Vault 推荐结构

> 本目录是一份**示例 Vault 骨架**。MindForge 不强制你的 Vault 与本结构一比一对应，
> 但 `00-Inbox/` 与 `20-Knowledge-Cards/` 的命名约定必须与 `configs/mindforge.yaml` 中
> `vault.inbox_root` / `vault.cards_dir` 保持一致。

## 顶层约定

```
ObsidianVault/
├── 00-Inbox/                  ← MindForge 只读，所有 source 放这里（推荐入口）
├── 20-Knowledge-Cards/        ← MindForge Writer 唯一写入区
├── 30-Projects/               ← 你手动维护的项目主笔记（MindForge 只读）
├── 40-Reviews/                ← 复习/汇总
├── 90-Archive/
│   └── Skipped/               ← value_score 不达标的素材链接清单
└── _attachments/              ← 图片等附件
```

## 第一天使用

1. 运行 `mindforge init` 创建 vault 骨架。
2. 把第一个 markdown 文件放入 `00-Inbox/`。
3. 运行 `mindforge watch add <path>` 或 `mindforge import <path>` 注册 source 并启动后台处理。
4. 运行 `mindforge runs list` / `mindforge runs show <run_id>` 查看进度。
5. 生成 ai_draft 后：`mindforge approve list` / `approve show` / `approve confirm`。
6. 已审批知识通过 `mindforge library list` / `recall` / `wiki` 查阅。

## 三条物理隔离原则

1. **`00-Inbox/` 一律只读**：MindForge 永不写、不删、不重命名。
2. **`20-Knowledge-Cards/` 由 MindForge 创建**：人工只改 `status` / `Human Note`。
3. **`30-Projects/` 完全人工维护**：MindForge 只读，用作召回锚点。

## source 接入方式

MindForge 通过 `mindforge watch add <path>` 或 `mindforge import <path>` 接入 source。
你可以直接指向任意本地文件或文件夹，无需预先创建分类子目录。

详细数据契约见 `docs/MINDFORGE_PROTOCOL.md`（如存在）。
