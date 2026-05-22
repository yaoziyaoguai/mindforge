import { useEffect, useState } from "react";
import { getLibraryCardDetail, saveLibraryCardBody } from "../api/library";
import { moveLibraryCardToTrash } from "../api/trash";
import type { LibraryCardDetailResponse, LibraryCardsResponse } from "../api/types";
import { CardWorkspace } from "../components/CardWorkspace";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { StatusCard } from "../components/StatusCard";
import { friendlyStatus } from "../lib/utils";

export function LibraryPage({ data, onRefresh }: { data: LibraryCardsResponse; onRefresh?: () => void }) {
  const initialRef = new URLSearchParams(window.location.search).get("card") ?? data.cards[0]?.id ?? data.cards[0]?.rel_path;
  const [selected, setSelected] = useState<string | undefined>(initialRef ?? undefined);
  const [detail, setDetail] = useState<LibraryCardDetailResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selected) return;
    setError(null);
    getLibraryCardDetail(selected)
      .then(setDetail)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Card failed to load"));
  }, [selected]);

  async function refreshSelected() {
    if (!selected) return;
    setDetail(await getLibraryCardDetail(selected));
  }

  async function handleMoveToTrash() {
    if (!selected) return;
    try {
      const result = await moveLibraryCardToTrash(selected);
      setMessage(result.message);
      setDetail(null);
      setSelected(undefined);
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Move to trash failed");
    }
  }

  if (data.cards.length === 0) {
    return (
      <div className="space-y-6">
        <header>
          <h1 className="text-2xl font-semibold text-ink">知识库</h1>
          <p className="mt-1 text-sm text-muted">已确认的知识卡片，可供阅读、编辑和搜索。</p>
        </header>
        <EmptyState
          title="知识库为空"
          action={{
            label: "前往审阅 AI 草稿",
            description: "在审阅页面确认 AI 生成的草稿后，它们会自动出现在知识库中。也可以先添加知识源。",
            href: "/drafts",
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-ink">知识库</h1>
        <p className="mt-1 text-sm text-muted">已确认的知识卡片，可供阅读、编辑和搜索。</p>
      </header>
      <div className="grid gap-4 md:grid-cols-4">
        <StatusCard label="已确认知识" value={data.stats.by_status.human_approved ?? 0} status={(data.stats.by_status.human_approved ?? 0) > 0 ? "ok" : "info"} detail="可供阅读、编辑和搜索。" />
        <StatusCard label="待确认草稿" value={data.stats.by_status.ai_draft ?? 0} status={(data.stats.by_status.ai_draft ?? 0) > 0 ? "warn" : "ok"} detail="等待审阅确认的 AI 草稿。" />
        <StatusCard label="搜索索引" value={data.stats.index_exists ? "就绪" : "需重建"} status={data.stats.index_exists ? "ok" : "warn"} detail={data.stats.next_action} />
        <StatusCard label="知识卡片总数" value={data.stats.total_cards} status={data.stats.total_cards > 0 ? "ok" : "info"} detail="本地知识库条目。" />
      </div>
      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        <div className="space-y-2">
          {data.cards.map((card) => {
            const ref = card.id ?? card.rel_path;
            return (
              <button
                className={`w-full rounded-md border p-4 text-left transition ${selected === ref ? "border-primary bg-blue-50" : "border-line bg-panel hover:border-primary"}`}
                key={card.rel_path}
                onClick={() => setSelected(ref)}
                type="button"
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-medium text-ink">{card.title ?? card.rel_path}</h3>
                  <span className={card.status === "human_approved" ? "text-xs text-safe" : "text-xs text-warn"}>{friendlyStatus(card.status)}</span>
                </div>
                <p className="mt-1 text-sm text-muted">{card.source_title ?? card.source_path_view?.display_path ?? "No source title"}</p>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted">
                  {card.track ? <span>track:{card.track}</span> : null}
                  {card.strategy_label ? <span>{card.strategy_label}</span> : null}
                  {card.updated_at ? <span>updated:{card.updated_at.slice(0, 10)}</span> : null}
                </div>
              </button>
            );
          })}
        </div>
        <div>
          {error ? <ErrorState message={error} /> : null}
          {!error && detail ? (
            <CardWorkspace
              detail={detail}
              mode="library"
              onSave={(body) => saveLibraryCardBody(selected ?? detail.card.id ?? detail.card.rel_path, body)}
              onSaved={refreshSelected}
              onMoveToTrash={handleMoveToTrash}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
