# Knowledge Detail UX Redesign Spec

## Problem

CardWorkspace.tsx (~630 lines) flat-renders all `## Heading` sections without information hierarchy. Users see Source Excerpt, AI Summary, AI Inference, Human Note, and Reusable Prompts as equal-level bordered sections with no distinction between "what this knowledge is" and "internal processing detail."

The "知识图谱" (Knowledge Graph) area shows raw relation types (same_source, same_tag, sha1) that normal users can't understand. Technical fields like source_content_hash, run_id appear throughout.

## Solution: 4-Layer Information Architecture

### Layer 1 — Default Reading (KnowledgeHero)
Visible immediately. User sees:
- Card title, status badge, track, source type
- One-sentence summary (first 150 chars of body, stripped markdown)
- Key points extracted from `## Key Points` section or body opening
- Tags list
- Source info (source_title, source_type)
- Human note preview if present

### Layer 2 — Structured Content (KnowledgeSections, default collapsed)
Two collapsible groups:
- **理解内容** (Understanding): AI Summary, Human Note, Key Points
- **处理过程** (Processing): Source Excerpt, AI Inference, Reusable Prompts, Principles
- All sections preserved via parseSections(), just grouped and collapsed

### Layer 3 — Related Knowledge (RelatedKnowledgePanel)
Replaces "知识图谱":
- `graph.title`: "知识图谱" → "相关知识"
- Relation reasons humanized:
  - same_source → "来自同一来源: {source_title}"
  - same_tag → "共享标签 #tag"
  - same_wiki_section → "同属章节: {section_title}"
  - similar_title_or_term → "标题或术语相似"
- Strength indicators simplified

### Layer 4 — Technical Evidence (collapsible `<details>`, default closed)
- Existing tech details: strategy_id, source_hash, run_id, prompt_versions
- Raw relation evidence
- All technical metadata that shouldn't be default-visible

## Component Changes

| Component | Action |
|-----------|--------|
| KnowledgeHero | New — Layer 1 rendering |
| KnowledgeSections | Refactor from CardSections — grouped, collapsible |
| RelatedKnowledgePanel | Refactor from GraphNavigationPanel + RelatedCardsPanel merge |
| TechnicalEvidencePanel | Extend existing `<details>` |
| CardWorkspace | Simplify to thin orchestrator |

## i18n Changes

- `graph.title`: "知识图谱" → "相关知识"
- `graph.related_by_source`: "同源" → "来自同一来源"
- `graph.shares_tag`: "同标签" → "共享标签"
- `graph.related_by_wiki_section`: "同 Wiki 章节" → "同属章节"
- `library.related_group_same_source`: "同源" → "来自同一来源"
- `library.related_group_same_tag`: "同标签" → "共享标签"
- `wiki.local_graph_preview`: "局部图谱预览" → "局部关系预览"
- `local_graph.title`: "局部关系预览" → "局部关系预览"

## Non-Goals

- No LLM calls
- No new dependencies
- No backend changes
- No approval boundary changes
- No information deletion
- No push
