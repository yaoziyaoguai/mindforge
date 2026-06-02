import { AlertTriangle, CheckCircle, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Locale } from "./i18n";
import { t } from "./i18n";

export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function statusTone(status: string): string {
  if (status === "ok") return "text-safe bg-safe/10 border-safe/20";
  if (status === "warn") return "text-warn bg-warn/10 border-warn/20";
  if (status === "error") return "text-danger bg-danger/10 border-danger/20";
  return "text-muted bg-muted/10 border-line";
}

/** 状态图标映射 —— 色盲用户可通过图标形状区分状态，不依赖颜色。
 *  不改 statusTone() 签名，在 badge 渲染处组合调用。
 *  返回 LucideIcon 组件或 null（未知状态不渲染图标）。 */
export function statusIcon(status: string): LucideIcon | null {
  if (status === "ok") return CheckCircle;
  if (status === "warn") return AlertTriangle;
  if (status === "error") return X;
  return null;
}

/** 状态标签 —— locale 参数可选，默认 zh；传入 locale 时返回对应语言标签。 */
export function statusLabel(status: string, locale?: Locale): string {
  const key = status === "ok" ? "status.ok" : status === "warn" ? "status.warn" : status === "error" ? "status.error" : null;
  if (!key) return "";
  return locale ? t(key, locale) : t(key, "zh");
}

export function truncateMiddle(value: string, max = 72): string {
  if (value.length <= max) return value;
  const head = Math.ceil((max - 3) / 2);
  const tail = Math.floor((max - 3) / 2);
  return `${value.slice(0, head)}...${value.slice(-tail)}`;
}

/** 用户侧状态文案映射 —— 把内部状态码（ai_draft、human_approved 等）转成用户可理解的标签。
 *  不改数据字段、不改 API 返回值、不改 approval 语义。
 *  locale 参数可选，默认 zh；传入 locale 时返回对应语言标签。
 *  技术原始状态通过 CardWorkspace 的 "Technical details" 折叠区保留，满足开发排查需要。 */
/** track 值 → i18n key 映射。已知内部 track 值（如 unrouted）转用户可读标签；
 *  用户自定义 track 原样展示。*/
export function friendlyTrack(track?: string | null, locale?: Locale): string {
  const map: Record<string, string> = {
    unrouted: "track.unrouted",
  };
  if (track && map[track]) {
    return locale ? t(map[track], locale) : t(map[track], "zh");
  }
  return track || "-";
}

/** 将内部 provider/routing ID 映射为用户可读名称。
 *  __model_routing__ 等双下划线前缀名称为内部路由配置，非用户可见模型。 */
export function friendlyProviderName(name?: string | null, locale?: Locale): string {
  if (!name) return "-";
  if (name === "__model_routing__") {
    return locale === "en" ? "Per-stage routing" : "按阶段路由";
  }
  if (name.startsWith("__") && name.endsWith("__")) {
    return locale === "en" ? "Auto routing" : "自动路由";
  }
  return name;
}

export function friendlyStatus(status?: string | null, locale?: Locale): string {
  const keyMap: Record<string, string> = {
    ai_draft: "status.ai_draft",
    human_approved: "status.human_approved",
    processed: "status.processed",
    skipped: "status.skipped",
    failed: "status.failed",
    pending: "status.pending",
    imported: "status.imported",
  };
  if (status && keyMap[status]) {
    return locale ? t(keyMap[status], locale) : t(keyMap[status], "zh");
  }
  return status || "-";
}

/** 卡片生命周期状态 → 徽章样式类名。
 *  ai_draft → 橙色调，human_approved → 绿色调，统一视觉语言。 */
export function cardStatusBadgeClass(status?: string | null): string {
  if (status === "human_approved") return "bg-safe/10 text-safe border-safe/20";
  if (status === "ai_draft") return "bg-warn/10 text-warn border-warn/20";
  return "bg-muted/10 text-muted border-line";
}

/* ── Display Mapping 函数 ─────────────────────────────────────────────
 * 中文学习型说明：以下函数将后端 internal id / status code 映射为用户可读的本地化文案。
 * 不改后端 API、不改数据字段 —— 仅前端 presentation 层做 localized display mapping。
 * 后端 internal id 保留在次要位置（小字、灰色、括号内）满足开发排查需要。
 *
 * 为什么不在后端翻译：
 * - 后端应返回 machine-readable identifiers，前端负责 human-readable labels
 * - 多语言切换是纯前端关注点，不应耦合到 API contract
 * - 后端 id 可能用于 route/逻辑判断，不应随着 locale 变化
 *
 * 为什么用户内容 / 专有名词不翻译：
 * - 用户创建的内容（卡片正文、source title）是用户数据，翻译会引入语义偏差
 * - 产品名 "MindForge"、算法名 "BM25"、adapter 名是专有标识，翻译反而降低可辨识度
 * - 技术标识（modelId、run_id）是用户自定义或系统生成，保留原名是唯一正确的引用方式
 * ─────────────────────────────────────────────────────────────────── */

