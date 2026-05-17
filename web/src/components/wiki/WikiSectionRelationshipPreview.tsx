import { GitBranch } from "lucide-react";
import type { WikiReferenceView } from "../../api/wiki";

interface Props {
  sectionTitle: string;
  refs: WikiReferenceView[];
}

export function WikiSectionRelationshipPreview({ sectionTitle, refs }: Props) {
  if (!refs.length) return null;

  const sources = unique(refs.map((ref) => ref.source_title ?? ref.source_path).filter(isString));
  const tags = unique(refs.flatMap((ref) => ref.tags));

  return (
    <div className="mt-4 rounded-md border border-line bg-white p-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-ink">
        <GitBranch className="h-4 w-4" /> Section Relationship Preview
      </h3>
      <p className="mt-1 text-xs text-muted">{sectionTitle} links {refs.length} approved knowledge cards.</p>

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
    </div>
  );
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values.filter((value) => value.trim())));
}

function isString(value: string | null): value is string {
  return value !== null;
}
