import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/EmptyState";
import { usePoll } from "../hooks/usePoll";
import type { PodInfo } from "../api/types";

export function PodMonitoring() {
  const { data, loadError } = usePoll<{ namespace: string; pods: PodInfo[] }>("/api/v1/pods");
  const pods = data?.data.pods ?? [];
  return (
    <>
      <PageHeader
        title="Pod Monitoring"
        summary="Pods in crosslayer-workloads from the Kubernetes API: node placement, Ready, restarts, Pod IP."
        payload={data}
        loadError={loadError}
      />
      <div className="panel">
        {pods.length === 0 ? (
          <EmptyState title="No pods" detail="The API returned an empty list or Kubernetes is unavailable." />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Pod</th>
                <th>App</th>
                <th>Node</th>
                <th>Phase</th>
                <th>Ready</th>
                <th>IP</th>
                <th>Restarts</th>
              </tr>
            </thead>
            <tbody>
              {pods.map((p) => (
                <tr key={`${p.namespace}/${p.name}`}>
                  <td>{p.name}</td>
                  <td>{p.app ?? "—"}</td>
                  <td>{p.node ?? "—"}</td>
                  <td>{p.phase}</td>
                  <td>{p.ready ? "true" : "false"}</td>
                  <td>{p.pod_ip ?? "—"}</td>
                  <td>{p.restarts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
