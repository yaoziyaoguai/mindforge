"""Source Plugin Slice 1 — SourceDocument 契约冻结测试 (TDD Red 阶段)。

为什么有这个文件
================

v0.9 Source ingestion milestone 的 Slice 1 目标是把 ``SourceDocument`` 升格
为一个**冻结的契约**：字段集封闭、provenance 强制、deterministic
fingerprint 已就位、且不能向 approval / draft / card 三个下游领域漏字段。

当前 ``src/mindforge/sources/base.py`` 已经实现了大部分契约（13+1=14 个
字段、``__post_init__`` 强制 source_id / source_type / source_path /
content_hash 必填、``compute_content_hash`` 对 key 顺序无关、``frozen=True``
不可变快照），但仍存在**真实的契约缺口**，本文件用 TDD Red 的方式把缺口
显式钉死，等待 Slice 1 Green 实施时由人工授权后再补 production 修补。

设计边界
========

- 本文件**只动 tests**，不动 production code；
- 不调用真实 LLM、不读 .env、不写 Obsidian vault、不触发 approval；
- 不实现 SourcePlugin / SourceAdapter / SourceMux；
- 仅用 ``compute_content_hash`` 这一个真实工具构造合法 fixture；
- 所有 import 仅来自 ``mindforge.sources.base``，不跨模块依赖。

Red / Green 期望
================

- **预期 Red**：``test_adapter_name_must_be_provided`` —— 当前
  ``__post_init__`` 没有把 ``adapter_name`` 列入必填校验，但 Slice 1 契约
  要求它必须是 provenance 的一部分。Red 的根因是 production 契约尚未补全，
  不是测试写错或环境缺失。
- **Green 守卫**：其余测试今天就应通过，作用是把"已经满足的契约"钉死，
  防止后续无意改坏。
"""

from __future__ import annotations

import dataclasses

import pytest

from mindforge.sources.base import (
    SourceAdapter,
    SourceDocument,
    compute_content_hash,
)


# ---------------------------------------------------------------------------
# 共享 fixture：构造一个**最小合法**的 SourceDocument，避开当前 __post_init__
# 已经强制的四个必填字段（source_id / source_type / source_path /
# content_hash），便于聚焦其他契约维度。
# ---------------------------------------------------------------------------


def _minimal_kwargs(**overrides: object) -> dict[str, object]:
    """返回构造 SourceDocument 所需的最小关键字参数集。

    - ``raw_text`` 给一个非空字符串以便 content_hash 有意义；
    - ``adapter_name`` 默认给一个非空值，单测可显式覆写为空来验证 Red；
    - 其余 provenance 字段保持默认（None / 空 list / 空 dict）。
    """
    base: dict[str, object] = {
        "source_id": "src-001",
        "source_type": "plain_markdown",
        "source_path": "fixtures/dummy.md",
        "raw_text": "hello world",
        "content_hash": compute_content_hash("hello world"),
        "adapter_name": "PlainMarkdownAdapter",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. 字段集封闭：v0.9 契约冻结后，字段名应是已知有限集合，新增/删除字段
#    都属于契约变更，必须显式过审。本测试是 Green 守卫。
# ---------------------------------------------------------------------------


def test_source_document_field_set_is_frozen() -> None:
    """SourceDocument 的字段名必须严格等于 v0.9 契约规定的 14 个。

    若未来有人新增字段（无论是 ai_summary、approval_status 还是 card_id），
    本测试会立刻 fail，强迫新增者走 ROADMAP v0.9 §A 的"契约变更"流程，
    而不是默默扩展数据形状。
    """
    expected = {
        "source_id",
        "source_type",
        "source_path",
        "title",
        "author",
        "source_url",
        "created_at",
        "captured_at",
        "tags",
        "highlights",
        "raw_text",
        "metadata",
        "content_hash",
        "adapter_name",
    }
    actual = {f.name for f in dataclasses.fields(SourceDocument)}
    assert actual == expected, (
        f"SourceDocument 字段集已偏离 v0.9 契约。"
        f"多出: {actual - expected}；缺少: {expected - actual}"
    )


# ---------------------------------------------------------------------------
# 2. 不能漏入 approval / draft / card 三个下游领域字段。这是 v0.9 §B 边界
#    的静态守卫：SourceDocument 是输入层契约，绝不携带后续生命周期状态。
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden",
    [
        "human_approved",
        "approval_state",
        "approved_at",
        "approved_by",
        "ai_draft",
        "draft_text",
        "draft_payload",
        "card_id",
        "card_payload",
        "review_state",
    ],
)
def test_source_document_does_not_leak_lifecycle_fields(forbidden: str) -> None:
    """SourceDocument 不能出现 approval / draft / card 任何字段名。

    Slice 1 契约：input 层只描述"原料"，不描述"加工状态"。任何下游字段
    出现在这里都意味着边界被打破（典型反模式：adapter 直接生成
    ai_draft、绕过 KnowledgeStrategy）。
    """
    field_names = {f.name for f in dataclasses.fields(SourceDocument)}
    assert forbidden not in field_names, (
        f"SourceDocument 不允许包含 {forbidden!r} 字段——"
        f"它属于下游 approval / strategy 领域，违反 v0.9 §B 边界。"
    )


