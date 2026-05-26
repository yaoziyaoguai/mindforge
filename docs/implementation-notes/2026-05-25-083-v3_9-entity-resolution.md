# v3.9 Entity Resolution & Concept Candidate Layer — Implementation Notes

**日期**: 2026-05-25
**状态**: complete
**基于**: [v3.7-v4.1 Graph View Roadmap](../plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md)

> **Status note (v4.6 docs simplification, 2026-05-26)**: This document is historical implementation evidence. Current product truth: Entity Resolution is lab/internal. Only ConceptCandidate deterministic detection exists; automatic entity promotion/linking is not supported. Not part of the product main path. See docs/README.md and docs/dev/docs-reset-index.md.

---

## 实现范围

### 新增模块：`src/mindforge/relations/entity_resolution.py`

**ConceptCandidate** (`@dataclass(frozen=True)`):
- `label`: 用户可读的候选实体名称
- `normalized_label`: 小写去符号规范化形式（用于匹配）
- `aliases`: 同义/近义别名 tuple
- `source_card_ids`: 提及此 candidate 的卡片 ID tuple
- `confidence`: 确定性置信度 (0.0-1.0)
- `evidence`: 人类可读的证据描述
- `source_type`: 来源类型（title / tag / wiki_section / body_token）
- `card_count`: 属性，返回 `len(source_card_ids)`

**`detect_concept_candidates(cards, min_confidence, max_candidates)`:**
- Phase 1: 从 cards 的 title / tags / wiki_sections / body_summary 提取 token
- Phase 2: token 出现 ≥2 张 card → ConceptCandidate
- Phase 3: 合并子串包含关系的候选（避免 "reinforcement learning" 和 "learning" 重复）
- Confidence 计算：card frequency + token specificity + context overlap
- 结果按置信度降序排列

### 确定性规则

1. **Exact match**: 相同 normalized token → 同一 candidate
2. **Substring containment**: "Reinforcement Learning" 包含 "Learning" → 合并为更大范围的 candidate
3. **Shared tag context**: 同一 tag 被多张 card 使用 → candidate
4. **Wiki section co-occurrence**: 同一 wiki section → 共享 topic entity
5. **Card frequency**: ≥2 cards 提及才成为 candidate

### 非 LLM / 非 Embedding 保证

- 纯 `re` 正则分词（英文 + 中文连续字符）
- 纯集合运算（card overlap, token frequency）
- 无网络调用、无模型加载、无外部 API
- 停用词表内置（中英文常见停用词）

### Entity ≠ ConceptCandidate 边界

- `ConceptCandidate` 没有 `status` / `approved` 字段
- `detect_concept_candidates` 是纯函数，不修改输入 cards
- 高置信度 ≠ 已确认
- 升级只能通过 explicit approval pipeline

---

## 测试

**`tests/relations/test_entity_resolution.py`** — 25 tests, 4 classes:
- `TestNormalizeAndTokenize` (6 tests): 规范化、分词、停用词过滤
- `TestConceptCandidateDataclass` (4 tests): frozen, card_count, aliases, defaults
- `TestDetectConceptCandidates` (10 tests): exact match, tags, wiki sections, body tokens, confidence, filtering, sorting, evidence
- `TestEntityVsConceptCandidateBoundary` (4 tests): 无 approved flag, 纯函数, 高置信度≠已确认, NodeType 区分

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/mindforge/relations/entity_resolution.py` | NEW | ConceptCandidate + detect_concept_candidates |
| `tests/relations/test_entity_resolution.py` | NEW | 25 entity resolution tests |
| `tests/test_review_approval_boundary.py` | MODIFIED | allowlist 新增 entity_resolution.py |

---

## 安全性审计

- [x] 不调用 LLM / embedding / vector DB
- [x] 不读取 .env 或 secrets
- [x] 不处理真实私人资料
- [x] 不写真实 Obsidian vault
- [x] 不破坏 explicit approval / human_approved 语义
- [x] ConceptCandidate 不能自动升级为 Entity
- [x] 纯确定性规则（正则 + 集合运算）

---

## Gate 结果

| Gate | 命令 | Timeout | Exit Code | 备注 |
|------|------|---------|-----------|------|
| ruff check | `ruff check src/ tests/ docs/` | no | 0 | clean |
| pytest full | `python -m pytest tests/ -q --tb=short` | no | 0 | ~3096 tests passed |

---

## 下一步

v4.0 Graph-backed Sensemaking Workspace:
- 主题/社区子图
- Source influence path
- Card evolution path
- Bridge nodes / orphan islands
- Evidence trail
- Candidate vs Fact 切换
