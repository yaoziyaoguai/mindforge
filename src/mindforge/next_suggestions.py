"""Next-suggestion 推断的纯逻辑层。

中文学习型说明：
- 这一层是 ``mindforge next`` / ``mindforge today`` / ``mindforge start`` 共用
  的“下一步推荐”引擎。它只接收一个 ``MindForgeConfig`` 和文件系统的可观察
  事实（vault / inbox / state.json / 卡片 frontmatter / index 文件），返回一
  组带优先级的 ``NextSuggestion``。
- 设计边界：
  * 不读 ``.env``，不调任何 LLM / Cubox / 网络。
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
# ``try_first`` 是 v0.7.x UX completion 引入的最高优先级，专门留给“零配置
# safe demo 入口”这种新用户友好建议；它必须排在 ``critical`` 前面。
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

    suggestions: list[NextSuggestion] = []
    vault_root = cfg.vault.root
    inbox = cfg.vault.inbox_path
    cards = cfg.vault.cards_path
    projects_dir = cfg.vault.projects_path
    workdir = cfg.state.workdir

    # 1. vault 是否完整
    if not vault_root.exists():
        # 用户友好性 polish：vault 缺失时，先把零配置 demo tour 推到最前。
        # 这样新用户不必先执行 ``mindforge init`` 也能 60 秒看到 fake/safe path
        # 跑通的效果；``mindforge init`` 仍然是 vault 真正落地前的必经一步，
        # 所以保留为 critical。
        suggestions.append(
            NextSuggestion(
                "mindforge demo",
                "60 秒零配置 tour（不需要 API key、不联网、不写 vault）",
                "recommended",
            )
        )
        suggestions.append(
            NextSuggestion(
                f"mindforge init --vault {vault_root}",
                "vault 根目录不存在，先一键铺骨架",
                "critical",
            )
        )
        return suggestions
    if not inbox.exists() or not cards.exists():
        suggestions.append(
            NextSuggestion(
                "mindforge init",
                "vault 子目录缺失（00-Inbox/ 或 20-Knowledge-Cards/）",
                "critical",
            )
        )

    # 2. inbox 是否有原料（统计文件数即可，**不读内容**）
    inbox_files = 0
    if inbox.exists():
        for p in inbox.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                inbox_files += 1
    if inbox_files == 0:
        suggestions.append(
            NextSuggestion(
                f"# 把 markdown 放到 {inbox}/ManualNotes/ 或 Cubox/ 等子目录",
                "inbox 当前为空，没有可加工的原料",
                "info",
            )
        )

    # 3. state.json 是否有未处理（raw/triaged）
    state_path = cfg.state.state_path
    raw_or_triaged = 0
    drafts_in_state = 0
    if state_path.exists():
        try:
            data = _json.loads(state_path.read_text(encoding="utf-8"))
            entries = data.get("items") or data.get("documents") or {}
            for entry in entries.values():
                st = entry.get("status", "")
                if st in {"raw", "triaged"}:
                    raw_or_triaged += 1
        except Exception:
            pass
    if inbox_files > 0 and raw_or_triaged == 0 and not state_path.exists():
        suggestions.append(NextSuggestion("mindforge scan", "inbox 有文件但 state.json 还没建立", "critical"))
    elif raw_or_triaged > 0:
        suggestions.append(
            NextSuggestion(
                "mindforge process --limit 10",
                f"state 中有 {raw_or_triaged} 条未跑完 pipeline",
                "critical",
            )
        )

    # 4. ai_draft 待审核（**只**统计 frontmatter 的 status 字段）
    draft_count = 0
    if cards.exists():
        try:
            import yaml as _yaml

            for p in cards.rglob("*.md"):
                if p.name.startswith("_"):
                    continue
                try:
                    text = p.read_text(encoding="utf-8")
                    if not text.startswith("---"):
                        continue
                    end = text.find("\n---", 3)
                    if end < 0:
                        continue
                    fm = _yaml.safe_load(text[3:end]) or {}
                    if fm.get("status") == "ai_draft":
                        draft_count += 1
                except Exception:
                    continue
        except Exception:
            pass
    drafts_in_state = draft_count
    if draft_count > 0:
        suggestions.append(
            NextSuggestion(
                "mindforge approve list",
                f"有 {draft_count} 张 ai_draft 卡片等待审核（不会自动 approve）",
                "recommended",
            )
        )

    # 5. 索引是否存在
    index_path = workdir / "index" / "bm25.json"
    card_file_count = 0
    if cards.exists():
        card_file_count = sum(
            1
            for p in cards.rglob("*.md")
            if p.is_file() and not p.name.startswith("_")
        )
    if cards.exists() and not index_path.exists() and card_file_count > 0:
        # 即使全部 ai_draft，也给一次 rebuild 提示（recall --include-drafts 仍能用）。
        suggestions.append(
            NextSuggestion(
                "mindforge index rebuild",
                "BM25 索引尚未建立（recall 需要它）",
                "recommended",
            )
        )

    # 6. 复习 backlog
    overdue = 0
    if cards.exists():
        try:
            import yaml as _yaml

            now = _dt.now().astimezone()
            for p in cards.rglob("*.md"):
                if p.name.startswith("_"):
                    continue
                try:
                    text = p.read_text(encoding="utf-8")
                    if not text.startswith("---"):
                        continue
                    end = text.find("\n---", 3)
                    if end < 0:
                        continue
                    fm = _yaml.safe_load(text[3:end]) or {}
                    if fm.get("status") != "human_approved":
                        continue
                    ra = fm.get("review_after")
                    if not ra:
                        continue
                    if isinstance(ra, str):
                        try:
                            ra = _dt.fromisoformat(ra.replace("Z", "+00:00"))
                        except Exception:
                            continue
                    if hasattr(ra, "tzinfo") and ra.tzinfo is None:
                        ra = ra.replace(tzinfo=now.tzinfo)
                    if ra <= now:
                        overdue += 1
                except Exception:
                    continue
        except Exception:
            pass
    if overdue > 0:
        suggestions.append(
            NextSuggestion(
                "mindforge review backlog",
                f"有 {overdue} 张复习卡片已 overdue",
                "recommended",
            )
        )

    # 7. 项目上下文（有 30-Projects 文件即提示）
    project_count = 0
    if projects_dir.exists():
        project_count = sum(
            1
            for p in projects_dir.glob("*.md")
            if not p.name.startswith("_") and p.is_file()
        )
    if project_count > 0 and drafts_in_state >= 0:
        suggestions.append(
            NextSuggestion(
                "mindforge project list",
                f"vault 中有 {project_count} 个项目笔记，可生成 context pack",
                "info",
            )
        )

    # 8. 兜底：什么都没建议时给一条 doctor
    if not suggestions:
        suggestions.append(NextSuggestion("mindforge doctor", "看起来一切就绪；定期跑 doctor 自检", "info"))
    return compact_next_suggestions(suggestions)


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
