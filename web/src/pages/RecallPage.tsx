import { useState } from "react";
import { recall } from "../api/recall";
import type { RecallResponse } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";

/** 将 BM25 分数映射为用户可理解的相关性标签，不暴露原始浮点数。
 *  BM25 是词法匹配算法（非语义 RAG），分数区间和语义模型不可直接比较。 */
function scoreLabel(score: number): { label: string; tone: string } {
  if (score >= 0.7) return { label: "高相关", tone: "text-safe" };
  if (score >= 0.4) return { label: "相关", tone: "text-warn" };
  return { label: "低相关", tone: "text-muted" };
}

export function RecallPage({ onNavigate }: { onNavigate: (href: string) => void }) {
  const [query, setQuery] = useState("");
  const [data, setData] = useState<RecallResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const q = query.trim();
    if (!q) return;
    setError(null);
    setSearching(true);
    try {
      setData(await recall(q));
    } catch (err) {
      setError(err instanceof Error ? err.message : "搜索失败");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">搜索知识</h1>
        <p className="mt-1 text-sm text-muted">搜索已确认的知识卡片。当前使用 BM25 词法匹配，非语义 RAG 检索。</p>
      </header>
      <form className="flex gap-2" onSubmit={submit}>
        <input
          className="min-w-0 flex-1 rounded-md border border-line bg-panel px-3 py-2"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜索知识卡片..."
          value={query}
          disabled={searching}
        />
        <button
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          disabled={searching || !query.trim()}
          type="submit"
        >
          {searching ? (
            <>
              <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              搜索中...
            </>
          ) : (
            "搜索"
          )}
        </button>
      </form>
      {error ? (
        <div className="rounded-md border border-danger bg-red-50 p-3 text-sm text-ink">
          <div className="flex items-start gap-2">
            <span className="mt-0.5 font-medium text-danger">搜索失败</span>
            <span className="flex-1">{error}</span>
            <button className="text-xs text-muted hover:text-ink" onClick={() => { setError(null); submit(new Event("submit") as unknown as React.FormEvent); }} type="button">重试</button>
          </div>
        </div>
      ) : null}
      {!data && !error ? (
        <EmptyState
          title="输入关键词开始搜索"
          action={{
            label: "搜索已确认知识",
            description: "输入关键词后查询已确认的知识卡片。如果没有结果，请先确认一些 AI 草稿或尝试其他关键词。",
          }}
        />
      ) : null}
      {data?.empty_state && data.hits.length === 0 ? <EmptyState title="没有找到匹配的知识卡片" action={data.empty_state} /> : null}
      {data && data.hits.length === 0 && !data.empty_state ? (
        <EmptyState
          title="没有找到匹配的知识卡片"
          action={{
            label: "前往审阅 AI 草稿",
            description: "确认更多知识卡片后再搜索，或尝试不同的关键词。当前使用 BM25 词法匹配，非语义检索。",
            href: "/drafts",
          }}
        />
      ) : null}
      {data?.hits.length ? (
        <div className="space-y-3">
          {data.hits.map((hit) => {
            const sl = scoreLabel(hit.score);
            return (
              <article key={hit.rel_path} className="rounded-md border border-line bg-panel p-4">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="font-semibold text-ink">{hit.title ?? hit.rel_path}</h2>
                  <span className={`text-sm font-medium ${sl.tone}`}>{sl.label}</span>
                </div>
                <p className="mt-2 text-sm text-muted">匹配原因: {hit.why_this_matched}</p>
                <button
                  className="mt-3 rounded-md border border-line px-3 py-1.5 text-sm font-medium text-primary"
                  onClick={() => onNavigate(hit.detail_href ?? `/library?card=${encodeURIComponent(hit.card_ref ?? hit.rel_path)}`)}
                  type="button"
                >
                  打开知识卡片
                </button>
              </article>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
