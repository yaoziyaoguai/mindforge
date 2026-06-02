import { useEffect, useState } from "react";
import { Check, Search, X, RefreshCw } from "lucide-react";
import { getDraftDetail, saveDraftBody } from "../api/drafts";
import { approveDraft, rejectDraft } from "../api/approval";
import type { DraftDetailResponse, DraftsResponse } from "../api/types";
import { BoundaryBadge } from "../components/BoundaryBadge";
import { friendlyStatus, cardStatusBadgeClass } from "../lib/utils";
import { useLocale } from "../lib/i18n";

/**
 * ReviewPage - 人工审阅页面
 *
 * 中文学习型说明：
 * 此页面承载 Human Review (人工审阅) 的主路径。
 * 1. 左侧草稿列表 + 右侧预览/审批面板，参考参考图 image4 布局。
 * 2. Approve 必须是单条、显式、不可误触的操作。
 * 3. 不存在 Approve All，不存在 auto approve。
 * 4. 只有 ai_draft 状态的草稿出现在此列表中。
 * 5. approve/reject 后刷新列表，不自动跳转。
 */

export function ReviewPage({
  data,
  onRefresh,
  providerState,
}: {
  data: DraftsResponse;
  onRefresh: () => void;
  providerState?: string;
}) {
  const [selected, setSelected] = useState<string | undefined>(
    data.drafts.find((d) => d.status === "ai_draft")?.id ?? data.drafts.find((d) => d.status === "ai_draft")?.rel_path
  );
  const [detail, setDetail] = useState<DraftDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [search, setSearch] = useState("");
  const { locale, t } = useLocale();

  const aiDrafts = data.drafts.filter((d) => d.status === "ai_draft");
  const humanApproved = data.drafts.filter((d) => d.status === "human_approved");
  const filtered = search
    ? aiDrafts.filter((d) => (d.title ?? d.rel_path ?? "").toLowerCase().includes(search.toLowerCase()))
    : aiDrafts;

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    setError(null);
    getDraftDetail(selected)
      .then((d) => {
        setDetail(d);
        setConfirming(false);
        setReviewed(false);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Draft failed to load"));
  }, [selected]);

  async function handleApprove() {
    if (!selected || !detail) return;
    setBusy(true);
    setError(null);
    try {
      await approveDraft(selected, { confirm: true, reviewed_source: reviewed });
      setConfirming(false);
      setReviewed(false);
      await onRefresh();
      setSelected(undefined);
      setDetail(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleReject() {
    if (!selected || !detail) return;
    setBusy(true);
    setError(null);
    try {
      await rejectDraft(selected, {});
      setConfirming(false);
      setReviewed(false);
      await onRefresh();
      setSelected(undefined);
      setDetail(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setBusy(false);
    }
  }

  if (data.drafts.length === 0) {
    return (
      <div className="space-y-6">
        <header className="page-header">
          <h1>{t("review.title")}</h1>
          <p>{t("review.subtitle")}</p>
        </header>
        <div className="mf-card rounded-xl p-10 text-center">
          <p className="text-lg font-semibold text-ink" style={{ fontFamily: "var(--mf-font-serif)" }}>
            {t("review.empty_title")}
          </p>
          <p className="mt-2 text-sm text-muted">{t("review.empty_desc")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="page-header">
        <h1>{t("review.title")}</h1>
        <p>
          {t("review.subtitle")}
          {providerState !== "ready" && (
            <span className="ml-2" style={{ color: "var(--mf-text-tertiary)", fontSize: "var(--mf-text-caption)" }}>
              · {t("review.demo_mode_hint")}
            </span>
          )}
        </p>
      </header>

      {/* 产品边界提示：明确 Review 路径需要显式人工确认 */}
      <section className="mf-card-soft rounded-lg p-4">
        <p className="text-xs text-muted leading-relaxed">
          <BoundaryBadge type="source" />
          <span className="ml-1.5">{t("review.boundary_desc")}</span>
        </p>
      </section>

      {/* 统计摘要行 */}
      <div className="flex flex-wrap items-center gap-6 text-sm">
        <span className="flex items-center gap-1.5">
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-bold" style={{ color: "var(--mf-accent)" }}>
            {aiDrafts.length}
          </span>
          <span style={{ color: "var(--mf-text-secondary)" }}>{t("review.stat_ai_drafts")}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="rounded-full px-2 py-0.5 text-xs font-bold" style={{ background: "rgba(20,150,107,0.12)", color: "var(--mf-approved)" }}>
            {humanApproved.length}
          </span>
          <span style={{ color: "var(--mf-text-secondary)" }}>{t("review.stat_approved")}</span>
        </span>
      </div>

      {/* 左列表 + 右面板布局 */}
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        {/* ── 左侧：草稿列表 ── */}
        <div className="space-y-3">
          {/* 搜索框 */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: "var(--mf-text-tertiary)" }} aria-hidden="true" />
            <input
              type="text"
              className="w-full rounded-lg border border-line bg-surface pl-9 pr-3 py-2 text-sm text-ink placeholder:text-muted/60 focus:outline-none focus:ring-2"
              style={{ "--mf-shadow-raised": "var(--mf-shadow-flat)", borderRadius: "var(--mf-radius-md)", boxShadow: "0 0 0 1px var(--mf-border)", focusRingColor: "var(--mf-accent)" } as React.CSSProperties}
              placeholder={t("review.search_placeholder")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* 草稿项列表 */}
          <div className="space-y-2 max-h-[640px] overflow-y-auto pr-1">
            {filtered.map((draft) => {
              const id = draft.id ?? draft.rel_path;
              const isActive = selected === id;
              return (
                <button
                  key={draft.rel_path}
                  type="button"
                  onClick={() => { setSelected(id); setConfirming(false); setReviewed(false); }}
                  className={`w-full rounded-xl border text-left transition-all ${
                    isActive
                      ? "border-[var(--mf-accent)]/40 bg-[var(--mf-accent)]/5 shadow-sm"
                      : "border-line hover:border-[var(--mf-accent)]/20 hover:bg-accent-faint/50"
                  }`}
                  style={{ padding: "var(--mf-space-sm) var(--mf-space-md)", borderRadius: "var(--mf-radius-lg)" }}
                >
                  <h3
                    className="font-medium leading-snug text-ink"
                    style={{ fontFamily: "var(--mf-font-serif)", fontSize: "var(--mf-text-body)" }}
                  >
                    {draft.title ?? draft.rel_path}
                  </h3>
                  <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                    <span className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${cardStatusBadgeClass(draft.status)}`}>
                      {friendlyStatus(draft.status, locale)}
                    </span>
                    {draft.source_title && (
                      <span className="text-[11px]" style={{ color: "var(--mf-text-tertiary)" }}>{draft.source_title}</span>
                    )}
                    {draft.value_score != null && (
                      <span className="text-[11px]" style={{ color: "var(--mf-text-tertiary)" }}>
                        {t("review.value_score")}: {draft.value_score}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
            {filtered.length === 0 && search && (
              <p className="py-6 text-center text-sm" style={{ color: "var(--mf-text-tertiary)" }}>
                {t("review.no_results")}
              </p>
            )}
          </div>
        </div>

        {/* ── 右侧：预览 + 审批面板 ── */}
        <div className="space-y-4">
          {error && (
            <div className="rounded-lg border border-[var(--mf-error)]/30 bg-[var(--mf-error)]/5 p-3 text-sm" style={{ color: "var(--mf-error)" }}>
              {error}
              <button
                type="button"
                className="ml-3 inline-flex items-center gap-1 text-xs font-medium"
                style={{ color: "var(--mf-accent)" }}
                onClick={() => { setError(null); if (selected) getDraftDetail(selected).then(setDetail).catch(() => {}); }}
              >
                <RefreshCw className="h-3 w-3" /> {t("review.retry")}
              </button>
            </div>
          )}

          {detail ? (
            <>
              {/* 预览面板 */}
              <div className="mf-card rounded-xl p-6">
                <h2
                  className="font-semibold text-ink"
                  style={{ fontFamily: "var(--mf-font-serif)", fontSize: "var(--mf-text-h3)" }}
                >
                  {detail.draft.title ?? detail.draft.rel_path}
                </h2>
                <div className="mt-3 text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--mf-text-secondary)", lineHeight: 1.7 }}>
                  {(detail.body ?? "").slice(0, 800)}
                  {(detail.body ?? "").length > 800 ? (
                    <span className="text-muted">... {t("review.preview_truncated")}</span>
                  ) : null}
                </div>
              </div>

              {/* 审批面板 */}
              <div className="mf-card rounded-xl p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <h3
                      className="font-semibold text-ink"
                      style={{ fontFamily: "var(--mf-font-serif)", fontSize: "var(--mf-text-body)" }}
                    >
                      {t("review.decision_panel_title")}
                    </h3>
                    <p className="mt-1 text-xs" style={{ color: "var(--mf-text-tertiary)" }}>
                      {t("review.decision_panel_desc")}
                    </p>
                  </div>
                  <span className="rounded-full px-2.5 py-1 text-[11px] font-bold" style={{ background: "rgba(216,135,34,0.12)", color: "var(--mf-draft)" }}>
                    {t("approval.status_ai_draft")}
                  </span>
                </div>

                <div className="mt-5 space-y-3">
                  {/* 审阅确认复选框 */}
                  <label className="flex items-start gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={reviewed}
                      onChange={(e) => setReviewed(e.target.checked)}
                      className="mt-0.5 h-4 w-4 rounded"
                      style={{ accentColor: "var(--mf-accent)" }}
                    />
                    <span className="text-sm leading-relaxed text-ink">
                      {t("approval.reviewed_checkbox")}
                    </span>
                  </label>

                  {/* Approve 按钮 — 二次确认模式 */}
                  {!confirming ? (
                    <button
                      type="button"
                      disabled={!reviewed || busy}
                      onClick={() => setConfirming(true)}
                      className="w-full rounded-lg px-4 py-2.5 text-sm font-bold text-white transition-all disabled:opacity-40"
                      style={{
                        background: "linear-gradient(135deg, var(--mf-accent), #6f5cff)",
                        boxShadow: "0 10px 24px rgba(91, 70, 246, 0.24)",
                      }}
                    >
                      <Check className="mr-2 inline h-4 w-4" />
                      {t("approval.confirm_button")}
                    </button>
                  ) : (
                    <div className="rounded-lg border p-4" style={{ borderColor: "var(--mf-accent-soft)", background: "var(--mf-accent-faint)" }}>
                      <p className="text-sm font-bold" style={{ color: "var(--mf-accent)" }}>
                        {t("approval.confirm_title")}
                      </p>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={handleApprove}
                        className="mt-3 w-full rounded-lg px-4 py-2.5 text-sm font-bold text-white transition-all disabled:opacity-40"
                        style={{ background: "linear-gradient(135deg, var(--mf-accent), #6f5cff)" }}
                      >
                        <Check className="mr-2 inline h-4 w-4" />
                        {t("approval.confirm_final")}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirming(false)}
                        className="mt-2 w-full rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-surface"
                        style={{ borderColor: "var(--mf-border)", color: "var(--mf-text-secondary)" }}
                      >
                        {t("approval.cancel")}
                      </button>
                    </div>
                  )}

                  {/* Reject 按钮 — 独立操作，与 Approve 视觉区分 */}
                  <button
                    type="button"
                    disabled={busy}
                    onClick={handleReject}
                    className="w-full rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors"
                    style={{
                      borderColor: "var(--mf-error)",
                      color: "var(--mf-error)",
                      background: "rgba(208, 75, 75, 0.04)",
                    }}
                  >
                    <X className="mr-2 inline h-4 w-4" />
                    {t("approval.reject")}
                  </button>
                </div>

                {/* 安全提示：不存在 Approve All，不存在 auto approve */}
                <p className="mt-4 text-[11px] text-center" style={{ color: "var(--mf-text-tertiary)" }}>
                  {t("review.safety_note")}
                </p>
              </div>
            </>
          ) : (
            <div className="mf-card rounded-xl flex flex-col items-center justify-center p-12 text-center" style={{ minHeight: "320px" }}>
              <div className="mb-3 h-12 w-12 rounded-full" style={{ background: "var(--mf-accent-soft)" }}>
                <Check className="mx-auto mt-2.5 h-6 w-6" style={{ color: "var(--mf-accent)" }} />
              </div>
              <p className="font-medium text-ink" style={{ fontFamily: "var(--mf-font-serif)" }}>
                {t("review.empty_selection_title")}
              </p>
              <p className="mt-1 text-sm" style={{ color: "var(--mf-text-tertiary)" }}>
                {t("review.empty_selection_desc")}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
