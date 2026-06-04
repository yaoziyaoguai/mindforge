# Knowledge Experience 重构实现计划

> **供 agent 工作者使用：** REQUIRED SUB-SKILL: 使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 来逐步实现本计划。步骤使用 checkbox（`- [ ]`）语法用于跟踪。

**目标：** 通过严格执行审批边界、引入类型化知识和语义关系，以及从单一 Markdown 文件迁移到运行时 API presenter，完全重构 Knowledge/Wiki 体验。

**架构：** 废弃 `llm_rebuild_wiki` 以阻止未经授权的 AI 文本生成。增强 `CardSummary` 添加 `knowledge_type` 和 `relations`。实现 `TopicPresenter` 动态聚合已审批卡片。为前端提供新的 REST API。（前端 UI 实现将是单独的后续计划）。

**技术栈：** Python, FastAPI, Pytest, YAML（用于 frontmatter）。

---

### 任务 1：冻结当前风险（废弃 `llm_rebuild_wiki`）

**文件：**
- 修改：`src/mindforge_web/routers/wiki.py`
- 修改：`tests/test_wiki_related_sections.py`（或类似的 wiki 路由测试以调整预期）

- [ ] **步骤 1：编写路由的失败测试**

```python
# 在 tests/test_wiki_router.py 中创建/修改测试（或类似文件）
def test_wiki_rebuild_llm_is_deprecated(client, mock_facade):
    response = client.post("/api/wiki/rebuild", json={"mode": "llm"})
    assert response.status_code == 410 # 或 400 带特定消息
    data = response.json()
    assert data["ok"] is False
    assert "deprecated" in data["error"].lower()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_wiki_router.py -v`（根据实际测试位置调整文件名）
预期：失败（当前返回 200 OK 或尝试构建）

- [ ] **步骤 3：编写最小实现**

修改 `src/mindforge_web/routers/wiki.py` 中的 `wiki_rebuild`：

```python
@router.post("/rebuild")
def wiki_rebuild(
    payload: WikiRebuildRequest | None = None,
    facade: WebFacade = Depends(get_facade),
):
    """（已废弃）从 v0.5 起，直接 LLM Wiki 重建已禁用以强制执行审批边界。"""
    from fastapi.responses import JSONResponse
    
    return JSONResponse(
        status_code=410,
        content={
            "ok": False,
            "mode": payload.mode if payload else facade.cfg.wiki.mode,
            "error": "Direct LLM Wiki rebuild is deprecated in v0.5 to enforce strict approval boundaries. LLM summaries must now be generated as AI drafts and explicitly approved."
        }
    )
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_wiki_router.py -v`
预期：通过

- [ ] **步骤 5：提交**

```bash
git add src/mindforge_web/routers/wiki.py tests/
git commit -m "feat(wiki): deprecate llm_rebuild_wiki API endpoint"
```

---

### 任务 2：实现 Knowledge Model v2 核心

**文件：**
- 修改：`src/mindforge/cards.py`
- 创建/修改：`tests/test_knowledge_model_v2.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/test_knowledge_model_v2.py
import pytest
from pathlib import Path
from mindforge.cards import _load_summary

def test_load_summary_parses_knowledge_model_v2(tmp_path):
    card_path = tmp_path / "test_card.md"
    card_path.write_text(
        "---\n"
        "id: card_123\n"
        "status: human_approved\n"
        "knowledge_type: claim\n"
        "relations:\n"
        "  - type: supports\n"
        "    target_id: card_456\n"
        "human_note: This is a test note.\n"
        "---\n"
        "Body text\n",
        encoding="utf-8"
    )
    
    summary = _load_summary(card_path, tmp_path)
    
    assert summary.knowledge_type == "claim"
    assert summary.human_note == "This is a test note."
    assert len(summary.relations) == 1
    assert summary.relations[0]["type"] == "supports"
    assert summary.relations[0]["target_id"] == "card_456"

def test_load_summary_knowledge_model_fallbacks(tmp_path):
    card_path = tmp_path / "test_card_legacy.md"
    card_path.write_text(
        "---\n"
        "id: card_legacy\n"
        "status: human_approved\n"
        "---\n"
        "Body text\n",
        encoding="utf-8"
    )
    
    summary = _load_summary(card_path, tmp_path)
    
    assert summary.knowledge_type == "concept" # 默认 fallback
    assert summary.human_note is None
    assert summary.relations == ()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_knowledge_model_v2.py -v`
预期：失败（`CardSummary` 缺少新属性）

- [ ] **步骤 3：编写最小实现**

修改 `src/mindforge/cards.py`：
1. 在 `CardSummary` dataclass 中添加：
```python
    # M5.x Knowledge Model v2
    knowledge_type: str = "concept"
    relations: tuple[dict[str, str], ...] = ()
    human_note: str | None = None
```
2. 添加辅助函数 `_parse_relations`：
```python
def _parse_relations(v: Any) -> tuple[dict[str, str], ...]:
    if not isinstance(v, list):
        return ()
    parsed = []
    for item in v:
        if isinstance(item, dict):
            rel_type = str(item.get("type", ""))
            target_id = str(item.get("target_id", ""))
            if rel_type and target_id:
                parsed.append({"type": rel_type, "target_id": target_id})
    return tuple(parsed)
```
3. 更新 `_load_summary` 返回实例化：
```python
        # ... 已有参数 ...
        knowledge_type=_str_or_none(data.get("knowledge_type")) or "concept",
        human_note=_str_or_none(data.get("human_note")),
        relations=_parse_relations(data.get("relations")),
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_knowledge_model_v2.py -v`
预期：通过

