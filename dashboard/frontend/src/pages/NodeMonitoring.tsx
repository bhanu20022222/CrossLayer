import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/EmptyState";
import { usePoll } from "../hooks/usePoll";
import type { NodeInfo } from "../api/types";

export function NodeMonitoring() {
  const { data, loadError } = usePoll<NodeInfo[]>("/api/v1/nodes");
  const nodes = data?.data ?? [];
  return (
    <>
      <PageHeader
        title="Node Monitoring"
        summary="Node inventory, capacity and Ready condition from the Kubernetes API. Utilisation charts live under CPU and Memory."
        payload={data}
        loadError={loadError}
      />
      <div className="panel">
        {nodes.length === 0 ? (
          <EmptyState
            title="No nodes"
            detail="Provide a kubeconfig (or run the API on the master). This view will not display the documented 4-node table unless the API returns those objects."
          />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Role</th>
                <th>Zone</th>
                <th>Ready</th>
                <th>Internal IP</th>
                <th>CPU cap</th>
                <th>Mem cap</th>
                <th>Kubelet</th>
                <th>OS</th>
              </tr>
            </thead>
            <tbody>
              {nodes.map((n) => (
                <tr key={n.name}>
                  <td>{n.name}</td>
                  <td>{n.role ?? "—"}</td>
                  <td>{n.zone ?? "—"}</td>
                  <td>
                    <span className={`dot ${n.ready ? "ok" : "bad"}`} />
                    {n.ready ? "Ready" : "NotReady"}
                  </td>
                  <td>{n.addresses.InternalIP ?? "—"}</td>
                  <td>{n.cpu_capacity ?? "—"}</td>
                  <td>{n.memory_capacity ?? "—"}</td>
                  <td>{n.kubelet_version ?? "—"}</td>
                  <td>{n.os_image ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