# ---------------------------------------------------------------------------
# 3. 不可变快照：frozen=True 是 SourceDocument 的硬约束，下游加工管线不能
#    改写已经入库的 input。
# ---------------------------------------------------------------------------


def test_source_document_is_frozen() -> None:
    doc = SourceDocument(**_minimal_kwargs())
    with pytest.raises(dataclasses.FrozenInstanceError):
        doc.raw_text = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 4. Provenance completeness：source_id / source_type / source_path 已被
#    __post_init__ 强制；adapter_name 也属于 provenance，但**构造期不强制**
#    ——历史上 Scanner 在派发后统一回填，让 adapter 不必重复 ``adapter_name
#    =self.name``。Slice 1 契约因此通过查询接口 ``is_provenance_complete()``
#    钉死边界：
#    - 构造期允许 adapter_name 为空（Scanner-backfill 友好）；
#    - 但对外 emit 前必须 ``is_provenance_complete()`` 为真，否则 Scanner
#      / 下游消费者应拒绝该文档。
#
#    Slice 1 Red 阶段曾把这条契约错放在 ``__post_init__`` 上（DID NOT RAISE
#    Red）；审计后发现那种实现会强迫修改 7 个 adapter + 多个 fixture，
#    属于机械搬运。现按"查询接口 + Scanner 出口校验"重新表达契约。
# ---------------------------------------------------------------------------


def test_is_provenance_complete_returns_false_when_adapter_name_missing() -> None:
    """空 adapter_name 的 SourceDocument 必须 is_provenance_complete() = False。

    背景：``state.json`` 用 adapter_name 反向追溯"这条 SourceDocument 是
    哪个 adapter 解析出来的"。空字符串意味着 Scanner 还没回填或 backfill
    链路出 bug —— 此时下游不应消费这条记录。
    """
    doc = SourceDocument(**_minimal_kwargs(adapter_name=""))
    assert doc.is_provenance_complete() is False


def test_is_provenance_complete_returns_true_when_adapter_name_present() -> None:
    """填好 adapter_name 的 SourceDocument 必须 is_provenance_complete() = True。"""
    doc = SourceDocument(**_minimal_kwargs(adapter_name="PlainMarkdownAdapter"))
    assert doc.is_provenance_complete() is True


def test_is_provenance_complete_is_pure_query() -> None:
    """is_provenance_complete 是纯查询：不抛异常、不改状态、可重复调用。"""
    doc = SourceDocument(**_minimal_kwargs(adapter_name="X"))
    first = doc.is_provenance_complete()
    second = doc.is_provenance_complete()
    assert first is True and second is True
    # frozen 守卫已确保 doc 不可变；这里再次确认调用未触发任何属性写入。
    assert doc.adapter_name == "X"


