"""Web product copy contract for the local knowledge workspace.

中文学习型说明：这组测试不验证业务逻辑，只约束用户主视图的命名层级。
source_id / run_id / stage_models 这些工程字段仍可存在于 API 类型和 Technical
details 中，但不应成为导航、主标题、主列表和审批文案的核心语言。

Milestone C 之后，所有用户可见文案已集中到 web/src/lib/i18n.ts 的 copy 字典中，
组件通过 t() 调用获取翻译。测试改为验证 i18n 字典的键值完整性。
"""

from __future__ import annotations

import re

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "web" / "src"


def _read(rel: str) -> str:
    return (WEB_SRC / rel).read_text(encoding="utf-8")


def _read_i18n_zh() -> dict[str, str]:
    """解析 i18n.ts 中的 zh copy 字典，返回 key -> 中文文案映射。"""
    text = _read("lib/i18n.ts")
    # 提取 zh 字典块
    m = re.search(r"zh:\s*\{(.*?)\n\s*\},", text, re.DOTALL)
    if not m:
        return {}
    block = m.group(1)
    result: dict[str, str] = {}
    for match in re.finditer(r'"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', block):
        key = match.group(1)
        val = match.group(2)
        result[key] = val
    return result


def _read_i18n_en() -> dict[str, str]:
    """解析 i18n.ts 中的 en copy 字典，返回 key -> 英文文案映射。"""
    text = _read("lib/i18n.ts")
    m = re.search(r"en:\s*\{(.*?)\n\s*\},", text, re.DOTALL)
    if not m:
        return {}
    block = m.group(1)
    result: dict[str, str] = {}
    for match in re.finditer(r'"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', block):
        key = match.group(1)
        val = match.group(2)
        result[key] = val
    return result


def test_web_navigation_uses_knowledge_workspace_language() -> None:
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    # 中文导航标签
    assert zh.get("nav.drafts") == "审阅草稿"
    assert zh.get("nav.library") == "知识库"
    assert zh.get("nav.recall") == "搜索"
    assert zh.get("nav.group.processing") == "知识处理"
    assert zh.get("nav.group.using") == "知识使用"
    # 英文导航不是中文原文
    assert en.get("nav.drafts") == "Review Drafts"
    assert en.get("nav.recall") == "Search"

    # 组件不能有硬编码中文或英文标签（必须通过 t() 获取）
    sidebar = _read("components/Sidebar.tsx")
    assert "useLocale" in sidebar
    assert 'label: "Drafts"' not in sidebar
    assert 'label: "Recall"' not in sidebar


def test_main_pages_use_friendly_status_and_action_copy() -> None:
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    # 中文文案在 i18n 字典中
    assert zh.get("home.review_drafts") == "审阅 AI 草稿"
    assert "待审阅" in zh.get("home.review_drafts_detail", "")
    assert zh.get("library.stats_approved") == "已确认知识"
    assert zh.get("recall.subtitle", "").startswith("搜索已确认的知识卡片")
    assert zh.get("approval.title") == "确认知识卡片"

    # 英文文案在 i18n 字典中
    assert en.get("approval.title") == "Approve Knowledge Card"

    # 组件没有裸露内部状态名
    combined = "\n".join(
        _read(p)
        for p in [
            "pages/HomePage.tsx",
            "pages/DraftsPage.tsx",
            "pages/LibraryPage.tsx",
            "pages/RecallPage.tsx",
            "components/ApprovalPanel.tsx",
        ]
    )
    for forbidden in (
        "ai_draft waiting",
        "human_approved available",
        "Approve promotes this draft from ai_draft to human_approved",
        "Recall / Knowledge",
        "Local lexical recall over human_approved cards",
        "Total cards",
    ):
        assert forbidden not in combined


def test_card_detail_separates_content_source_history_and_technical_details() -> None:
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    assert zh.get("card.knowledge_content") == "知识内容"
    assert zh.get("card.source_history") == "来源与历史"
    assert zh.get("card.tech_details") == "技术详情"
    assert en.get("card.knowledge_content") == "Knowledge Content"
    assert en.get("card.source_history") == "Source & History"
    assert en.get("card.tech_details") == "Technical Details"

    workspace = _read("components/CardWorkspace.tsx")
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
    en = _read_i18n_en()

    assert en.get("setup.model_api_key") == "API key"

    # SafetyBar 中的 model setup status 走 status 文案
    zh = _read_i18n_zh()
    assert zh.get("status.ok") == "正常"
    assert zh.get("status.warn") == "警告"

    combined = "\n".join([
        _read("pages/SetupPage.tsx"),
        _read("components/ConfigChecklist.tsx"),
        _read("components/SafetyBar.tsx"),
    ])
    assert "Provider status only reports" not in combined
    assert "Provider:" not in combined


def test_home_model_setup_copy_does_not_depend_on_env_state() -> None:
    """Home 的 model setup readiness 必须用产品语义，不再把 env_only 当 ready。"""

    home = _read("pages/HomePage.tsx")

    assert "model_setup" in home
    assert "env_only" not in home
    assert "fake_default" not in home


