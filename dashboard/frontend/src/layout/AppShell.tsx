import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthGate";
import { usePoll } from "../hooks/usePoll";
import type { HealthData } from "../api/types";

const LINKS = [
  ["/overview", "Cluster Overview"],
  ["/nodes", "Node Monitoring"],
  ["/pods", "Pod Monitoring"],
  ["/compute", "CPU and Memory"],
  ["/network", "Network Monitoring"],
  ["/affinity", "Network Affinity"],
  ["/application", "Latency and Throughput"],
  ["/graph", "Service Dependency Graph"],
  ["/twin", "Digital Twin"],
  ["/decisions", "Migration Decision Center"],
  ["/migrations", "Migration History"],
  ["/experiments", "Experimental Evaluation"],
];

export function AppShell() {
  const { username, logout, logoutError } = useAuth();
  const { data } = usePoll<HealthData>("/api/v1/health", 20000);
  const prom = data?.data.prometheus.ok;
  const kube = data?.data.kubernetes.ok;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <h1>CrossLayer</h1>
          <p>Network-aware migration research dashboard. Values are measured or marked unavailable.</p>
        </div>
        <nav>
          {LINKS.map(([to, label]) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : "")}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="panel" style={{ marginTop: "auto" }}>
          <h3>Signed in as {username}</h3>
          <button
            type="button"
            onClick={() => {
              void logout().catch(() => undefined);
            }}
          >
            Sign out
          </button>
          {logoutError ? <p className="auth-error" role="alert">{logoutError}</p> : null}
        </div>
        <div className="panel">
          <h3>Collectors</h3>
          <div>
            <span className={`dot ${prom ? "ok" : "bad"}`} />
            Prometheus {prom ? "reachable" : "not reachable"}
          </div>
          <div style={{ marginTop: "0.35rem" }}>
            <span className={`dot ${kube ? "ok" : "bad"}`} />
            Kubernetes {kube ? "reachable" : "not reachable"}
          </div>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
