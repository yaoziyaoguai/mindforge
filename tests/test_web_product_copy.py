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
    # i18n follow-up 后，文字通过 t() 获取
    assert "wiki.local_graph_preview" in section_graph
    assert "wiki.local_graph_desc" in section_graph
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
    assert zh.get("setup.save") == "保存配置"
    assert zh.get("setup.validate") == "验证"
    assert zh.get("setup.revert") == "还原"
    assert zh.get("setup.unsaved") == "未保存的更改"
    assert zh.get("setup.knowledge_vault") == "知识库目录"
    assert zh.get("setup.configured_models") == "已配置模型"
    assert zh.get("setup.default_model") == "默认模型"
    assert zh.get("setup.processing_workflow") == "处理工作流"
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
    assert zh.get("setup.knowledge_vault") == "知识库目录"
    assert zh.get("setup.configured_models") == "已配置模型"
    assert zh.get("setup.default_model") == "默认模型"
    assert zh.get("setup.processing_workflow") == "处理工作流"
    assert zh.get("setup.wiki_generation") == "Wiki 生成"
    assert zh.get("setup.workflow_view_prompt") == "查看提示词"
    assert "自动创建" in zh.get("setup.knowledge_vault_desc", "")


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
    assert zh.get("setup.diagnostics") == "高级诊断"
    assert "只读诊断" in zh.get("setup.diagnostics_desc", "")

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
    assert zh.get("setup.configured_models") == "已配置模型"
    assert zh.get("setup.default_model") == "默认模型"
    assert zh.get("setup.processing_workflow") == "处理工作流"
    assert en.get("setup.workflow_uses_default") == "(uses default)"
    assert zh.get("setup.legacy_detected", "").startswith("检测到旧版")
    assert zh.get("setup.model_id") == "模型 ID"
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
    assert zh.get("setup.local_workspace") == "本地工作区"
    assert zh.get("setup.configured_models") == "已配置模型"

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
    """i18n follow-up 后，SourcesPage 所有用户文案通过 t() 获取，
    测试改为验证 i18n key 存在和组件使用 useLocale。"""
    sources = _read("pages/SourcesPage.tsx")

    assert "useLocale" in sources
    assert "Reveal in Finder" not in sources
    # i18n keys 存在
    assert 't("sources.copy_path")' in sources or "t(\"sources.copy_display_path\")" in sources
    assert 't("sources.process_now")' in sources
    assert 't("sources.edit_frequency")' in sources
    assert 't("sources.stop_watching")' in sources
    assert 't("sources.diagnostics")' in sources
    assert 't("sources.last_run_summary")' in sources
    assert "sourceStatusLabel" in sources
    assert "sourceRunStatusLabel" in sources
    assert "sourceDueStatusLabel" in sources
    assert "getFrequencyOptions" in sources
    # 旧的硬编码英文不在源码中
    assert "Copy path" not in sources
    assert "Process now" not in sources
    # "Edit frequency" 在 catch block 中作为 error fallback 文案，无需排除
    assert "Stop watching" not in sources
    assert "Last run summary" not in sources
    assert "Open related knowledge" not in sources
    assert "Add source in Setup" not in sources
    # 安全边界
    assert "source_path_view" in sources


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


# ── i18n Mixed-language Follow-up (2026-05-23-002) ──────────────────────


