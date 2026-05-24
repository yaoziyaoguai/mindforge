# v1.2 U2 Relation Scoring Enhancement — Implementation Notes

## 变更概要

引入多因子加权评分模块 `scoring.py`，替代 v0.6 的固定 strength 权重，支持共享实体数量加权和时效性加权。

## 实现决策

### 新模块: scoring.py

- `RelationWeights`: 可配置权重 dataclass
- `compute_tag_strength()`: 共享 1 个 tag → 0.5, 2 → 0.6, 3 → 0.7, 4+ → 0.8 (capped at 0.95)
- `compute_wiki_strength()`: 共享 1 个 section → 0.7, 2 → 0.8, ...
- `compute_source_strength()`: 固定 0.8（多 source 共享极少见）
- `compute_recency_bonus()`: 30 天内 0.1, 30-90 天线性衰减, 90+ 天 0
- `compute_multi_factor_strength()`: 综合加权 → clamp [0.05, 0.99]

### related_cards.py 更新

- `same_tag`: 计算目标卡片的共享标签数量，使用 `compute_tag_strength()` 加权
- `same_wiki_section`: 计算目标卡片的共享章节数量，使用 `compute_wiki_strength()` 加权
- `same_source`: 添加 recency bonus（时效性加权）
- 所有边类型支持 `compute_multi_factor_strength()` 综合公式

### 测试

- 新增 `tests/relations/test_scoring.py`: 12 个 scoring 模块单元测试
- 新增 `test_multi_tag_gives_higher_strength`: 验证多标签共享强度更高
- 新增 `test_multi_wiki_section_gives_higher_strength`: 验证多章节共享强度更高

## Gate 结果

| Gate | Exit Code |
|------|-----------|
| `python -m pytest tests/ -q` | 0 (386 passed, 1 skipped) |
| `ruff check src tests` | 0 |
| `git diff --check` | 0 |

## 已知限制

- 时效性加权依赖卡片 `created_at` 字段，fake dogfood 卡片可能没有此字段
- 评分公式的权重未经过大规模数据调优，当前基于经验设定
- source 共享不计多实体（同一 source 的卡片数量不是关系强度信号）
