/**
 * Wiki Page — structured presentation of Main Wiki.
 *
 * Fetches /api/wiki/page (structured WikiPageViewModel JSON) and renders
 * TOC + sections with Markdown → safe HTML via DOMPurify.
 *
 * SDD_WIKI_PRESENTATION_V2 §4.4, §9.
 */

import { useEffect, useState, useCallback } from "react";
import { WikiTOC } from "../components/wiki/WikiTOC";
import { WikiSection } from "../components/wiki/WikiSection";
import { WikiReferencePanel } from "../components/wiki/WikiReferencePanel";
import { WikiEmptyState } from "../components/wiki/WikiEmptyState";
import { WikiErrorState } from "../components/wiki/WikiErrorState";
import { WikiLoadingState } from "../components/wiki/WikiLoadingState";
import { renderMarkdown } from "../lib/wiki-renderer";
import type { WikiPageViewModel } from "../api/wiki";

interface WikiStatus {
  wiki_path: string;
  exists: boolean;
  last_rebuilt_at: string | null;
  approved_card_count: number;
  wiki_card_count: number;
  model_ready: boolean;
  model_ready_label: string;
}

interface WikiRebuildResult {
  ok: boolean;
  mode?: string;
  wiki_path?: string;
  included_cards?: number;
  section_count?: number;
  additional_cards?: number;
  model_id?: string;
  warnings?: string[];
  last_rebuilt_at?: string;
  error?: string;
}

