# Proposal: ReviewableArtifact Boundary (docs-only, NOT authorized)

> **状态**: proposal-only。**未授权实现**。本文档仅记录未来可能的
> 类型化 artifact 协议方向, 供后续 RFC 启动时参考。当前 v0.13
> Stage 1 不在 production 代码中引入此协议, 不抽 service 层, 不重构
> 任何现有模块。

## 1. 动机

随着 MindForge real-capable opt-in 路径就绪, 系统中出现的 "可被人类
review 的 artifact" 类型不断增加:

| 类型 | 来源 | 当前文件 |
| --- | --- | --- |
| `preview_packet` | custom strategy preview | `src/mindforge/strategies/preview_packet.py` |
| `ai_draft` | processor pipeline | `src/mindforge/processors/*` |
| `readiness_report` | provider readiness | `src/mindforge/provider_readiness.py` (v0.13 Stage 1 新增) |
| `real_smoke_result` | synthetic real-LLM smoke | `src/mindforge/real_smoke.py` (v0.13 Stage 1 新增) |
| `recall_hit` | recall service | `src/mindforge/recall_service.py` |
| `weekly_review_packet` | review service | `src/mindforge/review_service.py` |

这些 artifact 在以下方面共享语义:

1. 都 **不是** `human_approved`;
2. 都可以被 presenter 渲染;
3. 都 **不可** 直接写入 vault / cards / 永久知识;
4. 都需要显式 human gate 才能升级为 `human_approved`。

但目前每类 artifact 都自己定义结构, 没有统一协议来在类型层面表达
"我是 reviewable 的, 我永远不会被自动 approve"。

## 2. 提案 (sketch only)

```python
from typing import Protocol, Literal

ArtifactKind = Literal[
    "preview_packet",
    "ai_draft_preview",
    "readiness_report",
    "real_smoke_result",
    "recall_hit",
    "weekly_review_packet",
]

class ReviewableArtifact(Protocol):
    kind: ArtifactKind
    source_alias: str | None      # provider alias, None = no provider
    is_human_approved: bool        # 永远 False; 类型签名即文档
    is_persisted: bool             # 是否已写入永久存储 (永远 False for previews)
    audit: dict[str, str | bool]   # 非敏感审计元数据
```

约束:

- 所有 ReviewableArtifact 实现的 `is_human_approved` 字段 **类型签名上**
  不被允许为 `True`; 通过 `typing.Literal[False]` 限定。
- `audit` 中 **不允许** 出现 secret value、user-private content 或文件
  绝对路径 (`Path.home()` 下的实际路径)。
- 升级为 `human_approved` 必须经由显式 `ApprovalService.approve(...)`
  调用产生一个 **不同类型** 的 artifact (`ApprovedKnowledgeCard`),
  而不是把现有 ReviewableArtifact 字段翻转。

## 3. 与现有代码的关系 (不修改)

- `preview_packet.py` 当前已经是 pure data; 未来如果协议落地, 可以
  补一层 `ReviewableArtifactView(packet)` 适配, 不改动 packet 自身。
- `ApprovalService` 当前已经是唯一 `human_approved` 产生路径; 协议
  落地不需要改 ApprovalService 接口。
- `provider_readiness.py` / `real_smoke.py` 返回 `dict`, 未来可以补
  `to_reviewable_artifact()` 适配方法; 不改返回值。

## 4. 启动前置 (criteria for future RFC)

只有满足以下 **全部** 条件, 才考虑启动 ReviewableArtifact 协议的
正式 RFC:

1. 至少 3 类 artifact 已稳定落地 (目前 v0.13 Stage 1 后达到 6 类,
   ✅);
2. 出现至少 2 个跨 artifact 的横切需求 (例: 统一 audit log / 统一
   presenter 入口 / 统一 export 流程) 且当前散落实现已经造成维护
   负担;
3. 有明确的 deprecation plan, 不破坏现有命令对外接口;
4. 协议本身不引入 runtime cost (仅 typing.Protocol, 无动态调度);
5. 协议落地不会触发 `human_approved` 自动化的任何路径。

## 5. 拒绝条件 (when NOT to do this)

- 仅为了 "代码看起来更整齐" — 抽象需要承担维护成本;
- 仅为了 "未来可能扩展" 而提前抽象 — 违反 YAGNI;
- 任何会让 `human_approved` 字段在某个代码路径下变成可由非
  ApprovalService 设置的设计 — 立即拒绝;
- 任何会让协议依赖 `cli` / `presenter` / `cards` / `obsidian` /
  `cubox` 模块的设计 — 违反低耦合。

## 6. 当前不做什么

- 不在 `src/mindforge/` 下新增任何 `reviewable_artifact.py`;
- 不修改 `preview_packet.py` / `provider_readiness.py` / `real_smoke.py`
  的返回值结构;
- 不为 `ApprovalService` 添加新参数;
- 不引入 `typing.Protocol` 到现有 production 模块。

本文档仅供阅读、对照、未来 RFC 启动参考。
