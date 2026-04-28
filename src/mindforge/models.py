"""通用数据模型 — RunRecord / StageRecord / ItemState / Card 等。

设计原则
========

1. **协议数据 vs 状态数据 分离**
   - ``SourceDocument``（在 ``mindforge.sources.base``）= adapter ↔ 加工管线 的协议；
   - ``ItemState`` / ``StageRecord`` / ``RunRecord``（在本文件）= checkpoint 与
     run jsonl 的状态记录。两类数据职责不同，不能混。

2. **dataclass 优先**
   - 所有模型用 ``dataclass`` 表达；序列化由 ``checkpoint`` / ``logging_setup``
     等模块负责，模型本身不持有 IO。

3. **为 v0.1 而生，不为未来想象**
   - 只放 v0.1 真正会用到的字段；不要先把"以后可能要"的字段都堆进来。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

# ItemStatus 的状态枚举，对应 docs/MINDFORGE_PROTOCOL.md §状态机
# v0.1 只在 M1 用 raw / skipped 两个状态；其余在 M2/M3 才会被 set。
ItemStatus = Literal[
    "raw",            # scanner 看到了，但还没 triage
    "triaged",        # 已分流，但 distill 未完成
    "skipped",        # value_score 不够，主动放弃
    "processed",      # Card 已写入
    "failed",         # 任一阶段失败
    "human_approved", # 人工把 Card status 改为 human_approved 后回写
]

StageName = Literal[
    "triage",
    "distill",
    "link_suggestion",
    "review_questions",
    "action_extraction",
]


@dataclass
class StageRecord:
    """单个 stage 的执行记录（写入 state.json.items.<key>.stages.<stage>）。

    每条记录回答："这个文件的这个 stage，是用哪个 model_alias / 哪个 prompt
    版本跑的？什么时候跑的？成功还是失败？"

    这是 v0.1 可观察性契约的最细粒度，决定了"事后能否复盘某张卡片为什么这么写"。
    """

    stage: StageName
    model_alias: str
    provider: str
    actual_model: str
    prompt_version: str           # 例如 "triage@v1"
    status: Literal["ok", "failed", "skipped"]
    processed_at: datetime
    error_message: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None


@dataclass
class ItemState:
    """单条 inbox 文件的处理状态（写入 state.json.items.<key>）。

    key 形如 ``"<source_type>::<source_path>"``，由 checkpoint 模块拼装。
    """

    source_id: str
    source_type: str
    adapter_name: str
    source_path: str
    content_hash: str
    status: ItemStatus = "raw"
    track: str | None = None
    value_score: int | None = None
    card_path: str | None = None          # 写入的 Knowledge Card 相对路径
    last_run_id: str | None = None
    first_seen_at: datetime | None = None
    processed_at: datetime | None = None
    error_message: str | None = None
    stages: dict[str, StageRecord] = field(default_factory=dict)
    # M3 反 AI 污染闸门：仅 `mindforge approve` CLI 写入，pipeline 永远不写。
    # 详见 docs/M3_HUMAN_APPROVAL_PROTOCOL.md。
    approved_at: datetime | None = None
    approval_method: str | None = None  # v0.1 仅 "explicit_cli"

    @property
    def state_key(self) -> str:
        """state.json 中本条记录的复合 key。"""
        return f"{self.source_type}::{self.source_path}"


@dataclass
class RunRecord:
    """一次 ``mindforge process`` 调用的整体元数据（写入 runs/<run_id>.jsonl 头）。

    具体每条事件由 ``logging_setup``（M2 引入）按行追加；本结构只是头部摘要。
    """

    run_id: str
    started_at: datetime
    active_profile: str
    triggered_by: Literal["scan", "process", "process_file"] = "process"


__all__ = [
    "ItemStatus",
    "StageName",
    "StageRecord",
    "ItemState",
    "RunRecord",
]
