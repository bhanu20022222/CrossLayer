# CrossLayer — System Architecture

**Telemetry decision (11 Nov 2026):** two Prometheus planes — L3/L4 node prober + L7 in-app metrics; Envoy later; no Istio/Linkerd/Cilium now. See `docs/architecture/telemetry_planes.md` and `docs/architecture/microservice_contract.md`.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION WORKLOADS                     │
│         Document Retrieval ←──→ Document Verification       │
│                        ↑  Load Generator  ↑                 │
└────────────────────────┼──────────────────┼─────────────────┘
                         │                  │
                    Telemetry          Telemetry
                         │                  │
┌────────────────────────┼──────────────────┼─────────────────┐
│                  METRIC COLLECTION LAYER                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Compute  │  │ Network  │  │   App    │  │ Storage  │    │
│  │ Metrics  │  │ Metrics  │  │ Metrics  │  │ Metrics  │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │              │             │              │          │
│       └──────────────┴─────────────┴──────────────┘          │
│                           │                                  │
│                     PROMETHEUS                               │
└───────────────────────────┼──────────────────────────────────┘
                            │
┌───────────────────────────┼──────────────────────────────────┐
│              CROSS-LAYER FEATURE ENGINE                      │
│                           │                                  │
│  ┌────────────────────────┴────────────────────────────┐     │
│  │              Feature Extraction                     │     │
│  │  CPU | MEM | LAT | BW | LOSS | APP | DEP | MIG     │     │
│  └────────────────────────┬────────────────────────────┘     │
│                           │                                  │
│  ┌────────────────────────┴────────────────────────────┐     │
│  │          Application Dependency Graph               │     │
│  │     Service A ──(100 req/s, 12ms)──→ Service B      │     │
│  └────────────────────────┬────────────────────────────┘     │
└───────────────────────────┼──────────────────────────────────┘
                            │
┌───────────────────────────┼──────────────────────────────────┐
│                DECISION ENGINE                               │
│                           │                                  │
│  ┌──────────┐   ┌────────┴───────┐   ┌──────────────┐       │
│  │ Rule-    │   │ Node Scoring   │   │ ML Prediction│       │
│  │ Based    │──→│ S = Σ wᵢfᵢ    │←──│ (Python API) │       │
│  │ Engine   │   └────────┬───────┘   └──────────────┘       │
│  └──────────┘            │                                   │
│              ┌───────────┴───────────┐                       │
│              │  Migration Decision   │                       │
│              │  B(p,n) > C_mig + H   │                       │
│              └───────────┬───────────┘                       │
└──────────────────────────┼───────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────┐
│              GO KUBERNETES CONTROLLER                         │
│                          │                                    │
│  ┌──────────┐  ┌─────────┴──────┐  ┌──────────────────┐     │
│  │ Cluster  │  │ Migration      │  │ Policy           │     │
│  │ Observer │  │ Coordinator    │  │ Validator        │     │
│  └──────────┘  └─────────┬──────┘  └──────────────────┘     │
│                          │                                    │
│                  Kubernetes API                               │
└──────────────────────────┼───────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
     Worker 1         Worker 2         Worker 3
```

## Module Descriptions

### Module 1: Metric Collection Layer
Collects CPU, memory, network latency, throughput, packet loss, jitter, application response time, request rate, and storage metrics from all nodes and pods.

**Technologies**: Prometheus, Node Exporter, kube-state-metrics, application instrumentation

### Module 2: Application Dependency Graph
Represents service communication as a directed weighted graph G = (V, E) where edges carry communication frequency, observed latency, traffic volume, and criticality.

### Module 3: Cross-Layer Feature Engine
Combines all collected metrics into a normalised feature vector:

```
Xᵢ = [CPUᵢ, MEMᵢ, LATᵢ, BWᵢ, LOSSᵢ, JITTERᵢ, APPᵢ, DEPᵢ, STORAGEᵢ, MIGᵢ]
```

### Module 4: Decision Engine
Calculates node suitability score:

```
S(n,p) = w₁C(n) + w₂M(n) + w₃N(n,p) + w₄A(n,p) + w₅D(n,p) - w₆R(n,p)
```

Migrates only when: `B(p,n) > C_migration + H`

### Module 5: Go Kubernetes Controller
Watches workloads, consumes metrics, requests placement recommendations, validates candidates, executes controlled rescheduling, and records decisions.

### Module 6: Python ML Engine
Predicts node suitability and migration benefit using interpretable models (Linear Regression, Random Forest, XGBoost).

### Module 7: Digital Twin
Maintains a logical representation of cluster topology, workload dependencies, and network conditions for simulation and prediction validation.

## Kubernetes Namespace Design

| Namespace | Purpose |
|-----------|---------|
| crosslayer-system | Go controller, decision engine |
| crosslayer-workloads | Document retrieval, verification, load generator |
| crosslayer-ml | Python prediction API |
| crosslayer-experiments | Experiment jobs, benchmarks |
| observability | Prometheus, Grafana, Loki, Tempo (existing) |

## Controller Operating Modes

| Mode | Behaviour |
|------|-----------|
| Observe | Collect metrics and monitor workloads |
| Recommend | Generate placement recommendations |
| Dry-run | Evaluate and validate proposed actions |
| Controlled | Execute approved workload rescheduling |
| Autonomous | Execute policies automatically (future) |
