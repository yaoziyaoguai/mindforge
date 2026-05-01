"""Phase 1 — CLI Product Shape Completion: 端到端闭环 dogfood smoke。

本测试不是为了"再测一遍 process pipeline"，而是 Phase 1 的**叙述脊柱**：
用一份真实形态的 Cubox markdown 样本，把 ``docs/ROADMAP.md`` 中"9 步闭环"
里的核心 5 步串起来跑一次，验证 Bundle A (KnowledgeStrategy seam) 与
Bundle B (ApprovalDecision seam) 在真实路径上协同工作。

闭环路径
--------

.. code::

   Cubox sample fixture (.md)                   # 一等 source（不接真实 API）
        │
        ▼
   CuboxMarkdownAdapter.parse()                 # 一等 adapter
        │
        ▼
   SourceDocument                               # 协议层；processor 只依赖此
        │
        ▼
   build_strategy(DEFAULT_STRATEGY_NAME, ctx)   # Bundle A：策略 seam
        │  (内部走 five-stage Pipeline + fake provider)
        ▼
   ai_draft Knowledge Card (Markdown)           # 写到 sample workspace
        │
        ▼
   apply_decision(REQUEST(card, APPROVE))       # Bundle B：决定 seam
        │
        ▼
   human_approved Knowledge Card                # frontmatter 显式晋升

为什么用一条端到端测试而不是新增 workspace seam 模块
--------------------------------------------------

Bundle C 审计发现 obsidian-centered workspace（``obsidian.py`` /
``obsidian_workflow.py`` / ``writer.py``）与 Cubox 一等 adapter
（``sources/cubox_markdown.py``）**已是 production-grade**。再为"看起来
架构化"造一个 workspace seam 模块属于机械搬运。Phase 1 真正缺的是把
两条新 seam（strategy + decision）与一等 adapter（Cubox）拼到一条
**可执行、可断言、可作为活文档**的端到端路径上。

安全边界（与 Bundle C+D 用户脚本对齐）
--------------------------------------

- 不读 ``.env``、不联网、不接真实 Cubox API、不调真实 LLM。
- sample workspace 完全在 ``tmp_path`` 下，与真实 vault 完全隔离。
- 仅 fake provider；``ai_draft → human_approved`` 必须通过显式
  ``apply_decision(APPROVE)``，绝无自动晋升。
- Workspace 仅含人类可读 Markdown；运行期 state/runs/cache 必须落在
  ``.mindforge/`` 之外，不污染 ``vault/``。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mindforge.approver import (
    ApprovalDecision,
    ApprovalRequest,
    apply_decision,
)
from mindforge.cli import app
from mindforge.config import load_mindforge_config
from mindforge.sources.cubox_markdown import CuboxMarkdownAdapter
from mindforge.sources.registry import _BUILTIN_ADAPTERS

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts"
TEMPLATE_PATH = REPO_ROOT / "templates" / "knowledge_card.md.j2"
TRACKS_PATH = REPO_ROOT / "configs" / "learning_tracks.yaml"
CUBOX_SAMPLE = REPO_ROOT / "tests" / "fixtures" / "sample_cubox_note.md"

runner = CliRunner()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _build_cubox_sample_workspace(tmp_path: Path) -> tuple[Path, Path, Path]:
    """构造与 Cubox 一等 adapter 配套的 sample workspace + config。

    与既有 ``test_process_e2e._build_vault_with_fake_llm`` 形态保持一致，
    差别仅在：source registry 启用 ``cubox_markdown``，inbox 放真实形态的
    Cubox markdown 样本。fake provider 默认安全路径完全保留。
    """

    vault = tmp_path / "vault"
    inbox_cubox = vault / "00-Inbox" / "Cubox"
    inbox_cubox.mkdir(parents=True)
    (vault / "20-Knowledge-Cards").mkdir(parents=True)

    cubox_file = inbox_cubox / "sample.md"
    shutil.copyfile(CUBOX_SAMPLE, cubox_file)

    cfg = {
        "version": 0.1,
        "vault": {
            "root": str(vault),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {
            "enabled": ["cubox_markdown"],
            "registry": {
                "cubox_markdown": {
                    "adapter": "CuboxMarkdownAdapter",
                    "inbox_subdir": "Cubox",
                    "file_glob": "*.md",
                    "enabled": True,
                },
            },
        },
        "state": {
            "workdir": str(tmp_path / ".mindforge"),
            "state_file": "state.json",
            "runs_dir": "runs",
            "index_file": "index.jsonl",
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {
                "fake": {
                    "triage": "f1",
                    "distill": "f1",
                    "link_suggestion": "f1",
                    "review_questions": "f1",
                    "action_extraction": "f1",
                }
            },
            "models": {
                "f1": {
                    "provider": "fake-local",
                    "type": "fake",
                    "base_url": "fake://",
                    "model": "fake-1",
                    "timeout_seconds": 5,
                    "max_retries": 0,
                }
            },
        },
        "prompts": {
            "triage_version": "v1",
            "distill_version": "v1",
            "link_suggestion_version": "v1",
            "review_questions_version": "v1",
            "action_extraction_version": "v1",
        },
        "logging": {"level": "INFO", "file": str(tmp_path / "mf.log")},
    }
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir()
    cfg_path = cfg_dir / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return cfg_path, vault, cubox_file


def _process_args(cfg_path: Path) -> list[str]:
    return [
        "process",
        "--config",
        str(cfg_path),
        "--prompts-dir",
        str(PROMPTS_DIR),
        "--tracks",
        str(TRACKS_PATH),
        "--template",
        str(TEMPLATE_PATH),
    ]


# ---------------------------------------------------------------------------
# 1. Adapter contract：Cubox sample → SourceDocument，不污染 processor
# ---------------------------------------------------------------------------


def test_cubox_sample_parses_to_source_document_via_registry() -> None:
    """``CuboxMarkdownAdapter`` 必须能把样本解析为合法 ``SourceDocument``。

    用 ``_BUILTIN_ADAPTERS`` 取类（与 ``build_active_adapters`` 内部一致）
    再实例化，保证 Phase 1 一等 adapter 的注册路径仍是公开契约。
    """

    adapter_cls = _BUILTIN_ADAPTERS["CuboxMarkdownAdapter"]
    adapter = adapter_cls()
    assert isinstance(adapter, CuboxMarkdownAdapter)
    assert adapter.source_type == "cubox_markdown"

    doc = adapter.load(str(CUBOX_SAMPLE))
    # SourceDocument 的强契约字段必填且非空
    assert doc.source_id
    assert doc.source_type == "cubox_markdown"
    # 注：adapter_name 是 Scanner 层填充的，adapter.load() 单独调不一定填
    assert doc.content_hash
    # Cubox 特有内容（highlights）落地为协议层的 highlights 列表
    assert any("ReAct" in (h.text or "") for h in doc.highlights), (
        "Cubox highlights 解析丢失；下游 processor 依赖 SourceDocument.highlights，"
        "不应被 adapter 私有字段隐藏"
    )


# ---------------------------------------------------------------------------
# 2. End-to-end Phase 1 closed loop
# ---------------------------------------------------------------------------


def test_phase1_cubox_closed_loop_produces_human_approved_card(tmp_path: Path) -> None:
    """Phase 1 闭环：Cubox 样本 → strategy seam → ai_draft → APPROVE → human_approved。

    本测试是 ROADMAP "9 步闭环"的可执行规约。任何一处退化（adapter 改契约、
    strategy seam 被绕过、apply_decision dispatcher 漏接 APPROVE、writer
    把 runtime state 写进 vault）都会立刻红灯。
    """

    cfg_path, vault, src_file = _build_cubox_sample_workspace(tmp_path)
    src_before = src_file.read_text("utf-8")

    # ---- step ①②③④：Cubox → SourceDocument → strategy → ai_draft ----
    # 通过 CLI 走真实路径；CLI 内部使用 build_strategy(DEFAULT_STRATEGY_NAME, ...)
    # （Bundle A），这是把 Bundle A seam 拉进 Phase 1 端到端断言的关键。
    r = runner.invoke(app, _process_args(cfg_path))
    assert r.exit_code == 0, r.output
    assert "processed=1" in r.output

    cards = list((vault / "20-Knowledge-Cards").rglob("*.md"))
    assert len(cards) == 1, f"期望 1 张 ai_draft 卡片，实得 {cards}"
    card_path = cards[0]
    card_text = card_path.read_text("utf-8")

    # Cubox 一等 adapter 的来源信息必须保留到 frontmatter，便于人工溯源
    assert "status: ai_draft" in card_text
    assert "source_type: cubox_markdown" in card_text
    assert "adapter_name: CuboxMarkdownAdapter" in card_text

    # 原始 Cubox 文件 100% 不被改写（00-Inbox 只读契约）
    assert src_file.read_text("utf-8") == src_before

    # ---- step ⑤⑥⑦：apply_decision(APPROVE) → human_approved ----
    cfg = load_mindforge_config(cfg_path)
    request = ApprovalRequest(card_path=card_path, decision=ApprovalDecision.APPROVE)
    effect = apply_decision(request, cfg=cfg)

    assert effect.kind == "approved"
    assert effect.prev_status == "ai_draft"
    assert effect.new_status == "human_approved"
    after = card_path.read_text("utf-8")
    assert "status: human_approved" in after
    assert "approval_method: explicit_cli" in after


# ---------------------------------------------------------------------------
# 3. Workspace 安全边界：vault 只装人类可读知识资产
# ---------------------------------------------------------------------------


_FORBIDDEN_VAULT_NAMES = {
    ".mindforge",
    "runs",
    "state",
    "telemetry",
    "index",
    "cache",
    "logs",
}


def test_phase1_sample_vault_contains_only_human_readable_artifacts(
    tmp_path: Path,
) -> None:
    """Obsidian-centered workspace 不允许混入运行期派生数据。

    与 ``safety_policy.OBSIDIAN_MANIFEST_SAFETY_LABELS`` 形成双层护栏：
    safety_policy 是策略，本测试是端到端事实快照。任何时候有人把 state.json /
    runs/*.jsonl / SQLite / vector index 写进 vault，本测试立刻爆炸。
    """

    cfg_path, vault, _src = _build_cubox_sample_workspace(tmp_path)
    r = runner.invoke(app, _process_args(cfg_path))
    assert r.exit_code == 0, r.output

    # 运行期目录必须落在 cfg.state.workdir（tmp_path/.mindforge），不进 vault
    assert (tmp_path / ".mindforge").is_dir()

    leaked: list[Path] = []
    for entry in vault.rglob("*"):
        if entry.name in _FORBIDDEN_VAULT_NAMES:
            leaked.append(entry)
    assert not leaked, (
        f"sample workspace 出现运行期派生路径：{leaked}；"
        f"Obsidian-centered workspace 必须只装人类可读 markdown"
    )

    # 所有非隐藏文件必须是 .md（除 README）
    for f in vault.rglob("*"):
        if not f.is_file() or f.name.startswith("."):
            continue
        assert f.suffix in {".md", ""}, (
            f"vault 出现非人类可读文件：{f}（仅允许 .md / README）"
        )


# ---------------------------------------------------------------------------
# 4. 不自动 approve：fake provider 不能跨过 ai_draft 边界
# ---------------------------------------------------------------------------


def test_phase1_fake_provider_does_not_auto_promote_to_human_approved(
    tmp_path: Path,
) -> None:
    """``mindforge process`` 在任何 fake provider 路径上都只能产出 ai_draft。

    这是反 AI 污染闸门的端到端兜底：即使整个 Phase 1 闭环跑通，AI 自身
    永远碰不到 human_approved；只有显式 ``apply_decision(APPROVE)`` 才能晋升。
    """

    cfg_path, vault, _src = _build_cubox_sample_workspace(tmp_path)
    r = runner.invoke(app, _process_args(cfg_path))
    assert r.exit_code == 0, r.output

    cards = list((vault / "20-Knowledge-Cards").rglob("*.md"))
    assert len(cards) == 1
    card_text = cards[0].read_text("utf-8")
    assert "status: ai_draft" in card_text
    assert "status: human_approved" not in card_text


# ---------------------------------------------------------------------------
# 5. 非 APPROVE decisions 在端到端路径上也必须显式爆炸（兜底回归）
# ---------------------------------------------------------------------------


def test_phase1_non_approve_decisions_still_raise_on_real_card(tmp_path: Path) -> None:
    """端到端拿到一张真实 ai_draft 卡片后，6 个未实现 decision 仍必须 raise。

    Bundle B 的单元测试用合成 fixture 验证；本测试用 Phase 1 闭环产出的
    真实卡片再验一次，避免"单元测试通过但端到端被某个 happy-path 短路"。
    """

    from mindforge.approver import NotImplementedDecisionError

    cfg_path, vault, _src = _build_cubox_sample_workspace(tmp_path)
    r = runner.invoke(app, _process_args(cfg_path))
    assert r.exit_code == 0, r.output

    cards = list((vault / "20-Knowledge-Cards").rglob("*.md"))
    card_path = cards[0]
    cfg = load_mindforge_config(cfg_path)

    for decision in (
        ApprovalDecision.REJECT,
        ApprovalDecision.DEFER,
        ApprovalDecision.APPEND_AS_EVIDENCE,
        ApprovalDecision.LINK_TO_EXISTING,
        ApprovalDecision.MERGE_CANDIDATE,
        ApprovalDecision.SPLIT,
    ):
        with pytest.raises(NotImplementedDecisionError):
            apply_decision(
                ApprovalRequest(card_path=card_path, decision=decision),
                cfg=cfg,
            )
        # 卡片仍是 ai_draft，未被错误副作用篡改
        assert "status: ai_draft" in card_path.read_text("utf-8")
