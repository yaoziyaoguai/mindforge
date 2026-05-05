import type { SourceStatus } from "../api/types";

export function SourceList({ sources }: { sources: SourceStatus[] }) {
  return (
    <div className="overflow-hidden rounded-md border border-line bg-panel">
      <table className="w-full text-left text-sm">
        <thead className="bg-stone-100 text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Source</th>
            <th className="px-4 py-3 font-medium">Path</th>
            <th className="px-4 py-3 font-medium">Files</th>
            <th className="px-4 py-3 font-medium">Processed</th>
            <th className="px-4 py-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {sources.map((source) => (
            <tr key={source.source_type}>
              <td className="px-4 py-3">
                <div className="font-medium text-ink">{source.source_type}</div>
                <div className="text-xs text-muted">{source.adapter}</div>
              </td>
              <td className="px-4 py-3 text-muted">{source.path}</td>
              <td className="px-4 py-3">{source.file_count}</td>
              <td className="px-4 py-3">{source.processed_count}</td>
              <td className={source.exists ? "px-4 py-3 text-safe" : "px-4 py-3 text-warn"}>
                {source.exists ? "ready" : "missing folder"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