/** workflow step id → 本地化展示标签。
 *  后端 config.py REQUIRED_STAGES 固定为 triage/distill/link_suggestion/
 *  review_questions/action_extraction，前端按 step.id 匹配。 */
export function workflowStepLabel(stepId: string, locale?: Locale): string {
  const labels: Record<Locale, Record<string, string>> = {
    zh: {
      triage: "初筛",
      distill: "提炼",
      link_suggestion: "关联建议",
      review_questions: "复习问题",
      action_extraction: "行动项提取",
    },
    en: {
      triage: "Triage",
      distill: "Distill",
      link_suggestion: "Link Suggestion",
      review_questions: "Review Questions",
      action_extraction: "Action Extraction",
    },
  };
  return labels[locale ?? "zh"]?.[stepId] ?? stepId;
}

/** workflow step id → 本地化 purpose 文案。
 *  后端返回的 step.purpose 是中文描述，en 模式下需要前端做 display mapping。
 *  与 workflowStepLabel() 同模式：按 step.id 匹配，未匹配时 fallback 到原始 purpose。 */
export function workflowStepPurpose(stepId: string, fallback: string, locale?: Locale): string {
  const purposes: Record<Locale, Record<string, string>> = {
    zh: {
      triage: "初筛：快速扫描来源文件，过滤明显不相关内容，标记候选片段。",
      distill: "提炼：从候选片段中提取核心知识点，生成结构化摘要。",
      link_suggestion: "关联建议：检测与已有知识卡片的潜在关联，建议双向链接。",
      review_questions: "复习问题：基于提炼结果生成复习问题，辅助间隔重复。",
      action_extraction: "行动项提取：识别可操作的任务项，生成行动建议。",
    },
    en: {
      triage: "Triage: scan source files, filter irrelevant content, and mark candidate segments.",
      distill: "Distill: extract core knowledge points from candidate segments and generate structured summaries.",
      link_suggestion: "Link Suggestion: detect potential connections to existing knowledge cards and suggest bidirectional links.",
      review_questions: "Review Questions: generate review questions based on distilled results for spaced repetition.",
      action_extraction: "Action Extraction: identify actionable tasks and generate action suggestions.",
    },
  };
  return purposes[locale ?? "zh"]?.[stepId] ?? fallback;
}

/** 后端 active_strategy_status → 本地化展示标签。 */
export function strategyStatusLabel(status: string, locale?: Locale): string {
  const labels: Record<Locale, Record<string, string>> = {
    zh: { "default workflow": "默认工作流" },
    en: { "default workflow": "Default workflow" },
  };
  return labels[locale ?? "zh"]?.[status] ?? status;
}

/** 后端 active_strategy_label → 本地化展示标签。 */
export function strategyNameLabel(name: string, locale?: Locale): string {
  const labels: Record<Locale, Record<string, string>> = {
    zh: { "Knowledge Card Workflow": "知识卡片工作流" },
    en: { "Knowledge Card Workflow": "Knowledge Card Workflow" },
  };
  return labels[locale ?? "zh"]?.[name] ?? name;
}

/** 后端 active_strategy_description → 本地化展示文案。
 *  与 strategyNameLabel() 同模式：按 description 原文匹配，未匹配时 fallback 到原始文案。 */
export function strategyDescriptionLabel(description: string, locale?: Locale): string {
  const descriptions: Record<Locale, Record<string, string>> = {
    zh: {
      "默认 Knowledge Card Workflow：内部执行 triage → distill → link_suggestion → review_questions → action_extraction 五段 prompt pipeline，生成 ai_draft Knowledge Card，必须经人工 approve 才成为正式知识。":
        "默认 Knowledge Card Workflow：内部执行 triage → distill → link_suggestion → review_questions → action_extraction 五段 prompt pipeline，生成 ai_draft Knowledge Card，必须经人工 approve 才成为正式知识。",
    },
    en: {
      "默认 Knowledge Card Workflow：内部执行 triage → distill → link_suggestion → review_questions → action_extraction 五段 prompt pipeline，生成 ai_draft Knowledge Card，必须经人工 approve 才成为正式知识。":
        "Default Knowledge Card Workflow: executes a five-stage prompt pipeline internally — triage → distill → link_suggestion → review_questions → action_extraction — generating ai_draft Knowledge Cards that must be explicitly approved before becoming official knowledge.",
    },
  };
  return descriptions[locale ?? "zh"]?.[description] ?? description;
}

