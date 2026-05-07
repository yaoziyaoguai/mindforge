"""Web product copy contract for the local knowledge workspace.

中文学习型说明：这组测试不验证业务逻辑，只约束用户主视图的命名层级。
source_id / run_id / stage_models 这些工程字段仍可存在于 API 类型和 Technical
details 中，但不应成为导航、主标题、主列表和审批文案的核心语言。
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "web" / "src"


def _read(rel: str) -> str:
    return (WEB_SRC / rel).read_text(encoding="utf-8")


def test_web_navigation_uses_knowledge_workspace_language() -> None:
    sidebar = _read("components/Sidebar.tsx")

    assert 'label: "Review"' in sidebar
    assert 'label: "Knowledge Library"' in sidebar
    assert 'label: "Search"' in sidebar
    assert 'label: "Drafts"' not in sidebar
    assert 'label: "Recall"' not in sidebar


def test_main_pages_use_friendly_status_and_action_copy() -> None:
    home = _read("pages/HomePage.tsx")
    drafts = _read("pages/DraftsPage.tsx")
    library = _read("pages/LibraryPage.tsx")
    search = _read("pages/RecallPage.tsx")
    approval = _read("components/ApprovalPanel.tsx")

    combined = "\n".join([home, drafts, library, search, approval])
    assert "Review drafts" in combined
    assert "Needs review" in combined
    assert "Approved knowledge" in combined
    assert "Search approved knowledge" in combined
    assert "Approve knowledge" in combined

    for forbidden in (
        "ai_draft waiting",
        "human_approved available",
        "Approve promotes this draft from ai_draft to human_approved",
        "Recall / Knowledge",
        "Local lexical recall over human_approved cards",
        "Total cards",
        "AI drafts",
    ):
        assert forbidden not in combined


def test_card_detail_separates_content_source_history_and_technical_details() -> None:
    workspace = _read("components/CardWorkspace.tsx")

    assert "Knowledge content" in workspace
    assert "Source & history" in workspace
    assert "Technical details" in workspace
    assert "Provenance / Debug" not in workspace

    # 工程字段只能作为 Technical details 内容出现，不作为 header 中的主状态文案。
    header_block = workspace.split("<details", 1)[0]
    for forbidden in ("source_id", "run_id", "stage_models", "source_content_hash"):
        assert forbidden not in header_block


def test_setup_copy_uses_model_and_secret_safe_language() -> None:
    setup = _read("pages/SetupPage.tsx")
    checklist = _read("components/ConfigChecklist.tsx")
    safety = _read("components/SafetyBar.tsx")
    combined = "\n".join([setup, checklist, safety])

    assert "Model provider" in combined
    assert "API key" in combined
    assert "present/missing" in combined
    assert "Provider status only reports" not in combined
    assert "Provider:" not in combined


def test_setup_page_exposes_safe_editor_controls() -> None:
    setup = _read("pages/SetupPage.tsx")

    assert "Save setup" in setup
    assert "Validate" in setup
    assert "Revert" in setup
    assert "Unsaved changes" in setup
    assert "Vault path" in setup
    assert "Active provider" in setup
    assert "API key" in setup
    assert "type=\"password\"" not in setup
    assert "api_key_value" not in setup


def test_setup_page_uses_effective_env_config_language() -> None:
    setup = _read("pages/SetupPage.tsx")
    checklist = _read("components/ConfigChecklist.tsx")
    combined = "\n".join([setup, checklist])

    assert "source = config" in setup
    assert "source = env" in setup
    assert "source = missing" in setup
    assert "Default model" not in setup
    assert "Default base URL" not in setup
    assert "Effective base URL" not in setup
    assert "Effective model" not in setup
    assert "Copy base URL" not in setup
    assert "Copy model" not in setup
    assert "Copy API key env name" in setup
    assert "Copy API key value" not in setup
    assert "present (" in setup
    assert "No model provider configured" in setup
    assert "Configure a provider to generate AI drafts." in setup
    assert "You can still add and monitor sources" in setup
    assert "fake-fast" not in setup
    assert "fake://" not in setup
    assert "fake_default" not in setup
    assert "Environment variable presence" in checklist
    assert "Process environment diagnostics" in checklist
    assert "Env keys" not in checklist
    assert "0 configured" not in combined


def test_setup_sources_section_decenters_cubox_config_fields() -> None:
    setup = _read("pages/SetupPage.tsx")

    assert "Local workspace" in setup
    assert "Model provider" in setup
    assert "Default watched inbox" not in setup
    assert "Manage sources" not in setup
    assert "MindForge can process files placed in this inbox" not in setup
    assert "Cubox JSON export path" not in setup
    assert "Cubox import path" not in setup
    assert "Cubox export folder" not in setup
    assert "Obsidian inbox" not in setup
    assert "Downloads folder" not in setup
    assert "Manual notes folder" not in setup


def test_sources_path_actions_and_status_copy_are_user_safe() -> None:
    sources = _read("pages/SourcesPage.tsx")
    source_list = _read("components/SourceList.tsx")
    combined = "\n".join([sources, source_list])

    assert "Copy path" in combined
    assert "Reveal in Finder" in combined
    assert "Copied" in combined
    assert "Processed" in combined
    assert "Recursive: yes" in combined
    assert "Frequency" in sources
    assert "Last scan" in sources
    assert "Next scan" in sources
    assert "Due" in sources
    assert "Changed since last scan" in sources
    assert "Deleted since last scan" in sources
    assert "New since last scan" in sources
    assert "Add a file or folder" in sources
    assert "Add source" in sources
    assert "Add and process now" in sources
    assert "Process now" in sources
    assert "Edit frequency" in sources
    assert "Processing..." in sources
    assert "MindForge automatically detects whether the path is a file or folder." in sources
    assert "Folders are scanned recursively." in sources
    assert "Frequency applies only to the top-level source you add" in sources
    assert "Manual means no automatic scanning." in sources
    assert "Automation only creates draft knowledge cards." in sources
    assert "Approved knowledge requires explicit approval." in sources
    assert "files scanned" in sources
    assert "skipped" in sources
    assert "drafts created" in sources
    assert "More actions" not in sources
    assert "Process all due sources" not in sources
    assert "Process all sources now" not in sources
    assert "Add watched file" not in sources
    assert "Add watched folder" not in sources
    assert "Import once" not in sources
    assert "Scan now" not in sources
    assert "folder · default" not in sources
    assert "default cannot be deleted" not in sources
    assert "built-in inbox" in sources
    assert "Skipped reasons" in combined
    assert "Drafts created" in sources
    assert "Open related knowledge" in sources
    assert "supported=" not in sources
    assert "failed=" not in sources
    assert "Open generated knowledge" not in combined
    assert "Adapter ready" not in sources
    assert "Has generated knowledge" not in sources
    assert "\"ready\"" not in source_list
    assert "Approved" not in source_list
