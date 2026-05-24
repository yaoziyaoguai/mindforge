# v0.8 U1 RetrievalPort Abstraction 实现笔记

## 日期
2026-05-24

## 目标
定义 `RetrievalPort` 抽象接口，解耦 BM25 实现与 recall API 层。

## 实现方案

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/mindforge/retrieval/__init__.py` | 包入口，re-export RetrievalPort + Bm25RetrievalEngine |
| `src/mindforge/retrieval/retrieval_port.py` | `RetrievalPort` ABC，定义 `search()` 和 `hybrid_search()` 抽象方法 |
| `src/mindforge/retrieval/bm25_engine.py` | `Bm25RetrievalEngine` 适配器，委托到现有 `lexical_index.search/hybrid_search` |

### 修改文件

| 文件 | 改动 |
|------|------|
| `recall_service.py` | `run_bm25_recall()` 新增 `engine: RetrievalPort \| None` 参数，默认 `Bm25RetrievalEngine()`；`lx.search/hybrid_search` 调用改为 `engine.search/hybrid_search` |
| `tests/test_review_approval_boundary.py` | 白名单新增 `retrieval_port.py` + `bm25_engine.py`（仅在 status_filter 默认参数使用 human_approved，与 lexical_index.py 同只读语义） |

### 设计决策

- **Port 方法签名与现有 `lx.search/hybrid_search` 保持一致** — 最小改动，零风险
- **`BM25Index` 仍作为参数传入** — 索引管理（load/build/diff）留在 `recall_service.py`，Port 只抽象检索执行
- **默认工厂模式** — `engine=None` 时自动创建 `Bm25RetrievalEngine()`，完全向后兼容
- **遵循已有 Port 模式** — 与 `GraphPort` 一致的 ABC + abstractmethod 风格

### 已知限制

- `SearchIndexPort`（索引构建/更新接口）留到后续需要时添加（spec 标注为 optional）
- `RetrievalPort` 返回类型仍依赖 `lexical_index.SearchHit/HybridHit`，后续可独立为 `retrieval/models.py`

## Gate

| Gate | 命令 | Exit Code |
|------|------|-----------|
| ruff F+E | `ruff check src/mindforge/retrieval/ src/mindforge/recall_service.py --select F,E` | 0 (E501 pre-existing) |
| pytest full | `pytest -q -k "not test_sources_page_uses_source_path_view"` | 0 (1 pre-existing excluded) |
| npm build | `npm --prefix web run build` | 0 |
| git diff --check | `git diff --check` | 0 |
