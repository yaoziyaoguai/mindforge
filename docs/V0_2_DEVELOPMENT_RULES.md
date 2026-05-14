# MindForge v0.2 Development Rules

> **Status**: Draft
> **Date**: 2026-05-14
>
> 本文档定义 v0.2 所有 milestone 的统一开发规则。每个 implementer / coding agent
> 必须在开始工作前阅读本文档和对应 RFC/SDD。

---

## 1. 开发前置规则

1. **每个 milestone 先写 characterization tests**。
   - 在修改任何现有代码前，先为当前行为写 characterization test。
   - 确保新实现不破坏已测试行为。

2. **每个 adapter 先写 synthetic fixture tests**。
   - TXT / HTML / PDF / DOCX adapter 必须提供 synthetic test fixtures。
   - Fixture 必须包含：正常输入、空输入、边界情况、恶意输入（如适用）。
   - 不得使用真实用户数据作为 text fixture。

3. **每个功能必须有 acceptance tests**。
   - Acceptance test 对应 RFC 中的 Acceptance Criteria。
   - 每个 acceptance criterion 至少一个 test case。

4. **每次 coding prompt 必须引用对应 RFC/SDD section**。
   - Implementer 必须知道自己在实现 RFC/SDD 的哪个 section。
   - Commit message 应提及相关的 RFC 编号。

---

## 2. Scope 边界规则

5. **不允许 coding agent 自创 scope**。
   - 所有实现必须限定在 RFC/SDD 定义的范围内。
   - 超出 scope 的实现必须通过 RFC 更新来纳入。

6. **不允许绕过 ai_draft / approval / human_approved**。
   - `ai_draft` 只能由 processing pipeline 生成。
   - `human_approved` 只能由用户显式确认。
   - 不新增自动审批路径。

7. **不允许读取 secrets**。
   - 不读取 `.env`。
   - 不读取 `.mindforge/secrets.json`。
   - 不输出任何 API key / token / secret。

8. **不允许处理真实私人资料**。
   - 测试只能用 synthetic fixtures。
   - 不能用真实 Obsidian vault 路径。
   - 不能用真实 Cubox / 其他账户数据。

---

## 3. Architecture 边界规则

9. **不允许新增大依赖而不写 ADR/RFC**。
   - 任何新的第三方依赖必须先在对应 RFC 中记录并评估。
   - 评估维度：license、platform support、maintenance status、security history。

10. **不允许把 PDF/HTML/DOCX/TXT 解析逻辑塞进 processor**。
    - Processor 只能消费 `SourceDocument`。
    - Processor 不能 `import pdf` / `import docx` / `import bs4` 等格式相关库。
    - 所有格式特异性限定在 SourceAdapter 内部。

11. **不允许 unsafe Markdown/HTML rendering**。
    - 不直接 `innerHTML` 未净化内容。
    - 必须 sanitize：strip `<script>`、`<iframe>`、`onclick`、`onerror` 等。
    - 默认禁用 unsafe embedded HTML。

---

## 4. Review Packet 规则

12. **Review packet 必须包含**：
    - **Changed files**：修改/新增文件列表
    - **Tests run**：运行的测试命令和结果
    - **Evidence**：test output / characterization diff / screenshot（如适用）
    - **Risks**：已知风险和未覆盖路径
    - **RFC/SDD section mapping**：每个 changed file 对应哪个 RFC/SDD section
    - **Deferred items**：有意延后的项及其原因

---

## 5. Commit 规则

- Commit message 格式：`<type>(v0.2/<milestone>): <description>`
- 示例：`feat(v0.2/m1): add extraction_warnings to SourceDocument`
- 每次 commit 必须是可独立 review 的工作单元。
- 不 push、不 tag、不 merge main until explicit authorization。

---

## 6. 质量门

每次实现完成后运行：

```bash
git diff --check
python -m ruff check src tests
python -m pytest -q
```

如果误改 src/tests（当前 docs-only 阶段不应有代码变更），必须运行完整测试。

---

## 7. 相关文档

- [V0_2_ROADMAP.md](roadmap/V0_2_ROADMAP.md)
- [RFC_0001_SOURCE_ADAPTER_V2.md](rfc/RFC_0001_SOURCE_ADAPTER_V2.md)
- [RFC_0002_WIKI_PRESENTATION_V2.md](rfc/RFC_0002_WIKI_PRESENTATION_V2.md)
- [SDD_SOURCE_ADAPTER_V2.md](sdd/SDD_SOURCE_ADAPTER_V2.md)
- [SDD_WIKI_PRESENTATION_V2.md](sdd/SDD_WIKI_PRESENTATION_V2.md)
