import type { NextAction } from "../api/types";

export function EmptyState({ title, action }: { title: string; action?: NextAction | null }) {
  return (
    <section className="rounded-md border border-dashed border-line bg-panel p-8">
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      {action ? (
        <>
          <p className="mt-2 text-sm text-muted">{action.description}</p>
          {action.command ? (
            <code className="mt-4 block rounded bg-stone-100 px-3 py-2 text-sm text-ink">{action.command}</code>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
