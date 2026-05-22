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
          {/* action.href 渲染 a 链接；action.onClick 渲染 button；两者互斥，href 优先 */}
          {action.href ? (
            <a
              className="mt-4 inline-block rounded-md bg-primary px-4 py-2 text-sm font-medium text-white no-underline"
              href={action.href}
            >
              {action.label}
            </a>
          ) : action.onClick ? (
            <button
              className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white"
              onClick={action.onClick}
              type="button"
            >
              {action.label}
            </button>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
