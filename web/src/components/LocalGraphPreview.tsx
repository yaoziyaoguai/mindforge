import { GitBranch } from "lucide-react";
import type { LocalGraphResponse, RelatedCardResponse } from "../api/types";
import { useLocale } from "../lib/i18n";

interface Props {
  graph?: LocalGraphResponse | null;
  relatedCards?: RelatedCardResponse[];
  onSelectCard?: (ref: string) => void;
}

export function LocalGraphPreview({ graph, relatedCards = [], onSelectCard }: Props) {
  const { t } = useLocale();
  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];
  const nearbyNodes = nodes.filter((node) => node.id !== graph?.center_id);

  return (
    <section className="border-t border-line p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-ink">
          <GitBranch className="h-4 w-4" /> Local Graph Preview
        </h3>
        <span className="text-xs text-muted">{relatedCards.length} related cards</span>
      </div>

      {relatedCards.length ? (
        <div className="mt-4 space-y-3">
          {relatedCards.map((item) => (
            <a
              className="block rounded-md border border-line bg-white p-3 transition hover:border-primary cursor-pointer"
              href={`/library?card=${encodeURIComponent(item.card.id ?? item.card.rel_path)}`}
              key={item.card.rel_path}
              onClick={(e) => {
                if (onSelectCard) {
                  e.preventDefault();
                  onSelectCard(item.card.id ?? item.card.rel_path);
                }
              }}
              title={item.card.title ?? item.card.rel_path}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="font-medium text-ink">{item.card.title ?? item.card.rel_path}</div>
                  <div className="mt-1 text-xs text-muted">{item.card.source_title ?? item.card.source_path_view?.display_path ?? "No source title"}</div>
                </div>
                <div className="flex flex-wrap gap-1">
                  {item.reasons.map((reason) => (
                    <span className="rounded bg-muted/10 px-1.5 py-0.5 text-[10px] font-medium text-muted" key={`${item.card.rel_path}-${reason.reason}`}>
                      {reason.label}
                    </span>
                  ))}
                </div>
              </div>
            </a>
          ))}
        </div>
      ) : (
        <p className="mt-3 rounded-md border border-line bg-white px-3 py-2 text-sm text-muted">
          No deterministic relationships found yet. This preview uses shared source, tags, wiki section, review batch, and nearby source location; it is not a global Graph page.
        </p>
      )}

      {nearbyNodes.length ? (
        <div className="mt-5">
          <h4 className="text-xs font-semibold uppercase text-muted">Local graph</h4>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {nearbyNodes.map((node) => (
              <a
                className="rounded-md border border-line bg-white px-3 py-2 text-sm text-ink transition hover:border-primary cursor-pointer"
                href={node.href ?? "#"}
                key={`${node.type}-${node.id}`}
                onClick={node.href ? (e) => {
                  if (onSelectCard && (node.type === "card" || node.type === "wiki_section")) {
                    e.preventDefault();
                    if (node.type === "card") {
                      onSelectCard(node.id);
                    }
                    // wiki_section: navigate via href (wiki page)
                  }
                } : undefined}
                title={node.label}
              >
                <span className="mr-2 rounded bg-muted/10 px-1.5 py-0.5 text-[10px] uppercase text-muted">{node.type.replace("_", " ")}</span>
                {node.label}
                {node.type === "wiki_section" && node.card_count != null && node.card_count > 0 ? (
                  <span className="ml-2 inline-flex items-center rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                    {t("wiki.local_graph_section_cards").replace("{count}", String(node.card_count))}
                  </span>
                ) : null}
              </a>
            ))}
          </div>
          {edges.length ? (
            <div className="mt-3 flex flex-wrap gap-1">
              {edges.map((edge) => (
                <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary" key={`${edge.source_id}-${edge.target_id}-${edge.reason}`}>
                  {edge.label}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
