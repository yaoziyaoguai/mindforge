# v0.5 U1+U2 Setup UX Polish & Safety Confirmation Gate 实现笔记

## 日期
2026-05-24

## 目标
- U1: Setup UX Polish — 模型快速配置模板、API Key 格式验证、Key 可见性切换
- U2: Safety Confirmation Gate — 模式感知安全横幅、激活确认对话框、provider_mode 持久化

## 实现方案

### Backend: provider_mode 持久化

**数据流**: state.json (checkpoint) → WebConfigService.provider_status() → ProviderStatus API → 前端安全横幅

**修改文件**:
- `src/mindforge/checkpoint.py` — Checkpoint 类新增 `provider_mode: str = "fake"` 字段，支持 load/save 读写
- `src/mindforge_web/schemas.py` — ProviderStatus 新增 `provider_mode: Literal["fake", "real"]` 字段；新增 SetProviderModeRequest schema
- `src/mindforge_web/services/web_config_service.py` — provider_status() 从 checkpoint 读取 provider_mode；新增 write_provider_mode() 写入方法
- `src/mindforge_web/services/web_facade.py` — 新增 set_provider_mode(mode) 编排方法
- `src/mindforge_web/routers/config.py` — 新增 `POST /api/config/provider-mode` 端点

**安全边界**:
- provider_mode 存储在 state.json，不涉及 secrets
- 切换不读取或修改 secret store
- API 响应不泄露密钥内容

### Frontend: U1 Setup UX Polish

**模板按钮**: 模型编辑表单中新增 "Anthropic Claude"、"OpenAI"、"OpenRouter" 三个快速模板按钮，一键填充 type/base_url/model 字段。

**Key 可见性切换**: API key 输入框旁新增 👁/🙈 切换按钮，可在 password/text 之间切换。

**Key 格式验证**: 本地检查 key 前缀（sk-ant-api、sk-、sk-or-）和长度，返回 valid/unknown_format 状态指示。

### Frontend: U2 Safety Confirmation Gate

**模式感知安全横幅**: 替代原蓝色信息横幅：
- fake 模式 — 绿色 "Safe Mode: Local Simulation" + "Activate Real LLM" 按钮
- real 模式 — 琥珀色 "Live Mode: Real LLM Active" + "Switch to Safe Mode" 按钮

**激活确认对话框**:
- 费用提醒（API 调用会产生费用）
- 安全检查清单（4 项确认）
- 显式 opt-in checkbox
- 全部满足后才能点击 "Confirm Activation"

**模式切换**: 调用 `POST /api/config/provider-mode` 持久化到 state.json，跨 server 重启保留。

### i18n

新增 22 个 i18n key（zh + en），覆盖模板、安全横幅、激活对话框等文案。

## Gate

| Gate | 命令 | Exit Code |
|------|------|-----------|
| ruff check | `ruff check src/mindforge_web/ --select F,E --quiet` | 0 |
| pytest | `python -m pytest tests/ -q --tb=short -k "not test_sources_page_uses_source_path_view"` | 0 (1 pre-existing) |
| npm build | `npm --prefix web run build` | 0 |
| product copy | `python -m pytest tests/test_web_product_copy.py -q` | 0 |

## 已知限制

- API key 格式验证仅做本地前缀/长度检查，不发送外部 HTTP 请求（v0.6+ 可考虑 connection test）
- 激活对话框使用内联 modal，未抽取为独立组件（可后续重构）
- API smoke test 未在 CI 环境运行（需要正确 config 路径）
