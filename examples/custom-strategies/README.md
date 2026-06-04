# 示例自定义策略 — 合成数据，仅预览

本目录存放的是**合成、非敏感**的声明式自定义策略示例文件。其用途包括：

- 用真实可加载的文件记录 v0.12 声明式自定义策略的格式。
- 支撑 `tests/test_custom_preview_packet_contract.py` 中 Family E 基线断言（Slice 4 发现 + Slice 5 仅预览拒绝）。
- 为下游贡献者提供一个可直接复制粘贴的起点，供其适配自己的（同样为合成的）实验。

## 安全契约

根据 `docs/V0_13_DOGFOODING_READINESS.md` 和 v0.12 能力矩阵（`docs/V0_12_CAPABILITY_MATRIX.md`），本目录中的任何文件：

- **仅供审阅** — `mindforge` 将拒绝执行；
- 绝不会触发真实的 LLM provider 调用；
- 绝不会读取 `.env`；
- 绝不会写入任何 Obsidian vault；
- 绝不会生成 `ai_draft`，也绝不会生成已审批卡片；
- 绝不会自动审批任何内容。

仅当用户显式传递 `--custom-path examples/custom-strategies/` 标志给 `mindforge strategies list` 时才会加载。MindForge 不会隐式扫描此目录。

## 文件

- `user_concept_review.yaml` — 最小合成示例，状态为 `preview`，`safety_policy: ai_draft_only`。与 Slice 5 预览包测试所固定的规范有效样本形状相同。

## 如何查看

```bash
.venv/bin/mindforge strategies list \
  --custom-path examples/custom-strategies/
```

该命令会将此合成策略与内置策略一同列出，并清晰标记为 `(custom)` 和仅预览。要求 `mindforge` 实际运行它将失败，并抛出 `NotYetImplementedStrategyError("preview" + "discovery is not execution")` —— 这是预期且有文档记录的行为。
