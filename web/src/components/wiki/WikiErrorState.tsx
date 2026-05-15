/**
 * Wiki error state component.
 *
 * Shown when the wiki rebuild or fetch fails.
 *
 * SDD_WIKI_PRESENTATION_V2 §9.
 */

import { AlertTriangle, RefreshCw } from "lucide-react";

interface WikiErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function WikiErrorState({ message, onRetry }: WikiErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-line bg-panel p-12 text-center">
      <AlertTriangle size={48} className="mb-4 text-warn" />
      <h2 className="mb-2 text-lg font-semibold text-ink">Wiki unavailable</h2>
      <p className="mb-4 max-w-md text-sm text-muted">{message}</p>
      <button
        onClick={onRetry}
        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
        type="button"
      >
        <RefreshCw size={14} />
        Retry
      </button>
    </div>
  );
}
