import { SourceBadge } from "./SourceBadge";
import type { Envelope } from "../api/types";

export function PageHeader({
  title,
  summary,
  payload,
  loadError,
}: {
  title: string;
  summary: string;
  payload?: Envelope<unknown> | null;
  loadError?: string | null;
}) {
  return (
    <div className="page-head">
      <div>
        <h2>{title}</h2>
        <p>{summary}</p>
        {loadError ? <p className="error">{loadError}</p> : null}
        {payload?.error ? <p className="error">{payload.error}</p> : null}
      </div>
      <div className="badges">
        {payload ? <SourceBadge kind={payload.value_kind} /> : null}
        {payload ? <span className="badge">{payload.source}</span> : null}
      </div>
    </div>
  );
}
