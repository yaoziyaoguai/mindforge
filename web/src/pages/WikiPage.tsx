/**
 * Wiki Page — orchestration layer.
 *
 * Fetches /api/wiki/status and /api/wiki/page, manages rebuild, delegates
 * all rendering to decomposed components.
 *
 * SDD_WIKI_WEB_PRESENTATION_ADDENDUM §12.
 */

import { useEffect, useState, useCallback } from "react";
import { WikiHeader } from "../components/wiki/WikiHeader";
import { WikiStatusBar } from "../components/wiki/WikiStatusBar";
import { WikiReadingPane } from "../components/wiki/WikiReadingPane";
import { WikiTOC } from "../components/wiki/WikiTOC";
import { WikiAdvancedActions } from "../components/wiki/WikiAdvancedActions";
import { WikiEmptyState } from "../components/wiki/WikiEmptyState";
import { WikiErrorState } from "../components/wiki/WikiErrorState";
import { WikiLoadingState } from "../components/wiki/WikiLoadingState";
import { useLocale } from "../lib/i18n";
import type { WikiPageViewModel } from "../api/wiki";

interface WikiStatus {
  wiki_path: string;
  exists: boolean;
  last_rebuilt_at: string | null;
  approved_card_count: number;
  wiki_card_count: number;
  is_stale: boolean;
  new_approved_count: number;
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
  const { t } = useLocale();

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
      setError(t("wiki.load_failed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

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
        setMessage(
          t("wiki.rebuild_result")
            .replace("{mode}", data.mode ?? "?")
            .replace("{cards}", String(data.included_cards ?? 0))
            .replace("{sections}", String(data.section_count ?? 0))
            .replace("{model}", data.model_id ?? "-"),
        );
        if (data.warnings?.length) {
          setMessage(
            (prev) =>
              (prev ?? "") + " — " + t("wiki.warnings") + ": " + data.warnings!.join("; "),
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
        setError(t("wiki.rebuild_server_error").replace("{error}", data.error ?? "unknown error"));
      }
      await load();
    } catch {
      setError(t("wiki.rebuild_failed"));
    } finally {
      setBusy(false);
    }
  }

  // -- loading state -------------------------------------------------------

  if (loading) {
    return (
      <div className="space-y-6">
        <WikiHeader />
        <WikiLoadingState />
      </div>
    );
  }

  // -- error state after initial load --------------------------------------

  if (error && !page) {
    return (
      <div className="space-y-6">
        <WikiHeader />
        <WikiErrorState message={error} onRetry={() => load()} />
      </div>
    );
  }

  // -- rebuild in progress -------------------------------------------------

  if (busy) {
    return (
      <div className="space-y-6">
        <WikiHeader />
        <WikiLoadingState />
      </div>
    );
  }

  // -- empty state (no wiki / no approved cards) ---------------------------

  const noApprovedCards =
    status != null && status.approved_card_count === 0;
  const wikiNotBuilt = status != null && !status.exists && !noApprovedCards;

  if (!page && (noApprovedCards || wikiNotBuilt || !status?.model_ready)) {
    const modelReady = status?.model_ready ?? false;
    return (
      <div className="space-y-6">
        <WikiHeader />

        {status && (
          <WikiStatusBar
            exists={status.exists}
            lastRebuiltAt={status.last_rebuilt_at}
            wikiCardCount={status.wiki_card_count}
            approvedCardCount={status.approved_card_count}
            isStale={status.is_stale}
            newApprovedCount={status.new_approved_count}
            modelReady={status.model_ready}
            modelReadyLabel={status.model_ready_label}
            busy={busy}
            onRebuild={() => rebuild("llm")}
          />
        )}

        <WikiEmptyState
          noApprovedCards={noApprovedCards}
          modelReady={modelReady}
        />

        <WikiAdvancedActions
          busy={busy}
          onFallbackRebuild={() => rebuild("deterministic")}
        />
      </div>
    );
  }

  // -- ready state: structured wiki with TOC + sections --------------------

  return (
    <div className="space-y-6">
      <WikiHeader />

      {message ? <p className="text-sm text-primary">{message}</p> : null}
      {error ? <p className="text-sm text-danger">{error}</p> : null}

      {status && (
        <WikiStatusBar
          exists={status.exists}
          lastRebuiltAt={status.last_rebuilt_at}
          wikiCardCount={status.wiki_card_count}
          approvedCardCount={status.approved_card_count}
          isStale={status.is_stale}
          newApprovedCount={status.new_approved_count}
          modelReady={status.model_ready}
          modelReadyLabel={status.model_ready_label}
          busy={busy}
          onRebuild={() => rebuild("llm")}
        />
      )}

      {page && (
        <div className="flex gap-6">
          <WikiTOC sections={page.sections} />
          <WikiReadingPane page={page} />
        </div>
      )}

      <WikiAdvancedActions
        busy={busy}
        onFallbackRebuild={() => rebuild("deterministic")}
      />
    </div>
  );
}
