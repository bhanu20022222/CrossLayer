# CrossLayer — Day 1 Report

**Date**: 9 November 2026
**Project**: CrossLayer — A Cross-Layer Digital Twin Framework for Network-Aware Workload Migration in Kubernetes

---

## Day 1 Summary

Day 1 established the project foundation: cluster verification, repository creation, documentation, and the first research workload deployment.

## Cluster Inventory — Verified

| Node | Role | IP | CPU | RAM (Allocatable) | OS | Kernel |
|------|------|----|-----|--------------------|----|--------|
| k8s-master-1 | Control Plane | 10.2.0.145 | 24 cores | ~64 GB | Ubuntu 24.04.3 LTS | 6.8.0-107-generic |
| k8s-worker-1 | Worker | 10.2.0.131 | 24 cores | ~64 GB | Ubuntu 24.04.3 LTS | 6.8.0-71-generic |
| k8s-worker-2 | Worker | 10.2.0.132 | 24 cores | ~64 GB | Ubuntu 24.04.3 LTS | 6.8.0-71-generic |
| k8s-worker-3 | Worker | 10.2.0.133 | 24 cores | ~64 GB | Ubuntu 24.04.3 LTS | 6.8.0-71-generic |

**Total Cluster**: 96 CPU cores, ~256 GB RAM

| Component | Status | Details |
|-----------|--------|---------|
| Kubernetes | v1.33.13 | MicroK8s, 203 days old |
| Container Runtime | containerd 1.7.29 | — |
| CNI | Calico | calico-node on all 4 nodes |
| Prometheus | ✅ Running | kube-prom-stack in `observability` namespace |
| Grafana | ✅ Running | admin / prom-operator |
| Node Exporter | ✅ Running | All 4 nodes |
| kube-state-metrics | ✅ Running | — |
| Loki + Promtail | ✅ Running | Log aggregation |
| Tempo | ✅ Running | Distributed tracing |
| Metrics Server | ✅ Running | — |
| Container Registry | ✅ Running | localhost:32000 |
| Storage Class | microk8s-hostpath | Default |
| RBAC | ❌ Disabled | To be noted |
| Node Taints | None | Master accepts workloads |

### Resource Usage at Day 1

| Node | CPU Usage | CPU % | Memory Usage | Memory % |
|------|-----------|-------|--------------|----------|
| k8s-master-1 | 569m | 2% | 7339 Mi | 11% |
| k8s-worker-1 | 135m | 0% | 5641 Mi | 8% |
| k8s-worker-2 | 539m | 2% | 5313 Mi | 8% |
| k8s-worker-3 | 700m | 2% | 6544 Mi | 10% |

## Tasks Completed

### ✅ 1. Cluster Inspection
- Verified all 4 nodes are `Ready`
- Confirmed 24 CPU cores and ~64 GB RAM per node
- Identified CNI as Calico
- Identified existing monitoring stack (Prometheus, Grafana, Loki, Tempo)
- Recorded existing namespaces and workloads

### ✅ 2. Node Labelling
- Labelled k8s-master-1 with `node-role.kubernetes.io/control-plane`
- Labelled k8s-worker-1/2/3 with `node-role.kubernetes.io/worker`
- Added zone labels: `crosslayer.io/zone=zone-a/b/c`

### ✅ 3. Namespace Creation
Created 4 project namespaces:
- `crosslayer-system` — Controller and decision engine
- `crosslayer-workloads` — Application workloads
- `crosslayer-ml` — ML prediction API
- `crosslayer-experiments` — Experiment jobs

### ✅ 4. Document Retrieval Microservice
- Built nginx-based document retrieval service
- Serves 8 research-relevant documents via REST API
- Endpoints: `/health`, `/ready`, `/api/documents`, `/api/placement`, `/metrics`
- Structured JSON logging
- Prometheus metrics endpoint

### ✅ 5. Kubernetes Deployment
- 3 replicas with `topologySpreadConstraints`
- Pods distributed across k8s-master-1, k8s-worker-2, k8s-worker-3
- Liveness and readiness probes configured
- Resource requests: 100m CPU, 64Mi memory
- Resource limits: 500m CPU, 128Mi memory
- ClusterIP service on port 80
- NodePort service on port 30080

### ✅ 6. Endpoint Verification
All endpoints tested and returning correct responses:

| Endpoint | Status | Response |
|----------|--------|----------|
| `/health` | ✅ | `{"status":"healthy","service":"document-retrieval","version":"0.1.0"}` |
| `/api/documents` | ✅ | 8 documents returned with served_by info |
| `/api/placement` | ✅ | Pod hostname and timestamp |

