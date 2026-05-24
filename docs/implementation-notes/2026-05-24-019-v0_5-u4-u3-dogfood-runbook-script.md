# v0.5 U4+U3 Dogfood Runbook & Fake Dogfood Script 实现笔记

## 日期
2026-05-24

## 目标
- U4: 合并 docs/dogfood.md + docs/real-llm-dogfood.md → docs/dogfood-runbook.md
- U3: 编写 scripts/fake_dogfood.sh 端到端 fake dogfood 验证脚本

## 实现方案

### U4: Dogfood Runbook

**合并策略**：
- 保留两份原始文档的全部内容，添加 redirect header
- 新建 `docs/dogfood-runbook.md` 以统一结构重新组织：
  1. 快速开始（Fake Provider）
  2. 自动验证（fake_dogfood.sh）
  3. 配置真实 LLM
  4. 首次 Scan & Review
  5. 审批 Approve & Wiki
  6. Recall 检索验证
  7. 安全检查清单（新增）
  8. Friction Log
  9. 清理
  10. 常见问题

**安全检查清单**（新增）：配置安全、审批安全、检索安全、沙箱隔离、网络与隐私共 5 个维度，每个维度可勾选确认。

### U3: Fake Dogfood Script

**增强点**（相比 scripts/dogfood_smoke.sh）：
- 导入全部 6 份 samples（而非单一样本）
- 新增 S8: wiki rebuild 步骤
- 结构化 FAIL_COUNT 计数器，退出码 = 失败步骤数
- 多个 recall 查询交叉验证
- S11: 结束后清理临时文件

**安全不变**：
- 零网络请求、零 API key、零 .env 读取
- 所有 LLM 调用使用 fake provider
- 数据全部在 /tmp

## Gate

| Gate | 命令 | Exit Code |
|------|------|-----------|
| bash syntax | `bash -n scripts/fake_dogfood.sh` | 0 |
| git diff --check | `git diff --check` | 0 |

## 已知限制

- fake_dogfood.sh 未在 CI 中自动运行（需要 Python venv + mindforge 安装）
- wiki rebuild 对 fake provider 内容的验证精度有限（fake 内容为确定性占位输出）
- 原始 dogfood 文档保留作为参考，但不再维护更新
