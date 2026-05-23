import { AlertTriangle, CheckCircle, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Locale } from "./i18n";
import { t } from "./i18n";

export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function statusTone(status: string): string {
  if (status === "ok") return "text-safe bg-green-50 border-green-200";
  if (status === "warn") return "text-warn bg-amber-50 border-amber-200";
  if (status === "error") return "text-danger bg-red-50 border-red-200";
  return "text-muted bg-stone-50 border-line";
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
    },
  };
  return labels[locale ?? "zh"]?.[key] ?? null;
}