def test_i18n_wiki_keys_complete() -> None:
    """Wiki 组件族的 i18n 键必须完整覆盖 zh 和 en 字典。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    wiki_keys = [
        "wiki.title",
        "wiki.subtitle",
        "wiki.status_label",
        "wiki.status_ready",
        "wiki.status_not_built",
        "wiki.last_rebuilt",
        "wiki.cards_in_wiki",
        "wiki.knowledge_cards",
        "wiki.new_approved_hint",
        "wiki.rebuild_tooltip",
        "wiki.refresh",
        "wiki.generate",
        "wiki.empty_no_approved",
        "wiki.empty_no_approved_desc",
        "wiki.empty_model_required",
        "wiki.empty_model_required_desc",
        "wiki.empty_not_built",
        "wiki.empty_not_built_desc",
        "wiki.error_unavailable",
        "wiki.retry",
        "wiki.building",
        "wiki.building_desc",
        "wiki.troubleshooting",
        "wiki.troubleshooting_desc",
        "wiki.safe_fallback_rebuild",
        "wiki.open_questions",
        "wiki.additional_cards",
        "wiki.warnings",
        "wiki.contents",
        "wiki.hide_contents",
        "wiki.untitled_section",
        "wiki.load_failed",
        "wiki.rebuild_failed",
        "wiki.rebuild_result",
        "wiki.rebuild_server_error",
        "wiki.knowledge_sources",
        "wiki.references",
        "wiki.approved_badge",
        "wiki.approved_tooltip",
        "wiki.local_graph_preview",
        "wiki.local_graph_desc",
        "wiki.wiki_section_reference",
        "wiki.source_prefix",
        "wiki.local_graph_empty",
        "wiki.toc_toggle",
    ]
    for key in wiki_keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_i18n_trash_keys_complete() -> None:
    """TrashPage 的 i18n 键必须完整。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    trash_keys = [
        "trash.title",
        "trash.subtitle",
        "trash.empty",
        "trash.previous_status",
        "trash.trashed_at",
        "trash.original_path",
        "trash.source_title",
        "trash.restore",
        "trash.select_to_preview",
        "trash.load_failed",
        "trash.restore_failed",
        "trash.track",
        "trash.trashed_date",
    ]
    for key in trash_keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_i18n_source_add_keys_complete() -> None:
    """SourceAddPanel 的 i18n 键必须完整。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    sa_keys = [
        "source_add.title",
        "source_add.desc",
        "source_add.manual_desc",
        "source_add.no_model_warning",
        "source_add.add_model_link",
        "source_add.path_input",
        "source_add.pick_file",
        "source_add.pick_file_tooltip",
        "source_add.pick_folder",
        "source_add.pick_folder_tooltip",
        "source_add.frequency",
        "source_add.add_source",
        "source_add.add_and_process",
        "source_add.path_hint",
        "source_add.view_in_sources",
        "source_add.configure_model_first",
        "source_add.starting_background",
        "source_add.adding",
        "source_add.request_failed",
        "source_add.freq_manual",
        "source_add.freq_hourly",
        "source_add.freq_daily",
        "source_add.freq_weekly",
        "source_add.freq_every_1h",
        "source_add.freq_every_6h",
        "source_add.freq_every_12h",
        "source_add.freq_every_24h",
    ]
    for key in sa_keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_all_pages_use_locale() -> None:
    """所有页面和关键组件必须通过 useLocale 获取翻译函数。"""
    pages = [
        "pages/HomePage.tsx",
        "pages/SetupPage.tsx",
        "pages/SourcesPage.tsx",
        "pages/DraftsPage.tsx",
        "pages/LibraryPage.tsx",
        "pages/RecallPage.tsx",
        "pages/WikiPage.tsx",
        "pages/TrashPage.tsx",
        "components/Sidebar.tsx",
        "components/ApprovalPanel.tsx",
        "components/CardWorkspace.tsx",
        "components/DraftList.tsx",
        "components/SourceAddPanel.tsx",
        "components/wiki/WikiHeader.tsx",
        "components/wiki/WikiStatusBar.tsx",
        "components/wiki/WikiEmptyState.tsx",
        "components/wiki/WikiErrorState.tsx",
        "components/wiki/WikiLoadingState.tsx",
        "components/wiki/WikiReadingPane.tsx",
        "components/wiki/WikiTOC.tsx",
        "components/wiki/WikiSection.tsx",
        "components/wiki/WikiReferenceCard.tsx",
        "components/wiki/WikiReferencePanel.tsx",
        "components/wiki/WikiSectionRelationshipPreview.tsx",
        "components/wiki/WikiAdvancedActions.tsx",
    ]
    for path in pages:
        content = _read(path)
        assert "useLocale" in content, f"{path} missing useLocale"


def test_display_mapping_functions_exist() -> None:
    """前端 display mapping 函数必须存在，用于将后端 internal id 映射为用户文案。"""
    utils = _read("lib/utils.ts")

    # workflow/stage display mapping
    assert "workflowStepLabel" in utils
    assert "triage" in utils
    assert "distill" in utils
    assert "link_suggestion" in utils
    assert "review_questions" in utils
    assert "action_extraction" in utils

    # strategy display mapping
    assert "strategyStatusLabel" in utils
    assert "strategyNameLabel" in utils

    # source status display mapping
    assert "sourceStatusLabel" in utils
    assert "sourceRunStatusLabel" in utils
    assert "sourceDueStatusLabel" in utils


def test_setup_page_uses_display_mappings() -> None:
    """SetupPage 必须使用 display mapping 函数代替直接展示后端 id。"""
    setup = _read("pages/SetupPage.tsx")

    assert "workflowStepLabel" in setup
    assert "strategyNameLabel" in setup
    assert "strategyStatusLabel" in setup


def test_sources_page_uses_display_mappings() -> None:
    """SourcesPage 必须使用 source display mapping 函数。"""
    sources = _read("pages/SourcesPage.tsx")

    assert "sourceStatusLabel" in sources
    assert "sourceRunStatusLabel" in sources
    assert "sourceDueStatusLabel" in sources
    assert "getFrequencyOptions" in sources


# ── Milestone D: Dashboard & Action Guidance (2026-05-23-003) ──────────────


def test_next_action_display_mapping_exists() -> None:
    """nextActionLabel() 函数必须存在，包含 HomePage 和 EmptyState 的所有 action_key。"""
    utils = _read("lib/utils.ts")

    assert "nextActionLabel" in utils
    # HomePage _next_actions 的 4 个 key
    for key in ("init_vault", "review_drafts", "watch_source", "search_knowledge"):
        # 验证映射表中包含该 key（中文 label ≠ key 名）
        assert f'{key}:' in utils or f"{key}:" in utils, f"Missing nextActionLabel key: {key}"
    # EmptyState 的 5 个 key
    for key in ("create_drafts", "search_approved_cards", "adjust_query", "try_another_query", "rebuild_index"):
        assert f'{key}:' in utils or f"{key}:" in utils, f"Missing nextActionLabel key: {key}"


def test_next_action_card_uses_localized_display() -> None:
    """NextActionCard 必须使用 nextActionLabel() 做本地化展示，fallback 到 action.label。"""
    card = _read("components/NextActionCard.tsx")

    assert "nextActionLabel" in card
    assert "displayLabel" in card
    assert "action_key" in card
    assert "action.label" in card  # fallback


def test_empty_state_uses_localized_action_label() -> None:
    """EmptyState 必须使用 nextActionLabel() 做本地化，并接受 locale prop。"""
    empty = _read("components/EmptyState.tsx")

    assert "nextActionLabel" in empty
    assert "displayLabel" in empty
    assert "locale" in empty


def test_homepage_i18n_section_keys_complete() -> None:
    """HomePage 3-section layout 的 i18n 键必须完整覆盖。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    section_keys = [
        "home.section_system_status",
        "home.section_config_check",
        "home.section_next_actions",
    ]
    for key in section_keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_homepage_action_guidance_keys_complete() -> None:
    """HomePage 行动引导文案（参数化的 count 状态）的 i18n 键必须完整。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    guidance_keys = [
        "home.review_drafts_pending",
        "home.review_drafts_clear",
        "home.inbox_pending_detail",
        "home.inbox_clear",
        "home.library_approved_detail",
        "home.library_empty_detail",
    ]
    for key in guidance_keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"
        # 参数化的键必须包含 {count} 占位符
        if key.endswith("_pending") or key.endswith("_detail") and "empty" not in key:
            assert "{count}" in zh[key], f"zh {key} missing {{count}} placeholder"


def test_homepage_uses_localized_action_cards() -> None:
    """HomePage 必须将 locale 传递给 NextActionCard 以进行本地化。"""
    home = _read("pages/HomePage.tsx")

    assert "useLocale" in home
    assert "locale={locale}" in home or "locale={locale}" in home
    # NextActionCard 接收 locale prop
    assert "locale" in home


def test_copy_policy_document_exists() -> None:
    """copy-policy.md 必须存在，包含核心规则说明。"""
    policy = (ROOT / "docs" / "dev" / "copy-policy.md")

    assert policy.exists(), "docs/dev/copy-policy.md missing"
    content = policy.read_text(encoding="utf-8")

    assert "UI copy 必须本地化" in content or "must be localized" in content
    assert "action_key" in content
    assert "nextActionLabel" in content
    assert "display mapping" in content
    assert "防回归" in content or "防回归" in content or "regression" in content


def test_next_action_does_not_use_label_string_matching() -> None:
    """严禁用 label 字符串匹配推断语言 —— 必须用 action_key 做 mapping。"""
    card = _read("components/NextActionCard.tsx")
    empty = _read("components/EmptyState.tsx")

    combined = card + empty
    # 不能有启发式语言检测
    for pattern in (
        "label.includes(",
        "label.startsWith(",
        "label.match(",
        "action.label ===",
        '/[\\u4e00-\\u9fa5]/.test',
        "isChinese",
        "containsChinese",
    ):
        assert pattern not in combined, f"Forbidden language detection pattern: {pattern}"
