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


def test_local_graph_views_are_visible_list_fallbacks_without_graph_libraries() -> None:
    """Local Graph Preview 是产品能力名，relationship preview 只是局部视图说明。"""

    workspace_graph = _read("components/LocalGraphPreview.tsx")
    section_graph = _read("components/wiki/WikiSectionRelationshipPreview.tsx")
    package = (ROOT / "web" / "package.json").read_text(encoding="utf-8")
    combined = "\n".join([workspace_graph, section_graph, package])

    assert "Local Graph Preview" in workspace_graph
    assert "Local Graph Preview" in section_graph
    assert "relationship preview" in section_graph
    assert "not a global Graph page" in workspace_graph
    assert "/library?card=" in combined
    for forbidden in ("<canvas", "d3", "cytoscape", "vis-network", "networkx"):
        assert forbidden not in combined.lower()


def test_setup_copy_uses_model_and_secret_safe_language() -> None:
    setup = _read("pages/SetupPage.tsx")
    checklist = _read("components/ConfigChecklist.tsx")
    safety = _read("components/SafetyBar.tsx")
    combined = "\n".join([setup, checklist, safety])

    assert "Model setup" in combined
    assert "API key" in combined
    assert "configured, missing, or hidden" in combined
    assert "Provider status only reports" not in combined
    assert "Provider:" not in combined


def test_home_model_setup_copy_does_not_depend_on_env_state() -> None:
    """Home 的 model setup readiness 必须用产品语义，不再把 env_only 当 ready。"""

    home = _read("pages/HomePage.tsx")

    assert "model_setup" in home
    assert "env_only" not in home
    assert "fake_default" not in home


def test_setup_page_exposes_safe_editor_controls() -> None:
    setup = _read("pages/SetupPage.tsx")

    assert "Save setup" in setup
    assert "Validate" in setup
    assert "Revert" in setup
    assert "Unsaved changes" in setup
    assert "Knowledge vault" in setup
    assert "Configured models" in setup
    assert "Default model" in setup
    assert "Processing workflow" in setup
    assert "API key" in setup
    # type=password 现在是安全的用户输入字段（永不预填），不是 secret 泄露路径
    assert "autoComplete=\"off\"" in setup
    assert "api_key_value" not in setup


def test_setup_save_and_validate_use_current_ui_draft() -> None:
    """Save/Validate 必须包含正在编辑的 model 草稿，而不是旧 config 快照。"""

    setup = _read("pages/SetupPage.tsx")

    assert "const draftForm = useMemo(() => formWithEditing(form, editing)" in setup
    assert "JSON.stringify(draftForm) !== JSON.stringify(savedForm)" in setup
    assert "validateSetupConfig(patchFromForm(current))" in setup
    assert "saveSetupConfig(patchFromForm(current))" in setup
    assert "api_key_action: \"clear\"" in setup
    assert "api_key_action: event.target.value ? \"update\" : \"keep\"" in setup


def test_setup_main_ui_hides_env_mapping_and_legacy_debug_fields() -> None:
    setup = _read("pages/SetupPage.tsx")
    main_ui = setup.split("Diagnostics for advanced users", 1)[0]

    for forbidden in (
        "Environment variable overrides",
        "API key env",
        "Base URL env",
        "Model env",
        "Technical internal route",
        "Provider readiness",
        "Raw config path",
        "Config file",
        "Token status",
        "Process environment diagnostics",
        "Environment variable presence",
        "data.config_path",
        "active_profile",
        "profiles",
        "Create missing vault directories on save",
        "missing directories",
        "internal directory state",
    ):
        assert forbidden not in main_ui

    assert "Knowledge vault" in main_ui
    assert "Created automatically" in main_ui
    assert "Configured models" in main_ui
    assert "Default model" in main_ui
    assert "Processing workflow" in main_ui
    assert "Wiki generation" in main_ui
    assert "View prompt" in main_ui


