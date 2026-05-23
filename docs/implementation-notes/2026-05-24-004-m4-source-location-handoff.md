# M4 Source Location — Handoff Notes

**Date:** 2026-05-24
**Phase:** M4 (Source Location / Provenance, SDD §8.1)
**Status:** 管线已接通（location 计算 + writer 传参），模板渲染为下一步

---

## 当前做到了哪一步

M4 source location pipeline 的 **计算 → 传递** 已接通：

1. `location_parser.py` — 完成：`parse_source_location()` + `source_location_to_dict()`，支持 `ProvenanceBlock` 和 `dict` 两种输入，按 `source_type` 分派转换。
2. `process_executor.py` — `_compute_location_for_card()` 已接入 `process_one_result()` 主流程。
3. `writer.py` — `CardWriter.write()` 新增 `location` 参数，传入 `template.render()`。
4. `provenance/__init__.py` — 导出 `parse_source_location` 和 `source_location_to_dict`。

**未完成：** 模板 (`knowledge_card.md.j2`) 尚未使用 `location` 变量渲染 source location 信息。Jinja2 不会因为传入未使用变量报错，所以当前状态是安全的。

---

## 已修改文件

| File | Change |
|------|--------|
| `src/mindforge/provenance/location_parser.py` | **新增** — 核心解析逻辑 |
| `src/mindforge/provenance/__init__.py` | 导出新函数 |
| `src/mindforge/process_executor.py` | 新增 `_compute_location_for_card()`，接入 `process_one_result()` |
| `src/mindforge/writer.py` | `write()` 新增 `location` 参数，传入 `template.render()` |

---

## U1–U5 完成状态

| Unit | Description | Status |
|------|-------------|--------|
| U1 | `SourceLocation` dataclass (`location.py`) | ✅ done (prior) |
| U2 | `location_parser.py` — 核心解析逻辑 | ✅ done |
| U3 | `process_executor.py` wiring | ✅ done |
| U4 | `writer.py` — `location` param pass-through | ✅ done |
| U5 | Template rendering (`knowledge_card.md.j2`) | ❌ not started |

---

## 最小 gate 结果

- `python -c "import mindforge.provenance.location_parser"` — ✅ pass
- `git diff --check` — ✅ clean
- `pytest -k "location or provenance or writer or process_executor"` — ✅ 全部通过
- `pytest tests/` (全量) — ⚠️ 1 pre-existing 失败（`test_sources_page_uses_source_path_view_not_raw_path_for_display_or_copy`），与 M4 无关
- Smoke test (parse_source_location with dict, ProvenanceBlock, None input) — ✅ pass

---

## 下一会话从哪里继续

### 优先级 1: Template 渲染 (U5)

两个模板文件需要更新，添加 source location 区块：
- `templates/knowledge_card.md.j2`
- `src/mindforge/assets/templates/knowledge_card.md.j2`

模板中应使用 `{% if location %}` 条件块，调用 `location.display`、`location.source_type`、`location.heading_path` 等字段。参考 SDD §8.1 的 display format。

### 优先级 2: 遍历测试

- 在 `tests/` 中添加 `location_parser` 的单元测试，覆盖每种 source_type
- 添加 writer + location 传入的集成测试
- 运行一个 fake dogfood 验证卡片中包含 source location 区块

### 继续方式

```
新会话运行: /mf-autopilot
```

不要回旧 Milestone。

---

## 当前 git 状态

```
M src/mindforge/process_executor.py
M src/mindforge/provenance/__init__.py
M src/mindforge/writer.py
?? src/mindforge/provenance/location_parser.py
```
