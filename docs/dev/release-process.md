# Release Process

MindForge 发布流程。

---

## 版本号

遵循 `v<major>.<minor>` 格式：

- **v0.1** — 稳定 release，local-first / LLM-first 主链路完成
- **v0.2** — 开发中，Multi-source ingestion + Wiki presentation

---

## 发布检查清单

### 代码质量

- [ ] `ruff check src tests` 通过
- [ ] 完整测试套件通过（`pytest -q`）
- [ ] 无 hardcoded secrets
- [ ] 无 debug print / console.log 残留

### 文档

- [ ] README.zh-CN.md 和 README.md 更新
- [ ] 用户文档（`docs/zh-CN/`、`docs/en/`）与代码同步
- [ ] 开发者文档更新
- [ ] Release notes 包含 breaking changes 和迁移指南

### 安全

- [ ] API key 不在代码、日志、文档中
- [ ] Secret store 路径在 `.gitignore` 中
- [ ] 无自动审批路径
- [ ] Wiki 不从 raw source 生成

### 发布步骤

1. 确保所有检查通过
2. 更新 version 标识
3. 写 release notes
4. 打 tag：`git tag v<version>`
5. 推送 tag：`git push origin v<version>`

---

## Release Notes 模板

```markdown
## vX.Y

### 新功能
- ...

### 改进
- ...

### 修复
- ...

### 已知限制
- ...

### 迁移指南
- ...
```

---

## 回滚策略

如发现严重问题：

1. 确认问题范围和影响
2. 评估 fix forward vs rollback
3. 如需 rollback：回退到上一个稳定 tag
4. 发布 hotfix 版本
