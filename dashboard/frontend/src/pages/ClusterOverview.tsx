import { PageHeader } from "../components/PageHeader";
import { usePoll } from "../hooks/usePoll";
import type { OverviewData } from "../api/types";

export function ClusterOverview() {
  const { data, loadError } = usePoll<OverviewData>("/api/v1/cluster/overview");
  const d = data?.data;
  return (
    <>
      <PageHeader
        title="Cluster Overview"
        summary="Live node and workload counts from the Kubernetes API, plus Prometheus target health. Missing backends are reported, not guessed."
        payload={data}
        loadError={loadError}
      />
      <div className="grid kpis">
        <Kpi label="Nodes" value={d?.node_count} />
        <Kpi label="Ready nodes" value={d?.ready_node_count} />
        <Kpi label="All pods" value={d?.pod_count} />
        <Kpi label="Workload pods" value={d?.workload_pod_count} hint={d?.workload_namespace} />
      </div>
      <div className="grid split" style={{ marginTop: "0.9rem" }}>
        <div className="panel">
          <h3>Nodes (Kubernetes)</h3>
          <NodeTable nodes={d?.nodes ?? []} />
        </div>
        <div className="panel">
          <h3>Prometheus up</h3>
          <UpTable rows={d?.prometheus_up ?? []} />
        </div>
      </div>
    </>
  );
}

function Kpi({ label, value, hint }: { label: string; value?: number | null; hint?: string }) {
  return (
    <div className="panel kpi">
      <h3>{label}</h3>
      <div className="value">{value == null ? "—" : value}</div>
      {hint ? <div className="hint">{hint}</div> : null}
    </div>
  );
}

function NodeTable({ nodes }: { nodes: OverviewData["nodes"] }) {
  if (!nodes.length) return <p className="empty">No node objects from the Kubernetes API.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Role</th>
          <th>Ready</th>
          <th>CPU</th>
          <th>Memory</th>
        </tr>
      </thead>
      <tbody>
        {nodes.map((n) => (
          <tr key={n.name}>
            <td>{n.name}</td>
            <td>{n.role ?? "—"}</td>
            <td>{n.ready ? "Ready" : "NotReady"}</td>
            <td>{n.cpu_capacity ?? "—"}</td>
            <td>{n.memory_capacity ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function UpTable({ rows }: { rows: OverviewData["prometheus_up"] }) {
  if (!rows.length) return <p className="empty">No `up` series from Prometheus.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Job</th>
          <th>Instance</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {rows.slice(0, 20).map((r, i) => (
          <tr key={`${r.job}-${r.instance}-${i}`}>
            <td>{r.job ?? "—"}</td>
            <td>{r.instance ?? "—"}</td>
            <td>{r.value ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
