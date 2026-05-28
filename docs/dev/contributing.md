# Contributing

MindForge 贡献指南。

---

## 开发环境

```bash
git clone https://github.com/yaoziyaoguai/mindforge.git
cd mindforge
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## 代码标准

- **Python 3.11+**，类型注解全部函数签名
- **ruff** 格式化 + linting
- **PEP 8** 命名规范
- 不可变数据优先（`dataclass(frozen=True)`、`NamedTuple`）

### Quality Gate

```bash
ruff check src tests
```

---

## 项目约定

### CLI 命令组织

- 根 `cli.py` 只做命令注册
- 每个命令族由独立 `*_cli.py` 模块实现
- CLI 和 Web 共享同一 service 层

### 策略开发

- 策略元数据在策略模块顶层声明
- registry 只汇总，不创作元数据
- 新增策略需声明 provider_mode / safety_policy / output_schema_id

### Security

- 不在代码、日志、错误消息中暴露 API key
- 不在业务代码中按 provider_type 分支
- Prompt 全文和 LLM 返回文本不作为 error_message

---

## 测试

### 运行测试

```bash
# 临时 HOME，避免污染真实 workspace
rm -rf /private/tmp/mindforge-test-home
mkdir -p /private/tmp/mindforge-test-home
HOME=/private/tmp/mindforge-test-home python -m pytest -q
```

### TDD 工作流

1. 写测试（RED）
2. 运行确认失败
3. 写最小实现（GREEN）
4. 运行确认通过
5. 重构（IMPROVE）

### 测试分类

| 类型 | 位置 | 说明 |
|------|------|------|
| 单元测试 | `tests/` | 函数、工具、组件 |
| 集成测试 | `tests/` | 跨模块交互 |
| 产品契约测试 | `tests/test_product_surface_alignment.py` | README/文档断言 |
| Smoke 测试 | `tests/test_onboarding_smoke.py` | 用户路径端到端 |

### 产品契约测试

部分测试 assert README.zh-CN.md 中的特定 token。修改文档或重构安全描述时需同步更新这些测试。

---

## PR 流程

> **MindForge 个人项目默认遵循 Fast Lane 流程。**
> 低风险文档、小 UI、copy/polish、单文件前端展示改动可在 main 上完成验证后直接 commit/push。
> 涉及 provider、approval/human_approved、secrets、真实数据、路径安全、workspace/runtime state、架构重构、大范围 Web 改动、多方协作时，才走 PR / 独立审计。

**高风险改动 PR 流程：**

1. 从 `main` 创建 feature 分支
2. 写测试 → 实现 → 重构
3. 运行 `ruff check src tests`
4. 运行完整测试套件
5. 提交（遵循 Conventional Commits）
6. 推送并创建 PR

### Commit 格式

```
<type>: <description>

feat: add source adapter for HTML
fix: handle empty vault on first wiki rebuild
docs: update model setup guide
test: add recall BM25 coverage
refactor: extract secret store to own module
```

---

## 文档

- 用户文档在 `docs/zh-CN/` 和 `docs/en/`
- 开发者文档在 `docs/dev/`
- 设计文档在 `docs/design/`（RFC、SDD、Roadmap）
- 内部规则在 `.github/` 下（如适用）
