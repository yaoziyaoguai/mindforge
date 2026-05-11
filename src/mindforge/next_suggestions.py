"""Next-suggestion 推断的纯逻辑层。

中文学习型说明：
- 这一层是 ``mindforge next`` / ``mindforge today`` / ``mindforge start`` 共用
  的“下一步推荐”引擎。它只接收一个 ``MindForgeConfig`` 和文件系统的可观察
  事实（vault / inbox / state.json / processing runs / 卡片 frontmatter / index 文件），返回一
  组带优先级的 ``NextSuggestion``。
- 设计边界：
  * 不读 secret，不调任何 LLM / 网络。
  * 不调用 Typer / Rich / ``console`` —— 输出格式化由 CLI 层的 presenter
    负责，本模块严禁出现 ``from .cli import …``。
  * 不修改任何文件，全部读路径。
- 该模块从 ``cli.py`` 巨石中独立出来，主要为了：
  * 让 ``mindforge --help`` / Typer 入口模块更瘦。
  * 让 ``next``/``today``/``start`` 的核心策略可以被单测直接覆盖，无需经过
    Typer ``CliRunner``。
  * 用一条架构边界测试（见 ``tests/test_architecture_boundaries.py``）防止
    将来又把 ``cli.py`` 的耦合 leak 回来。
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass
from datetime import datetime as _dt

from .config import MindForgeConfig

__all__ = [
    "NextSuggestion",
    "next_suggestions",
    "compact_next_suggestions",
    "PRIORITY_ORDER",
]


# ``next``/``today``/``start`` 与 doctor Action items 共用同一套优先级排序。
# ``try_first`` 是最高优先级，专门留给“下一条最短主路径”建议；它必须排在
# ``critical`` 前面。
PRIORITY_ORDER: dict[str, int] = {
    "try_first": -1,
    "critical": 0,
    "recommended": 1,
    "info": 2,
}


@dataclass(frozen=True)
class NextSuggestion:
    """“下一步该做什么”推荐项的不可变值对象。

    - ``command``：用户可以直接拷贝执行的命令字符串。
    - ``reason``：一句话解释为什么推荐它（不暴露内部实现细节）。
    - ``priority``：``try_first`` / ``critical`` / ``recommended`` / ``info`` 之一。
    """

    command: str
    reason: str
    priority: str


def next_suggestions(cfg: MindForgeConfig) -> list[NextSuggestion]:
    """根据 vault / state 当前状态，推断"下一步该做什么"。

    返回带 priority 的建议；JSON 仍保留 v0.4.2 的 command / reason 字段。

    判定来源全部是文件系统可观察事实，不做任何 AI 推断；
    每一条都对应一条用户能直接执行的命令。
    """

    if not cfg.vault.root.exists():
        return _missing_vault_suggestions(cfg)

    suggestions: list[NextSuggestion] = []
    suggestions.extend(_vault_shape_suggestions(cfg))
    inbox_files = _count_inbox_files(cfg)
    suggestions.extend(_inbox_suggestions(cfg, inbox_files))
    suggestions.extend(_state_suggestions(cfg, inbox_files))

    draft_count = _count_cards_by_status(cfg, "ai_draft")
    if draft_count > 0:
        suggestions.append(
            NextSuggestion(
                _vault_command(cfg, "mindforge approve list"),
                f"有 {draft_count} 张 ai_draft 卡片等待审核（不会自动 approve）",
                "recommended",
            )
        )

    suggestions.extend(_index_suggestions(cfg))
    suggestions.extend(_review_suggestions(cfg))
    suggestions.extend(_project_suggestions(cfg))
    if not suggestions:
        suggestions.append(
            NextSuggestion("mindforge doctor", "看起来一切就绪；定期跑 doctor 自检", "info")
        )
    return compact_next_suggestions(suggestions)


def _missing_vault_suggestions(cfg: MindForgeConfig) -> list[NextSuggestion]:
    """vault 缺失时只指向真实初始化路径。"""

    return [
        NextSuggestion(
            "mindforge web",
            "打开 Web Setup 配置真实模型与本地知识库",
            "recommended",
        ),
        NextSuggestion(
            f"mindforge init --vault {cfg.vault.root}",
            "vault 根目录不存在，先一键铺骨架",
            "critical",
        ),
    ]


def _vault_shape_suggestions(cfg: MindForgeConfig) -> list[NextSuggestion]:
    if cfg.vault.inbox_path.exists() and cfg.vault.cards_path.exists():
        return []
    return [
        NextSuggestion(
            _vault_command(cfg, "mindforge init"),
            "vault 子目录缺失（00-Inbox/ 或 20-Knowledge-Cards/）",
            "critical",
        )
    ]


def _count_inbox_files(cfg: MindForgeConfig) -> int:
    inbox = cfg.vault.inbox_path
    if not inbox.exists():
        return 0
    return sum(1 for p in inbox.rglob("*") if p.is_file() and not p.name.startswith("."))


def _inbox_suggestions(cfg: MindForgeConfig, inbox_files: int) -> list[NextSuggestion]:
    if inbox_files != 0:
        return []
    return [
        NextSuggestion(
            f"# 把本地 markdown/txt 文件放到 {cfg.vault.inbox_path}/ 等 source 目录",
            "inbox 当前为空，没有可加工的原料",
            "info",
        )
    ]


def _state_suggestions(cfg: MindForgeConfig, inbox_files: int) -> list[NextSuggestion]:
    state_path = cfg.state.state_path
    raw_or_triaged = _count_raw_or_triaged_state_entries(state_path)
    if inbox_files > 0 and raw_or_triaged == 0 and not state_path.exists():
        return [
            NextSuggestion(
                _vault_command(cfg, "mindforge watch add <file-or-folder>"),
                "已有 source 文件；注册 source 会创建后台 processing run",
                "critical",
            ),
            NextSuggestion(
                _vault_command(cfg, "mindforge runs list"),
                "用 runs 查看后台 processing 进度",
                "critical",
            )
        ]
    if raw_or_triaged > 0:
        return [
            NextSuggestion(
                _vault_command(cfg, "mindforge import <file-or-folder>"),
                f"发现 {raw_or_triaged} 条旧待处理记录；新主路径请重新导入 source 创建后台 run",
                "critical",
            )
        ]
    return []


def _count_raw_or_triaged_state_entries(state_path) -> int:  # type: ignore[no-untyped-def]
    if not state_path.exists():
        return 0
    try:
        data = _json.loads(state_path.read_text(encoding="utf-8"))
        entries = data.get("items") or data.get("documents") or {}
        return sum(1 for entry in entries.values() if entry.get("status", "") in {"raw", "triaged"})
    except Exception:
        return 0


def _iter_card_frontmatters(cards_path):  # type: ignore[no-untyped-def]
    if not cards_path.exists():
        return
    try:
        import yaml as _yaml
    except Exception:
        return
    for path in cards_path.rglob("*.md"):
        if path.name.startswith("_"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if not text.startswith("---"):
                continue
            end = text.find("\n---", 3)
            if end < 0:
                continue
            yield _yaml.safe_load(text[3:end]) or {}
        except Exception:
            continue


def _count_cards_by_status(cfg: MindForgeConfig, status: str) -> int:
    return sum(1 for fm in _iter_card_frontmatters(cfg.vault.cards_path) or () if fm.get("status") == status)


def _index_suggestions(cfg: MindForgeConfig) -> list[NextSuggestion]:
    cards = cfg.vault.cards_path
    index_path = cfg.state.workdir / "index" / "bm25.json"
    card_file_count = 0
    if cards.exists():
        card_file_count = sum(
            1 for p in cards.rglob("*.md") if p.is_file() and not p.name.startswith("_")
        )
    if cards.exists() and not index_path.exists() and card_file_count > 0:
        return [
            NextSuggestion(
                _vault_command(cfg, "mindforge index rebuild"),
                "BM25 索引尚未建立（recall 需要它）",
                "recommended",
            )
        ]
    return []


def _review_suggestions(cfg: MindForgeConfig) -> list[NextSuggestion]:
    overdue = _count_overdue_review_cards(cfg)
    if overdue <= 0:
        return []
    return [
        NextSuggestion(
            _vault_command(cfg, "mindforge review backlog"),
            f"有 {overdue} 张复习卡片已 overdue",
            "recommended",
        )
    ]


def _count_overdue_review_cards(cfg: MindForgeConfig) -> int:
    now = _dt.now().astimezone()
    overdue = 0
    for fm in _iter_card_frontmatters(cfg.vault.cards_path) or ():
        if fm.get("status") != "human_approved":
            continue
        review_after = _parse_review_after(fm.get("review_after"), now)
        if review_after is not None and review_after <= now:
            overdue += 1
    return overdue


def _parse_review_after(value, now: _dt) -> _dt | None:  # type: ignore[no-untyped-def]
    if not value:
        return None
    if isinstance(value, str):
        try:
            value = _dt.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    if hasattr(value, "tzinfo") and value.tzinfo is None:
        value = value.replace(tzinfo=now.tzinfo)
    return value


def _project_suggestions(cfg: MindForgeConfig) -> list[NextSuggestion]:
    projects_dir = cfg.vault.projects_path
    project_count = 0
    if projects_dir.exists():
        project_count = sum(
            1 for p in projects_dir.glob("*.md") if not p.name.startswith("_") and p.is_file()
        )
    if project_count == 0:
        return []
    return [
        NextSuggestion(
            _vault_command(cfg, "mindforge project list"),
            f"vault 中有 {project_count} 个项目笔记，可生成 context pack",
            "info",
        )
    ]


def _vault_command(cfg: MindForgeConfig, command: str) -> str:
    """把建议命令绑定到当前 vault，保证复制后仍在同一个目标上运行。

    中文学习型说明：``next`` / ``start`` 是产品入口，输出的每条命令都应该
    可以直接复制。真实验收时用户常传入临时 disposable vault；如果建议命令
    丢掉 ``--vault``，下一步就会回到配置里的默认私人
    vault，既卡顿也有安全风险。这里仍是纯字符串策略，不依赖 CLI/Rich。
    """

    if "--vault" in command:
        return command
    return f"{command} --vault {cfg.vault.root}"


def compact_next_suggestions(suggestions: list[NextSuggestion]) -> list[NextSuggestion]:
    """对建议列表按优先级稳定排序并截断。

    超过 5 条时只保留前 4 条 + 1 条 "运行 doctor 看完整自检" 提示，避免
    用户面对一长串建议时反而不知所措。``sorted`` 是稳定排序，所以同优先级
    内部仍按调用方加入顺序。
    """

    suggestions = sorted(suggestions, key=lambda s: PRIORITY_ORDER.get(s.priority, 9))
    if len(suggestions) <= 5:
        return suggestions
    shown = suggestions[:4]
    hidden = len(suggestions) - len(shown)
    shown.append(
        NextSuggestion(
            "mindforge doctor",
            f"还有 {hidden} 条低优先级建议；运行 doctor 查看完整自检",
            "info",
        )
    )
    return shown