- [ ] **步骤 5：提交**

```bash
git add src/mindforge/cards.py tests/test_knowledge_model_v2.py
git commit -m "feat(cards): implement knowledge model v2 schema and fallbacks"
```

---

### 任务 3：实现 Topic Presenter（审批边界强制执行）

**文件：**
- 创建：`src/mindforge/topic_presenter.py`
- 创建：`tests/test_topic_presenter.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/test_topic_presenter.py
from datetime import datetime
from pathlib import Path
from mindforge.cards import CardSummary
from mindforge.topic_presenter import build_topic_view

def test_topic_presenter_enforces_approval_boundary():
    approved_card = CardSummary(
        id="c1", title="Approved", status="human_approved", path=Path("c1.md"), rel_path="c1.md",
        projects=(), tags=(), source_type=None, track="React", knowledge_type="concept"
    )
    draft_card = CardSummary(
        id="c2", title="Draft", status="ai_draft", path=Path("c2.md"), rel_path="c2.md",
        projects=(), tags=(), source_type=None, track="React", knowledge_type="summary"
    )
    
    view = build_topic_view("React", [approved_card, draft_card])
    
    assert view["topic"] == "React"
    assert len(view["cards"]) == 1
    assert view["cards"][0]["id"] == "c1"
    # draft card 绝不能被包含
    
def test_topic_presenter_groups_by_knowledge_type():
    c1 = CardSummary(id="c1", title="C1", status="human_approved", path=Path("c1.md"), rel_path="c1", projects=(), tags=(), source_type=None, track="React", knowledge_type="concept")
    c2 = CardSummary(id="c2", title="C2", status="human_approved", path=Path("c2.md"), rel_path="c2", projects=(), tags=(), source_type=None, track="React", knowledge_type="claim")
    
    view = build_topic_view("React", [c1, c2])
    
    assert view["type_counts"]["concept"] == 1
    assert view["type_counts"]["claim"] == 1
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_topic_presenter.py -v`
预期：失败（`mindforge.topic_presenter` 未找到）

- [ ] **步骤 3：编写最小实现**

创建 `src/mindforge/topic_presenter.py`：
```python
from typing import Any, Iterable
from .cards import CardSummary

def build_topic_view(topic: str, all_cards: Iterable[CardSummary]) -> dict[str, Any]:
    """
    构建 topic 的安全运行时视图。
    关键：强制执行审批边界。仅包含 human_approved 卡片。
    """
    approved_cards = []
    type_counts: dict[str, int] = {}
    
    for card in all_cards:
        # 严格审批边界
        if card.status != "human_approved":
            continue
            
        if card.track != topic:
            continue
            
        approved_cards.append({
            "id": card.id,
            "title": card.title,
            "knowledge_type": card.knowledge_type,
            "relations": list(card.relations),
            "tags": list(card.tags),
            "summary": "", # 实际实现中可能需要小心地获取 body snippet
            "value_score": card.value_score
        })
        
        k_type = card.knowledge_type or "concept"
        type_counts[k_type] = type_counts.get(k_type, 0) + 1
        
    return {
        "topic": topic,
        "total_approved_cards": len(approved_cards),
        "type_counts": type_counts,
        "cards": approved_cards
    }
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_topic_presenter.py -v`
预期：通过

- [ ] **步骤 5：提交**

```bash
git add src/mindforge/topic_presenter.py tests/test_topic_presenter.py
git commit -m "feat(presenter): implement strict TopicPresenter with approval boundaries"
```

---

### 任务 4：暴露 Topic API

**文件：**
- 创建：`src/mindforge_web/routers/topics.py`
- 修改：`src/mindforge_web/app.py`（引入新路由，先检查结构）
- 创建：`tests/test_api_topics.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/test_api_topics.py
def test_get_topic_view(client, mock_facade):
    # 如果需要，设置 mock_facade.cfg 指向虚拟数据，或 mock iter_cards
    # 目前只测试端点存在性和基本结构
    response = client.get("/api/topics/TestTopic")
    assert response.status_code == 200
    data = response.json()
    assert "topic" in data
    assert data["topic"] == "TestTopic"
    assert "cards" in data
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_api_topics.py -v`
预期：失败（404 Not Found）

- [ ] **步骤 3：编写最小实现**

创建 `src/mindforge_web/routers/topics.py`：
```python
from fastapi import APIRouter, Depends
from mindforge_web.deps import get_facade
from mindforge_web.services.web_facade import WebFacade
from mindforge.cards import iter_cards
from mindforge.topic_presenter import build_topic_view

router = APIRouter(prefix="/api/topics", tags=["topics"])

@router.get("/{topic_name}")
def get_topic(topic_name: str, facade: WebFacade = Depends(get_facade)):
    scan = iter_cards(facade.cfg.vault.root, facade.cfg.vault.cards_dir)
    view = build_topic_view(topic_name, scan.cards)
    return view
```

*（注意：验证路由在哪里引入，可能在 `src/mindforge_web/app.py` 或 `src/mindforge_web/main.py`。在那里引入路由。）*
```python
# 例如在 app.py 中：
# from .routers import topics
# app.include_router(topics.router)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_api_topics.py -v`
预期：通过

- [ ] **步骤 5：提交**

```bash
git add src/mindforge_web/routers/topics.py tests/test_api_topics.py
# git add src/mindforge_web/app.py（如果修改了）
git commit -m "feat(api): expose /api/topics endpoint driven by TopicPresenter"
```
