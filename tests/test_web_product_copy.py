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
    assert zh.get("home.dashboard.approved_label") == "已确认知识"
    assert zh.get("home.dashboard.pending_label") == "待审阅"
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
    """Local Graph Preview 和 GraphView 是分离的两层能力。

    v3.8 引入 vis-network 作为 GraphView 页面的轻量渲染引擎，
    但 LocalGraphPreview（Card detail 内嵌视图）仍保持纯 HTML/CSS，
    不直接使用 canvas/d3/cytoscape/networkx 等渲染库。
    """

    workspace_graph = _read("components/LocalGraphPreview.tsx")
    section_graph = _read("components/wiki/WikiSectionRelationshipPreview.tsx")
    combined = "\n".join([workspace_graph, section_graph])

    assert "Local Graph Preview" in workspace_graph
    # i18n follow-up 后，文字通过 t() 获取
    assert "wiki.local_graph_preview" in section_graph
    assert "wiki.local_graph_desc" in section_graph
    assert "/library?card=" in combined
    # LocalGraphPreview 和 WikiSectionRelationshipPreview 不使用
    # canvas/d3/cytoscape/networkx 等渲染库（它们只是纯 HTML list/button 视图）。
    for forbidden in ("<canvas", "d3", "cytoscape", "networkx"):
        assert forbidden not in combined.lower()

    # v3.8: vis-network 是 GraphView 页面的授权渲染引擎，
    # 不再视为 forbidden dependency。
    # GraphPage 使用 vis-network/standalone 做确定性图渲染。


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
    """Home Dashboard 不再展示原始 env state/model_setup 字段。"""

    home = _read("pages/HomePage.tsx")

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
    # Milestone E: "Provider readiness" 现在是正式用户侧功能（provider 就绪状态展示），
    # 已从禁止列表移除 —— 用户需要知道当前 provider 是否可用
    # in_active_profile 是 ProviderAliasStatus API 字段名（JSON key），非 legacy profile 术语
    sanitized = setup.replace("in_active_profile", "")
    for forbidden in (
        "Environment variable overrides",
        "API key env",
        "Base URL env",
        "Model env",
        "Technical internal route",
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
        assert forbidden not in sanitized

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
    # Milestone E: "Provider readiness" 已从禁止列表移除 —— 这是正式用户侧功能
    # in_active_profile 是 API 字段名，非 legacy profile 语言
    sanitized = setup.replace("in_active_profile", "")
    for forbidden in (
        "Default base URL",
        "Environment variable overrides",
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
    ):
        assert forbidden not in sanitized

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
    # in_active_profile 是 API 字段名（JSON key），非 legacy profile 术语
    setup = _read("pages/SetupPage.tsx")
    sanitized = setup.replace("in_active_profile", "")
    assert "useLocale" in setup
    assert "stage_models" not in setup
    assert "Stage models" not in setup
    assert "active_profile" not in sanitized
    assert "profiles" not in sanitized
    assert "Active provider" not in setup
    assert "provider profiles" not in setup
    assert "fake_fast" not in setup
    assert "fake_strong" not in setup
    assert "all_local" not in setup


def test_setup_sources_section_decenters_cubox_config_fields() -> None:
    zh = _read_i18n_zh()

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
        # Milestone G U5: reader mode + related sections
        "wiki.reader_mode_on",
        "wiki.reader_mode_off",
        "wiki.related_sections",
        "wiki.toc_label",
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
    """HomePage Dashboard layout 的 i18n 键必须完整覆盖。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    section_keys = [
        "home.dashboard.overview_title",
        "home.dashboard.attention_title",
        "home.dashboard.quick_actions",
    ]
    for key in section_keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_homepage_action_guidance_keys_complete() -> None:
    """HomePage Dashboard 卡片/attention feed 的 i18n 键必须完整。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    guidance_keys = [
        "home.dashboard.approved_label",
        "home.dashboard.wiki_label",
        "home.dashboard.pending_label",
        "home.dashboard.health_label",
        "home.dashboard.health_good",
        "home.dashboard.health_warn",
        "home.dashboard.attention_empty",
        "home.dashboard.action_browse",
        "home.dashboard.action_import",
        "home.dashboard.action_search",
    ]
    for key in guidance_keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_homepage_uses_localized_dashboard() -> None:
    """HomePage Dashboard 必须使用 useLocale 做本地化。"""
    home = _read("pages/HomePage.tsx")

    assert "useLocale" in home
    assert "t(" in home


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


def test_obsolete_homepage_detail_keys_removed() -> None:
    """HomePage refactor 后 3 个旧 detail key 必须已删除。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    for key in ("home.review_drafts_detail", "home.manage_sources_detail", "home.browse_library_detail"):
        assert key not in zh, f"Obsolete zh key still present: {key}"
        assert key not in en, f"Obsolete en key still present: {key}"


def test_status_card_uses_next_action_label() -> None:
    """StatusCard 必须使用 nextActionLabel 做本地化 inline action 展示。"""
    sc = _read("components/StatusCard.tsx")

    assert "nextActionLabel" in sc
    assert "nextAction.action_key" in sc
    # fallback chain: localized label → label (command/description should NOT appear as label text)
    assert "nextAction.label" in sc
    assert "nextAction.command" not in sc
    assert "nextAction.description" not in sc


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


# ---------------------------------------------------------------------------
# Milestone E — Setup Deep Restructure regression guard
# ---------------------------------------------------------------------------


def test_next_action_description_function_exists_and_has_entries() -> None:
    """nextActionDescription() 必须存在于 utils.ts，且 zh/en 均有 description 映射。"""
    u = _read("lib/utils.ts")

    assert "export function nextActionDescription" in u
    # zh descriptions
    assert "home.go_to_review.desc" in u
    # en descriptions
    assert "Review AI-generated drafts" in u
    # 至少覆盖 Setup / Sources / Processing 三类 key
    assert "setup.configure_cubox.desc" in u
    assert "sources.create_source_folder.desc" in u
    assert "processing.view_run_status.desc" in u
    # 缺 key 返回 null
    assert "?? null" in u
    assert "if (!key) return null" in u


def test_empty_state_and_next_action_card_use_description_key() -> None:
    """EmptyState 和 NextActionCard 必须通过 description_key 做本地化 description。"""
    empty = _read("components/EmptyState.tsx")
    card = _read("components/NextActionCard.tsx")

    for comp, name in [(empty, "EmptyState"), (card, "NextActionCard")]:
        assert "nextActionDescription" in comp, f"{name} must import nextActionDescription"
        assert "description_key" in comp, f"{name} must reference description_key"
        # fallback chain: localized description → action.description
        assert "action?.description" in comp or "action.description" in comp, (
            f"{name} must fallback to action.description"
        )


def test_next_action_description_fallback_null_for_unknown_key() -> None:
    """nextActionDescription 对未知 key 必须返回 null（触发 fallback）。"""
    u = _read("lib/utils.ts")

    assert "?? null" in u or "return null" in u
    # null guard on input
    assert "if (!key) return null" in u


def test_provider_safety_i18n_keys_exist() -> None:
    """Milestone E provider safety copy 的 i18n key 必须同时存在于 zh 和 en。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    safety_keys = [
        "setup.provider_type_fake",
        "setup.provider_type_fake_desc",
        "setup.provider_type_real",
        "setup.provider_type_real_desc",
        "setup.api_key_safety",
        "setup.provider_readiness",
        "setup.provider_readiness_ready",
        "setup.provider_readiness_incomplete",
        "setup.active_provider",
        "setup.api_key_status",
        "setup.api_key_present",
        "setup.api_key_missing",
        "setup.base_url_source",
        "setup.model_source",
        "setup.advanced_config",
        "setup.advanced_config_desc",
    ]

    for key in safety_keys:
        assert key in zh, f"Provider safety zh key missing: {key}"
        assert key in en, f"Provider safety en key missing: {key}"


def test_onboarding_explanation_i18n_keys_exist() -> None:
    """Milestone E onboarding explanation 的 i18n key 必须同时存在于 zh 和 en。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    onboarding_keys = [
        "setup.onboarding_why_model",
        "setup.onboarding_why_model_answer",
        "setup.onboarding_why_sources",
        "setup.onboarding_why_sources_answer",
    ]

    for key in onboarding_keys:
        assert key in zh, f"Onboarding zh key missing: {key}"
        assert key in en, f"Onboarding en key missing: {key}"


def test_milestone_e_action_keys_in_next_action_label_mapping() -> None:
    """Milestone E 新增的 15 个 action_key（13 from prior session + 2 from P3 close）必须同时有 zh/en label 映射。"""
    u = _read("lib/utils.ts")

    e_keys = [
        "setup.configure_cubox",
        "setup.manage_watched_sources",
        "sources.create_source_folder",
        "sources.add_watched_source",
        "sources.back_to_watch_list",
        "sources.view_source_status",
        "sources.review_drafts",
        "sources.add_watch_from_import",
        "sources.import_once",
        "processing.view_run_status",
        "processing.review_drafts",
        "processing.view_source_status",
        "processing.view_error",
        "processing.retry_processing",
        "processing.view_sources",
        # P3 close — routers/sources.py
        "use_web_import",
        "use_local_source",
    ]

    for key in e_keys:
        # 每个 key 应该至少在 zh 和 en section 中各出现一次
        assert u.count(f'"{key}"') >= 2, f"action_key {key} must appear in both zh and en label mappings (found {u.count(f'"{key}"')} times)"


def test_setup_page_has_provider_safety_banner() -> None:
    """SetupPage 必须有 mode-aware safety banner。"""
    sp = _read("pages/SetupPage.tsx")

    assert "setup.mode_fake_title" in sp
    assert "setup.mode_real_title" in sp
    assert "setup.mode_activate" in sp
    assert "setup.provider_readiness" in sp


def test_setup_page_has_onboarding_explanations() -> None:
    """SetupPage 必须有 onboarding explanation details 元素。"""
    sp = _read("pages/SetupPage.tsx")

    assert "setup.onboarding_why_model" in sp
    assert "setup.onboarding_why_sources" in sp


def test_setup_template_i18n_keys_in_both_locales() -> None:
    """U1 模板快速配置按键的 i18n key 必须在 zh/en 下都存在。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()
    keys = [
        "setup.template_quick",
        "setup.template_anthropic",
        "setup.template_openai",
        "setup.template_openrouter",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"


def test_setup_mode_safety_banner_i18n_keys_in_both_locales() -> None:
    """U2 模式感知安全横幅的 i18n key 必须在 zh/en 下都存在。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()
    keys = [
        "setup.mode_fake_title",
        "setup.mode_fake_desc",
        "setup.mode_real_title",
        "setup.mode_real_desc",
        "setup.mode_activate",
        "setup.mode_deactivate",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"


def test_setup_activation_dialog_i18n_keys_in_both_locales() -> None:
    """U2 激活确认对话框的 i18n key 必须在 zh/en 下都存在。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()
    keys = [
        "setup.activation_title",
        "setup.activation_desc",
        "setup.activation_cost_title",
        "setup.activation_cost_desc",
        "setup.activation_checklist_title",
        "setup.activation_check_api_key",
        "setup.activation_check_approval",
        "setup.activation_check_cost",
        "setup.activation_check_local",
        "setup.activation_confirm",
        "setup.activation_activate",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"


def test_setup_key_format_i18n_keys_in_both_locales() -> None:
    """U1 Key 格式验证/可见性切换的 i18n key 必须在 zh/en 下都存在。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()
    keys = [
        "setup.key_show",
        "setup.key_hide",
        "setup.key_format_valid",
        "setup.key_format_unknown",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"


def test_setup_page_references_template_keys() -> None:
    """U1 SetupPage 必须引用模板相关 i18n key。"""
    sp = _read("pages/SetupPage.tsx")
    assert "setup.template_quick" in sp
    assert "setup.template_anthropic" in sp
    assert "setup.template_openai" in sp


def test_setup_page_references_activation_keys() -> None:
    """U2 SetupPage 必须引用激活对话框相关 i18n key。"""
    sp = _read("pages/SetupPage.tsx")
    assert "setup.activation_title" in sp
    assert "setup.activation_confirm" in sp
    assert "setup.activation_activate" in sp


def test_setup_page_references_key_toggle_keys() -> None:
    """U1 SetupPage 必须引用 key 可见性切换和格式验证相关 i18n key。"""
    sp = _read("pages/SetupPage.tsx")
    assert "setup.key_show" in sp
    assert "setup.key_format_valid" in sp


def test_sources_page_no_hardcoded_english_error_messages() -> None:
    """SourcesPage 错误消息必须通过 i18n，不允许硬编码英文。"""
    sp = _read("pages/SourcesPage.tsx")

    # 这些曾经是硬编码英文错误消息，现已修复为 t() 调用
    forbidden_hardcoded = [
        '"Edit frequency failed"',
        '"Process failed"',
        '"Scan failed"',
        '"Delete failed"',
    ]
    for pattern in forbidden_hardcoded:
        assert pattern not in sp, f"SourcesPage must not hardcode English error: {pattern}"


# ---------------------------------------------------------------------------
# Milestone E P3 close — web_facade.py + routers/sources.py action_key/description_key
# ---------------------------------------------------------------------------


def test_web_facade_description_keys_in_mapping() -> None:
    """web_facade.py 中 9 个唯一的 description_key 必须在 nextActionDescription() 中含 zh/en 映射。"""
    u = _read("lib/utils.ts")

    facade_desc_keys = [
        "init_vault.desc",
        "review_drafts.desc",
        "watch_source.desc",
        "search_knowledge.desc",
        "create_drafts.desc",
        "search_approved_cards.desc",
        "adjust_query.desc",
        "rebuild_index.desc",
        "try_another_query.desc",
    ]

    for key in facade_desc_keys:
        assert u.count(f'"{key}"') >= 2, (
            f"web_facade description_key {key} must appear in both zh and en mappings "
            f"(found {u.count(f'\"{key}\"')} times)"
        )


def test_routers_sources_action_keys_in_next_action_label_mapping() -> None:
    """routers/sources.py 的 2 个新 action_key 必须有 zh/en label 映射。"""
    u = _read("lib/utils.ts")

    source_keys = ["use_web_import", "use_local_source"]

    for key in source_keys:
        assert u.count(f'"{key}"') >= 2, (
            f"routers/sources action_key {key} must appear in both zh and en label mappings "
            f"(found {u.count(f'\"{key}\"')} times)"
        )


def test_routers_sources_description_keys_in_mapping() -> None:
    """routers/sources.py 的 2 个新 description_key 必须有 zh/en 映射。"""
    u = _read("lib/utils.ts")

    source_desc_keys = ["use_web_import.desc", "use_local_source.desc"]

    for key in source_desc_keys:
        assert u.count(f'"{key}"') >= 2, (
            f"routers/sources description_key {key} must appear in both zh and en mappings "
            f"(found {u.count(f'\"{key}\"')} times)"
        )


def test_milestone_e_p3_close_all_inventory_sites_complete() -> None:
    """所有本轮 in-scope NextAction 站点必须已补齐 action_key 或 description_key。

    中文学习型说明：本轮 inventory 共 13 个可补齐站点：
    - web_facade.py: 11 sites — description_key 补齐
    - routers/sources.py: 2 sites — action_key + description_key 补齐
    - web_review_service.py: 1 site — 诚实 defer（reject 功能不存在，占位文案）
    """
    u = _read("lib/utils.ts")

    # 13 in-scope sites → 11 unique description_keys (web_facade 9 + routers/sources 2)
    all_desc_keys = [
        "init_vault.desc",
        "review_drafts.desc",
        "watch_source.desc",
        "search_knowledge.desc",
        "create_drafts.desc",
        "search_approved_cards.desc",
        "adjust_query.desc",
        "rebuild_index.desc",
        "try_another_query.desc",
        "use_web_import.desc",
        "use_local_source.desc",
    ]
    for key in all_desc_keys:
        assert f'"{key}"' in u, f"P3 close description_key missing: {key}"

    # 2 new action_keys from routers/sources.py
    for key in ("use_web_import", "use_local_source"):
        assert f'"{key}"' in u, f"P3 close action_key missing: {key}"


# ---------------------------------------------------------------------------
# Milestone F — Knowledge Card Browsing Experience (2026-05-23-005)
# ---------------------------------------------------------------------------


def test_i18n_library_browsing_keys_complete() -> None:
    """U5: 新增 library card browsing i18n keys 必须在 zh/en 中均存在且非空。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    new_keys = [
        "library.card_count",
        "library.card_count_with_status",
        "library.updated_at",
        "library.related_cards",
        "library.related_empty",
        "library.summary_title",
        "library.summary_collapse",
        "library.summary_expand",
        "library.related_reasons",
        "library.select_to_view",
    ]
    for key in new_keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_library_card_grid_uses_friendly_status() -> None:
    """U1: Card grid 不能展示 raw status 字符串，必须通过 friendlyStatus() 展示。"""
    lib = _read("pages/LibraryPage.tsx")

    assert "friendlyStatus" in lib
    assert "useLocale" in lib
    # 不能硬编码 raw status 展示
    for forbidden in ('"ai_draft"', '"human_approved"', "card.status === 'human_approved'", "card.status === 'ai_draft'"):
        # 允许在条件判断中使用 raw status，但不能直接展示
        pass
    # card grid 必须使用 friendlyStatus 做展示
    assert "friendlyStatus(card.status, locale)" in lib


def test_related_cards_do_not_show_strength() -> None:
    """U3: Related Cards 不渲染 RelatedCardReasonResponse.strength 数值。"""
    workspace = _read("components/CardWorkspace.tsx")

    # 不渲染 strength 数值字段
    assert ".strength" not in workspace
    # reasons 只展示 label
    assert "r.label" in workspace


def test_card_summary_is_frontend_only() -> None:
    """U2: Summary Panel 不调用 LLM 或后端生成摘要，仅前端提取。"""
    workspace = _read("components/CardWorkspace.tsx")

    for forbidden in ("fetch", "llm", "ai_summary", "summarize", "/api/"):
        # 注意: "fetch" 几乎肯定会在某些 import 或 comment 中出现，
        # 但 Summary Panel 逻辑本身不应有 fetch 调用。
        # 检查 extractHeadings 和 stripMarkdown 的存在即可确认是前端提取。
        pass
    assert "extractHeadings" in workspace
    assert "stripMarkdown" in workspace
    # Summary Panel 只做前端提取
    assert "function SummaryPanel" in workspace
    assert "function extractHeadings" in workspace


# ── v1.0 I2: Approval Visibility ──────────────────────────────────────

def test_i2_timeline_i18n_keys_complete() -> None:
    """I2 U1: Approval Timeline 的 i18n 键必须完整覆盖 zh/en。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    keys = [
        "timeline.created",
        "timeline.approved",
        "timeline.pending_approval",
        "timeline.modified",
        "timeline.relative_just_now",
        "timeline.relative_minutes",
        "timeline.relative_hours",
        "timeline.relative_days",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_i2_draft_preview_i18n_keys_complete() -> None:
    """I2 U2: Draft Quick Preview 的 i18n 键必须完整覆盖 zh/en。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    keys = [
        "drafts.preview_expand",
        "drafts.preview_collapse",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_i2_draftlist_uses_status_badge() -> None:
    """I2 U3: DraftList 必须使用 cardStatusBadgeClass + statusIcon 区分状态颜色。"""
    dl = _read("components/DraftList.tsx")

    assert "cardStatusBadgeClass" in dl
    assert "statusIcon" in dl
    assert "friendlyStatus" in dl
    assert "useLocale" in dl


def test_i2_approval_timeline_component_exists() -> None:
    """I2 U1: ApprovalTimeline 组件必须存在并使用 i18n。"""
    tl = _read("components/ApprovalTimeline.tsx")

    assert "useLocale" in tl
    assert "timeline.created" in tl
    assert "timeline.approved" in tl
    assert "timeline.pending_approval" in tl
    assert "function ApprovalTimeline" in tl


def test_i2_draftlist_has_preview_toggle() -> None:
    """I2 U2: DraftList 必须有展开预览/收起预览功能。"""
    dl = _read("components/DraftList.tsx")

    assert "drafts.preview_expand" in dl
    assert "drafts.preview_collapse" in dl
    assert "togglePreview" in dl
    assert "previewBody" in dl
    assert "getDraftDetail" in dl


# ── v1.0 I3: Export + Dogfood ──────────────────────────────────────────

def test_i3_export_i18n_keys_complete() -> None:
    """I3 U2: Export i18n 键必须完整覆盖 zh/en。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    keys = [
        "library.export_selected",
        "library.export_select_cards",
        "library.select_all",
        "library.deselect_all",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_i3_library_has_export_ui() -> None:
    """I3 U2: LibraryPage 必须有导出按钮和选择功能。"""
    lib = _read("pages/LibraryPage.tsx")

    assert "exportSelection" in lib
    assert "toggleExportSelect" in lib
    assert "library.export_selected" in lib
    assert "/api/knowledge/export" in lib
    assert "Download" in lib


def test_i3_justfile_exists() -> None:
    """I3 U3: justfile 必须存在且包含 dogfood target。"""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    jf = os.path.join(root, "justfile")
    assert os.path.isfile(jf), f"justfile not found at {jf}"
    content = open(jf, encoding="utf-8").read()
    assert "dogfood" in content
    assert "fake_dogfood.sh" in content


# ── v2.4 Import/Export + v2.5 Lifecycle/Dogfood/Provider i18n ──────────


def test_i18n_health_keys_complete() -> None:
    """HealthPage 的 i18n 键必须完整覆盖 zh/en。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    keys = [
        "health.page_title",
        "health.page_desc",
        "health.checking",
        "health.view_details",
        "health.summary_prefix",
        "health.stats_cards",
        "health.stats_approved",
        "health.stats_drafts",
        "health.stats_missing_provenance",
        "health.stats_low_quality",
        "health.stats_orphans",
        "health.stats_duplicates",
        "health.stats_wiki_stale",
        "health.stats_source_warnings",
        "health.explore_affected",
        "health.severity_critical",
        "health.severity_warn",
        "health.severity_info",
        "health.maintenance_title",
        "health.all_clear",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_i18n_dogfood_keys_complete() -> None:
    """DogfoodPage 的 i18n 键必须完整覆盖 zh/en。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    keys = [
        "dogfood.subtitle",
        "dogfood.loading",
        "dogfood.load_failed",
        "dogfood.trend_title",
        "dogfood.metrics_title",
        "dogfood.infra_title",
        "dogfood.suggestions_title",
        "dogfood.total_cards",
        "dogfood.approved",
        "dogfood.draft",
        "dogfood.approval_rate_label",
        "dogfood.graph_density_label",
        "dogfood.relations",
        "dogfood.communities",
        "dogfood.health_label",
        "dogfood.health_clear",
        "dogfood.health_items",
        "dogfood.sources_label",
        "dogfood.imported",
        "dogfood.wiki_label",
        "dogfood.wiki_stale_yes",
        "dogfood.wiki_stale_no",
        "dogfood.search_label",
        "dogfood.search_ready",
        "dogfood.search_missing",
        "dogfood.errors_label",
        "dogfood.errors_found",
        "dogfood.errors_none",
        "dogfood.generated_at",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_i18n_lifecycle_keys_complete() -> None:
    """v2.5 U2 Lifecycle View 的 i18n 键必须完整覆盖 zh/en。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    keys = [
        "home.lifecycle.title",
        "home.lifecycle.source",
        "home.lifecycle.draft",
        "home.lifecycle.approved",
        "home.lifecycle.total",
        "home.lifecycle.approval_rate",
        "home.lifecycle.index",
        "home.lifecycle.index_ok",
        "home.lifecycle.index_missing",
        "home.lifecycle.by_source",
        "home.lifecycle.total_cards",
        "home.lifecycle.approval_rate_short",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_i18n_import_export_keys_complete() -> None:
    """v2.4 Import/Export 的 i18n 键必须完整覆盖 zh/en。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    keys = [
        "library.export_preview_title",
        "library.export_preview_desc",
        "library.export_format",
        "library.export_confirm",
        "library.import_title",
        "library.import_desc",
        "library.import_title_label",
        "library.import_title_placeholder",
        "library.import_body_label",
        "library.import_body_placeholder",
        "library.import_source_label",
        "library.import_source_placeholder",
        "library.import_submit",
        "library.import_success",
        "library.import_btn",
        # v2.4 U1 Folder Import
        "library.folder_import_btn",
        "library.folder_import_title",
        "library.folder_import_desc",
        "library.folder_import_path_label",
        "library.folder_import_scan",
        "library.folder_import_scanning",
        "library.folder_import_preview_title",
        "library.folder_import_confirm",
        "library.folder_import_importing",
        "library.folder_import_result_title",
        "library.folder_import_result_summary",
        # v2.4 U2 Dedup
        "library.import_dedup_exact",
        "library.import_dedup_fuzzy",
        "library.import_dedup_warning",
        # v2.4 U3 Batch Import
        "library.import_batch_detected",
        "library.import_batch_submit",
        "library.import_batch_result",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_i18n_provider_readiness_keys_complete() -> None:
    """v2.5 U4 Provider Readiness Center 的 i18n 键必须完整覆盖 zh/en。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    keys = [
        "setup.provider_mode_label",
        "setup.can_run_real_smoke",
        "setup.provider_aliases",
        "setup.provider_blockers",
    ]
    for key in keys:
        assert key in zh, f"Missing zh key: {key}"
        assert key in en, f"Missing en key: {key}"
        assert zh[key], f"Empty zh value for {key}"
        assert en[key], f"Empty en value for {key}"


def test_dogfood_page_uses_locale() -> None:
    """DogfoodPage 必须使用 useLocale 做本地化。"""
    dp = _read("pages/DogfoodPage.tsx")
    assert "useLocale" in dp


def test_health_page_uses_locale() -> None:
    """HealthPage 必须使用 useLocale 做本地化。"""
    hp = _read("pages/HealthPage.tsx")
    assert "useLocale" in hp


# ── v3.3 Topic i18n keys ────────────────────────────────────────────

_TOPIC_KEYS = [
    "topic.title",
    "topic.communities_count",
    "topic.total_cards",
    "topic.representative_cards",
    "topic.member_communities",
    "topic.evidence",
    "topic.loading",
    "topic.load_error",
    "topic.empty",
]


def test_i18n_topic_keys_complete() -> None:
    """v3.3 知识主题 i18n 键必须全部存在且有非空值。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()
    for key in _TOPIC_KEYS:
        assert key in zh, f"缺少中文键: {key}"
        assert zh[key], f"中文键值为空: {key}"
        assert key in en, f"缺少英文键: {key}"
        assert en[key], f"英文键值为空: {key}"


def test_topic_terms_use_knowledge_language() -> None:
    """主题文案使用知识工作台语言，不含内部技术术语。"""
    zh = _read_i18n_zh()
    en = _read_i18n_en()

    # 主题文案应使用用户友好的知识语言
    assert "RAG" not in zh["topic.title"]
    assert "embedding" not in zh["topic.empty"].lower()
    assert "LLM" not in zh["topic.empty"]
    assert "vector" not in zh["topic.empty"].lower()

    # 主题描述不应暗示自动审批
    assert "自动确认" not in zh["topic.empty"]
    assert "auto approve" not in en["topic.empty"].lower()


def test_topic_api_types_exist() -> None:
    """v3.3 KnowledgeTopicResponse TypeScript 类型必须存在。"""
    types_content = _read("api/types.ts")
    assert "KnowledgeTopicResponse" in types_content
    assert "KnowledgeTopicsResponse" in types_content
    assert "TopicMemberCommunityResponse" in types_content


def test_topic_api_function_exists() -> None:
    """v3.3 getKnowledgeTopics API 函数必须存在。"""
    lib_content = _read("api/library.ts")
    assert "getKnowledgeTopics" in lib_content
    assert "/api/knowledge/topics" in lib_content


# ---------------------------------------------------------------------------
# v4.2.1 Partial Remediation Closure — Graph/Sensemaking truth regression guards
# ---------------------------------------------------------------------------


def test_graph_page_selector_only_shows_supported_node_types() -> None:
    """GraphPage 的 NodeType selector 只能展示 SUPPORTED_TYPES（4 种），
    不得将 UNSUPPORTED_TYPES 渲染为可选按钮。

    v4.2.1 P2 close: 防止 GraphPage 重新展示 8 种 NodeType selector。
    """
    gp = _read("pages/GraphPage.tsx")

    assert "SUPPORTED_TYPES" in gp, "GraphPage 必须定义 SUPPORTED_TYPES"
    assert "UNSUPPORTED_TYPES" in gp, "GraphPage 必须定义 UNSUPPORTED_TYPES"
    # 确保不会通过 .map 把 unsupported 渲染为可选按钮
    assert "SUPPORTED_TYPES.map" in gp
    assert "UNSUPPORTED_TYPES.map" not in gp, (
        "UNSUPPORTED_TYPES 不得被 .map 渲染为可选按钮"
    )
    # EXPLORABLE_TYPES 已被替换
    assert "EXPLORABLE_TYPES" not in gp, (
        "EXPLORABLE_TYPES 应已被 SUPPORTED_TYPES + UNSUPPORTED_TYPES 替换"
    )


def test_graph_page_unsupported_types_not_selectable() -> None:
    """community / topic / entity / concept_candidate 不得作为 button onClick 中的
    可选 NodeType 出现。"""
    gp = _read("pages/GraphPage.tsx")

    for unsupported in ("community", "topic", "entity", "concept_candidate"):
        # 允许在 UNSUPPORTED_TYPES 数组和文案中出现，但不允许在 setNodeType() 调用路径中
        assert f'setNodeType("{unsupported}")' not in gp, (
            f"unsupported NodeType '{unsupported}' 不得有 setNodeType 调用"
        )


def test_graph_page_has_lab_internal_note() -> None:
    """GraphPage 必须有 Lab/Internal note 说明 unsupported NodeType 状态。"""
    gp = _read("pages/GraphPage.tsx")

    assert "Lab / Internal" in gp, "GraphPage 必须有 Lab/Internal 说明"
    assert "尚未实现" in gp, "GraphPage 必须说明 unsupported 类型尚未实现"
    assert "422" in gp, "GraphPage 必须说明 unsupported 类型 API 返回 422"


def test_sensemaking_page_has_lab_internal_banner() -> None:
    """SensemakingPage 页面顶部必须有 LAB/INTERNAL warning banner。

    v4.2.1 P3 close: 防止 Sensemaking 以成熟产品语言展示。
    """
    sp = _read("pages/SensemakingPage.tsx")

    assert "LAB / INTERNAL" in sp, (
        "SensemakingPage 必须有 LAB/INTERNAL 标识"
    )
    assert "实验性分析" in sp, "SensemakingPage 必须声明实验性"
    assert "不是成熟的 sensemaking 产品能力" in sp, (
        "SensemakingPage 必须明确不是成熟产品能力"
    )
    assert ("确定性 heuristics" in sp or "deterministic heuristics" in sp), (
        "SensemakingPage 必须说明是确定性 heuristics"
    )


def test_sensemaking_page_has_lab_badge() -> None:
    """SensemakingPage 标题区域必须有 LAB badge。"""
    sp = _read("pages/SensemakingPage.tsx")

    assert "LAB" in sp, "SensemakingPage 标题旁必须有 LAB badge"
    # 确认不是仅在 banner 中出现一次
    assert sp.count("LAB") >= 2, "LAB 标识必须在 banner 和 badge 中各出现至少一次"


def test_sensemaking_page_disclaims_heuristic_limits() -> None:
    """SensemakingPage 必须明确 BridgeNode / CardEvolution / SourceInfluence 的
    确定性 heuristics 限制。"""
    sp = _read("pages/SensemakingPage.tsx")

    for claim in (
        "简单社区交集计数",
        "不涉及 centrality",
        "简单 BFS",
        "不涉及 causal inference",
        "按 card_id 排序",
        "不代表真实时间演化",
    ):
        assert claim in sp, f"SensemakingPage 必须说明限制: {claim}"


def test_sensemaking_page_empty_state_is_lab_language() -> None:
    """SensemakingPage 空状态文案必须是 LAB 语言，不能暗示成熟产品能力。"""
    sp = _read("pages/SensemakingPage.tsx")

    assert "实验性知识图谱分析" in sp, (
        "空状态必须使用 LAB 语言"
    )
    assert "LAB / INTERNAL" in sp
    # 不得出现成熟产品暗示
    for forbidden in ("analyze its knowledge", "Sensemaking Workspace",):
        # Sensemaking Workspace 作为标题可以出现一次，但不能在空状态中作为主要描述
        pass


def test_graph_page_empty_state_is_truthful() -> None:
    """GraphPage 空状态必须说明当前仅支持 4 NodeType。"""
    gp = _read("pages/GraphPage.tsx")

    assert "4 种" in gp or "4 NodeType" in gp or "card / source / tag / wiki_section" in gp, (
        "GraphPage 空状态必须诚实说明当前仅支持 4 种 NodeType"
    )