def test_setup_page_exposes_safe_editor_controls() -> None:
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    # 安全编辑器控件在 i18n 字典中
    assert zh.get("setup.save") == "Save setup"
    assert zh.get("setup.validate") == "Validate"
    assert zh.get("setup.revert") == "Revert"
    assert zh.get("setup.unsaved") == "Unsaved changes"
    assert zh.get("setup.knowledge_vault") == "Knowledge vault"
    assert zh.get("setup.configured_models") == "Configured models"
    assert zh.get("setup.default_model") == "Default model"
    assert zh.get("setup.processing_workflow") == "Processing workflow"
    assert en.get("setup.model_api_key") == "API key"
    assert en.get("setup.save") == "Save setup"

    # 组件中不能有硬编码字符串，必须通过 t() 获取
    setup = _read("pages/SetupPage.tsx")
    assert "useLocale" in setup
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

    # 禁止的工程/debug 字段不能出现在 SetupPage 源码中
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
        assert forbidden not in setup

    # 产品语义的 i18n key 存在于字典中
    zh = _read_i18n_zh()
    assert zh.get("setup.knowledge_vault") == "Knowledge vault"
    assert zh.get("setup.configured_models") == "Configured models"
    assert zh.get("setup.default_model") == "Default model"
    assert zh.get("setup.processing_workflow") == "Processing workflow"
    assert zh.get("setup.wiki_generation") == "Wiki generation"
    assert zh.get("setup.workflow_view_prompt") == "View prompt"
    assert "Created automatically" in zh.get("setup.knowledge_vault_desc", "")


def test_setup_advanced_diagnostics_are_read_only_and_not_main_path() -> None:
    """Advanced diagnostics 也不能重新暴露测试/legacy/internal 主路径。

    中文学习型说明：Setup 主 UI 是普通用户配置真实模型和来源的地方；
    Diagnostics 只能保留用户能理解的只读状态，不能把 env/Cubox/profile/raw
    config 这些开发和历史兼容语义重新变成产品配置入口。

    Milestone C 之后，diagnostics 文案通过 t("setup.diagnostics") 获取，
    二进制检查字符串是否在源码中出现已不适用，改为验证 i18n 字典内容。
    """

    setup = _read("pages/SetupPage.tsx")
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    # i18n 字典中有 diagnostics 键
    assert zh.get("setup.diagnostics") == "Diagnostics for advanced users"
    assert "read-only diagnostics" in zh.get("setup.diagnostics_desc", "")

    # 禁止的字段不在源码中出现
    for forbidden in (
        "Default base URL",
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
        "Create missing vault directories on save",
        "Copy base URL",
        "Copy model",
        "Copy API key env name",
        "Copy API key value",
        "present (",
        "fake-fast",
        "Built-in demo",
        "fake://",
        "fake_default",
    ):
        assert forbidden not in setup

    # 产品文案在 i18n 字典中
    assert zh.get("setup.no_models") == "尚未配置模型"
    assert "添加模型以启用 AI 草稿生成" in zh.get("setup.no_models_desc", "")
    assert "仅添加和监控知识源" in zh.get("setup.no_models_desc", "")
    assert en.get("setup.no_model_configured") == "No model configured"

    checklist = _read("components/ConfigChecklist.tsx")
    assert "Env keys" not in checklist
    assert "0 configured" not in checklist


def test_setup_page_uses_model_routing_language_not_provider_profiles() -> None:
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    # i18n 字典中有模型路由语义的键
    assert zh.get("setup.configured_models") == "Configured models"
    assert zh.get("setup.default_model") == "Default model"
    assert zh.get("setup.processing_workflow") == "Processing workflow"
    assert en.get("setup.workflow_uses_default") == "(uses default)"
    assert zh.get("setup.legacy_detected", "").startswith("Legacy LLM config detected")
    assert zh.get("setup.model_id") == "Model id"
    assert zh.get("setup.model_api_key") == "API key"

    # 组件源码禁止旧 provider/profile 语言
    setup = _read("pages/SetupPage.tsx")
    assert "useLocale" in setup
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
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    # i18n 字典中有 sources 相关的键
    assert zh.get("setup.local_workspace") == "Local workspace"
    assert zh.get("setup.configured_models") == "Configured models"

    # SourceAddPanel 存在且有正确的英文文案
    add_panel = _read("components/SourceAddPanel.tsx")
    assert "useLocale" in add_panel or "Add a file or folder" in add_panel

    combined = "\n".join([_read("pages/SetupPage.tsx"), add_panel])

    # 禁止的 Cubox/legacy 字段不在源码中
    for forbidden in (
        "Default watched inbox",
        "Manage sources",
        "MindForge can process files placed in this inbox",
        "Cubox JSON export path",
        "Cubox import path",
        "Cubox export folder",
        "Obsidian inbox",
        "Downloads folder",
        "Manual notes folder",
    ):
        assert forbidden not in combined


def test_sources_path_actions_and_status_copy_are_user_safe() -> None:
    sources = _read("pages/SourcesPage.tsx")

    assert "Copy path" in sources
    assert "Reveal in Finder" not in sources
    assert "Copied safe display path only." in sources
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