/** source.status → 本地化展示标签。 */
export function sourceStatusLabel(status: string, locale?: Locale): string {
  const labels: Record<Locale, Record<string, string>> = {
    zh: { active: "监控中", paused: "已暂停", error: "异常" },
    en: { active: "Watching", paused: "Paused", error: "Error" },
  };
  return labels[locale ?? "zh"]?.[status] ?? status;
}

/** source.processing_status → 本地化展示标签。 */
export function sourceRunStatusLabel(status?: string | null, locale?: Locale): string {
  if (!status) return "-";
  const labels: Record<Locale, Record<string, string>> = {
    zh: { idle: "空闲", queued: "排队中", running: "处理中", completed: "已完成", failed: "失败", partial_failed: "部分失败" },
    en: { idle: "Idle", queued: "Queued", running: "Running", completed: "Completed", failed: "Failed", partial_failed: "Partial failure" },
  };
  return labels[locale ?? "zh"]?.[status] ?? status.replace(/_/g, " ");
}

/** source.due_status → 本地化展示标签。 */
export function sourceDueStatusLabel(status?: string | null, locale?: Locale): string {
  if (!status) return "-";
  const labels: Record<Locale, Record<string, string>> = {
    zh: { due: "到期", overdue: "已逾期", upcoming: "未到", manual: "手动" },
    en: { due: "Due", overdue: "Overdue", upcoming: "Upcoming", manual: "Manual" },
  };
  return labels[locale ?? "zh"]?.[status] ?? status;
}

/* NextAction action_key → 本地化展示标签。
 * 中文学习型说明：action_key 是后端提供的稳定 machine-readable identifier，
 * 前端据此做 localized display mapping。label/description 作为兼容 fallback，
 * 缺 action_key 的 NextAction 直接展示 label。
 *
 * 为什么用 action_key 而非 label 匹配：
 * - label 是后端生成的自由文本，无稳定性保证，后续可能修改措辞
 * - action_key 是 contract 的一部分，不随 locale 或措辞调整变化
 * - 不用字符串匹配做语言检测，避免脆弱性
 *
 * 返回 null 表示 key 不在映射表中，调用方应 fallback 到 action.label。 */
export function nextActionLabel(key: string | null | undefined, locale?: Locale): string | null {
  if (!key) return null;
  const labels: Record<Locale, Record<string, string>> = {
    zh: {
      init_vault: "初始化知识库",
      review_drafts: "审核草稿",
      watch_source: "添加知识源",
      search_knowledge: "搜索知识",
      create_drafts: "新建草稿",
      search_approved_cards: "搜索已确认知识",
      adjust_query: "调整查询",
      try_another_query: "换一个关键词",
      rebuild_index: "重建索引",
      // Milestone D — HomePage / EmptyState action_key
      "home.go_to_review": "审阅 AI 草稿",
      "home.go_to_library": "浏览知识库",
      "home.configure_sources": "管理知识源",
      "home.go_to_setup": "检查配置",
      "empty.no_drafts": "添加知识源",
      "empty.no_approved": "审阅 AI 草稿",
      "empty.no_sources": "添加知识源",
      "empty.no_results": "调整查询",
      "empty.no_wiki": "重建 Wiki",
      // Milestone E — Setup / Sources / Processing action_key
      "setup.configure_cubox": "使用本地知识源",
      "setup.manage_watched_sources": "管理知识源",
      "sources.create_source_folder": "创建知识源目录",
      "sources.add_watched_source": "添加监控知识源",
      "sources.back_to_watch_list": "返回监控列表",
      "sources.view_source_status": "查看知识源状态",
      "sources.review_drafts": "审阅草稿",
      "sources.add_watch_from_import": "添加监控",
      "sources.import_once": "一次性导入",
      "processing.view_run_status": "查看知识源状态",
      "processing.review_drafts": "审阅草稿",
      "processing.view_source_status": "查看知识源状态",
      "processing.view_error": "查看错误",
      "processing.retry_processing": "重试处理",
      "processing.view_sources": "查看知识源",
      // Milestone E P3 close — routers/sources.py
      "use_web_import": "使用 Web 导入",
      "use_local_source": "使用本地知识源",
    },
    en: {
      init_vault: "Initialize vault",
      review_drafts: "Review drafts",
      watch_source: "Watch or import source",
      search_knowledge: "Search knowledge",
      create_drafts: "Create drafts",
      search_approved_cards: "Search approved cards",
      adjust_query: "Adjust query",
      try_another_query: "Try another query",
      rebuild_index: "Rebuild index",
      // Milestone D — HomePage / EmptyState action_key
      "home.go_to_review": "Review drafts",
      "home.go_to_library": "Browse library",
      "home.configure_sources": "Manage sources",
      "home.go_to_setup": "Check setup",
      "empty.no_drafts": "Add sources",
      "empty.no_approved": "Review drafts",
      "empty.no_sources": "Add sources",
      "empty.no_results": "Adjust query",
      "empty.no_wiki": "Rebuild wiki",
      // Milestone E — Setup / Sources / Processing action_key
      "setup.configure_cubox": "Use local sources",
      "setup.manage_watched_sources": "Manage sources",
      "sources.create_source_folder": "Create source folder",
      "sources.add_watched_source": "Add watched source",
      "sources.back_to_watch_list": "Back to watch list",
      "sources.view_source_status": "View source status",
      "sources.review_drafts": "Review drafts",
      "sources.add_watch_from_import": "Add watch",
      "sources.import_once": "Import once",
      "processing.view_run_status": "View source status",
      "processing.review_drafts": "Review drafts",
      "processing.view_source_status": "View source status",
      "processing.view_error": "View error",
      "processing.retry_processing": "Retry processing",
      "processing.view_sources": "View sources",
      // Milestone E P3 close — routers/sources.py
      "use_web_import": "Use Web import",
      "use_local_source": "Use local source",
    },
  };
  return labels[locale ?? "zh"]?.[key] ?? null;
}

