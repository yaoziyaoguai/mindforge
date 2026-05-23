import type { NextAction } from "../api/types";
import type { Locale } from "../lib/i18n";
import { nextActionLabel } from "../lib/utils";

/* 中文学习型说明：action_key 优先用于本地化展示空状态操作标签。
 * label 是兼容 fallback，缺 action_key 时直接展示原始文案。
 * i18n 只改变 presentation，不改变 action 行为。 */
export function EmptyState({ title, action, locale }: { title: string; action?: NextAction | null; locale?: Locale }) {
  const displayLabel = nextActionLabel(action?.action_key, locale) ?? action?.label;
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
              {displayLabel}
            </a>
          ) : action.onClick ? (
            <button
              className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white"
              onClick={action.onClick}
              type="button"
            >
              {displayLabel}
            </button>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
