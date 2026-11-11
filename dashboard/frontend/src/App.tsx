import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthGate";
import { AppShell } from "./layout/AppShell";
import { ClusterOverview } from "./pages/ClusterOverview";
import { NodeMonitoring } from "./pages/NodeMonitoring";
import { PodMonitoring } from "./pages/PodMonitoring";
import { ComputeAnalytics } from "./pages/ComputeAnalytics";
import { NetworkMonitoring } from "./pages/NetworkMonitoring";
import { NetworkAffinity } from "./pages/NetworkAffinity";
import { ApplicationTraffic } from "./pages/ApplicationTraffic";
import { ExperimentalEvaluation } from "./pages/ExperimentalEvaluation";
import { DependencyGraph } from "./pages/DependencyGraph";
import { ResearchStub } from "./pages/ResearchStub";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<ClusterOverview />} />
          <Route path="/nodes" element={<NodeMonitoring />} />
          <Route path="/pods" element={<PodMonitoring />} />
          <Route path="/compute" element={<ComputeAnalytics />} />
          <Route path="/network" element={<NetworkMonitoring />} />
          <Route path="/affinity" element={<NetworkAffinity />} />
          <Route path="/application" element={<ApplicationTraffic />} />
          <Route path="/graph" element={<DependencyGraph />} />
          <Route
            path="/twin"
            element={
              <ResearchStub
                title="CrossLayer Digital Twin"
                summary="Will render the measured cluster snapshot plus explicitly labelled what-if predictions. No twin process exists in the repo yet."
                path="/api/v1/twin/state"
              />
            }
          />
          <Route
            path="/decisions"
            element={
              <ResearchStub
                title="Migration Decision Center"
                summary="KEEP/MIGRATE will appear only when the rule engine reads live telemetry. This screen refuses demo scores."
                path="/api/v1/decisions"
              />
            }
          />
          <Route
            path="/migrations"
            element={
              <ResearchStub
                title="Migration History"
                summary="Reschedule events, duration, and readiness will be appended by the future controller."
                path="/api/v1/migrations"
              />
            }
          />
          <Route path="/experiments" element={<ExperimentalEvaluation />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
