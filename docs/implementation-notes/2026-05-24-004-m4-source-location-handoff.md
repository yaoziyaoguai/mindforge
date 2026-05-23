# M4 Source Location — Handoff Notes

**Date:** 2026-05-24
**Phase:** M4 (Source Location / Provenance, SDD §8.1)
**Status:** ✅ M4 全部完成（U1-U5）

---

## 当前做到了哪一步

M4 Source Location / Provenance **全部完成** (U1-U5)：

1. `location_parser.py` — 完成：`parse_source_location()` + `source_location_to_dict()`，支持 `ProvenanceBlock` 和 `dict` 两种输入，按 `source_type` 分派转换。
2. `process_executor.py` — `_compute_location_for_card()` 已接入 `process_one_result()` 主流程。
3. `writer.py` — `CardWriter.write()` 新增 `location` 参数，传入 `template.render()`。
4. `provenance/__init__.py` — 导出 `parse_source_location` 和 `source_location_to_dict`。
5. `knowledge_card.md.j2` — 新增 `{% if location %}` 条件块，渲染 `source_location:` YAML frontmatter（source_type、display、heading_path、line_start/end、page_number、paragraph_start/end、css_selector）。

M4 完成 commit: `d223cd2`。

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
| U5 | Template rendering (`knowledge_card.md.j2`) | ✅ done (commit d223cd2) |

---

## 最小 gate 结果

- `python -c "import mindforge.provenance.location_parser"` — ✅ pass
- `git diff --check` — ✅ clean
- `pytest -k "location or provenance or writer or process_executor"` — ✅ 全部通过
- `pytest tests/` (全量) — ⚠️ 1 pre-existing 失败（`test_sources_page_uses_source_path_view_not_raw_path_for_display_or_copy`），与 M4 无关
- Smoke test (parse_source_location with dict, ProvenanceBlock, None input) — ✅ pass

---

## 下一阶段

M4 已全部完成。按 v0.3 roadmap 顺序 M1 → M4 → M2 → M3 → M5 → M6，下一 milestone 为 **M2 Wiki Quality**。

M2 尚未有 spec，新会话 `/mf-autopilot` 将先写 M2 spec 再进行实现。

---

## 当前 git 状态

```
M src/mindforge/process_executor.py
M src/mindforge/provenance/__init__.py
M src/mindforge/writer.py
?? src/mindforge/provenance/location_parser.py
```
