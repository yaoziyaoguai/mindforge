import { useEffect, useState } from "react";

interface WikiStatus {
  wiki_path: string;
  exists: boolean;
  last_rebuilt_at: string | null;
  approved_card_count: number;
  wiki_card_count: number;
  model_ready: boolean;
  model_ready_label: string;
}

interface WikiContent {
  content: string | null;
  exists: boolean;
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
  const [content, setContent] = useState<WikiContent | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    try {
      const [s, c] = await Promise.all([
        fetch("/api/wiki/status").then(r => r.json()),
        fetch("/api/wiki/content").then(r => r.json()),
      ]);
      setStatus(s);
      setContent(c);
    } catch {
      setMessage("Failed to load wiki");
    }
  }

  async function rebuild(mode: string) {
    setBusy(true);
    setMessage(null);
    try {
      const resp = await fetch(`/api/wiki/rebuild`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      const data: WikiRebuildResult = await resp.json();
      if (data.ok) {
        const parts: string[] = [`Wiki rebuilt (${data.mode}): ${data.included_cards} cards`];
        if (data.section_count) parts.push(`${data.section_count} sections`);
        if (data.model_id) parts.push(`model: ${data.model_id}`);
        setMessage(parts.join(", "));
        if (data.warnings?.length) {
          setMessage(prev => (prev ?? "") + " — Warnings: " + data.warnings!.join("; "));
        }
      } else {
        setMessage(`Rebuild failed: ${data.error ?? "unknown error"}`);
      }
      await load();
    } catch {
      setMessage("Wiki rebuild failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">Wiki</h1>
        <p className="mt-1 text-sm text-muted">Main Wiki is generated from approved knowledge cards. Source files are not copied or deleted.</p>
      </header>

      {message ? <p className="text-sm text-primary">{message}</p> : null}

      {/* Status */}
      {status ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <div className="rounded-md border border-line bg-panel px-3 py-2">
            <span className="text-muted">Status: </span>
            <span className={status.exists ? "text-safe" : "text-warn"}>{status.exists ? "Exists" : "Missing"}</span>
          </div>
          {status.exists ? (
            <>
              <div className="rounded-md border border-line bg-panel px-3 py-2">
                <span className="text-muted">Last rebuilt: </span>
                <span className="text-ink">{status.last_rebuilt_at?.slice(0, 19) ?? "—"}</span>
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
          <button className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busy || !status.model_ready} onClick={() => rebuild("llm")} type="button" title={status.model_ready ? "Rebuild Wiki with LLM synthesis" : status.model_ready_label}>
            Rebuild Wiki
          </button>
        </div>
      ) : null}

      {/* Wiki content */}
      <div className="rounded-md border border-line bg-panel p-5">
        {content?.content ? (
          <pre className="whitespace-pre-wrap font-sans text-sm text-ink leading-relaxed">{content.content}</pre>
        ) : (
          <div>
            <p className="text-sm text-muted">Wiki has not been generated yet. Click Rebuild Wiki or run mindforge wiki rebuild.</p>
            {!status?.model_ready && <p className="text-sm text-warn">Model setup required for Wiki generation. Complete model setup first.</p>}
          </div>
        )}
      </div>

      {/* Advanced: deterministic template rebuild fallback */}
      <details className="rounded-md border border-line p-3">
        <summary className="cursor-pointer text-sm font-medium text-muted">Advanced</summary>
        <div className="mt-3 space-y-3">
          <p className="text-xs text-muted">Template rebuild is a troubleshooting fallback. It does not require a model and produces a structured summary from approved cards without LLM synthesis. This is not the recommended Wiki generation path.</p>
          <button className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink disabled:opacity-50" disabled={busy} onClick={() => rebuild("deterministic")} type="button">
            Template rebuild (no model)
          </button>
        </div>
      </details>
    </div>
  );
}