def test_setup_advanced_diagnostics_are_read_only_and_not_main_path() -> None:
    """Advanced diagnostics 也不能重新暴露测试/legacy/internal 主路径。

    中文学习型说明：Setup 主 UI 是普通用户配置真实模型和来源的地方；
    Diagnostics 只能保留用户能理解的只读状态，不能把 env/Cubox/profile/raw
    config 这些开发和历史兼容语义重新变成产品配置入口。
    """

    setup = _read("pages/SetupPage.tsx")
    checklist = _read("components/ConfigChecklist.tsx")
    combined = "\n".join([setup, checklist])
    advanced = setup.split("Diagnostics for advanced users", 1)[1]

    assert "Default base URL" not in setup
    assert "Diagnostics for advanced users" in setup
    assert "read-only diagnostics" in advanced
    for forbidden in (
        "Environment variable overrides",
        "Provider readiness",
        "Raw config path",
        "Token status",
        "Configuration checklist",
        "Environment variable presence",
        "Process environment diagnostics",
        "Technical internal route",
        "Cubox",
        "cubox",
        "api_key_env",
        "base_url_env",
        "model_env",
        "active_profile",
        "profiles",
        "__model_routing__",
    ):
        assert forbidden not in advanced
    assert "Create missing vault directories on save" not in setup
    assert "Environment variable presence" not in combined
    assert "Process environment diagnostics" not in combined
    # Effective base URL / model 仅在 Advanced diagnostics 展示，不在主 UI
    assert "Copy base URL" not in setup
    assert "Copy model" not in setup
    assert "Copy API key env name" not in setup  # 主 UI 不再展示 env var name copy；移至 Advanced
    assert "Copy API key value" not in setup
    assert "present (" not in setup  # 不再在卡片中展示脱敏 key，改用 API key status tag
    assert "No model configured" in setup
    assert "Add a model to generate AI drafts." in setup
    assert "You can still add and monitor sources" in setup
    assert "fake-fast" not in setup
    assert "Built-in demo" not in setup
    assert "fake://" not in setup
    assert "fake_default" not in setup
    assert "Env keys" not in checklist
    assert "0 configured" not in combined


def test_setup_page_uses_model_routing_language_not_provider_profiles() -> None:
    setup = _read("pages/SetupPage.tsx")

    assert "Configured models" in setup
    assert "Default model" in setup
    assert "Processing workflow" in setup
    assert "Workflow step" in setup
    assert "uses default" in setup  # 新版 UI 不再折叠，直接展示所有 steps
    assert "Legacy LLM config detected" in setup
    assert "Model id" in setup
    assert "API key:" in setup
    assert "Active strategy" in setup or "active_strategy" in setup.lower()
    assert "stage_models" not in setup
    assert "Stage models" not in setup
    assert "active_profile" not in setup
    assert "profiles" not in setup
    assert "Active provider" not in setup
    assert "provider profiles" not in setup
    assert "fake_fast" not in setup
    assert "fake_strong" not in setup
    assert "all_local" not in setup


def test_setup_sources_section_decenters_cubox_config_fields() -> None:
    setup = _read("pages/SetupPage.tsx")
    add_panel = _read("components/SourceAddPanel.tsx")
    combined = "\n".join([setup, add_panel])

    assert "Local workspace" in setup
    assert "Configured models" in setup
    assert "SourceAddPanel" in setup
    assert "Add a file or folder" in combined
    assert "Path input" in combined
    assert "Frequency" in combined
    assert "Add source" in combined
    assert "Add and process now" in combined
    assert "View in Sources" in combined
    assert "MindForge automatically detects whether the path is a file or folder." in combined
    assert "Folders are scanned recursively." in combined
    assert "Frequency applies only to the top-level source you add." in combined
    assert "Manual means no automatic scanning." in combined
    assert "Automation only creates draft knowledge cards." in combined
    assert "Approved knowledge requires explicit approval." in combined
    assert "Default watched inbox" not in combined
    assert "Manage sources" not in combined
    assert "MindForge can process files placed in this inbox" not in combined
    assert "Cubox JSON export path" not in combined
    assert "Cubox import path" not in combined
    assert "Cubox export folder" not in combined
    assert "Obsidian inbox" not in combined
    assert "Downloads folder" not in combined
    assert "Manual notes folder" not in combined


