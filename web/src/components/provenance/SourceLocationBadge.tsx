/** M4 SourceLocationBadge — SDD §8.1 */

import { useEffect, useState } from "react";
import type { SourceLocationResponse } from "../../api/provenance";
import { fetchCardLocation } from "../../api/provenance";

interface SourceLocationBadgeProps {
  cardId: string;
  hasSource: boolean;
}

export function SourceLocationBadge({
  cardId,
  hasSource,
}: SourceLocationBadgeProps) {
  const [location, setLocation] = useState<SourceLocationResponse | null>(
    null,
  );

  useEffect(() => {
    if (!hasSource) return;
    let cancelled = false;
    fetchCardLocation(cardId)
      .then((loc) => {
        if (!cancelled) setLocation(loc);
      })
      .catch(() => {
        if (!cancelled) setLocation(null);
      });
    return () => {
      cancelled = true;
    };
  }, [cardId, hasSource]);

  if (!location) return null;

  return (
    <div>
      <dt className="text-xs uppercase text-muted">Source location</dt>
      <dd className="mt-1 break-words text-ink">{location.display}</dd>
    </div>
  );
}