/* NextAction description_key → 本地化 description 文案。
 * 与 nextActionLabel() 同模式：后端提供稳定的 description_key，
 * 前端据此做 localized display mapping。缺 key 或未匹配时返回 null，
 * 调用方应 fallback 到 action.description。
 *
 * 中文学习型说明：description_key 解决 EmptyState / NextActionCard 中
 * action.description 为原始英文、无法随 zh/en 切换的问题。不翻译用户内容。 */
export function nextActionDescription(key: string | null | undefined, locale?: Locale): string | null {
  if (!key) return null;
  const descriptions: Record<Locale, Record<string, string>> = {
    zh: {
      "home.go_to_review.desc": "审核 AI 生成的草稿，决定批准或驳回。",
      "home.go_to_library.desc": "浏览已确认的知识卡片和 Wiki。",
      "home.configure_sources.desc": "管理知识源和自动处理流程。",
      "home.go_to_setup.desc": "配置模型连接和处理参数。",
      "empty.no_drafts.desc": "添加知识源并开始处理，生成第一批 AI 草稿。",
      "empty.no_approved.desc": "审核 AI 草稿并确认优质卡片，构建知识库。",
      "empty.no_sources.desc": "添加 Markdown、PDF 或 DOCX 文件作为知识源。",
      "empty.no_results.desc": "调整搜索词或筛选条件后重试。",
      "empty.no_wiki.desc": "确认知识卡片后重建 Wiki，生成结构化知识视图。",
      // Setup / Sources / Processing descriptions
      "setup.configure_cubox.desc": "第一阶段请添加本地文件或文件夹作为知识源。",
      "setup.manage_watched_sources.desc": "管理已监控的知识源和一次性导入。",
      "sources.create_source_folder.desc": "创建 inbox 子目录后再放入本地知识源文件。",
      "sources.add_watched_source.desc": "注册文件或文件夹并后台处理当前内容。",
      "sources.back_to_watch_list.desc": "确认默认 inbox 和用户添加的监控项。",
      "sources.view_source_status.desc": "查看知识源处理状态、跳过原因或错误信息。",
      "sources.review_drafts.desc": "新生成的 AI 草稿需要手动审核确认。",
      "sources.add_watch_from_import.desc": "支持文件和文件夹；后续自动处理暂未实现。",
      "sources.import_once.desc": "适合一次性导入外部文件或文件夹。",
      "processing.view_run_status.desc": "后台处理正在进行中，可继续使用 MindForge。",
      "processing.review_drafts.desc": "审核生成的 AI 草稿后再确认保存。",
      "processing.view_source_status.desc": "查看此知识源的处理摘要。",
      "processing.view_error.desc": "打开知识源页面查看最新处理错误。",
      "processing.retry_processing.desc": "修复问题后重新点击「立即处理」。",
      "processing.view_sources.desc": "未生成草稿；知识源页面显示跳过原因。",
      // Milestone E P3 close — web_facade.py description_key
      "init_vault.desc": "当前知识库路径不存在；请先创建本地知识库。",
      "review_drafts.desc": "有 AI 草稿等待人工审核和显式确认。",
      "watch_source.desc": "添加文件或文件夹作为知识源，自动生成 AI 草稿。",
      "search_knowledge.desc": "本地知识库已就绪；可以搜索已确认的知识卡片。",
      "create_drafts.desc": "没有 AI 草稿。先在知识源页面添加或导入文件/文件夹。",
      "search_approved_cards.desc": "输入关键词后使用本地 BM25 词法匹配查询已确认的知识卡片。",
      "adjust_query.desc": "搜索查询无法执行，请缩短或调整关键词后重试。",
      "rebuild_index.desc": "索引缺失或过期时可重建本地 BM25 索引。",
      "try_another_query.desc": "没有命中已确认的知识卡片；换一个关键词或先确认 AI 草稿。",
      // Milestone E P3 close — routers/sources.py description_key
      "use_web_import.desc": "Web 导入不加入监控知识源，也不会自动确认。",
      "use_local_source.desc": "请先添加本地文件或文件夹知识源；不会联网或自动确认。",
    },
    en: {
      "home.go_to_review.desc": "Review AI-generated drafts and decide to approve or reject.",
      "home.go_to_library.desc": "Browse approved knowledge cards and wiki.",
      "home.configure_sources.desc": "Manage knowledge sources and processing.",
      "home.go_to_setup.desc": "Configure model connections and processing parameters.",
      "empty.no_drafts.desc": "Add sources to start processing and generate your first AI drafts.",
      "empty.no_approved.desc": "Review drafts and approve quality cards to build your knowledge base.",
      "empty.no_sources.desc": "Add markdown, PDF, or DOCX files as knowledge sources.",
      "empty.no_results.desc": "Try adjusting your search terms or filters.",
      "empty.no_wiki.desc": "Approve cards and rebuild the wiki to generate a structured knowledge view.",
      // Setup / Sources / Processing descriptions
      "setup.configure_cubox.desc": "Phase 1: add local files or folders as knowledge sources.",
      "setup.manage_watched_sources.desc": "Manage watched sources and one-time imports.",
      "sources.create_source_folder.desc": "Create the inbox subdirectory before adding local source files.",
      "sources.add_watched_source.desc": "Register a file or folder and process current content in background.",
      "sources.back_to_watch_list.desc": "Verify default inbox and remaining user-added watches.",
      "sources.view_source_status.desc": "Check source processing status, skip reasons, or errors.",
      "sources.review_drafts.desc": "New AI drafts require manual review before approval.",
      "sources.add_watch_from_import.desc": "Supports files and folders; automated processing not yet available.",
      "sources.import_once.desc": "Suitable for one-time import of external files or folders.",
      "processing.view_run_status.desc": "Processing is running in the background; you can keep using MindForge.",
      "processing.review_drafts.desc": "Review generated AI drafts before approving.",
      "processing.view_source_status.desc": "See the processing summary for this source.",
      "processing.view_error.desc": "Open Sources to inspect the latest processing error.",
      "processing.retry_processing.desc": "Try Process now again after fixing the issue.",
      "processing.view_sources.desc": "No draft was generated; Sources shows the reason.",
      // Milestone E P3 close — web_facade.py description_key
      "init_vault.desc": "The vault path does not exist. Create a local vault first.",
      "review_drafts.desc": "AI drafts are waiting for human review and explicit approval.",
      "watch_source.desc": "Add files or folders as knowledge sources to auto-generate AI drafts.",
      "search_knowledge.desc": "Local knowledge base is ready. Search approved knowledge cards.",
      "create_drafts.desc": "No AI drafts yet. Add or import files/folders on the Sources page first.",
      "search_approved_cards.desc": "Enter keywords to search approved cards using local BM25 lexical matching.",
      "adjust_query.desc": "Search query cannot be executed. Try shortening or adjusting your keywords.",
      "rebuild_index.desc": "Rebuild the local BM25 index when missing or stale.",
      "try_another_query.desc": "No approved cards matched. Try another keyword or approve drafts first.",
      // Milestone E P3 close — routers/sources.py description_key
      "use_web_import.desc": "Web import does not add to watched sources or auto-approve.",
      "use_local_source.desc": "Add a local file or folder source first. No network calls or auto-approval.",
    },
  };
  return descriptions[locale ?? "zh"]?.[key] ?? null;
}
