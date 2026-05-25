"""v3.9 Entity Resolution & Concept Candidate Layer — 确定性候选实体检测。

中文学习型说明：本模块从知识卡片中提取 ConceptCandidate（候选实体），
使用纯确定性规则（exact match / substring / shared context），
不调用 LLM / embedding / vector DB。

ConceptCandidate 属于 candidate graph，不能自动升级为 Entity —
升级需用户显式确认（human_approved pipeline）。

核心规则：
1. Exact match: 相同 normalized label → 同一 candidate
2. Substring containment: "Reinforcement Learning" 包含 "Learning" → weak link
3. Shared tag context: 两张 card 共享 ≥2 tags → candidate 可能有共同 entity
4. Wiki section co-occurrence: 同一 wiki section 下的 card → 共享 topic entity
5. Source proximity: 同一 source 相邻位置的 card → 共享 context entity

Entity ≠ ConceptCandidate:
- Entity: 用户已确认的语义实体，属于 fact graph
- ConceptCandidate: 自动检测的候选，属于 candidate graph
- Tag: 用户手动的标签
- Topic: 合并社区的计算产物
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass


# ── ConceptCandidate ────────────────────────────────


@dataclass(frozen=True)
class ConceptCandidate:
    """候选实体（candidate graph），未经用户确认不得进入 fact graph。

    中文学习型说明：
    - label: 用户可读的候选实体名称（如 "Transformer 架构"）
    - normalized_label: 小写去空格后的规范化形式（如 "transformer架构"），用于匹配
    - aliases: 同义/近义别名列表
    - source_card_ids: 提及此候选的卡片 ID 集合
    - confidence: 确定性置信度分数 (0.0-1.0)，基于共现频率和上下文重叠
    - evidence: 人类可读的证据描述
    - source_type: 候选来源类型（title / tag / wiki_section / body_token）
    """

    label: str
    normalized_label: str
    aliases: tuple[str, ...] = ()
    source_card_ids: tuple[str, ...] = ()
    confidence: float = 0.0
    evidence: str = ""
    source_type: str = "title"

    @property
    def card_count(self) -> int:
        return len(self.source_card_ids)


# ── 规范化与分词工具 ──────────────────────────────────


def _normalize(text: str) -> str:
    """规范化文本：小写、去除多余空白、去除非字母数字/中文的符号。"""
    # 保留中文、英文、数字、空格
    cleaned = re.sub(r"[^\w\s一-鿿]", " ", text.lower())
    # 合并空白
    return re.sub(r"\s+", "", cleaned)


def _tokenize(text: str) -> list[str]:
    """从中英文混合文本中提取有意义的 token。

    中文学习型说明：简单分词策略 —
    - 英文：按空格和标点分割，过滤短于 2 字符的 token
    - 中文：保留连续中文字符（2-6 字）
    - 过滤停用词列表中的 token
    """
    tokens: list[str] = []
    # 英文 token：按非字母数字分割
    english_tokens = re.findall(r"[a-zA-Z]{2,}", text)
    tokens.extend(t.lower() for t in english_tokens)

    # 中文 token：连续中文字符（2-8 字）
    chinese_tokens = re.findall(r"[一-鿿]{2,8}", text)
    tokens.extend(chinese_tokens)

    # 过滤停用词
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "in", "on", "at", "to", "for", "of", "by", "with", "from",
        "and", "or", "not", "but", "if", "then", "else", "when",
        "this", "that", "these", "those", "it", "its", "he", "she",
        "的", "了", "在", "是", "我", "有", "和", "就", "不",
        "人", "都", "一", "一个", "上", "也", "很", "到", "说",
        "要", "去", "你", "会", "着", "没有", "看", "好", "自己",
    }
    return [t for t in tokens if t.lower() not in stopwords]


# ── ConceptCandidate 检测 ──────────────────────────────


def detect_concept_candidates(
    cards: list[dict[str, object]],
    *,
    min_confidence: float = 0.15,
    max_candidates: int = 200,
) -> list[ConceptCandidate]:
    """从卡片列表中检测 ConceptCandidate（确定性规则）。

    Args:
        cards: 卡片字典列表，每张卡片至少包含 id, title, tags, wiki_sections, body_summary
        min_confidence: 最低置信度阈值（低于此值的候选被过滤）
        max_candidates: 返回的最大候选数量

    Returns:
        ConceptCandidate 列表，按置信度降序排列
    """
    # Phase 1: 从每张卡片提取候选 token
    # token → list[(card_id, source_type)]
    token_to_cards: dict[str, list[tuple[str, str]]] = defaultdict(list)
    card_token_sets: dict[str, set[str]] = {}

    for card in cards:
        card_id = str(card.get("id", ""))
        if not card_id:
            continue

        card_tokens: set[str] = set()

        # 从 title 提取
        title = str(card.get("title", ""))
        for token in _tokenize(title):
            token_to_cards[token].append((card_id, "title"))
            card_tokens.add(token)

        # 从 tags 提取
        tags = card.get("tags") or []
        for tag in tags:
            tag_str = str(tag).lower().strip()
            # tag 本身就是候选实体
            if len(tag_str) >= 2:
                normalized = _normalize(tag_str)
                token_to_cards[normalized].append((card_id, "tag"))
                card_tokens.add(normalized)

        # 从 wiki_sections 提取
        sections = card.get("wiki_sections") or []
        for section in sections:
            section_str = str(section).strip()
            if section_str:
                normalized = _normalize(section_str)
                if len(normalized) >= 2:
                    token_to_cards[normalized].append((card_id, "wiki_section"))
                    card_tokens.add(normalized)

        # 从 body_summary 提取 token
        body = str(card.get("body_summary", ""))
        for token in _tokenize(body):
            token_to_cards[token].append((card_id, "body_token"))
            card_tokens.add(token)

        card_token_sets[card_id] = card_tokens

    # Phase 2: 构建 ConceptCandidate — 每个出现 ≥2 张 card 的 token 成为候选
    candidates: list[ConceptCandidate] = []

    for token, card_refs in token_to_cards.items():
        unique_card_ids = list(dict.fromkeys(cid for cid, _ in card_refs))
        if len(unique_card_ids) < 2:
            continue  # 只在一张卡中出现，不是候选

        # 确定主要 source_type
        source_types = [st for _, st in card_refs]
        primary_type = max(set(source_types), key=source_types.count)

        # 计算 confidence
        confidence = _compute_confidence(token, unique_card_ids, card_token_sets)

        if confidence < min_confidence:
            continue

        evidence = _build_evidence(token, unique_card_ids, card_refs)

        candidates.append(ConceptCandidate(
            label=token,
            normalized_label=token,
            source_card_ids=tuple(unique_card_ids),
            confidence=confidence,
            evidence=evidence,
            source_type=primary_type,
        ))

    # Phase 3: Substring grouping — 合并包含关系的候选
    merged = _merge_substring_candidates(candidates)

    # Phase 4: 按置信度降序排列，限制数量
    merged.sort(key=lambda c: c.confidence, reverse=True)
    return merged[:max_candidates]


def _compute_confidence(
    token: str,
    card_ids: list[str],
    card_token_sets: dict[str, set[str]],
) -> float:
    """计算候选实体的确定性置信度分数。

    基于：
    - 提及卡片数量（多卡提及 → 高置信度）
    - 共享标签的卡片比例
    - token 长度（较长的 token 更具体，置信度更高）
    """
    n_cards = len(card_ids)
    # Base: card count factor (0.0-0.5)
    # 2 cards → 0.2, 5 cards → 0.35, 10+ cards → 0.5
    card_factor = min(0.5, 0.1 + 0.05 * min(n_cards, 8))

    # Token specificity (0.0-0.3): longer tokens are more specific
    specificity = min(0.3, len(token) * 0.03)

    # Context overlap (0.0-0.2): shared non-token context between cards
    overlap_score = 0.0
    if n_cards >= 2 and card_token_sets:
        pairs_checked = 0
        total_overlap = 0.0
        ids = list(card_ids)
        for i in range(min(n_cards, 8)):
            for j in range(i + 1, min(n_cards, 8)):
                set_i = card_token_sets.get(ids[i], set())
                set_j = card_token_sets.get(ids[j], set())
                if set_i and set_j:
                    union = len(set_i | set_j)
                    intersection = len(set_i & set_j)
                    if union > 0:
                        total_overlap += intersection / union
                        pairs_checked += 1
        if pairs_checked > 0:
            overlap_score = min(0.2, total_overlap / pairs_checked * 0.4)

    return round(card_factor + specificity + overlap_score, 3)


def _build_evidence(
    token: str,
    card_ids: list[str],
    card_refs: list[tuple[str, str]],
) -> str:
    """构建人类可读的候选实体证据描述。"""
    source_counts: dict[str, int] = defaultdict(int)
    for _, st in card_refs:
        source_counts[st] += 1

    parts = [f"提及实体 '{token}' 的卡片: {len(card_ids)} 张"]
    for st, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        type_names = {
            "title": "标题", "tag": "标签", "wiki_section": "Wiki 章节",
            "body_token": "正文",
        }
        parts.append(f"{type_names.get(st, st)}: {count}")
    return "; ".join(parts)


def _merge_substring_candidates(
    candidates: list[ConceptCandidate],
) -> list[ConceptCandidate]:
    """合并有子串包含关系的候选实体。

    中文学习型说明：如果 candidate A 的 normalized_label 包含 candidate B 的
    normalized_label，且提及卡片高度重叠，则合并为一个更大范围的 candidate。
    这避免了 "reinforcement learning" 和 "learning" 同时作为独立候选的问题。
    """
    if len(candidates) <= 1:
        return candidates

    merged: list[ConceptCandidate] = []
    used = [False] * len(candidates)

    for i, ci in enumerate(candidates):
        if used[i]:
            continue

        ci_cards = set(ci.source_card_ids)
        aliases = list(ci.aliases)
        all_cards = set(ci_cards)
        max_confidence = ci.confidence
        primary_label = ci.label  # 保留最长的 label

        for j, cj in enumerate(candidates):
            if i == j or used[j]:
                continue
            cj_cards = set(cj.source_card_ids)

            # 检查包含关系
            ni = ci.normalized_label
            nj = cj.normalized_label
            is_contained = (ni != nj) and (ni in nj or nj in ni)

            if not is_contained:
                continue

            # 检查卡片重叠率（至少 50%）
            overlap = len(ci_cards & cj_cards)
            min_cards = min(len(ci_cards), len(cj_cards))
            if min_cards == 0 or overlap / min_cards < 0.5:
                continue

            # 合并
            all_cards = all_cards | cj_cards
            max_confidence = max(max_confidence, cj.confidence)
            aliases.append(cj.label)
            if len(nj) > len(primary_label):
                primary_label = cj.label
            used[j] = True

        used[i] = True
        # 子串合并后略微提升置信度
        merged_confidence = min(1.0, max_confidence + 0.05 * len(aliases))

        merged.append(ConceptCandidate(
            label=primary_label,
            normalized_label=_normalize(primary_label),
            aliases=tuple(sorted(set(aliases))),
            source_card_ids=tuple(sorted(all_cards)),
            confidence=round(merged_confidence, 3),
            evidence=f"合并候选: {primary_label}" + (
                f", 别名: {', '.join(aliases)}" if aliases else ""
            ),
            source_type=ci.source_type,
        ))

    # 添加未被合并的候选
    for i, c in enumerate(candidates):
        if not used[i]:
            merged.append(c)

    return merged


__all__ = ["ConceptCandidate", "detect_concept_candidates"]
