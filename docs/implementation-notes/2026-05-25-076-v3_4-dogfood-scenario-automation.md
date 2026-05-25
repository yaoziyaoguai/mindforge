# v3.4 Dogfood Scenario Automation

## 概述

建立 Python 级 dogfood 场景编排器，模拟 import → scan → graph detection → community detection → report generation 的完整知识生命周期。

纯 fake 数据，不调用真实 LLM，不处理真实私人资料。

## 已完成

### U1: Dogfood Scenario Runner (`src/mindforge/dogfood/`)

- `ScenarioStep` / `ScenarioConfig` / `ScenarioResult` frozen dataclasses
- `run_dogfood_scenario(workspace_dir, *, config)` — 执行完整生命周期场景
  - Step 1: workspace_setup — 使用 `build_sample_workspace()` 创建样本工作区
  - Step 2: card_scan — 加载配置、扫描卡片、按 status 分类统计
  - Step 3: graph_detection — 运行 DeterministicGraphBuilder + community detection
  - Step 4: report_generation — 调用 `compute_dogfood_report()` 生成报告
  - Step 5: export_verification — 可选导出验证（默认关闭）
- `run_cli()` — CLI 入口：`python -m mindforge.dogfood.scenario_runner [workspace_dir]`
- 每个步骤记录状态 (passed/skipped/failed)、耗时和证据

### U2: Tests (15 tests)

- `TestScenarioRunner` (9): 全部步骤通过、确认率正确、图谱检测找到边、必需步骤齐全、摘要含关键指标、耗时字段、导出默认跳过、空目录处理、确定性
- `TestScenarioConfig` (2): 禁用图谱、启用导出
- `TestScenarioResult` (2): 不可变性
- `TestCLI` (2): CLI 入口存在、模块导入干净

### U3: 安全边界

- `scenario_runner.py` 已加入 `human_approved` literal 白名单
- 仅做只读统计（按 status 分类计数），不修改卡片状态
- 不执行 approve，不绕过 explicit approval 语义

## 设计决策

- **fake data only** — 场景使用 `tests/fixtures/sample_workspace.py` 生成，不接触真实数据
- **no real LLM** — 所有 provider 设置为 `fake`，不调用任何外部 API
- **deterministic** — 相同配置多次运行产生相同结果（卡片数、图边数、社区数均一致）
- **default export disabled** — 默认不执行导出验证以避免副作用，通过 `ScenarioConfig(run_export=True)` 显式启用

## Gate 结果

| Gate | Command | Exit Code | Result |
|------|---------|-----------|--------|
| ruff | `ruff check src/mindforge/dogfood/ tests/test_dogfood_scenario.py` | 0 | clean (4 auto-fixed) |
| pytest (unit) | `python -m pytest tests/test_dogfood_scenario.py -v` | 0 | 15 passed |
| pytest (full) | `python -m pytest tests/ -q` | 0 | ~2960+ passed |
| npm build | `npm --prefix web run build` | 0 | built in 2.35s |

## 已知限制

- 场景编排器依赖 `tests/fixtures/sample_workspace`（非 production 路径），适合开发和 CI 场景
- 未实现 Web 前端层面的场景 UI 控制面板
- 未模拟 search index 构建步骤（需要 lexical index 初始化）
- export 步骤目前为占位（仅计数，不生成实际导出文件）
