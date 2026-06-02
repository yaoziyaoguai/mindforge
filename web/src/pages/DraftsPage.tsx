import { useEffect, useState } from "react";
import { Search, Eye, Trash2, ArrowRight, FileText } from "lucide-react";
import { getDraftDetail, saveDraftBody } from "../api/drafts";
import { moveDraftToTrash } from "../api/trash";
import type { DraftDetailResponse, DraftsResponse } from "../api/types";
import { CardWorkspace } from "../components/CardWorkspace";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { useLocale } from "../lib/i18n";
import { friendlyStatus, friendlyTrack } from "../lib/utils";

/**
 * DraftsPage - AI 草稿列表 + 预览
 *
 * 中文学习型说明：
 * 此页面展示所有 ai_draft 状态的草稿。
 * 1. 表格列表 + 预览面板，参考参考图 image7 布局。
 * 2. 明确展示 ai_draft 状态 — 草稿不是正式知识。
 * 3. 可以有 Send to Review / Edit / Move to Trash，基于已有能力。
 * 4. 没有后端能力的动作 disabled / hidden。
 * 5. 不允许把 draft 混入 Library — 只展示 ai_draft。
 */

export function DraftsPage({
  data,
  onRefresh,
  providerState,
}: {
  data: DraftsResponse;
  onRefresh: () => void;
  providerState?: string;
}) {
  const [selected, setSelected] = useState<string | undefined>(data.drafts[0]?.id ?? data.drafts[0]?.rel_path);
  const [detail, setDetail] = useState<DraftDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const { locale, t } = useLocale();

  // 只展示 ai_draft 状态的草稿 — 保护 Draft ≠ Library 的产品边界
  const aiDrafts = data.drafts.filter((d) => d.status === "ai_draft");
  const filtered = search
    ? aiDrafts.filter((d) => (d.title ?? d.rel_path ?? "").toLowerCase().includes(search.toLowerCase()))
    : aiDrafts;

  useEffect(() => {
    if (!selected) return;
    setError(null);
    getDraftDetail(selected)
      .then(setDetail)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Draft failed to load"));
  }, [selected]);

  async function refreshSelected() {
    if (!selected) return;
    const next = await getDraftDetail(selected);
    setDetail(next);
    onRefresh();
  }

  async function handleMoveToTrash() {
    if (!selected) return;
    try {
      const result = await moveDraftToTrash(selected);
      setMessage(result.message);
      setDetail(null);
      setSelected(undefined);
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Move to trash failed");
    }
  }

  // Empty state
  if (aiDrafts.length === 0) {
    return (
      <div className="space-y-6">
        <header className="page-header">
          <h1>{t("drafts.title")}</h1>
          <p>
            {t("drafts.subtitle")}
            {providerState !== "ready" && (
              <span className="ml-2" style={{ color: "var(--mf-text-tertiary)", fontSize: "var(--mf-text-caption)" }}>
                · {t("drafts.demo_mode_hint")}
              </span>
            )}
          </p>
        </header>
        <EmptyState
          title={t("drafts.empty_title")}
          action={data.empty_state ?? {
            label: t("drafts.empty_label"),
            description: t("drafts.empty_desc"),
            href: "/sources",
          }}
          locale={locale}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="page-header">
        <h1>{t("drafts.title")}</h1>
        <p>
          {t("drafts.subtitle")}
          {providerState !== "ready" && (
            <span className="ml-2" style={{ color: "var(--mf-text-tertiary)", fontSize: "var(--mf-text-caption)" }}>
              · {t("drafts.demo_mode_hint")}
            </span>
          )}
        </p>
      </header>

      {/* 统计摘要行 */}
      <div className="flex flex-wrap items-center gap-6 text-sm">
        <span className="flex items-center gap-1.5">
          <span className="rounded-full bg-[var(--mf-draft)]/10 px-2 py-0.5 text-xs font-bold" style={{ color: "var(--mf-draft)" }}>
            {aiDrafts.length}
          </span>
          <span style={{ color: "var(--mf-text-secondary)" }}>{t("drafts.stat_all_drafts")}</span>
        </span>
        <span className="text-xs" style={{ color: "var(--mf-text-tertiary)" }}>
          {t("drafts.boundary_note")}
        </span>
      </div>

      {/* 搜索 + 草稿列表 */}
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        {/* ── 草稿列表 ── */}
        <div className="space-y-3">
          {/* 搜索框 */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: "var(--mf-text-tertiary)" }} aria-hidden="true" />
            <input
              type="text"
              className="w-full rounded-lg border border-line bg-surface pl-9 pr-3 py-2 text-sm text-ink placeholder:text-muted/60 focus:outline-none"
              style={{ borderRadius: "var(--mf-radius-md)", boxShadow: "0 0 0 1px var(--mf-border)" }}
              placeholder={t("drafts.search_placeholder")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* 草稿项表格 */}
          <div className="rounded-xl border border-line bg-panel overflow-hidden">
            {/* Table header */}
            <div className="grid grid-cols-12 gap-2 px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wide border-b border-line" style={{ color: "var(--mf-text-tertiary)" }}>
              <div className="col-span-5">{t("drafts.col_title")}</div>
              <div className="col-span-2 text-center">{t("drafts.col_status")}</div>
              <div className="col-span-3">{t("drafts.col_source")}</div>
              <div className="col-span-2 text-right">{t("drafts.col_score")}</div>
            </div>

            {/* Rows */}
            <div className="max-h-[520px] overflow-y-auto">
              {filtered.length === 0 && search ? (
                <p className="py-10 text-center text-sm" style={{ color: "var(--mf-text-tertiary)" }}>
                  {t("review.no_results")}
                </p>
              ) : (
                filtered.map((draft) => {
                  const id = draft.id ?? draft.rel_path;
                  const isActive = selected === id;
                  return (
                    <button
                      key={draft.rel_path}
                      type="button"
                      onClick={() => { setSelected(id); setMessage(null); setError(null); }}
                      className={`w-full grid grid-cols-12 gap-2 px-4 py-3 text-left border-b border-line/50 transition-colors last:border-b-0 ${
                        isActive
                          ? "bg-[var(--mf-accent)]/5 border-l-[3px] border-l-[var(--mf-accent)]"
                          : "hover:bg-stone-50/60 border-l-[3px] border-l-transparent"
                      }`}
                      style={{ borderRadius: 0 }}
                    >
                      <div className="col-span-5 min-w-0">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 shrink-0" style={{ color: "var(--mf-text-tertiary)" }} />
                          <h3 className="text-sm font-medium text-ink truncate" style={{ fontFamily: "var(--mf-font-serif)" }}>
                            {draft.title ?? draft.rel_path}
                          </h3>
                        </div>
                        {draft.track && (
                          <p className="mt-0.5 text-[11px]" style={{ color: "var(--mf-text-tertiary)" }}>
                            {friendlyTrack(draft.track, locale)}
                          </p>
                        )}
                      </div>
                      <div className="col-span-2 flex items-center justify-center">
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium" style={{
                          background: "rgba(216,135,34,0.12)",
                          color: "var(--mf-draft)",
                        }}>
                          {friendlyStatus(draft.status, locale)}
                        </span>
                      </div>
                      <div className="col-span-3 min-w-0">
                        <span className="text-[11px] truncate block" style={{ color: "var(--mf-text-tertiary)" }}>
                          {draft.source_title ?? "-"}
                        </span>
                      </div>
                      <div className="col-span-2 text-right">
                        <span className="text-sm font-medium text-ink">
                          {draft.value_score != null ? draft.value_score : "-"}
                        </span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {message && (
            <p className="text-sm" style={{ color: "var(--mf-text-secondary)" }}>{message}</p>
          )}
        </div>

        {/* ── 预览面板 ── */}
        <div>
          {error ? <ErrorState message={error} /> : detail ? (
            <div className="space-y-4">
              <div className="mf-card rounded-xl p-5">
                <h2
                  className="font-semibold text-ink"
                  style={{ fontFamily: "var(--mf-font-serif)", fontSize: "var(--mf-text-body)" }}
                >
                  {detail.draft.title ?? detail.draft.rel_path}
                </h2>
                <div className="mt-3 text-sm leading-relaxed whitespace-pre-wrap max-h-[320px] overflow-y-auto" style={{ color: "var(--mf-text-secondary)", lineHeight: 1.7 }}>
                  {(detail.body ?? "").slice(0, 600)}
                  {(detail.body ?? "").length > 600 ? (
                    <span className="text-muted">... {t("drafts.preview_truncated")}</span>
                  ) : null}
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="flex flex-col gap-2">
                <button
                  className="mf-primary-button rounded-lg px-4 py-2.5 text-sm font-bold"
                  onClick={() => onRefresh()}
                  type="button"
                >
                  <ArrowRight className="mr-1.5 h-4 w-4" />
                  {t("drafts.send_to_review")}
                </button>
                <button
                  className="mf-secondary-button rounded-lg px-4 py-2.5 text-sm"
                  onClick={() => {}}
                  type="button"
                  disabled
                >
                  <Eye className="mr-1.5 h-4 w-4" />
                  {t("drafts.view_full_detail")}
                </button>
                <button
                  className="rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors"
                  style={{
                    borderColor: "var(--mf-error)",
                    color: "var(--mf-error)",
                    background: "rgba(208, 75, 75, 0.04)",
                  }}
                  onClick={handleMoveToTrash}
                  type="button"
                >
                  <Trash2 className="mr-1.5 h-4 w-4" />
                  {t("card.move_to_trash")}
                </button>
              </div>

              {/* 产品边界提示：草稿不是正式知识 */}
              <p className="text-[11px] text-center leading-relaxed" style={{ color: "var(--mf-text-tertiary)" }}>
                {t("drafts.boundary_note_long")}
              </p>
            </div>
          ) : (
            <div className="mf-card rounded-xl flex flex-col items-center justify-center p-12 text-center" style={{ minHeight: "320px" }}>
              <div className="mb-3 h-12 w-12 rounded-full" style={{ background: "var(--mf-accent-soft)" }}>
                <FileText className="mx-auto mt-2.5 h-6 w-6" style={{ color: "var(--mf-accent)" }} />
              </div>
              <p className="font-medium text-ink" style={{ fontFamily: "var(--mf-font-serif)" }}>
                {t("drafts.empty_selection_title")}
              </p>
              <p className="mt-1 text-sm" style={{ color: "var(--mf-text-tertiary)" }}>
                {t("drafts.empty_selection_desc")}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
