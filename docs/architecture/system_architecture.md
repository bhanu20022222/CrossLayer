# System Architecture — Detailed Design

## Module 1: Kubernetes Cluster Monitoring

### Metrics Collected
| Metric | Description | Unit |
|--------|-------------|------|
| CPU utilisation | CPU consumed by node and pod | % |
| Memory utilisation | RAM usage by node and pod | % |
| CPU requests | Allocated CPU requests | Cores |
| Memory requests | Allocated memory requests | Bytes |
| Pod status | Running, pending, failed | Enum |
| Node status | Ready, not ready | Enum |
| Pod placement | Which node hosts each pod | String |
| Available resources | Remaining allocatable resources | Cores / Bytes |

### Implementation
- Kubernetes API via Go client-go
- Metrics Server (already enabled)
- Prometheus (kube-prom-stack, already deployed)
- Node Exporter (already on all 4 nodes)
- kube-state-metrics (already running)

## Module 2: Network Monitoring

### Metrics Collected
| Metric | Description | Unit |
|--------|-------------|------|
| RTT | Round-trip time between nodes | ms |
| Latency | Communication delay | ms |
| Throughput | Actual data transfer rate | Mbps |
| Bandwidth | Available link capacity | Mbps |
| Packet loss | Percentage of lost packets | % |
| Jitter | Variation in packet delay | ms |
| TCP retransmissions | Retransmitted packets | Count |

### Network Topology
```
k8s-master-1 (10.2.0.145)
        │
        ├── k8s-worker-1 (10.2.0.131)
        │
        ├── k8s-worker-2 (10.2.0.132)
        │
        └── k8s-worker-3 (10.2.0.133)

Pod Network: 10.1.x.x (Calico)
Service Network: 10.152.183.x
```

## Module 3: Application Dependency Graph

Service communication represented as: G = (V, E)

Each edge: E_ij = (frequency, latency, bandwidth_demand, criticality)

## Module 4: Cross-Layer Feature Engine

Feature vector per workload-node pair:
```
X_i = [CPU_i, MEM_i, LAT_i, BW_i, LOSS_i, JITTER_i, APP_i, DEP_i, STORAGE_i, MIG_i]
```

## Module 5: Decision Engine

### Node Suitability Score
```
S(n,p) = w1*C(n) + w2*M(n) + w3*N(n,p) + w4*A(n,p) + w5*D(n,p) - w6*R(n,p)
```

### Initial Weights
| Parameter | Weight |
|-----------|--------|
| CPU suitability | 0.15 |
| Memory suitability | 0.15 |
| Network suitability | 0.25 |
| Application suitability | 0.20 |
| Dependency locality | 0.15 |
| Migration risk | 0.10 |

### Migration Decision
Migrate when: `B(p,n) > C_migration + H`

Where:
- B(p,n) = J_current(p) - J_target(p,n) (expected benefit)
- C_migration = estimated migration cost
- H = configurable hysteresis threshold
