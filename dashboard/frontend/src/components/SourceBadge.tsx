import type { ValueKind } from "../api/types";

export function SourceBadge({ kind }: { kind: ValueKind }) {
  return <span className={`badge ${kind}`}>{kind}</span>;
}
