import { useState } from "react";
import { recall } from "../api/recall";
import type { RecallResponse } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { useLocale } from "../lib/i18n";

/** 将 BM25 分数映射为用户可理解的相关性标签，不暴露原始浮点数。
 *  BM25 是词法匹配算法（非语义 RAG），分数区间和语义模型不可直接比较。 */
function scoreLabel(score: number, t: (key: string) => string): { label: string; tone: string } {
  if (score >= 0.7) return { label: t("recall.score_high"), tone: "text-safe" };
  if (score >= 0.4) return { label: t("recall.score_medium"), tone: "text-warn" };
  return { label: t("recall.score_low"), tone: "text-muted" };
}

export function RecallPage({ onNavigate }: { onNavigate: (href: string) => void }) {
  const [query, setQuery] = useState("");
  const [data, setData] = useState<RecallResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [showExplain, setShowExplain] = useState(false);
  const { locale, t } = useLocale();

  async function runSearch(queryText: string): Promise<void> {
    if (!queryText) return;
    setError(null);
    setSearching(true);
    setShowExplain(false);
    try {
      setData(await recall(queryText));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("recall.error_fallback"));
    } finally {
      setSearching(false);
    }
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    runSearch(query.trim());
  }

  return (
    <div className="space-y-6">
      <header className="page-header">
        <h1>{t("recall.title")}</h1>
        <p>{t("recall.subtitle")}</p>
      </header>
      <form className="flex gap-2" onSubmit={handleSubmit}>
        <input
          id="recall-search"
          className="min-w-0 flex-1 rounded-md border border-line bg-panel px-3 py-2"
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("recall.placeholder")}
          aria-label={t("recall.placeholder")}
          value={query}
          disabled={searching}
        />
        <button
          className="inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          style={{ background: "var(--mf-accent)" }}
          disabled={searching || !query.trim()}
          type="submit"
        >
          {searching ? (
            <>
              <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              {t("recall.searching")}
            </>
          ) : (
            t("recall.search")
          )}
        </button>
      </form>
      {error ? (
        <div className="rounded-md border border-danger bg-red-50 p-3 text-sm text-ink">
          <div className="flex items-start gap-2">
            <span className="mt-0.5 font-medium text-danger">{t("recall.error_title")}</span>
            <span className="flex-1">{error}</span>
            <button className="text-xs text-muted hover:text-ink" onClick={() => runSearch(query.trim())} type="button">{t("recall.retry")}</button>
          </div>
        </div>
      ) : null}
      {!data && !error ? (
        <EmptyState locale={locale}
          title={t("recall.empty_prompt_title")}
          action={{
            label: t("recall.empty_prompt_label"),
            description: t("recall.empty_prompt_desc"),
          }}
        />
      ) : null}
      {data?.empty_state && data.hits.length === 0 ? <EmptyState locale={locale} title={t("recall.empty_no_results_title")} action={data.empty_state} /> : null}
      {data && data.hits.length === 0 && !data.empty_state ? (
        <EmptyState locale={locale}
          title={t("recall.empty_no_results_title")}
          action={{
            label: t("recall.empty_no_results_label"),
            description: t("recall.empty_no_results_desc"),
            href: "/drafts",
          }}
        />
      ) : null}
      {data?.hits.length ? (
        <div className="space-y-3">
          {data.hits.map((hit) => {
            const sl = scoreLabel(hit.score, t);
            return (
              <article
            key={hit.rel_path}
            className="p-4"
            style={{
              background: "var(--mf-surface)",
              border: "1px solid var(--mf-border)",
              borderRadius: "var(--mf-radius-md)",
              boxShadow: "var(--mf-shadow-raised)",
            }}
          >
                <div className="flex items-center justify-between gap-3">
                  <h2 className="font-semibold text-ink">{hit.title ?? hit.rel_path}</h2>
                  <span className={`text-sm font-medium ${sl.tone}`}>{sl.label}</span>
                </div>
                <p className="mt-2 text-sm text-muted">{t("recall.match_reason")}: {hit.why_this_matched}</p>
                <button
                  className="mt-3 rounded-md border border-line px-3 py-1.5 text-sm font-medium text-primary"
                  onClick={() => onNavigate(hit.detail_href ?? `/library?card=${encodeURIComponent(hit.card_ref ?? hit.rel_path)}`)}
                  type="button"
                >
                  {t("recall.open_card")}
                </button>
              </article>
            );
          })}
        </div>
      ) : null}
      {(data && (data.hits.length > 0 || data.hits.length === 0)) ? (
        <div className="mt-4 border-t border-line pt-4">
          <button
            className="flex items-center gap-1.5 text-sm text-muted hover:text-ink transition-colors"
            onClick={() => setShowExplain(!showExplain)}
            type="button"
          >
            <span className={`inline-block transition-transform ${showExplain ? "rotate-90" : ""}`}>&#9654;</span>
            {showExplain ? t("recall.explain_hide") : t("recall.explain_show")}
          </button>
          {showExplain ? (
            <div className="mt-3 rounded-md border border-line bg-panel p-4 space-y-3 text-sm">
              <h3 className="font-medium text-ink">{t("recall.explain_title")}</h3>
              <p className="text-muted">{t("recall.explain_lexical_boundary")}</p>
              {data.hits.length > 0 ? (
                <>
                  <div>
                    <span className="font-medium text-ink">{t("recall.explain_matched_fields")}: </span>
                    <span className="text-muted">{data.hits.slice(0, 3).map((h) => h.matched_fields?.join(", ") ?? "-").join(" | ")}</span>
                  </div>
                  <div>
                    <span className="font-medium text-ink">{t("recall.explain_top_terms")}: </span>
                    <span className="text-muted">
                      {(() => {
                        const terms = new Set<string>();
                        for (const h of data.hits.slice(0, 5)) {
                          for (const t of h.matched_terms_list ?? []) {
                            if (t && t !== "-") terms.add(t);
                          }
                        }
                        return [...terms].slice(0, 8).join(", ") || "-";
                      })()}
                    </span>
                  </div>
                </>
              ) : (
                <div>
                  <span className="font-medium text-ink">{t("recall.explain_no_hits_reason")}: </span>
                  <span className="text-muted">
                    {data.empty_state?.description ?? t("recall.empty_no_results_desc")}
                  </span>
                </div>
              )}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
