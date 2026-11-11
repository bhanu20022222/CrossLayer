export type ValueKind =
  | "measured"
  | "derived"
  | "predicted"
  | "simulated"
  | "unavailable";

export type Source = "prometheus" | "kubernetes" | "derived" | "none";

export interface Envelope<T> {
  source: Source;
  value_kind: ValueKind;
  as_of: string;
  error: string | null;
  data: T;
}

export interface HealthData {
  status: string;
  prometheus: { ok: boolean; url: string; error: string | null };
  kubernetes: { ok: boolean; error: string | null };
}

export interface NodeInfo {
  name: string;
  ready: boolean;
  unschedulable: boolean;
  addresses: Record<string, string>;
  cpu_capacity: string | null;
  memory_capacity: string | null;
  cpu_allocatable: string | null;
  memory_allocatable: string | null;
  kubelet_version: string | null;
  os_image: string | null;
  zone: string | null;
  role: string | null;
}

export interface PodInfo {
  name: string;
  namespace: string;
  node: string | null;
  phase: string;
  pod_ip: string | null;
  ready: boolean;
  restarts: number;
  labels: Record<string, string>;
  app: string | null;
  project: string | null;
}

export interface SeriesPoint {
  t: number;
  v: number;
}

export interface Series {
  name: string;
  labels: Record<string, string>;
  points: SeriesPoint[];
}

export interface NetworkInterface {
  instance: string;
  device: string;
  up: boolean | null;
  speed_bytes_per_second: number | null;
}

export interface NetworkData {
  range: string;
  step: string | null;
  receive: Series[];
  transmit: Series[];
  node_receive: Series[];
  node_transmit: Series[];
  node_receive_mbps: Series[];
  node_transmit_mbps: Series[];
  node_receive_packets: Series[];
  node_transmit_packets: Series[];
  node_receive_errors: Series[];
  node_transmit_errors: Series[];
  node_receive_drops: Series[];
  node_transmit_drops: Series[];
  node_receive_utilization: Series[];
  node_transmit_utilization: Series[];
  node_tcp_retransmits: Series[];
  inter_node_rtt_ms: Series[];
  inter_node_rtt_p50_ms: Series[];
  inter_node_rtt_p95_ms: Series[];
  inter_node_rtt_p99_ms: Series[];
  inter_node_jitter_ms: Series[];
  inter_node_loss_percent: Series[];
  interfaces: NetworkInterface[];
  probe_targets: { instance: string; up: boolean }[];
  note: string;
}

export interface EnvoyData {
  range: string;
  step: string | null;
  request_rate: Series[];
  latency_p50_seconds: Series[];
  latency_p95_seconds: Series[];
  latency_p99_seconds: Series[];
  response_4xx_rate: Series[];
  response_5xx_rate: Series[];
  downstream_connections_active: Series[];
  downstream_receive_bytes_rate: Series[];
  downstream_transmit_bytes_rate: Series[];
  upstream_request_rate: Series[];
  upstream_latency_p95_seconds: Series[];
  upstream_connections_active: Series[];
  upstream_connection_failures_rate: Series[];
  target_status: { envoy_service: string; instance: string; up: boolean }[];
  note: string;
}

export interface ApplicationTrafficData {
  range: string;
  request_rate: Series[];
  latency_p95: Series[];
  note: string;
}

export interface ExperimentMetricsData {
  range: string;
  step: string | null;
  request_rate: Series[];
  latency_p95: Series[];
  downstream_rate: Series[];
  downstream_latency_p95: Series[];
  note: string;
}

export interface ExperimentLoadStatus {
  state: "idle" | "running" | "stopped" | "completed";
  max_requests_per_second: number;
  max_duration_seconds: number;
  run_id?: string;
  requests_per_second?: number;
  duration_seconds?: number;
  attempted?: number;
  succeeded?: number;
  failed?: number;
  skipped?: number;
  elapsed_seconds?: number;
  last_error?: string | null;
  started_at?: string;
  ended_at?: string | null;
}

export interface OverviewData {
  node_count: number | null;
  ready_node_count: number | null;
  pod_count: number | null;
  workload_pod_count: number | null;
  workload_namespace: string;
  nodes: NodeInfo[];
  workload_pods: PodInfo[];
  prometheus_up: { job?: string; instance?: string; value: number | null }[];
  partial_errors: { kubernetes: string | null; prometheus: string | null };
}

export interface GraphData {
  nodes: { id: string }[];
  edges: {
    source: string;
    target: string;
    frequency_rps: number;
    p95_seconds: number | null;
    value_kind: ValueKind;
  }[];
  note: string;
}

export interface AffinityNode {
  name: string;
  ready: boolean;
  schedulable: boolean;
  network_utilization_percent: number | null;
}

export interface AffinityLink {
  source: string;
  target: string;
  score: number | null;
  coverage_percent: number;
  components: Record<string, number>;
  observed: Record<string, number>;
}

export interface AffinityCandidate {
  node: string;
  score: number | null;
  rank: number | null;
  is_current: boolean;
  ready: boolean;
  schedulable: boolean;
  traffic_coverage_percent: number;
  feature_coverage_percent: number;
  local_path_assumptions: number;
  communication_rps: number;
}

export interface PodAffinityRecommendation {
  pod: string;
  namespace: string;
  service: string;
  current_node: string;
  dependencies: [string, string][];
  advice: "consider_network_candidate" | "keep_current" | "insufficient_measurements";
  best_alternative_node: string | null;
  improvement_points: number | null;
  candidates: AffinityCandidate[];
}

export interface NetworkAffinityData {
  algorithm: {
    name: string;
    version: string;
    method: string;
    window: string;
    feature_weights: Record<string, number>;
    normalization: Record<string, string>;
    placement: string;
    advisory_policy: {
      minimum_improvement_points: number;
      minimum_traffic_coverage_percent: number;
      minimum_feature_coverage_percent: number;
    };
  };
  nodes: AffinityNode[];
  node_links: AffinityLink[];
  communications: {
    source: string;
    destination: string;
    requests_per_second: number;
    value_kind: ValueKind;
  }[];
  recommendations: PodAffinityRecommendation[];
  probe_targets_up: number;
  probe_targets_total: number;
  partial_errors: string[];
  note: string;
}
