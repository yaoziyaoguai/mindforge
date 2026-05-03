"""``mindforge doctor`` 的纯逻辑层。

中文学习型说明：
- 本模块从历史 ``cli.py`` 巨石中拆出，承担 doctor 命令的所有 *诊断与
  推断* 工作：
    * 读路径存在性、读 ``state.json`` 是否可解析；
    * 检查 BM25 索引是否过期 / 与配置漂移；
    * 统计 ``ai_draft`` / ``human_approved`` 卡片数与 overdue / due 7d；
    * 把 ``next_suggestions`` 与本地 recovery 检查合并成 doctor hints。
- 安全边界：
    * 不读取 ``.env`` 内容；
    * 不调用 LLM / Cubox / Upstage / 任何网络；
    * 不产生 ``human_approved`` 记录（只 *读* 该字段做统计）；
    * 不写 vault；
    * 不依赖 ``mindforge.cli`` / ``typer`` / ``rich`` / ``console``。
- 输出全部是 ``tuple`` / ``dict`` 等 plain-data，由 ``presenters/doctor``
  做 Rich 渲染。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from ..config import MindForgeConfig

__all__ = [
    "config_doctor_rows",
    "doctor_recovery_checks",
    "doctor_paths",
    "dir_state",
    "compute_doctor_hints",
]


def dir_state(p: Path) -> str:
    """目录存在性的三态判定。

    用 ``ok`` / ``error`` 两态够用：``warn`` 留给"父目录可恢复"场景，由
    ``config_doctor_rows`` 自己做。
    """

    if not p.exists() or not p.is_dir():
        return "error"
    return "ok"


def config_doctor_rows(cfg: MindForgeConfig) -> list[tuple[str, str, str, str]]:
    """配置诊断行；只做路径和 package asset 可读性检查。

    这些检查不会创建目录，不会读取 ``.env``，也不会调用 provider。路径可
    写性用父目录检查表示"setup 是否可恢复"，避免为了诊断而写探针文件。
    """

    rows: list[tuple[str, str, str, str]] = []
    rows.append((
        "ok" if cfg.vault.root.exists() else "warn",
        "vault.root",
        str(cfg.vault.root),
        "mindforge init --vault <path>" if not cfg.vault.root.exists() else "",
    ))
    for label, path in (
        ("cards dir", cfg.vault.cards_path),
        ("state parent", cfg.state.state_path.parent),
        ("index parent", (cfg.state.workdir / "index")),
        ("backup parent", (cfg.state.workdir / "backups")),
    ):
        parent = path if path.exists() else path.parent
        rows.append((
            "ok" if parent.exists() else "warn",
            label,
            str(path),
            "mindforge init --interactive" if not parent.exists() else "",
        ))
    profile_ok = cfg.llm.active_profile in cfg.llm.profiles
    rows.append((
        "ok" if profile_ok else "error",
        "active_profile",
        cfg.llm.active_profile,
        "edit mindforge.yaml llm.active_profile" if not profile_ok else "",
    ))
    try:
        from ..assets_runtime import bundled_text

        bundled_text("configs", "mindforge.yaml")
        bundled_text("templates", "knowledge_card.md.j2")
        rows.append(("ok", "package assets", "configs/templates readable", ""))
    except Exception as e:  # noqa: BLE001
        rows.append(("error", "package assets", f"{type(e).__name__}: {e}", "reinstall MindForge"))
    rows.append(("ok", "env policy", "config UX does not read .env", ""))
    rows.append(("ok", "llm policy", "setup defaults to fake / no real LLM call", ""))
    return rows


def doctor_recovery_checks(cfg: MindForgeConfig) -> dict[str, list[tuple[str, str, str]]]:
    """doctor plus 的本地恢复检查。

    中文学习型说明：这些检查只读路径存在性、JSON/YAML 可读性和 package
    asset 可访问性；不会读取 ``.env``，不会调用 LLM，也不会写 vault 或
    Obsidian notes。``actions`` 列表的优先级语义在 next_suggestions /
    cli sort 中共用：``try_first`` < ``critical`` < ``recommended`` <
    ``info``。
    """

    from ..checkpoint import Checkpoint

    rows: list[tuple[str, str, str]] = []
    actions: list[tuple[str, str]] = []

    state_path = cfg.state.state_path
    if state_path.exists():
        try:
            Checkpoint.load(state_path, backup=False)
            rows.append(("ok", "state.json", f"readable · {state_path}"))
        except Exception as e:  # noqa: BLE001
            rows.append(("error", "state.json", f"unreadable · {type(e).__name__}: {e}"))
            actions.append((
                "critical",
                "state.json 读取失败 → 先备份 .mindforge，再检查 JSON 或从 state.json.bak 恢复",
            ))
    else:
        rows.append(("warn", "state.json", f"missing · {state_path}"))
        actions.append(("recommended", "state.json 缺失 → 运行: mindforge scan"))

    cards_dir = cfg.vault.cards_path
    rows.append(("ok" if cards_dir.is_dir() else "error", "cards dir", str(cards_dir)))
    if not cards_dir.is_dir():
        actions.append(("critical", "Knowledge Cards 目录缺失 → 运行: mindforge init --interactive"))
        # 用户友好性 polish：在要求 init 之前先告诉新用户有零配置 demo 可选；
        # 这是 ``mindforge demo`` 60 秒 tour 的入口提示，不替换 init 的 critical 性。
        # UX completion: 用 try_first 优先级保证 demo 在 doctor Action items 列表
        # 第一行出现，让新用户在被多条 critical 提示劝退之前先看到安全演示路径。
        actions.append((
            "try_first",
            "想先跑零配置 tour（无需 vault / API key / 网络）→ 运行: mindforge demo",
        ))

    index_path = cfg.state.workdir / "index" / "bm25.json"
    rows.append((
        "ok" if index_path.exists() else "warn",
        "bm25 index",
        str(index_path) if index_path.exists() else "missing",
    ))
    if not index_path.exists():
        actions.append(("recommended", "BM25 索引缺失 → 运行: mindforge index rebuild"))

    try:
        from ..assets_runtime import bundled_text

        bundled_text("configs", "mindforge.yaml")
        bundled_text("templates", "knowledge_card.md.j2")
        rows.append(("ok", "package assets", "configs/templates readable"))
    except Exception as e:  # noqa: BLE001
        rows.append(("error", "package assets", f"unreadable · {type(e).__name__}: {e}"))
        actions.append(("critical", "package assets 不可读 → 检查安装包或重新安装 MindForge"))

    demo = Path("examples/demo-vault")
    rows.append((
        "ok" if demo.is_dir() else "info",
        "demo vault",
        str(demo) if demo.is_dir() else "not in current cwd",
    ))
    try:
        from ..cards import filter_cards, iter_cards

        approved = filter_cards(
            iter_cards(cfg.vault.root, cfg.vault.cards_dir).cards,
            status="human_approved",
        )
        # 只统计未来 7 天的复习总数：避免把 ``_build_review_schedule_export``
        # 这种重逻辑（属于 cli.py review 命令）拖进 doctor service 边界。
        now = datetime.now().astimezone()
        horizon = now + timedelta(days=7)
        total = 0
        for card in approved:
            ra = card.review_after
            if ra is None:
                continue
            ra = ra if ra.tzinfo else ra.replace(tzinfo=now.tzinfo)
            if ra <= horizon:
                total += 1
        rows.append((
            "ok" if total else "info",
            "review schedule",
            f"{total} item(s) in next 7 days",
        ))
        if not total:
            actions.append((
                "info",
                "未来 7 天无复习任务 → 运行: mindforge review weekly 查看整体状态",
            ))
    except Exception as e:  # noqa: BLE001
        rows.append(("warn", "review schedule", f"unavailable · {type(e).__name__}: {e}"))
    return {"rows": rows, "actions": actions}


def doctor_paths(cfg: MindForgeConfig) -> list[tuple[str, str]]:
    """声明 doctor 命令对外承诺的"会读 / 会写 / 永不写"路径列表。

    它是一份契约，不做任何 IO，只把 cfg 渲染成可解释的字符串。
    """

    return [
        ("reads inbox", str(cfg.vault.inbox_path)),
        ("reads cards", str(cfg.vault.cards_path)),
        ("reads state", str(cfg.state.state_path)),
        ("writes state", str(cfg.state.state_path)),
        ("writes runs", str(cfg.state.runs_path)),
        ("writes index", str(cfg.state.workdir / "index" / "bm25.json")),
        ("writes backups", str(cfg.state.workdir / "backups")),
        ("dry-run only", "obsidian stage defaults to --dry-run"),
        (
            "never writes",
            "formal Obsidian notes unless user explicitly writes staging/review",
        ),
    ]


def compute_doctor_hints(
    cfg: MindForgeConfig,
    recovery_actions: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """聚合 doctor 的 actionable hints。

    中文学习型说明：
    - 历史上这段逻辑直接堆在 ``doctor()`` 命令体中（200+ 行），混合了
      cards 统计、BM25 状态、复习 overdue/due 等业务推断。它们与 console
      渲染无关，属于 service 层职责。
    - 此函数 *只读* 卡片 frontmatter 与 BM25 索引的元信息；不会自动产生
      ``human_approved``，不会触发任何 LLM/网络。
    - 返回值仍是 ``[(priority, message)]``，由 ``cli.doctor`` 排序后交给
      presenter 渲染，保证向后兼容。
    """

    hints: list[tuple[str, str]] = list(recovery_actions)
    cards_dir = cfg.vault.cards_path
    if not cards_dir.exists():
        hints.append(("critical", "vault 目录缺失 → 运行: mindforge init --interactive"))
    if cfg.llm.active_profile not in cfg.llm.profiles:
        hints.append((
            "critical",
            f"active_profile={cfg.llm.active_profile!r} 未在 llm.profiles 中定义 → 检查 mindforge.yaml",
        ))
    elif cfg.llm.active_profile != "fake":
        hints.append((
            "critical",
            "active_profile 非 fake：真实跑 process 前请先 `mindforge llm ping` 校验环境变量",
        ))
    if cards_dir.exists():
        try:
            from .. import lexical_index as _lx
            from ..cards import iter_cards as _iter

            res = _iter(cfg.vault.root, cfg.vault.cards_dir)
            n_drafts = sum(1 for c in res.cards if c.status == "ai_draft")
            n_approved = sum(1 for c in res.cards if c.status == "human_approved")
            if not res.cards:
                hints.append((
                    "recommended",
                    "尚无 Knowledge Cards → 运行: mindforge scan && mindforge process",
                ))
            elif n_drafts > 0:
                hints.append((
                    "recommended",
                    f"{n_drafts} 张 ai_draft 待人工审核 → 运行: mindforge approve list",
                ))
            # v0.3.2: 没有 human_approved 但有 ai_draft → 提示 recall --include-drafts
            if res.cards and n_approved == 0 and n_drafts > 0:
                hints.append((
                    "info",
                    "暂无 human_approved 卡片 → 检索时加: mindforge recall --include-drafts",
                ))
            # v0.4.1: 检测 overdue / due 复习并给出建议
            if n_approved > 0:
                _now_doc = datetime.now().astimezone()
                _overdue = 0
                _due_7 = 0
                for _c in res.cards:
                    if _c.status != "human_approved" or _c.review_after is None:
                        continue
                    _ra = (
                        _c.review_after
                        if _c.review_after.tzinfo
                        else _c.review_after.replace(tzinfo=_now_doc.tzinfo)
                    )
                    if _ra <= _now_doc:
                        _overdue += 1
                    elif _ra <= _now_doc + timedelta(days=7):
                        _due_7 += 1
                if _overdue:
                    hints.append((
                        "recommended",
                        f"{_overdue} 张卡片已 overdue → 运行: mindforge review backlog",
                    ))
                elif _due_7:
                    hints.append((
                        "recommended",
                        f"{_due_7} 张卡片本周内到期 → 运行: mindforge review schedule --days 7",
                    ))
            # v0.3.1: BM25 索引检查（缺失 / 配置漂移 / mtime 漂移）
            idx_path = _lx.default_index_path(cfg.state.workdir)  # type: ignore[attr-defined]
            if not idx_path.exists():
                if res.cards:
                    hints.append((
                        "recommended",
                        "BM25 索引缺失 → 运行: mindforge index rebuild",
                    ))
            else:
                try:
                    idx = _lx.BM25Index.load(idx_path)
                    fw_cur = _lx.resolve_field_weights(cfg.search.bm25.fields)
                    cur_h = _lx.compute_config_hash(
                        field_weights=fw_cur,
                        k1=cfg.search.bm25.k1,
                        b=cfg.search.bm25.b,
                    )
                    if idx.config_hash and idx.config_hash != cur_h:
                        hints.append((
                            "recommended",
                            "BM25 索引与 search 配置不一致 → 运行: mindforge index rebuild",
                        ))
                    else:
                        diff = _lx.diff_index(idx, res.cards)
                        if not diff.fresh:
                            hints.append((
                                "recommended",
                                "BM25 索引 stale（卡片有变更） → 运行: mindforge index rebuild",
                            ))
                except Exception:  # noqa: BLE001
                    hints.append((
                        "recommended",
                        "BM25 索引读取失败 → 运行: mindforge index rebuild",
                    ))
        except Exception:  # noqa: BLE001
            pass
    return hints
