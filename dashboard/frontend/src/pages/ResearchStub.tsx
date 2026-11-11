import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/EmptyState";
import { usePoll } from "../hooks/usePoll";

export function ResearchStub({
  title,
  summary,
  path,
}: {
  title: string;
  summary: string;
  path: string;
}) {
  const { data, loadError } = usePoll<Record<string, unknown>>(path);
  return (
    <>
      <PageHeader title={title} summary={summary} payload={data} loadError={loadError} />
      <div className="panel">
        <EmptyState
          title="Awaiting a real engine"
          detail={
            data?.error ??
            "This module is wired to the API so the decision engine, twin, and experiment manager can attach later without changing the UI shell."
          }
        />
      </div>
    </>
  );
}
