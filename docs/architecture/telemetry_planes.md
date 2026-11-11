# CrossLayer Telemetry Planes

**Decision date:** 11 November 2026  
**Status:** Binding for microservice design. Do not install Istio, Linkerd, or Cilium until this document is revised.

This document answers: *which architecture collects the network and application parameters CrossLayer needs?*

## 1. One-line decision

**Do not install a full service mesh yet.**  
Use **two telemetry planes that both write to Prometheus**, then join them in the digital twin.

| Plane | Layer | What it measures | Tool |
|-------|-------|------------------|------|
| Compute | Node / Pod | CPU, memory, placement | Node Exporter, cAdvisor, kube-state-metrics (already on cluster) |
| Network L3/L4 | Node-to-node | RTT, loss, jitter, iface bytes | CrossLayer Network Prober DaemonSet + Node Exporter |
| Application L7 | Service-to-service | RPS, latency histogram, errors, caller→callee | In-app Prometheus client **now**; Envoy sidecar **later** |
| Migration | Control plane | Reschedule duration, readiness delay | Kubernetes events + our controller (future) |

A service mesh (Istio / Linkerd) only covers **L7 HTTP** well. It does **not** replace ping/TCP probes, `tc netem` experiments, CPU/memory, or migration cost.

That is the same distinction used when discussing NetMARKS: mesh telemetry is request/response (L7), not link RTT (L3).

## 2. Why not Istio / Linkerd / Cilium as the first step

| Option | What you get | Why not now |
|--------|----------------|-------------|
| **Istio** (Envoy + control plane) | Rich L7: source/dest, P50/P95, retries, mTLS | Heavy ( istiod, sidecars, CRDs ). Extra images. University network already blocks Docker Hub TLS. Easy to break Calico traffic. Overkill before a second microservice exists. |
| **Linkerd** | Lighter mesh, good HTTP metrics | Still a mesh install, extra CNI-adjacent hooks, image pull problem. |
| **Cilium + Hubble** | Excellent L3/L4 flows, optional L7 | Cluster **already uses Calico**. Replacing CNI is out of scope and high risk. Do not install Cilium on this cluster. |
| **Envoy sidecar only** (no Istio) | L7 histograms without a control plane | Good **Phase B**, after images are in `localhost:32000`. |
| **In-app Prometheus metrics** | RPS, latency, `dst_service` labels you control | **Phase A — do this first.** Works with the Flask stack you already have. No extra CNI. Images stay tiny. |

## 3. Target architecture (what you will build toward)

```
                         ┌──────────────────────────┐
                         │   DIGITAL TWIN / ENGINE  │
                         │  G=(V,E)  +  S(n,p)      │
                         └────────────▲─────────────┘
                                      │ PromQL / API
                         ┌────────────┴─────────────┐
                         │       PROMETHEUS         │
                         │   (observability ns)     │
                         └──────▲───────────▲───────┘
                                │           │
              ServiceMonitor    │           │  ServiceMonitor
                                │           │
              ┌─────────────────┴──┐     ┌──┴──────────────────┐
              │  L7 APPLICATION    │     │  L3/L4 NETWORK      │
              │  document-* pods   │     │  prober DaemonSet   │
              │  /metrics :8080    │     │  /metrics :9105     │
              │  (+ Envoy later)   │     │  one pod per node   │
              └────────────────────┘     └─────────────────────┘
                                │
                    Node Exporter + kube-state-metrics
                    (already deployed by kube-prom-stack)
```

### Data flow for one request (after both services exist)

1. Client hits `document-retrieval`.
2. Retrieval calls `http://document-verification/api/verify`.
3. Retrieval records **client** latency (`crosslayer_downstream_request_duration_seconds`).
4. Verification records **server** latency (`crosslayer_request_duration_seconds`).
5. Prober records **node-pair RTT** between the two hosting nodes (`crosslayer_probe_rtt_seconds`).
6. Twin edge \(E_{ij}\) = L7 frequency + L7 latency + L3 RTT of the node pair that currently hosts those pods.

You cannot get step 5 from a service mesh. You cannot get step 3–4 from ping alone. **You need both planes.**

## 4. Parameters each plane must produce

### 4.1 Compute (already largely available)

| Parameter | PromQL source (illustrative) | Twin field |
|-----------|------------------------------|------------|
| Node CPU | `rate(node_cpu_seconds_total{mode!="idle"}[5m])` | `C(n)` |
| Node memory | `node_memory_MemAvailable_bytes` | `M(n)` |
| Pod CPU | `rate(container_cpu_usage_seconds_total{namespace="crosslayer-workloads"}[5m])` | pod load |
| Pod memory | `container_memory_working_set_bytes` | pod load |
| Placement | kube-state-metrics `kube_pod_info` | `current_node` |

### 4.2 Network L3/L4 (must be built — not a mesh)

Prober DaemonSet: every node TCP-connects (or ICMP) to every other node on a fixed interval (for example 1 s). Export:

| Metric | Type | Labels | Meaning |
|--------|------|--------|---------|
| `crosslayer_probe_rtt_seconds` | Histogram / Summary | `src_node`, `dst_node` | Node-to-node RTT |
| `crosslayer_probe_loss_ratio` | Gauge | `src_node`, `dst_node` | Failed probes / total |
| `crosslayer_probe_jitter_seconds` | Gauge | `src_node`, `dst_node` | RTT variation |
| `crosslayer_probe_success_total` | Counter | `src_node`, `dst_node` | Success count |

Node Exporter (already running) adds:

