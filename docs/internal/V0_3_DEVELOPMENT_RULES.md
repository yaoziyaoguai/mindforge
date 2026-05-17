# MindForge v0.3 Development Rules

> **Status**: Draft
> **Date**: 2026-05-17
>
> 本文档定义 v0.3 所有 milestone（M1-M6）的统一开发规则。每个 implementer / coding agent 必须在开始工作前阅读本文档。

---

## How to start M1

1. Read this document fully.
2. Read `docs/design/rfc/RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md` — especially §7 (Functional Requirements) and §6 (Architecture Decisions).
3. Read `docs/design/sdd/SDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md` — especially §3.1 (CardQuality data model), §5 (Quality Rubric), §11 (Implementation Order).
4. **First action**: Write golden fixture and red tests for CardQuality rubric.
   - `tests/fixtures/quality_golden.py` — high/medium/low quality card fixtures
   - `tests/quality/test_rubric.py` — rubric scoring tests
   - `tests/quality/test_card_type.py` — card type classification tests
   - `tests/quality/test_warnings.py` — quality warnings tests
5. **DO NOT** modify existing card schema or approval logic until tests are written.
6. **DO NOT** implement M2-M6 in M1.
7. Every commit references an RFC/SDD section number.

**Step 1 prompt template:**

```
Implement M1 Phase P1: Quality rubric scoring and card type classification.
Scope: src/mindforge/quality/ only. Reference RFC_0003 §7 FR1, SDD §3.1, §5.
```

---

## 1. 开发前置规则

1. **每个 milestone 先写 golden fixture + red test**。
   - 在写任何实现代码前，先为确定性行为写 golden fixture。
   - Golden fixture 必须覆盖：正常输入、边界输入、预期输出。
   - 确保 test FAIL 后再开始实现。

2. **所有 quality scoring 必须可测试确定**。
   - 同一输入在任何时间、任何环境产生相同 score。
   - 不依赖 LLM 调用。
   - 不依赖 embedding / vector similarity。
   - 金标准测试：已知好卡片 score ≥ 70，已知差卡片 score < 40。

3. **所有 relation 计算必须可测试确定**。
   - 同一卡片集合在任何时间产生相同的 related cards。
   - 不依赖 semantic similarity。
   - Golden fixture 验证关系数量和 reason 正确性。

4. **每次 coding prompt 必须引用对应 RFC/SDD section**。
   - Implementer 必须知道自己在实现哪个 section。
   - Commit message 必须包含 RFC/SDD section 引用。

---

## 2. v0.3 硬边界规则

5. **不新增 ingestion format**。
   - M1-M6 不增加新的 source adapter。
   - 不修改 source ingestion pipeline。

6. **不引入新依赖**。
   - 不安装 Vector DB（Chroma, Pinecone, Weaviate, Qdrant, Milvus, LanceDB）。
   - 不安装 Graph DB（Neo4j, NetworkX 作为 graph DB 使用）。
   - 不安装 embedding 库（sentence-transformers, openai embeddings, text-embeddings-inference）。
   - 不安装新的外部 API SDK。
   - 仅使用 Python 标准库 + v0.2 已有依赖。

7. **Quality metadata 是只读附属**。
   - 不自动修改卡片 body/status 基于 quality score。
   - 不自动 approve 基于 quality score。
   - 不自动 reject 基于 quality score。
   - Quality 信息附属于 ai_draft / human_approved，用户始终保留最终决定权。

8. **不自动 mutation**。
   - 不自动 rebuild Wiki。
   - 不自动删除卡片。
   - 不自动修改 human_approved 内容。
   - M5 Health report 的 suggested_action 是建议，不是自动执行。

9. **Provenance 增强向后兼容 v0.2**。
   - provenance_blocks v1 的字段不改变。
   - v2 新增 `location` 字段为可选。
   - 无 location 的旧卡片正常工作。
   - copy/reveal 安全 allowlist 不变。

10. **Local graph 只用确定性关系**。
    - 所有 edges 基于已有确定性数据（JOIN on fields），不做 semantic similarity。
    - 不做 force-directed 毛线球（全局大图）。
    - 仅 1-hop neighbors。

---

## 3. Scope 边界规则

11. **不允许 coding agent 自创 scope**。
    - 所有实现必须限定在 RFC/SDD 定义的范围内。
    - 超出 scope 的实现必须通过 RFC 更新来纳入。

12. **不允许绕过 ai_draft / approval / human_approved**。
    - ai_draft 只能由 processing pipeline 生成。
    - human_approved 只能由用户显式确认。
    - 不新增自动审批路径。

13. **不允许读取 secrets**。
    - 不读取 `.env`。
    - 不读取 `.mindforge/secrets.json`。
    - 不输出任何 API key / token / secret。

14. **不允许处理真实私人资料**。
    - 测试只能用 synthetic fixtures。
    - 不能用真实 Obsidian vault 路径。
    - Golden fixture 中不包含真实用户数据。

---

## 4. Architecture 边界规则

15. **Quality 模块独立**。
    - `src/mindforge/quality/` 不依赖 wiki / relations / health 模块。
    - 其他模块可以依赖 quality。

16. **Relations 模块独立**。
    - `src/mindforge/relations/` 不依赖 wiki / health 模块。
    - 关系计算在内存中完成，不使用外部存储。

17. **Health 模块聚合**。
    - `src/mindforge/health/` 可以聚合 quality + relations + wiki 的信号。
    - Health report 是纯计算，不持久化状态（除非用户明确要求 snapshot）。