# ---------------------------------------------------------------------------
# 5. content_hash 即 deterministic fingerprint：同样输入必须同样 hash，
#    与 dict key 顺序无关；这是 v0.9 §C dedup 契约的基石。
# ---------------------------------------------------------------------------


def test_content_hash_is_deterministic_fingerprint() -> None:
    h1 = compute_content_hash("payload", {"url": "https://x", "lang": "zh"})
    h2 = compute_content_hash("payload", {"lang": "zh", "url": "https://x"})
    assert h1 == h2
    assert h1.startswith("sha256:"), "content_hash 必须显式带算法前缀，便于未来迁移"


def test_content_hash_diverges_on_different_text() -> None:
    h1 = compute_content_hash("payload-a")
    h2 = compute_content_hash("payload-b")
    assert h1 != h2


def test_content_hash_diverges_on_different_metadata() -> None:
    h1 = compute_content_hash("payload", {"url": "https://a"})
    h2 = compute_content_hash("payload", {"url": "https://b"})
    assert h1 != h2


# ---------------------------------------------------------------------------
# 6. 边界守卫：SourceDocument 必须**不**继承任何 strategy / approval /
#    processor 基类。这是 v0.9 §A "input layer 与 strategy/approval 解耦"
#    的静态守卫。
# ---------------------------------------------------------------------------


def test_source_document_has_no_strategy_or_approval_base() -> None:
    """SourceDocument 必须是纯 dataclass，不能 mixin 任何下游领域基类。"""
    bases = {b.__name__ for b in SourceDocument.__mro__}
    forbidden = {
        "KnowledgeStrategy",
        "ApprovalDecision",
        "Pipeline",
        "ProcessExecutor",
        "ReviewService",
        "ApprovalService",
    }
    leaked = bases & forbidden
    assert not leaked, f"SourceDocument 不能继承下游领域类：{leaked}"


# ---------------------------------------------------------------------------
# 7. 模块依赖守卫：``mindforge.sources.base`` 不应 import 任何 strategy /
#    approval / review / cli / processor 模块。这是 v0.9 §A "input 层是
#    最上游"的静态守卫——本测试通过读取模块对象的属性间接验证（不动 AST
#    工具，避免引入新依赖）。
# ---------------------------------------------------------------------------


def test_sources_base_module_has_no_downstream_imports() -> None:
    """``mindforge.sources.base`` 的命名空间里不应出现下游领域符号。

    如果 base.py 不慎 ``from ..strategies import ...`` 或类似，这些名字
    会出现在模块属性里，本测试会 fail 并指出泄漏。
    """
    import mindforge.sources.base as base_mod

    forbidden_substrings = (
        "Strategy",
        "Approval",
        "Review",
        "Pipeline",
        "Processor",
        "Cli",
        "Recall",
    )
    leaked = [
        name
        for name in dir(base_mod)
        if not name.startswith("_")
        and any(sub in name for sub in forbidden_substrings)
    ]
    # Highlight 里没有这些子串；SourceAdapter 也没有；正常情况下应为空集。
    assert leaked == [], (
        f"mindforge.sources.base 不应暴露下游领域符号：{leaked}"
    )


# ---------------------------------------------------------------------------
# 8. SourceAdapter 抽象契约不变：load() / can_handle() 仍是仅有的两个抽象
#    方法。Slice 2 才会扩展 capabilities()，本 Slice 1 钉死现状以防漂移。
# ---------------------------------------------------------------------------


def test_source_adapter_abstract_surface_is_minimal() -> None:
    """SourceAdapter 的抽象方法集合应严格等于 {can_handle, load}。

    若有人偷偷加了 ``fetch`` / ``sync`` / ``approve`` 等新抽象方法，
    本测试会 fail，强迫新增者把扩展挪到 Slice 2 capabilities 框架里。
    """
    abstracts = set(getattr(SourceAdapter, "__abstractmethods__", frozenset()))
    assert abstracts == {"can_handle", "load"}, (
        f"SourceAdapter 抽象方法集合已偏离 v0.9 契约：{abstracts}"
    )
