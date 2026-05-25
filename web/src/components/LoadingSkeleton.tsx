/**
 * CSS-only loading skeleton using Tailwind animate-pulse.
 *
 * H1 — Last-Mile Web Polish: replaces plain "Loading..." text with
 * page-appropriate skeleton placeholders. No new dependencies.
 */

function Block({ className }: { className?: string }) {
  return <div className={`rounded bg-muted/30 ${className ?? ""}`} />;
}

export function LoadingSkeleton({ variant = "default" }: { variant?: "default" | "wiki" | "library" | "drafts" | "search" | "sources" | "health" | "trash" | "setup" | "dogfood" }) {
  if (variant === "wiki") {
    return (
      <div className="space-y-6 animate-pulse">
        <Block className="h-8 w-48" />
        <div className="flex gap-6">
          <div className="hidden w-48 space-y-3 lg:block">
            <Block className="h-4 w-32" />
            <Block className="h-3 w-24" />
            <Block className="h-3 w-28" />
            <Block className="h-3 w-20" />
          </div>
          <div className="flex-1 space-y-4">
            <Block className="h-6 w-64" />
            <Block className="h-4 w-full" />
            <Block className="h-4 w-5/6" />
            <Block className="h-4 w-4/6" />
            <Block className="h-6 w-48" />
            <Block className="h-4 w-full" />
            <Block className="h-4 w-3/4" />
            <Block className="h-4 w-5/6" />
          </div>
        </div>
      </div>
    );
  }

  if (variant === "library") {
    return (
      <div className="space-y-6 animate-pulse">
        <Block className="h-8 w-40" />
        <Block className="h-4 w-64" />
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Block key={i} className="h-20" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Block key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  if (variant === "search") {
    return (
      <div className="space-y-6 animate-pulse">
        <Block className="h-8 w-40" />
        <Block className="h-4 w-96" />
        <div className="flex gap-2">
          <Block className="h-10 flex-1" />
          <Block className="h-10 w-24" />
        </div>
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Block key={i} className="h-24" />
          ))}
        </div>
      </div>
    );
  }

  if (variant === "sources") {
    return (
      <div className="space-y-6 animate-pulse">
        <Block className="h-8 w-32" />
        <Block className="h-4 w-80" />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Block key={i} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  if (variant === "health") {
    return (
      <div className="space-y-6 animate-pulse">
        <Block className="h-8 w-48" />
        <Block className="h-4 w-72" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Block key={i} className="h-24" />
          ))}
        </div>
        <Block className="h-48" />
      </div>
    );
  }

  if (variant === "trash") {
    return (
      <div className="space-y-6 animate-pulse">
        <Block className="h-8 w-32" />
        <Block className="h-4 w-64" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Block key={i} className="h-16" />
          ))}
        </div>
      </div>
    );
  }

  if (variant === "setup") {
    return (
      <div className="space-y-6 animate-pulse">
        <Block className="h-8 w-56" />
        <Block className="h-4 w-96" />
        <div className="flex gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Block key={i} className="h-10 w-28" />
          ))}
        </div>
        <div className="space-y-4">
          <Block className="h-64" />
        </div>
      </div>
    );
  }

  if (variant === "dogfood") {
    return (
      <div className="space-y-6 animate-pulse">
        <Block className="h-8 w-56" />
        <Block className="h-4 w-80" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Block key={i} className="h-20" />
          ))}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Block className="h-32" />
          <Block className="h-32" />
        </div>
      </div>
    );
  }

  if (variant === "drafts") {
    return (
      <div className="space-y-6 animate-pulse">
        <Block className="h-8 w-40" />
        <Block className="h-4 w-56" />
        <div className="grid gap-5 lg:grid-cols-[320px_1fr_280px]">
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Block key={i} className="h-16" />
            ))}
          </div>
          <Block className="h-96" />
          <Block className="h-64" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-pulse">
      <Block className="h-8 w-48" />
      <Block className="h-4 w-72" />
      <Block className="h-64 w-full" />
    </div>
  );
}