18. **每模块独立测试**。
    - 每个 `src/mindforge/<module>/` 有对应的 `tests/<module>/` 目录。
    - 跨模块 golden fixture 放在 `tests/fixtures/`。

---

## 5. 测试规则

19. **TDD 强制**。
    - 先写 golden fixture → red test → 实现 → green。
    - 禁止跳过 test 直接写实现。

20. **Golden fixture 覆盖所有 edge cases**。
    - 正常输入、空输入、边界情况、恶意输入（如适用）。
    - 不得使用真实用户数据。

21. **80% 测试覆盖率**。
    - 每个模块 ≥ 80% line coverage。
    - Integration tests 覆盖所有 API endpoints。

22. **不调 LLM 测试**。
    - 所有测试不调用真实 LLM API。
    - Quality rubric 基于确定性规则，测试不依赖外部服务。

---

## 6. Commit 规则

23. **每个 commit 引用 RFC/SDD section**。
    - 格式：`feat(v0.3/mX): description (RFC_0003 §Y)`
    - 例：`feat(v0.3/m1): implement quality rubric scoring (RFC_0003 §7 FR1.1, SDD §5.1)`

24. **每个 milestone 至少一个 commit**。
    - 不要跨 milestone 合并 commit。

25. **每个 milestone commit 前必须**：
    - `ruff check src/mindforge/<module>/` clean
    - `pytest tests/<module>/ -v` green
    - `pytest tests/ --cov=src/mindforge/<module> --cov-report=term-missing` ≥ 80%
    - 不破坏 v0.2 已有测试

---

## 7. Web UI 规则

26. **Quality display 清晰但不过度**。
    - Quality score 在 card detail 中显示为 badge（high/medium/low）。
    - 不要在主阅读区放完整的 rubric breakdown。
    - Rubric 细节放在可展开的 "Quality details" 区域。

27. **Related cards panel 简洁**。
    - 先显示关系类型分组，后显示卡片链接。
    - Reason badge 简洁（"Same source", "Same tag", "Same wiki section"）。
    - 不显示强度数值（strength 是内部排序用，不暴露给用户）。

28. **Local graph 先用 list view**。
    - v0.3 不实现 canvas/force-directed graph。
    - List view + indentation 表示层级关系。
    - 节点可点击跳转。

29. **Health page 易读**。
    - 按 severity 分组（critical → warn → info）。
    - 每个 issue 显示 affected items count 和 suggested action。
    - 不自动执行任何 action。

---

## 8. Milestone-by-Milestone Start Templates

### M1: Card Quality

```
Implement M1: Card Quality metadata.
Read RFC_0003 §6 AD-1, AD-2; §7 FR1.
Read SDD §3.1, §5.
First: write tests/fixtures/quality_golden.py + tests/quality/test_rubric.py.
DO NOT modify existing card schema. Quality metadata is read-only.
```

### M4: Source Location

```
Implement M4: Source Location / Provenance.
Read RFC_0003 §6 AD-5; §7 FR4.
Read SDD §3.4, §8.
First: write tests/fixtures/location_golden.py + tests/provenance/test_location.py.
DO NOT break v0.2 provenance_blocks. New location field is optional.
```

### M2: Wiki Quality

```
Implement M2: Wiki Quality Report.
Read RFC_0003 §7 FR2.
Read SDD §3.2, §6.
First: write tests/fixtures/wiki_quality_fixture.py + tests/wiki/test_wiki_quality.py.
DO NOT auto-rebuild Wiki.
```

### M3: Related Cards

```
Implement M3: Related Cards.
Read RFC_0003 §6 AD-4; §7 FR3.
Read SDD §3.3, §7.
First: write tests/fixtures/relations_golden.py + tests/relations/test_related_cards.py.
DO NOT use semantic similarity. Only deterministic field-based relations.
```

### M5: Knowledge Health

```
Implement M5: Knowledge Health.
Read RFC_0003 §7 FR5.
Read SDD §3.5, §9.
First: write tests/fixtures/health_golden.py + tests/health/test_health_service.py.
DO NOT auto-mutate cards. All actions are suggestions only.
```

### M6: Local Graph Preview

```
Implement M6: Local Graph Preview.
Read RFC_0003 §6 AD-3; §7 FR6.
Read SDD §3.6, §10.
First: write tests/fixtures/graph_golden.py + tests/relations/test_graph.py.
DO NOT add canvas library. List view + mini graph only.
USE in-memory graph construction only. No graph DB.
```

---

## 9. Stop Conditions per Milestone

| Milestone | Stop if... |
|-----------|-----------|
| M1 | Quality score 在 golden test 上相关性 < 80%；Web display 造成混淆 |
| M4 | 任何 source_type 的 location 计算不确定性；location 泄露不安全路径 |
| M2 | Faithfulness check 假阳性 > 30%；Wiki rebuild 速度退化 > 2x |
| M3 | Related cards 计算 > 500ms for 1000 cards；假阳性关系 > 10% |
| M5 | Health report 假阳性 > 20%；suggested action 可能引导危险操作 |
| M6 | Graph UI > M6 预算 50%；graph 计算 > 1s for 100 nodes |

---

## 10. References

- [V0.3 Roadmap](../design/roadmap/V0_3_KNOWLEDGE_QUALITY_AND_NAVIGATION_ROADMAP.md)
- [RFC 0003](../design/rfc/RFC_0003_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)
- [SDD Knowledge Quality](../design/sdd/SDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)
- [TDD Knowledge Quality](../design/tdd/TDD_KNOWLEDGE_QUALITY_AND_NAVIGATION.md)
- [V0.2 Development Rules](V0_2_DEVELOPMENT_RULES.md)
