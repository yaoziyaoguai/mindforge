# v0.5 U6 Safety Hardening Audit 实现笔记

## 日期
2026-05-24

## 目标
审计 MindForge 安全边界，验证以下 5 个维度无 P0/P1 安全问题：

1. `_is_real_environment()` — 环境判定正确性
2. Secret store 访问路径 — 最小必要原则
3. API 响应 key 脱敏 — 零泄露
4. Provider switching 边界 — 模式切换不泄露 key
5. `model_setup_readiness()` — fake 模式不要求 key

## 审计结果

### 维度 1: `_is_real_environment()` 

**文件**: `src/mindforge_web/services/web_facade.py:671-679`

**逻辑**: 
- 检查 vault root 路径是否包含 "demo-vault"、"dogfood-vault"、"tmp"
- `root.exists()` 检查路径存在性

**判定**: **PASS** — demo/dogfood vault 正确排除。字符串匹配 + `root.parts` tuple 检查。

**P2 发现**: `"tmp" not in root.parts` 使用 tuple 精确匹配路径组件，可能导致真实 vault 路径中包含名为 `tmp` 的目录时被误判为非真实环境。但此行为 err on the side of safety（宁可误判为 fake 也不误判为 real），实际风险低。

### 维度 2: Secret Store 访问路径

**文件**: `src/mindforge/secret_store.py`, `src/mindforge_web/services/web_config_secret_manager.py`, `src/mindforge/model_setup_readiness.py`

**调用链分析**:

| 调用方 | 方法 | 是否读取 raw key |
|--------|------|-----------------|
| WebConfigSecretManager | `present()` | 否（存在性检查） |
| WebConfigSecretManager | `masked()` | 否（脱敏返回） |
| model_setup_readiness | `present()` | 否（存在性检查） |
| LLM provider 层 | `get()` | 是（唯一合法 raw key 消费方） |

**判定**: **PASS** — Web 层和 readiness 层不调用 `SecretStore.get()`，只使用 `present()`（存在性检查）和 `masked()`（脱敏展示）。Raw key 只在 LLM provider 层调用 `get()` 获取，用于注入 provider runtime，符合最小必要原则。

### 维度 3: API 响应 Key 脱敏

**文件**: `src/mindforge_web/schemas.py`, `src/mindforge_web/services/web_config_service.py`

**API 响应字段审计**:

| Schema | 字段 | 是否包含 raw key |
|--------|------|-----------------|
| ProviderAliasStatus | `api_key_present: bool` | 否（布尔值） |
| ProviderStatus | `provider_mode` | 否（元数据） |
| ConfigStatusResponse | — | 否（无 key 字段） |
| Setup editable model | `api_key_masked_value: str\|None` | 否（masked 格式） |
| Setup editable model | `api_key_source: str` | 否（来源元数据） |
| Setup editable model | `api_key_status: str` | 否（状态标签） |

**脱敏格式**: `sk-****abcd`（前缀保留 + 后 4 位）

**判定**: **PASS** — 所有 API 端点均不返回 raw key。`/api/config/status`、`/api/config/editable`、`/api/config/provider-mode` 等端点只返回 mask 后的值或 presence 布尔值。

### 维度 4: Provider Switching 边界

**文件**: `src/mindforge/checkpoint.py`, `src/mindforge_web/routers/config.py`, `src/mindforge_web/services/web_config_service.py`

**数据流**:
1. `POST /api/config/provider-mode { mode: "real" }` → `set_provider_mode()` → `write_provider_mode()` → `Checkpoint.save(provider_mode="real")`
2. provider_mode 写入 `state.json`（checkpoint 文件）
3. API key 写入 `secrets.json`（secret store，独立文件）
4. 模式切换不涉及 secrets 文件读写

**物理分离验证**:
- `state.json`: checkpoint 元数据（provider_mode、last_scan 等）
- `.mindforge/secrets.json`: API key 存储
- `.gitignore`: `.mindforge/` 规则覆盖 secrets.json

**判定**: **PASS** — provider_mode 和 API key 物理分离存储，模式切换不读取、不复制、不传输 secrets。

### 维度 5: model_setup_readiness()

**文件**: `src/mindforge/model_setup_readiness.py:53`

```python
if model.type != "fake" and not model.api_key_optional and not store.present(model_id):
    missing.append(model_id)
```

**逻辑**:
- `model.type != "fake"` — fake 模型直接跳过，不检查 key
- `not model.api_key_optional` — 标记为 optional 的模型跳过
- `not store.present(model_id)` — 只检查 key 存在性，不读取值

**判定**: **PASS** — fake 模型和 `api_key_optional` 模型正确豁免 key 要求。使用 `present()` 而非 `get()` 检查。

## 审计总结

| 维度 | 结果 | 问题级别 |
|------|------|---------|
| 1. `_is_real_environment()` | PASS | P2: "tmp" in root.parts 可能过于宽泛（err on safe side） |
| 2. Secret store 访问路径 | PASS | — |
| 3. API 响应 key 脱敏 | PASS | — |
| 4. Provider switching 边界 | PASS | — |
| 5. model_setup_readiness() | PASS | — |

**结论**: 无 P0/P1 安全问题。无需代码修改。

## Gate

| Gate | 命令 | Exit Code |
|------|------|-----------|
| ruff check | `ruff check src/mindforge_web/ --select F,E --quiet` | 1 (pre-existing E501 line-too-long across 20+ files; U6 audit-only, no code changes) |
| pytest | `python -m pytest tests/ -q --tb=short -k "not test_sources_page_uses_source_path_view"` | 0 (1 pre-existing excluded) |
| npm build | `npm --prefix web run build` | 0 |
| product copy | `python -m pytest tests/test_web_product_copy.py -q` | 0 |
| git diff --check | `git diff --check` | 0 |

## 已知限制

- Secret store 未加密（v0.6+ 的安全增强，非 v0.5 scope）
- `_is_real_environment()` 使用启发式判断，非强制安全边界
- API key connection test 仅做本地格式/存在性验证，不发送外部请求（v0.6+ 可添加）