def test_sources_path_actions_and_status_copy_are_user_safe() -> None:
    sources = _read("pages/SourcesPage.tsx")

    assert "Copy path" in sources
    assert "Reveal in Finder" not in sources
    assert "Copied" in sources
    assert "files scanned" in sources
    assert "Recursive: yes" in sources
    assert "Frequency" in sources
    assert "Last scan" in sources
    assert "Next scan" in sources
    assert "Due" in sources
    assert "Changed since last scan" not in sources
    assert "Deleted since last scan" not in sources
    assert "New since last scan" not in sources
    assert "New=" not in sources
    assert "Changed=" not in sources
    assert "Skipped=" not in sources
    assert "Drafts created=" not in sources
    assert "Add source in Setup" in sources
    assert "Add a file or folder" not in sources
    assert "Path input" not in sources
    assert "Add and process now" not in sources
    assert "Process now" in sources
    assert "Edit frequency" in sources
    assert "Processing..." in sources
    assert "You can keep using MindForge." in sources
    assert "Last run summary" in sources
    assert "Last updated" in sources
    assert "Processing in the background. You can keep using MindForge." in sources
    assert "Try Process now again after fixing the issue." in sources
    assert "No draft was generated. Sources shows the reason." in sources
    assert "source.last_run_summary?.skipped ?? source.skipped_count" in sources
    assert "source.last_run_summary?.errors ?? source.failed_count" in sources
    assert "SummaryMetric" in sources
    assert "Diagnostics" in sources
    assert "Source details" in sources
    assert "This only stops future monitoring. It does not delete the folder, source files, or knowledge cards." in sources
    assert "Stop watching" in sources
    assert "Built-in inbox cannot be removed." not in sources
    assert "Built-in inbox frequency is fixed." not in sources
    assert "More actions" not in sources
    assert "Process all due sources" not in sources
    assert "Process all sources now" not in sources
    assert "Add watched file" not in sources
    assert "Add watched folder" not in sources
    assert "Import once" not in sources
    assert "Scan now" not in sources
    assert "folder · default" not in sources
    assert "default cannot be deleted" not in sources
    assert "Built-in inbox" in sources
    assert "Skipped reasons" in sources
    assert "Drafts created" in sources
    assert "Open related knowledge" in sources
    assert "supported=" not in sources
    assert "failed=" not in sources
    assert "Open generated knowledge" not in sources
    assert "Adapter ready" not in sources
    assert "Has generated knowledge" not in sources


def test_unused_source_list_component_is_removed_to_close_raw_path_callback_shape() -> None:
    """收尾防回归：删除未使用 SourceList，避免留下 raw path callback 语义入口。"""

    assert not (WEB_SRC / "components" / "SourceList.tsx").exists()


def test_source_path_ui_static_contracts_fail_closed_without_component_tests() -> None:
    """收尾防回归：暂无组件测试栈时，用静态 contract 锁住 source path UI 边界。

    中文学习型说明：这不是替代长期组件测试，只是 final stabilization 的轻量
    防回归边界。没有 source_path_view 时 UI 必须 fail-closed；不能重新出现
    onCopyPath(path) / onRevealPath(path) 这类 raw path callback 形状。
    """

    frontend = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(WEB_SRC.rglob("*.tsx"))
    )
    forbidden = (
        "onRevealPath?: (path: string)",
        "onCopyPath?: (path: string)",
        "onRevealPath?.(source.path)",
        "onCopyPath?.(source.path)",
        "copyPath(source.path)",
        "source_path ||",
        "source_path ??",
    )
    for pattern in forbidden:
        assert pattern not in frontend
    assert "source_path_view" in frontend


def test_web_client_parses_string_and_object_error_detail() -> None:
    """前端必须同时兼容 FastAPI string detail 与 object detail。

    中文学习型说明：Add Source / Process Now 是用户主链路。后端历史上既有
    ``detail: "message"``，也有 ``detail: {message}``；前端必须提取可行动
    文案，不能退化成浏览器的 ``Bad Request``。
    """

    client = _read("api/client.ts")

    assert 'typeof payload?.detail === "string"' in client
    assert "payload?.detail?.message" in client
    assert "response.statusText" in client
