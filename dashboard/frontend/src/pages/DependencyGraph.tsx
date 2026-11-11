import { useMemo } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/EmptyState";
import { usePoll } from "../hooks/usePoll";
import type { GraphData } from "../api/types";

export function DependencyGraph() {
  const { data, loadError } = usePoll<GraphData>("/api/v1/graph/dependencies");
  const g = data?.data;
  const nodes: Node[] = useMemo(
    () =>
      (g?.nodes ?? []).map((n, i) => ({
        id: n.id,
        data: { label: n.id },
        position: { x: 80 + (i % 3) * 220, y: 80 + Math.floor(i / 3) * 140 },
        style: { background: "#1f2c3a", color: "#e8eef4", border: "1px solid #3d9a8a", padding: 8 },
      })),
    [g],
  );
  const edges: Edge[] = useMemo(
    () =>
      (g?.edges ?? []).map((e, i) => ({
        id: `${e.source}-${e.target}-${i}`,
        source: e.source,
        target: e.target,
        label: `${e.frequency_rps.toFixed(2)} rps`,
        animated: e.frequency_rps > 0,
        style: { stroke: "#c4a35a" },
      })),
    [g],
  );
  return (
    <>
      <PageHeader
        title="Service Dependency Graph"
        summary="Directed edges from crosslayer_downstream_request_total. No synthetic 250 req/s edges."
        payload={data}
        loadError={loadError}
      />
      <div className="panel">
        {!g || g.nodes.length === 0 ? (
          <EmptyState
            title="No measured edges"
            detail={g?.note ?? "Downstream client metrics are not present in Prometheus yet."}
          />
        ) : (
          <div className="graph-wrap">
            <ReactFlowProvider>
              <ReactFlow nodes={nodes} edges={edges} fitView>
                <Background color="#2a3848" />
                <Controls />
                <MiniMap />
              </ReactFlow>
            </ReactFlowProvider>
          </div>
        )}
      </div>
    </>
  );
}
