"""Architecture boundaries for simple watch/import ingestion."""

from __future__ import annotations

import ast
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
INGESTION = REPO / "src" / "mindforge" / "ingestion_service.py"
CLI = REPO / "src" / "mindforge" / "cli.py"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            prefix = "mindforge." if node.level else ""
            result.add(prefix + node.module)
    return result


def test_ingestion_service_does_not_depend_on_cli_or_presenters() -> None:
    imports = _imports(INGESTION)
    forbidden = {
        "typer",
        "rich",
        "mindforge.cli",
        "mindforge.process_cli",
        "mindforge.watch_cli",
        "mindforge.import_cli",
        "mindforge.approve_presenter",
        "mindforge.process_presenter",
    }
    assert not (imports & forbidden)


def test_ingestion_service_has_no_real_llm_dotenv_or_auto_approve_boundary_leaks() -> None:
    source = INGESTION.read_text(encoding="utf-8")
    imports = _imports(INGESTION)
    forbidden_imports = {
        "dotenv",
        "openai",
        "anthropic",
        "litellm",
        "cohere",
        "ollama",
        "mindforge.approver",
        "mindforge.approval_service",
    }
    assert not (imports & forbidden_imports)
    assert "approve_card" not in source
    assert "human_approved" not in source
    assert "load_dotenv" not in source


def test_root_cli_registers_watch_and_import_but_no_inbox_command() -> None:
    source = CLI.read_text(encoding="utf-8")
    assert "app.add_typer(watch_app, name=\"watch\")" in source
    assert "app.command(\"import\")(import_cmd)" in source
    assert "name=\"inbox\"" not in source
    assert "inbox_app" not in source
