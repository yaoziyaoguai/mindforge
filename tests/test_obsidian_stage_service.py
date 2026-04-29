"""v0.7.9 — Obsidian staged export service 边界测试。

学习要点：CLI 负责 Typer/Rich 展示，service helper 只产出结构化路径、manifest
和 preflight 结果。测试直接覆盖 service 层，避免未来拆 CLI 时只能靠输出字符串
判断安全边界。
"""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from pathlib import Path

import yaml

from mindforge.config import load_mindforge_config
from mindforge.obsidian import obsidian_preflight
from mindforge.obsidian_stage import (
    build_obsidian_next_plan,
    build_preflight_display_plan,
    build_staged_diff_preview_plan,
    build_staged_manifest_payload,
    plan_staged_export,
    resolve_obsidian_source_for_preview,
    safe_relative_to,
    unique_export_path,
)
from mindforge.sources.obsidian_vault import ObsidianVaultSourceAdapter


def _make_service_vault(tmp_path: Path) -> tuple[Path, Path, Path]:
    vault = tmp_path / "obsidian-vault"
    (vault / "02-Knowledge").mkdir(parents=True)
    note = vault / "02-Knowledge" / "Agent Runtime.md"
    note.write_text("# Agent Runtime\n\nLocal only note.\n", encoding="utf-8")
    cfg_payload = {
        "version": 0.7,
        "vault": {
            "root": str(tmp_path / "mindforge-vault"),
            "inbox_root": "00-Inbox",
            "cards_dir": "20-Knowledge-Cards",
            "archive_dir": "90-Archive/Skipped",
        },
        "sources": {"enabled": [], "registry": {}},
        "state": {
            "workdir": str(tmp_path / ".mindforge"),
            "state_file": "state.json",
            "runs_dir": "runs",
            "index_file": "index.jsonl",
            "backup_state": True,
        },
        "obsidian": {
            "vault_path": str(vault),
            "staging_dir": "90-System/MindForge/Staging",
            "review_dir": "90-System/MindForge/Review",
            "include_dirs": ["02-Knowledge"],
            "exclude_dirs": [".obsidian", ".git", ".mindforge"],
            "read_only": True,
        },
        "triage": {"value_score_threshold": 5, "default_track": "unrouted"},
        "llm": {
            "active_profile": "fake",
            "profiles": {
                "fake": {
                    "triage": "fake_alias",
                    "distill": "fake_alias",
                    "link_suggestion": "fake_alias",
                    "review_questions": "fake_alias",
                    "action_extraction": "fake_alias",
                }
            },
            "models": {"fake_alias": {"provider": "fake", "type": "fake", "model": "fake"}},
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
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg_payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return vault, note, cfg_path


def _write_service_manifest(tmp_path: Path, *, output_dir: Path | None = None) -> tuple[Path, Path, Path, Path]:
    vault, note, cfg_path = _make_service_vault(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    doc = ObsidianVaultSourceAdapter(vault).load(str(note))
    plan = plan_staged_export(cfg=cfg, vault_root=vault, doc=doc, output_dir=output_dir or tmp_path / "exports")
    plan.export_dir.mkdir(parents=True, exist_ok=True)
    plan.target_path.write_text("# staged candidate\n", encoding="utf-8")
    payload = build_staged_manifest_payload(
        plan=plan,
        source_path=note,
        doc=doc,
        timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    plan.manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return vault, note, plan.target_path, plan.manifest_path


def _patch_manifest(manifest: Path, **updates) -> None:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    for key, value in updates.items():
        if key.startswith("write_gate__"):
            payload.setdefault("write_gate", {})[key.removeprefix("write_gate__")] = value
        elif value is None:
            payload.pop(key, None)
        else:
            payload[key] = value
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_staged_export_plan_builds_manifest_without_formal_note_write(tmp_path: Path) -> None:
    """service 只生成 staged export 证据链，不创建/覆盖正式 Obsidian note。"""
    vault, note, cfg_path = _make_service_vault(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    doc = ObsidianVaultSourceAdapter(vault).load(str(note))

    plan = plan_staged_export(cfg=cfg, vault_root=vault, doc=doc, output_dir=tmp_path / "exports")
    payload = build_staged_manifest_payload(
        plan=plan,
        source_path=note,
        doc=doc,
        timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert payload["source_note"] == "02-Knowledge/Agent Runtime.md"
    assert payload["action"] == "staged-export-create"
    assert payload["staged_markdown"].endswith("Agent-Runtime.md")
    assert payload["safety"]["no_formal_obsidian_note_write"] is True
    assert payload["safety"]["no_env_read"] is True
    assert payload["write_gate"]["writes_formal_notes_now"] is False
    assert safe_relative_to(plan.proposed_target, vault) == "90-System/MindForge/Review/Agent-Runtime.md"
    assert not plan.proposed_target.exists()
    assert note.read_text(encoding="utf-8") == "# Agent Runtime\n\nLocal only note.\n"


def test_stage_service_identifies_source_outside_vault(tmp_path: Path) -> None:
    """source 解析可兼容 cwd，但 vault 边界必须由 service helper 明确识别。"""
    vault, _note, _cfg_path = _make_service_vault(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("# outside\n", encoding="utf-8")

    resolved = resolve_obsidian_source_for_preview(outside, vault)

    assert resolved == outside.resolve()
    assert safe_relative_to(resolved, vault) is None


def test_staged_export_plan_uses_unique_path_and_reports_formal_conflict(tmp_path: Path) -> None:
    """同名 staged 文件不被覆盖；正式 vault 同名 note 只作为人工检查冲突返回。"""
    vault, note, cfg_path = _make_service_vault(tmp_path)
    cfg = load_mindforge_config(cfg_path)
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    existing_staged = export_dir / "Agent-Runtime.md"
    existing_staged.write_text("already inspected\n", encoding="utf-8")
    formal = vault / "02-Knowledge" / "Agent-Runtime-2.md"
    formal.write_text("human note stays\n", encoding="utf-8")
    doc = ObsidianVaultSourceAdapter(vault).load(str(note))

    plan = plan_staged_export(cfg=cfg, vault_root=vault, doc=doc, output_dir=export_dir)

    assert plan.target_path == export_dir / "Agent-Runtime-2.md"
    assert plan.action == "staged-export-create-unique"
    assert plan.formal_conflicts == (formal,)
    assert existing_staged.read_text(encoding="utf-8") == "already inspected\n"
    assert formal.read_text(encoding="utf-8") == "human note stays\n"
    assert unique_export_path(existing_staged) == export_dir / "Agent-Runtime-2.md"


def test_preflight_service_passes_complete_manifest(tmp_path: Path) -> None:
    """完整 manifest 返回 PASS，且 preflight 不写 proposed target。"""
    vault, note, _exported, manifest = _write_service_manifest(tmp_path)

    result = obsidian_preflight(vault_root=vault, manifest_path=manifest, default_staged_root=tmp_path / "exports")

    assert result.status == "PASS"
    assert result.blocked == []
    assert result.proposed_target is not None
    assert not result.proposed_target.exists()
    assert note.read_text(encoding="utf-8") == "# Agent Runtime\n\nLocal only note.\n"


def test_preflight_service_blocks_missing_manifest_field_and_markdown(tmp_path: Path) -> None:
    """manifest 缺字段或 staged markdown 消失时必须 BLOCKED，而不是猜测用户意图。"""
    vault, _note, exported, manifest = _write_service_manifest(tmp_path)
    _patch_manifest(manifest, action=None)

    missing_field = obsidian_preflight(vault_root=vault, manifest_path=manifest, default_staged_root=tmp_path / "exports")
    assert missing_field.status == "BLOCKED"
    assert "manifest 缺少 action" in missing_field.blocked

    _patch_manifest(manifest, action="staged-export-create")
    exported.unlink()
    missing_markdown = obsidian_preflight(vault_root=vault, manifest_path=manifest, default_staged_root=tmp_path / "exports")
    assert missing_markdown.status == "BLOCKED"
    assert any("staged markdown 不存在" in reason for reason in missing_markdown.blocked)


def test_preflight_service_blocks_path_safety_and_warns_existing_target(tmp_path: Path) -> None:
    """path safety 是 service 层规则：vault 外 target 阻断，已有 target 只 warning 不覆盖。"""
    vault, _note, _exported, manifest = _write_service_manifest(tmp_path)
    _patch_manifest(manifest, write_gate__proposed_target=str(tmp_path / "outside.md"))

    outside = obsidian_preflight(vault_root=vault, manifest_path=manifest, default_staged_root=tmp_path / "exports")
    assert outside.status == "BLOCKED"
    assert any("proposed target 不在 Obsidian vault 内" in reason for reason in outside.blocked)

    target = vault / "90-System" / "MindForge" / "Review" / "Agent-Runtime.md"
    target.parent.mkdir(parents=True)
    target.write_text("human review stays\n", encoding="utf-8")
    _patch_manifest(manifest, write_gate__proposed_target=str(target))
    warning = obsidian_preflight(vault_root=vault, manifest_path=manifest, default_staged_root=tmp_path / "exports")
    assert warning.status == "WARNING"
    assert any("不会覆盖" in reason for reason in warning.warnings)
    assert target.read_text(encoding="utf-8") == "human review stays\n"


def test_preflight_service_blocks_forbidden_and_unsafe_staged_output(tmp_path: Path) -> None:
    """runtime/cache/index/logs 等机器派生层不能进入 staged export 证据链。"""
    vault, _note, _exported, manifest = _write_service_manifest(tmp_path, output_dir=tmp_path / "runtime" / "exports")

    forbidden = obsidian_preflight(
        vault_root=vault,
        manifest_path=manifest,
        default_staged_root=tmp_path / "runtime" / "exports",
    )
    assert forbidden.status == "BLOCKED"
    assert any("禁止的机器派生层路径" in reason for reason in forbidden.blocked)

    _patch_manifest(manifest, staged_output_policy="default-state-workdir", staged_export_dir=str(tmp_path / "safe"))
    unsafe_root = obsidian_preflight(vault_root=vault, manifest_path=manifest, default_staged_root=tmp_path / "safe")
    assert unsafe_root.status == "BLOCKED"
    assert any("default staged output 必须位于" in reason for reason in unsafe_root.blocked)


def test_stage_service_does_not_read_env_call_llm_upload_or_write_notes(tmp_path: Path, monkeypatch) -> None:
    """service helper 不触发外部边界；正式 notes hash 在 plan/preflight 前后不变。"""
    vault, note, _exported, manifest = _write_service_manifest(tmp_path)
    before = note.read_text(encoding="utf-8")
    (tmp_path / ".env").write_text("MINDFORGE_LLM_API_KEY=secret\n", encoding="utf-8")

    def _blocked(*_args, **_kwargs):  # pragma: no cover
        raise AssertionError("service helper 不应触发外部边界")

    monkeypatch.setattr("mindforge.env_loader.load_dotenv_silently", _blocked)
    monkeypatch.setattr("mindforge.llm.build_providers", _blocked)
    monkeypatch.setattr(socket, "socket", _blocked)

    result = obsidian_preflight(vault_root=vault, manifest_path=manifest, default_staged_root=tmp_path / "exports")

    assert result.status == "PASS"
    assert note.read_text(encoding="utf-8") == before
    assert result.proposed_target is not None
    assert not result.proposed_target.exists()


def test_preflight_display_plan_calculates_next_action_without_cli_rendering(tmp_path: Path) -> None:
    """preflight next-action 属于 service 判断，CLI 只负责把结构化结果打印出来。"""
    vault, _note, _exported, manifest = _write_service_manifest(tmp_path)

    passed = obsidian_preflight(vault_root=vault, manifest_path=manifest, default_staged_root=tmp_path / "exports")
    pass_display = build_preflight_display_plan(passed)

    assert pass_display.status == "PASS"
    assert pass_display.exit_code == 0
    assert "manually inspect" in pass_display.next_action
    assert pass_display.future_gate == "staged export -> diff preview -> backup -> explicit confirmation"
    assert "不会写正式 Obsidian notes" in pass_display.no_write_boundary

    _patch_manifest(manifest, action=None)
    blocked = obsidian_preflight(vault_root=vault, manifest_path=manifest, default_staged_root=tmp_path / "exports")
    blocked_display = build_preflight_display_plan(blocked)
    assert blocked_display.status == "BLOCKED"
    assert blocked_display.exit_code == 2
    assert "not ready" in blocked_display.outcome_message


def test_diff_preview_plan_is_staged_only_and_structured(tmp_path: Path) -> None:
    """diff helper 只读取 staged 候选文件，返回结构化 diff，不碰正式 notes。"""
    vault, note, _cfg_path = _make_service_vault(tmp_path)
    formal_before = note.read_text(encoding="utf-8")
    staged = tmp_path / "exports" / "Agent-Runtime.md"

    missing = build_staged_diff_preview_plan(staged, "# proposed\n")
    assert missing.exists is False
    assert missing.diff_lines == ()
    assert "manifest before preflight" in missing.manual_inspection_hint

    staged.parent.mkdir(parents=True)
    staged.write_text("# old\n", encoding="utf-8")
    changed = build_staged_diff_preview_plan(staged, "# proposed\n")

    assert changed.exists is True
    assert changed.has_changes is True
    assert any(line.startswith("--- ") for line in changed.diff_lines)
    assert any("+# proposed" in line for line in changed.diff_lines)
    assert note.read_text(encoding="utf-8") == formal_before
    assert safe_relative_to(staged, vault) is None


def test_obsidian_next_plan_reports_manifest_status_and_no_write_boundary(tmp_path: Path) -> None:
    """obsidian next 的状态判断在 service 层完成；它只导航，不执行写入。"""
    vault, note, _exported, manifest = _write_service_manifest(tmp_path, output_dir=tmp_path / "staged")
    before = note.read_text(encoding="utf-8")

    plan = build_obsidian_next_plan(vault_root=vault, output_dir=tmp_path / "staged")

    assert plan.vault_exists is True
    assert plan.staged_export_count == 1
    assert plan.manifest_count == 1
    assert plan.latest_manifest == manifest
    assert "obsidian preflight" in plan.recommended_next
    assert "no .env, no real LLM, no formal note writes" in plan.safety_line
    assert "no apply command" in plan.boundary_line
    assert any("obsidian stage" in item.command and "--dry-run" in item.command for item in plan.commands)
    assert note.read_text(encoding="utf-8") == before


def test_obsidian_stage_service_has_no_typer_or_rich_dependency() -> None:
    """service 模块不能依赖 CLI presentation 库，避免业务判断和渲染重新耦合。"""
    source = Path("src/mindforge/obsidian_stage.py").read_text(encoding="utf-8")

    assert "import typer" not in source
    assert "from rich" not in source
    assert "Console(" not in source
    assert "Table(" not in source