### ✅ 7. Repository Structure Created

```
CrossLayer/
├── README.md
├── .gitignore
├── PROJECT_SPECIFICATION.md
├── ARCHITECTURE.md
├── DEVELOPMENT_ROADMAP.md
├── docs/
│   ├── research/
│   │   ├── problem_statement.md
│   │   ├── research_questions.md
│   │   ├── objectives.md
│   │   └── contributions.md
│   ├── architecture/
│   │   └── system_architecture.md
│   └── experiments/
│       └── evaluation_metrics.md
├── deployments/
│   ├── namespaces/
│   │   └── crosslayer-namespaces.yaml
│   └── workloads/
│       └── document-retrieval.yaml
├── workloads/
│   └── document-retrieval/
│       ├── app.py
│       ├── requirements.txt
│       ├── Dockerfile
│       ├── Dockerfile.nginx
│       └── nginx.conf
├── scripts/
│   └── cluster-inspection/
│       ├── inspect-cluster.sh
│       └── health-check.sh
├── controller/
│   └── README.md
├── ml-engine/
│   └── README.md
├── digital-twin/
│   └── README.md
├── experiments/
│   └── baseline/
│       └── README.md
└── tests/
    └── README.md
```

### ✅ 8. Git Repository Initialised

### ✅ 9. Documentation Written
- PROJECT_SPECIFICATION.md — Full project specification
- ARCHITECTURE.md — System architecture with diagrams
- DEVELOPMENT_ROADMAP.md — 10-month plan
- Research documentation (problem statement, objectives, questions, contributions)

## Problems Encountered and Resolved

| Problem | Root Cause | Resolution |
|---------|------------|------------|
| Docker Hub TLS error | University network blocks Docker Hub certificate verification | Used nginx:latest image already cached in containerd |
| Image not on workers | `imagePullPolicy: Never` with image only on master | Identified nginx:latest was cached on worker nodes from existing deployments |
| Pods stuck on workers | Calico CNI authorization error — calico-node pods had stale auth tokens | Restarted calico-node DaemonSet pods on all workers |
| Git identity missing | No git user configured on cluster | Configured local git identity |

## Infrastructure Notes

> [!WARNING]
> - Docker Hub is unreachable from the cluster (TLS certificate error)
> - All future images must be built using cached base images or the local registry (localhost:32000)
> - RBAC is disabled — should be enabled before production use
> - Master node has no taint — pods can schedule on it

## Deployment Status

| Resource | Namespace | Replicas | Status |
|----------|-----------|----------|--------|
| Deployment/document-retrieval | crosslayer-workloads | 3/3 | ✅ Running |
| Service/document-retrieval | crosslayer-workloads | ClusterIP | ✅ Active |
| Service/document-retrieval-nodeport | crosslayer-workloads | NodePort:30080 | ✅ Active |

**Pod Distribution**:
| Pod | Node | IP |
|-----|------|----|
| document-retrieval-...-z5jv5 | k8s-master-1 | 10.1.196.50 |
| document-retrieval-...-v9q5n | k8s-worker-2 | 10.1.140.10 |
| document-retrieval-...-fgtnj | k8s-worker-3 | 10.1.69.218 |

## Access Information

| Service | URL |
|---------|-----|
| Document Retrieval (NodePort) | http://10.2.0.145:30080 |
| Grafana | ClusterIP 10.152.183.42:80 (admin / prom-operator) |
| Prometheus | ClusterIP 10.152.183.218:9090 |

---

## Day 2 Plan

### Goal: Monitoring Infrastructure & Baseline Measurements

1. **Verify Prometheus is scraping our service**
   - Check if prometheus.io annotations are being picked up
   - Verify crosslayer metrics appear in Prometheus

2. **Access Grafana Dashboard**
   - Expose Grafana via NodePort for browser access
   - Create a CrossLayer cluster overview dashboard

3. **Deploy Document Verification Service**
   - Second microservice that communicates with document-retrieval
   - Establishes inter-service communication for dependency analysis

4. **Baseline Performance Measurements**
   - Measure response time from each node
   - Measure inter-node latency (ping between all node pairs)
   - Record CPU/memory baseline under load

5. **Load Generator**
   - Create a simple load generator to stress the document-retrieval service
   - Measure P50/P95/P99 response times under load

---

*Day 1 completed at 22:51 IST on 9 November 2026*