export function WikiPage() {
  const [status, setStatus] = useState<WikiStatus | null>(null);
  const [page, setPage] = useState<WikiPageViewModel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [s, p] = await Promise.all([
        fetch("/api/wiki/status").then((r) => r.json()),
        fetch("/api/wiki/page").then((r) => r.json()),
      ]);
      setStatus(s as WikiStatus);
      if ((p as Record<string, unknown>).exists === false) {
        setPage(null);
      } else {
        setPage(p as WikiPageViewModel);
      }
    } catch {
      setError("Failed to load wiki content from server.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function rebuild(mode: string) {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const resp = await fetch("/api/wiki/rebuild", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      const data: WikiRebuildResult = await resp.json();
      if (data.ok) {
        const parts: string[] = [
          `Wiki rebuilt (${data.mode}): ${data.included_cards} cards`,
        ];
        if (data.section_count) parts.push(`${data.section_count} sections`);
        if (data.model_id) parts.push(`model: ${data.model_id}`);
        setMessage(parts.join(", "));
        if (data.warnings?.length) {
          setMessage(
            (prev) =>
              (prev ?? "") + " — Warnings: " + data.warnings!.join("; "),
          );
        }
        if (data.last_rebuilt_at) {
          setStatus((prev) =>
            prev
              ? {
                  ...prev,
                  last_rebuilt_at: data.last_rebuilt_at ?? null,
                  wiki_card_count:
                    data.included_cards ?? prev.wiki_card_count,
                }
              : prev,
          );
        }
      } else {
        setError(`Rebuild failed: ${data.error ?? "unknown error"}`);
      }
      await load();
    } catch {
      setError("Wiki rebuild failed due to a network or server error.");
    } finally {
      setBusy(false);
    }
  }

  // -- loading state -----------------------------------------------------------

  if (loading) {
    return (
      <div className="space-y-6">
        <header>
          <h1 className="text-2xl font-semibold text-ink">Wiki</h1>
        </header>
        <WikiLoadingState />
      </div>
    );
  }

  // -- error state after initial load -------------------------------------------

  if (error && !page) {
    return (
      <div className="space-y-6">
        <header>
          <h1 className="text-2xl font-semibold text-ink">Wiki</h1>
        </header>
        <WikiErrorState message={error} onRetry={() => load()} />
      </div>
    );
  }

  // -- rebuild in progress ------------------------------------------------------

  if (busy) {
    return (
      <div className="space-y-6">
        <header>
          <h1 className="text-2xl font-semibold text-ink">Wiki</h1>
          <p className="mt-1 text-sm text-muted">
            Main Wiki is generated from approved knowledge cards.
          </p>
        </header>
        <WikiLoadingState />
      </div>
    );
  }

  // -- empty state (no wiki / no approved cards) --------------------------------

  const noApprovedCards =
    status != null && status.approved_card_count === 0;
  const wikiNotBuilt = status != null && !status.exists && !noApprovedCards;

  if (!page && (noApprovedCards || wikiNotBuilt || !status?.model_ready)) {
    const modelReady = status?.model_ready ?? false;
    return (
      <div className="space-y-6">
        <header>
          <h1 className="text-2xl font-semibold text-ink">Wiki</h1>
          <p className="mt-1 text-sm text-muted">
            Main Wiki is generated from approved knowledge cards.
          </p>
        </header>

        {status && (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <div className="rounded-md border border-line bg-panel px-3 py-2">
              <span className="text-muted">Approved cards: </span>
              <span className="text-ink">{status.approved_card_count}</span>
            </div>
            <button
              className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
              disabled={busy || !status.model_ready}
              onClick={() => rebuild("llm")}
              type="button"
              title={
                status.model_ready
                  ? "Rebuild Wiki with LLM synthesis"
                  : status.model_ready_label
              }
            >
              Rebuild Wiki
            </button>
          </div>
        )}

        <WikiEmptyState
          noApprovedCards={noApprovedCards}
          modelReady={modelReady}
        />

        <details className="rounded-md border border-line p-3">
          <summary className="cursor-pointer text-sm font-medium text-muted">
            Advanced
          </summary>
          <div className="mt-3 space-y-3">
            <p className="text-xs text-muted">
              Template rebuild is a troubleshooting fallback. It does not
              require a model.
            </p>
            <button
              className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink disabled:opacity-50"
              disabled={busy}
              onClick={() => rebuild("deterministic")}
              type="button"
            >
              Template rebuild (no model)
            </button>
          </div>
        </details>
      </div>
    );
  }

  // -- ready state: structured wiki with TOC + sections -------------------------

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Wiki</h1>
        <p className="mt-1 text-sm text-muted">
          Main Wiki is generated from approved knowledge cards.
        </p>
      </header>

      {message ? <p className="text-sm text-primary">{message}</p> : null}
      {error ? <p className="text-sm text-danger">{error}</p> : null}

      {/* Status bar */}
      {status ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <div className="rounded-md border border-line bg-panel px-3 py-2">
            <span className="text-muted">Status: </span>
            <span className={status.exists ? "text-safe" : "text-warn"}>
              {status.exists ? "Exists" : "Missing"}
            </span>
          </div>
          {status.exists ? (
            <>
              <div className="rounded-md border border-line bg-panel px-3 py-2">
                <span className="text-muted">Last rebuilt: </span>
                <span className="text-ink">
                  {status.last_rebuilt_at?.slice(0, 19) ?? "—"}
                </span>
              </div>
              <div className="rounded-md border border-line bg-panel px-3 py-2">
                <span className="text-muted">Cards in Wiki: </span>
                <span className="text-ink">{status.wiki_card_count}</span>
              </div>
            </>
          ) : null}
          <div className="rounded-md border border-line bg-panel px-3 py-2">
            <span className="text-muted">Approved cards: </span>
            <span className="text-ink">{status.approved_card_count}</span>
          </div>
          <button
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            disabled={busy || !status.model_ready}
            onClick={() => rebuild("llm")}
            type="button"
            title={
              status.model_ready
                ? "Rebuild Wiki with LLM synthesis"
                : status.model_ready_label
            }
          >
            Rebuild Wiki
          </button>
        </div>
      ) : null}

      {/* Wiki content: TOC + sections */}
      {page ? (
        <div className="flex gap-6">
          <WikiTOC sections={page.sections} />

          <div className="min-w-0 flex-1 space-y-8">
            {/* Overview */}
            {page.overview && (
              <section>
                <div
                  className="prose prose-sm max-w-none text-ink leading-relaxed"
                  dangerouslySetInnerHTML={{
                    __html: renderMarkdown(page.overview),
                  }}
                />
              </section>
            )}

            {/* Sections */}
            {page.sections.map((sec) => (
              <WikiSection key={sec.id} section={sec} />
            ))}

            {/* Open questions */}
            {page.open_questions.length > 0 && (
              <section>
                <h2 className="mb-3 text-lg font-semibold text-ink">
                  Open Questions
                </h2>
                <ul className="list-disc space-y-1 pl-5 text-sm text-ink">
                  {page.open_questions.map((q, i) => (
                    <li key={i}>{q.question}</li>
                  ))}
                </ul>
              </section>
            )}

            {/* Additional cards */}
            {page.additional_cards.length > 0 && (
              <WikiReferencePanel
                refs={page.additional_cards}
                title="Additional approved cards"
              />
            )}

            {/* Warnings */}
            {page.warnings.length > 0 && (
              <div className="rounded-md border border-warn/30 bg-warn/5 p-3">
                <p className="text-sm font-medium text-warn">Warnings</p>
                <ul className="mt-1 list-disc pl-5 text-xs text-muted">
                  {page.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      ) : null}

      {/* Advanced: deterministic fallback */}
      <details className="rounded-md border border-line p-3">
        <summary className="cursor-pointer text-sm font-medium text-muted">
          Advanced
        </summary>
        <div className="mt-3 space-y-3">
          <p className="text-xs text-muted">
            Template rebuild is a troubleshooting fallback. It does not require
            a model.
          </p>
          <button
            className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink disabled:opacity-50"
            disabled={busy}
            onClick={() => rebuild("deterministic")}
            type="button"
          >
            Template rebuild (no model)
          </button>
        </div>
      </details>
    </div>
  );
}
