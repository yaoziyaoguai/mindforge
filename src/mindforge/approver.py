"""M3 — human approval：把 ai_draft 卡片显式晋升为 human_approved。

设计契约（详见 ``README.md`` 的 approval boundary 与状态链路）

1. 这是 MindForge 的**反 AI 污染闸门**：``ai_draft → human_approved`` 这一
   状态转移在整个 v0.1 中只有 ``mindforge approve`` CLI 一个入口能触发；
   LLM pipeline / Writer / Triager 全部被禁止写 ``human_approved``。
2. 完全不调用 LLM、不需要 ``.env``、不依赖 active_profile。
3. **不**修改卡片正文，**不**改写源文件；只在 frontmatter 上追加
   ``status`` / ``approved_at`` / ``approval_method`` 三个字段。
4. ``human_approved`` 卡片再次 approve 是幂等的（不刷 timestamp、不重复
   写 state、不重复写 jsonl 业务事件）。
5. ``raw / triaged / skipped / failed / 未知`` status 的卡片必须**拒绝**
   approve；只有 ``ai_draft`` 才能晋升。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml

from .checkpoint import Checkpoint
from .config import MindForgeConfig
from .models import ItemState

# v0.1 唯一允许的 approval_method 取值；不接受参数注入。
APPROVAL_METHOD_EXPLICIT_CLI = "explicit_cli"

# 卡片必须处于此 status 才允许晋升。
_PROMOTABLE_STATUS = "ai_draft"
_TARGET_STATUS = "human_approved"


class ApprovalError(Exception):
    """approve 业务错误；CLI 据此映射 exit code。"""

    def __init__(self, message: str, *, exit_code: int, prev_status: str | None = None) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.prev_status = prev_status


# ---------------------------------------------------------------------------
# Bundle B：first-class ApprovalDecision seam
#
# 设计动机（务必理解再扩展，否则容易回退到巨石）：
#
# 1. ``ApprovalDecision`` 表达**用户/流程层面的"决定"**：用户在审 ai_draft
#    卡片时可能选择 approve / reject / defer / append-as-evidence /
#    link-to-existing / merge-candidate / split。这是一个**意图域**。
#
# 2. ``ApprovalEffect``（原 ``ApprovalOutcome``）表达**系统执行后的"效果"**：
#    实际 frontmatter 改了什么、是否幂等、是否找到 ItemState。这是**结果域**。
#
# 3. 把两者合在一个名字下（旧 ``ApprovalOutcome`` 同时承担"用户做了什么"和
#    "系统发生了什么"）会随着 reject/defer/merge/split 的加入迅速变成
#    "无所不包的状态字典"。本轮 rename + enum 是为了从源头切开。
#
# 4. 本轮**只接通 APPROVE 分支**（复用既有 ``approve_card``）。其余 6 个分支
#    在 ``apply_decision`` 中显式 ``raise NotImplementedDecisionError``，
#    错误消息明确说"该 decision 是已规划的扩展点，但尚未实现"。
#
#    显式 NotImplemented 而不是静默 ignore 的理由：
#    - CLI 层任何误用都会立刻爆炸，绝不会"假装成功"
#    - fitness 测试可以 AST 锁住"dispatcher 必须穷举所有 enum 成员"
#    - 后续 Bundle B-2/B-3 添加 reject/defer 时，只改 dispatcher 单分支，
#      调用方零感知
#
# 5. 本轮**不**新增任何 CLI 子命令；CLI ``approve`` 仍走既有
#    ``approve_explicit_card`` 路径。seam 只是把"决定"这件事在领域模型上
#    显式化，避免 review/approval 模块再次巨石化。
# ---------------------------------------------------------------------------


class ApprovalDecision(str, Enum):
    """用户对一张 ai_draft 卡片的**决定**。

    取值采用 ``str`` 基类是为了 JSON / 日志序列化时直接得到稳定字符串，
    避免 ``ApprovalDecision.APPROVE`` 在跨进程边界变成 ``"<ApprovalDecision.APPROVE: 'approve'>"``。

    枚举顺序无业务含义；新增分支必须**同时**在 :func:`apply_decision`
    的 dispatcher 中处理（由 fitness 测试静态保证）。
    """

    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"
    APPEND_AS_EVIDENCE = "append_as_evidence"
    LINK_TO_EXISTING = "link_to_existing"
    MERGE_CANDIDATE = "merge_candidate"
    SPLIT = "split"


class NotImplementedDecisionError(ApprovalError):
    """显式声明：该 decision 是 Phase 1 已规划的扩展点，但当前 bundle 未实现。

    继承 ``ApprovalError`` 是为了让 CLI 既有错误处理路径自然兜住（exit code
    复用），不必在 CLI 中新增分支。``exit_code=64`` 取自 ``EX_USAGE``：调用
    了一个语义合法但实现尚未到位的 decision，本质上是用法时序错误。
    """

    def __init__(self, decision: "ApprovalDecision") -> None:
        super().__init__(
            f"approval decision {decision.value!r} 已在领域模型中预留，"
            f"但当前版本尚未实现执行路径；仅 'approve' 已接通。",
            exit_code=64,
        )
        self.decision = decision


@dataclass(frozen=True)
class ApprovalRequest:
    """承载用户**意图**的值对象，不含任何 IO 行为。

    ``target_card_path`` / ``note`` 留给后续 link/merge/defer 分支使用，本轮
    APPROVE 分支不消费这两个字段。
    """

    card_path: Path
    decision: ApprovalDecision
    target_card_path: Path | None = None
    note: str | None = None


ApprovalEffectKind = Literal["approved", "already_approved"]


@dataclass(frozen=True)
class ApprovalEffect:
    """approve 成功路径的**执行效果**记录。失败一律抛 ApprovalError。

    历史名字 ``ApprovalOutcome`` 同时被理解为"用户决定"和"系统效果"，导致
    引入 ``ApprovalDecision`` 时命名碰撞。Bundle B 将其重命名为
    ``ApprovalEffect``，与 ``ApprovalDecision`` 形成清晰二元：
    ``decision``（用户做了什么）→ dispatcher → ``effect``（系统结果如何）。
    """

    kind: ApprovalEffectKind
    card_path: Path
    prev_status: str
    new_status: str
    approval_method: str
    approved_at: datetime | None  # already_approved 路径不更新此字段
    state_missing: bool


# 历史别名：保持外部 import ``from mindforge.approver import ApprovalOutcome``
# 暂时可用，便于未受控的下游脚本平滑过渡。本仓库内部一律使用新名字。
ApprovalOutcome = ApprovalEffect
ApprovalOutcomeKind = ApprovalEffectKind


# ---------------------------------------------------------------------------
# 内部：frontmatter 读写（不依赖 python-frontmatter dump，避免它默认
# sort_keys/重排顺序，破坏既有卡片字段顺序）
# ---------------------------------------------------------------------------


def _split_frontmatter(text: str) -> tuple[str, str]:
    """把 Markdown 文本拆成 (frontmatter_yaml, body)。

    严格要求文件以 ``---\\n`` 开头，并存在第二个 ``\\n---\\n`` 作为分隔。
    任何不满足都抛 ApprovalError(exit=3)。
    """
    if not text.startswith("---\n"):
        raise ApprovalError("卡片缺少 frontmatter（未以 '---' 开头）", exit_code=3)
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        # 兼容文件末尾恰好以 '\n---' 结尾、缺尾 newline 的情况
        if rest.endswith("\n---"):
            return rest[: -4], ""
        raise ApprovalError("卡片 frontmatter 未闭合（缺第二个 '---'）", exit_code=3)
    fm_text = rest[:end]
    body = rest[end + len("\n---\n") :]
    return fm_text, body


def _join_frontmatter(fm_text: str, body: str) -> str:
    if not fm_text.endswith("\n"):
        fm_text = fm_text + "\n"
    return f"---\n{fm_text}---\n{body}"


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def approve_card(
    card_path: Path,
    *,
    cfg: MindForgeConfig,
) -> ApprovalEffect:
    """显式人工晋升一张 Knowledge Card 为 ``human_approved``。

    不抛网络异常 / 不实例化 LLM。失败抛 ``ApprovalError``。

    state.json 同步：
    - 找到对应 ItemState（按 ``card_path`` 反查）→ 更新 status / approved_at /
      approval_method 并 save。
    - 找不到 → 仍 approve 卡片，``ApprovalEffect.state_missing=True``，
      由 CLI 在 jsonl 中标注。
    """
    if not card_path.exists() or not card_path.is_file():
        raise ApprovalError(f"卡片文件不存在：{card_path}", exit_code=2)

    raw = card_path.read_text(encoding="utf-8")
    fm_text, body = _split_frontmatter(raw)

    try:
        fm_data: Any = yaml.safe_load(fm_text)
    except yaml.YAMLError as e:
        raise ApprovalError(f"frontmatter YAML 解析失败：{e}", exit_code=3) from e
    if not isinstance(fm_data, dict):
        raise ApprovalError("frontmatter 必须是 YAML 对象", exit_code=3)

    prev_status = fm_data.get("status")
    if prev_status is None:
        raise ApprovalError("frontmatter 缺少 status 字段", exit_code=3)
    if not isinstance(prev_status, str):
        raise ApprovalError(f"status 字段类型异常：{type(prev_status).__name__}", exit_code=3)

    # 加载 checkpoint（即便 state 找不到对应 item，也允许 approve 走完）
    state_path = cfg.state.state_path
    checkpoint = Checkpoint.load(state_path)
    item: ItemState | None = _find_item_by_card(checkpoint, card_path, cfg)
    state_missing = item is None

    # ---- 幂等路径 ----
    if prev_status == _TARGET_STATUS:
        return ApprovalEffect(
            kind="already_approved",
            card_path=card_path,
            prev_status=prev_status,
            new_status=_TARGET_STATUS,
            approval_method=str(fm_data.get("approval_method") or APPROVAL_METHOD_EXPLICIT_CLI),
            approved_at=None,
            state_missing=state_missing,
        )

    # ---- 拒绝路径 ----
    if prev_status != _PROMOTABLE_STATUS:
        raise ApprovalError(
            f"status={prev_status!r} 不能晋升为 human_approved（仅 ai_draft 可晋升）",
            exit_code=4,
            prev_status=prev_status,
        )

    # ---- 晋升路径：改 frontmatter，原子写回 ----
    approved_at_iso = _now_iso()
    fm_data["status"] = _TARGET_STATUS
    fm_data["approved_at"] = approved_at_iso
    fm_data["approval_method"] = APPROVAL_METHOD_EXPLICIT_CLI

    # sort_keys=False 保留原顺序；新字段会出现在 dict 末尾（即原文件 yaml 末尾）
    new_fm_text = yaml.safe_dump(
        fm_data, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    _atomic_write(card_path, _join_frontmatter(new_fm_text, body))

    # ---- 同步 state.json ----
    if item is not None:
        item.status = _TARGET_STATUS  # type: ignore[assignment]
        item.approved_at = datetime.fromisoformat(approved_at_iso)
        item.approval_method = APPROVAL_METHOD_EXPLICIT_CLI
        checkpoint.save()

    return ApprovalEffect(
        kind="approved",
        card_path=card_path,
        prev_status=prev_status,
        new_status=_TARGET_STATUS,
        approval_method=APPROVAL_METHOD_EXPLICIT_CLI,
        approved_at=datetime.fromisoformat(approved_at_iso),
        state_missing=state_missing,
    )


def _find_item_by_card(
    checkpoint: Checkpoint, card_path: Path, cfg: MindForgeConfig
) -> ItemState | None:
    """按 card_path 在 checkpoint 中反查 ItemState。

    state.json 里 ``card_path`` 是相对 vault.cards_dir 的路径（writer 写入时
    保持的形式），所以这里需要把传入的 card_path 也归一化成相同形式。
    """
    cards_root = cfg.vault.cards_path
    vault_root = cfg.vault.root
    candidates: set[str] = {str(card_path), str(card_path.resolve())}
    for base in (vault_root, cards_root):
        try:
            rel = card_path.resolve().relative_to(base.resolve())
        except ValueError:
            continue
        candidates.add(str(rel))
        candidates.add(rel.as_posix())

    for item in checkpoint.all_items():
        if item.card_path and item.card_path in candidates:
            return item
        # writer 也可能写绝对路径；做一层 resolve 比较
        if item.card_path:
            try:
                if Path(item.card_path).resolve() == card_path.resolve():
                    return item
            except OSError:
                continue
    return None


__all__ = [
    "APPROVAL_METHOD_EXPLICIT_CLI",
    "ApprovalDecision",
    "ApprovalEffect",
    "ApprovalEffectKind",
    "ApprovalError",
    "ApprovalOutcome",  # 历史别名（= ApprovalEffect），保留以平滑迁移
    "ApprovalRequest",
    "NotImplementedDecisionError",
    "apply_decision",
    "approve_card",
]


# ---------------------------------------------------------------------------
# Decision dispatcher
#
# 当前唯一接通的分支是 APPROVE → ``approve_card``。其余 6 个分支是 Phase 1
# Roadmap 显式预留的扩展点，必须 raise :class:`NotImplementedDecisionError`
# 而不是 ``pass`` / 返回 None / 静默忽略：否则上层调用一旦误用，会得到一个
# "看起来成功"的 None，破坏 ai_draft / human_approved 边界。
#
# 新增 enum 成员时**必须**同步在本函数中处理一个对应分支；
# ``tests/test_approval_decision.py`` 中的 fitness 测试会 AST 静态保证这条
# 不变量，避免后续 Coding Agent 加了 enum 成员却忘了接 dispatcher。
# ---------------------------------------------------------------------------


def apply_decision(
    request: ApprovalRequest,
    *,
    cfg: MindForgeConfig,
) -> ApprovalEffect:
    """根据用户 decision 调用对应执行路径。

    本函数是 Phase 1 "first-class approval outcomes" 的入口 seam。它把
    "用户做了什么决定"（``ApprovalDecision``）和"系统执行后的效果"
    （``ApprovalEffect``）解耦，使后续 reject/defer/append/link/merge/split
    可以**只在本 dispatcher 中加分支**，无需扩散到 CLI / presenter / service。
    """

    decision = request.decision
    if decision is ApprovalDecision.APPROVE:
        return approve_card(request.card_path, cfg=cfg)
    if decision is ApprovalDecision.REJECT:
        raise NotImplementedDecisionError(decision)
    if decision is ApprovalDecision.DEFER:
        raise NotImplementedDecisionError(decision)
    if decision is ApprovalDecision.APPEND_AS_EVIDENCE:
        raise NotImplementedDecisionError(decision)
    if decision is ApprovalDecision.LINK_TO_EXISTING:
        raise NotImplementedDecisionError(decision)
    if decision is ApprovalDecision.MERGE_CANDIDATE:
        raise NotImplementedDecisionError(decision)
    if decision is ApprovalDecision.SPLIT:
        raise NotImplementedDecisionError(decision)
    # Defensive：枚举被扩展但 dispatcher 漏改时立刻爆炸；不静默 fallback。
    raise NotImplementedDecisionError(decision)
