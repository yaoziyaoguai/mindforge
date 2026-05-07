import { useEffect, useState } from "react";

interface WikiStatus {
  wiki_path: string;
  exists: boolean;
  last_rebuilt_at: string | null;
  approved_card_count: number;
  wiki_card_count: number;
}

interface WikiContent {
  content: string | null;
  exists: boolean;
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

  async function rebuild() {
    setBusy(true);
    try {
      const resp = await fetch("/api/wiki/rebuild", { method: "POST" });
      const data = await resp.json();
      if (data.ok) {
        setMessage(`Wiki rebuilt: ${data.included_cards} cards included`);
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
        <p className="mt-1 text-sm text-muted">Main Wiki is generated from approved knowledge cards. Source files are not copied or deleted. Run mindforge wiki rebuild to regenerate.</p>
      </header>

      {message ? <p className="text-sm text-primary">{message}</p> : null}

      {/* Status */}
      {status ? (
        <div className="flex flex-wrap gap-4 text-sm">
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
              <div className="rounded-md border border-line bg-panel px-3 py-2">
                <span className="text-muted">Approved cards available: </span>
                <span className="text-ink">{status.approved_card_count}</span>
              </div>
            </>
          ) : null}
          <button className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busy} onClick={rebuild} type="button">
            Rebuild Wiki
          </button>
        </div>
      ) : null}

      {/* Wiki content */}
      <div className="rounded-md border border-line bg-panel p-5">
        {content?.content ? (
          <pre className="whitespace-pre-wrap font-sans text-sm text-ink leading-relaxed">{content.content}</pre>
        ) : (
          <p className="text-sm text-muted">Wiki has not been generated yet. Click Rebuild Wiki or run mindforge wiki rebuild.</p>
        )}
      </div>
    </div>
  );
}