| Metric | Meaning |
|--------|---------|
| `node_network_receive_bytes_total` | Interface receive |
| `node_network_transmit_bytes_total` | Interface transmit |
| `node_network_receive_drop_total` | Drops (congestion hint) |
| `node_netstat_Tcp_RetransSegs` | TCP retranmits if exposed |

**Impairment experiments** (`tc netem` delay/loss) belong on this plane. The prober must move when you inject 50 ms on `k8s-worker-2`. L7 latency should rise *because* L3 RTT rose. That coupling is a core research result. A mesh-only graph cannot show it cleanly.

### 4.3 Application L7 (build into every microservice now)

| Metric | Type | Required labels |
|--------|------|-----------------|
| `crosslayer_request_total` | Counter | `service`, `method`, `endpoint`, `status`, `node` |
| `crosslayer_request_duration_seconds` | Histogram | `service`, `method`, `endpoint`, `node` |
| `crosslayer_downstream_request_total` | Counter | `service`, `dst_service`, `status`, `node` |
| `crosslayer_downstream_request_duration_seconds` | Histogram | `service`, `dst_service`, `node` |
| `crosslayer_active_requests` | Gauge | `service`, `node` |

Dependency graph construction:

```
V = distinct `service` label values
E_ij frequency = rate(crosslayer_downstream_request_total{service="i",dst_service="j"}[1m])
E_ij latency   = histogram_quantile(0.95, ... downstream duration ...)
criticality    = frequency × latency   (document the formula; do not invent numbers)
```

Histogram buckets (keep identical on every service):

`0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5`

### 4.4 Envoy HTTP telemetry (Phase B overlay)

Envoy is deployed as an explicit reverse-proxy overlay in front of the current CrossLayer
Services; it does not install a service mesh or replace the workload Pods. Keep in-app
metrics when application images are available. Envoy is a second, independent L7 observer
(good for the thesis: compare app vs proxy).

The overlay exports per-service downstream request rate, response-code classes, request
latency histograms, connection counts and bytes, plus upstream request rate/latency,
connections, and connection failures. Prometheus assigns an `envoy_service` target label.
Latency percentiles require real request observations and are not filled with defaults.

The live workloads are Nginx placeholders and do not make retrieval-to-verification calls.
The overlay measures requests traversing each public Service but cannot infer a
service-to-service dependency edge or caller identity without application calls/metadata.
Never label Envoy request latency as link RTT; it includes application and proxy time.

Do not delete the Flask counters when replacing the placeholder app images. They provide
application-level labels and downstream call identity that the generic proxy cannot infer.

## 5. Kubernetes wiring (so Prometheus actually scrapes)

kube-prom-stack **ignores** `prometheus.io/scrape` annotations unless an additional scrape config exists. Use a **ServiceMonitor**.

Contract for every CrossLayer Service:

```yaml
metadata:
  namespace: crosslayer-workloads
  labels:
    project: crosslayer
    app: <service-name>
spec:
  ports:
  - name: http          # MUST be named; ServiceMonitor uses this
    port: 80
    targetPort: 8080
```

ServiceMonitor (to be applied in `observability` once we have access to the master):

- `namespaceSelector`: `crosslayer-workloads`
- `selector`: `project: crosslayer`
- endpoint port name: `http`
- path: `/metrics`
- interval: `10s`

Prober ServiceMonitor: namespace `crosslayer-system`, port name `metrics`.

## 6. How this feeds the decision engine (later)

For pod `p` on node `n`, with partner service on node `m`:

```
N(n,p)  ← f( RTT(n,m), loss(n,m), jitter(n,m) )     # L3/L4 prober
A(n,p)  ← f( P95 L7 latency of p )                  # in-app / Envoy
D(n,p)  ← f( downstream RPS to partners, locality ) # L7 edges + placement
C(n), M(n) ← Node Exporter / cAdvisor
C_mig   ← measured reschedule time (not guessed)

S(n,p) = wC·C + wM·M + wN·N + wA·A + wD·D - wR·R
MIGRATE iff B(p,n') > C_mig + H
```

If a metric is missing, the engine must **fail closed** (KEEP) and record `telemetry_incomplete`. Never fill gaps with hardcoded scores.

## 7. Build order (do not skip)

1. Freeze this contract (this document).
2. Fix Prometheus scrape for `document-retrieval` (ServiceMonitor + Grafana).
3. Deploy Network Prober DaemonSet (L3/L4).
4. Build `document-verification` **using the microservice contract**.
5. Add downstream client metrics on retrieval → verification.
6. Graph job: PromQL → `G=(V,E)` with `source=measured`.
7. Envoy reverse-proxy telemetry overlay for the existing Services; preserve app Pods and
   keep the node-to-node prober separate.
8. Only then: rule engine on **live** series.
9. Istio remains optional and late (Month 5+), not a foundation.

## 8. Cluster constraints that affect this choice

- CNI = **Calico** → no Cilium install.
- Images: prefer `localhost:32000/crosslayer/...` because Docker Hub TLS has failed on this campus network.
- Namespaces already exist: `crosslayer-workloads`, `crosslayer-system`, `crosslayer-ml`, `crosslayer-experiments`, `observability`.
- Do not expose Prometheus on `0.0.0.0`. Use port-forward + SSH tunnel.

## 9. What we will not do

- Install Istio/Linkerd/Cilium “so that we get all metrics”.
- Print fake `f_ij = 250 req/s` or fake `S(n)=0.745`.
- Treat Envoy latency as node RTT.
- Mix synthetic and measured CSV rows without a `source` column.
- Auto-migrate production-like workloads before the rule engine is tested.
