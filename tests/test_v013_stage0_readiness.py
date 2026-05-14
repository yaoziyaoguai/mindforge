"""Local readiness assertion tests.

历史 v0.13 文档已经合并进 canonical docs；本文件继续守护同一组安全
承诺，但不再要求旧 milestone 文档存在。

设计原则
========
- 仅做 docs / fixture 字符串子串断言，零 import-time 副作用；
- 不 import production runtime；
- 不构造 LLM / 不读 dotenv / 不写 vault；
- 中文学习型注释解释每条断言为什么存在。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


_README = Path("README.md")
_FIXTURE_DIR = Path("examples/custom-strategies")
_FIXTURE_YAML = _FIXTURE_DIR / "user_concept_review.yaml"
_FIXTURE_README = _FIXTURE_DIR / "README.md"


# 中文学习型注释：readiness 文档的关键承诺以"短语"形式被 PR 审计；
# 一旦某条承诺在重写中被无意删除，子串断言会指名是哪条，便于 PR 反查。
_READINESS_REQUIRED_PHRASES: tuple[str, ...] = (
    "Keep API keys in the local secret store",
    "No secret file or real model call is used without explicit opt-in",
    "External account ingestion",
    "No formal Obsidian notes are written",
    "No automatic approve",
    "Custom executable strategy runtime",
    "no tag, no force push",
    "human decision gate",
    "local-first privacy contract",
)


def test_v013_stage0_readiness_doc_exists() -> None:
    """canonical local workflow 文档存在。"""

    assert _README.exists(), f"missing {_README}"


@pytest.mark.parametrize("phrase", _READINESS_REQUIRED_PHRASES)
def test_v013_stage0_readiness_doc_pins_safety_promise(phrase: str) -> None:
    """每条安全承诺都在文档里出现（大小写不敏感）。"""

    text = _README.read_text(encoding="utf-8").lower()
    assert phrase.lower() in text, (
        f"canonical docs 缺安全承诺关键字: {phrase!r}"
    )


def test_v013_stage0_readiness_doc_links_current_safety_docs() -> None:
    """Usage 必须让读者能找到 safety/roadmap 边界。"""

    text = _README.read_text(encoding="utf-8")
    assert "External account ingestion" in text
    assert "human_approved" in text


def test_v013_stage0_future_gates_still_present() -> None:
    """Roadmap 必须继续列出 real/RAG/approval 这些 future gates。"""

    text = _README.read_text(encoding="utf-8")
    for token in ("External account ingestion", "Real Obsidian", "RAG / embedding", "Approval UX"):
        assert token in text


def test_v013_stage0_synthetic_custom_strategy_fixture_exists() -> None:
    """非敏感 fixture 必须落地，否则 Stage 0 文档第 3.1 节是空头支票。"""

    assert _FIXTURE_DIR.is_dir()
    assert _FIXTURE_YAML.exists()
    assert _FIXTURE_README.exists()


def test_v013_stage0_synthetic_fixture_is_preview_only() -> None:
    """fixture 必须 status=preview / safety_policy=ai_draft_only —— 防止
    Stage 1+ 谁悄悄把示例改成 implemented + auto_approve。"""

    data = yaml.safe_load(_FIXTURE_YAML.read_text(encoding="utf-8"))
    assert data["status"] == "preview", data
    assert data["safety_policy"] == "ai_draft_only", data
    assert data["strategy_id"] == "user_concept_review", data


def test_v013_stage0_fixture_readme_warns_review_only() -> None:
    """fixture README 必须明确 review-only / 不调真实 LLM / 不写 vault。"""

    text = _FIXTURE_README.read_text(encoding="utf-8").lower()
    for phrase in (
        "review-only",
        "never causes a real llm",
        "never reads `.env`",
        "never writes any obsidian vault",
        "never auto-approves",
    ):
        assert phrase in text, (
            f"examples/custom-strategies/README.md 缺 review-only 关键短语: "
            f"{phrase!r}"
        )


def test_v013_stage0_does_not_introduce_production_runtime_change() -> None:
    """Stage 0 的承诺之一是不动 production；这条用 fixture 的"形状"
    再次反向验证：fixture 里**没有**任何运行期触点字段（如 python_callable
    / shell_command / auto_approve），因此即便被加载也只能停在 preview。
    """

    data = yaml.safe_load(_FIXTURE_YAML.read_text(encoding="utf-8"))
    forbidden = {
        "python_callable",
        "shell_command",
        "auto_approve",
        "real_provider_opt_in_force",
        "vault_write",
    }
    overlap = forbidden.intersection(data.keys())
    assert not overlap, f"synthetic fixture 含禁忌字段: {overlap}"
