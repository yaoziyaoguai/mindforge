import { GitBranch } from "lucide-react";
import type { WikiReferenceView } from "../../api/wiki";

interface Props {
  sectionTitle: string;
  refs: WikiReferenceView[];
}

export function WikiSectionRelationshipPreview({ sectionTitle, refs }: Props) {
  const sources = unique(refs.map((ref) => ref.source_title ?? ref.source_path).filter(isString));
  const tags = unique(refs.flatMap((ref) => ref.tags));

  return (
    <div className="mt-4 rounded-md border border-line bg-white p-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-ink">
        <GitBranch className="h-4 w-4" /> Section Relationship Preview
      </h3>
      <p className="mt-1 text-xs text-muted">{sectionTitle} links {refs.length} approved knowledge cards.</p>

      {refs.length > 0 ? (
        <>
          <div className="mt-3 space-y-2">
            {refs.map((ref) => (
              <a
                className="block rounded-md border border-line px-3 py-2 text-sm text-ink transition hover:border-primary"
                href={`/library?card=${encodeURIComponent(ref.card_id || ref.card_rel_path)}`}
                key={ref.card_rel_path}
              >
                <span className="font-medium">{ref.card_title}</span>
                <span className="ml-2 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                  Wiki section reference
                </span>
              </a>
            ))}
          </div>

          <div className="mt-3 flex flex-wrap gap-1">
            {sources.map((source) => (
              <span className="rounded bg-muted/10 px-1.5 py-0.5 text-[10px] text-muted" key={`source-${source}`}>
                Source: {source}
              </span>
            ))}
            {tags.map((tag) => (
              <span className="rounded bg-muted/10 px-1.5 py-0.5 text-[10px] text-muted" key={`tag-${tag}`}>
                #{tag}
              </span>
            ))}
          </div>
        </>
      ) : (
        // 中文学习型说明：这是 Wiki 内的局部关系预览 empty-state，不是全局 Graph 页面；
        // 关系只来自 shared source/tag/wiki section/review batch 等确定性信号。
        <p className="mt-3 rounded-md border border-line bg-muted/5 px-3 py-2 text-sm text-muted">
          This section has no visible relationships yet. Local Graph uses deterministic relationships from shared source, tags, wiki section, and review batches.
        </p>
      )}
    </div>
  );
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values.filter((value) => value.trim())));
}

function isString(value: string | null): value is string {
  return value !== null;
}
