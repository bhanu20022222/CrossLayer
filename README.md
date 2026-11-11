# CrossLayer

**A Cross-Layer Digital Twin Framework for Network-Aware Workload Migration in Kubernetes Across Cloud and Edge Environments**

> Cloud-Native Workload Orchestration at the Edge: A Deployment Review and Future Directions

## Overview

CrossLayer is a research prototype that improves Kubernetes workload placement by jointly considering application dependencies, network performance, compute resources, and migration costs. Unlike conventional Kubernetes scheduling that primarily considers resource requests and node availability, CrossLayer collects and analyses metrics from multiple system layers to make intelligent migration decisions.

## Research Question

> Can a cross-layer decision framework that jointly considers application dependencies, network performance, compute resources, and migration costs improve workload placement compared with conventional Kubernetes scheduling?

## Architecture

```
           APPLICATION WORKLOADS
                    |
           Service Communication
                    |
        Application & Network Metrics
                    |
        +---------------------------+
        |       PROMETHEUS          |
        | CPU / RAM / Latency       |
        | Throughput / Packet Loss  |
        +---------------------------+
                    |
           CROSS-LAYER ENGINE
                    |
        +---------------------------+
        |  Feature Extraction       |
        |  Node Scoring             |
        |  Dependency Analysis      |
        |  Migration Cost           |
        +---------------------------+
                    |
            PYTHON ML MODEL
                    |
            GO CONTROLLER
                    |
             Kubernetes API
                    |
        Migration / Rescheduling
                    |
      +-------------+-------------+
      |             |             |
    Worker 1      Worker 2      Worker 3
```

## Infrastructure

| Node | Role | IP | CPU | RAM |
|------|------|----|-----|-----|
| k8s-master-1 | Control Plane | 10.2.0.145 | 24 cores | ~64 GB |
| k8s-worker-1 | Worker | 10.2.0.131 | 24 cores | ~64 GB |
| k8s-worker-2 | Worker | 10.2.0.132 | 24 cores | ~64 GB |
| k8s-worker-3 | Worker | 10.2.0.133 | 24 cores | ~64 GB |

- **Kubernetes**: MicroK8s v1.33.13
- **OS**: Ubuntu 24.04.3 LTS
- **CNI**: Calico
- **Monitoring**: Prometheus + Grafana + Loki + Tempo (kube-prom-stack)
- **Container Registry**: localhost:32000

## Technology Stack

| Technology | Purpose |
|-----------|---------|
| Kubernetes / MicroK8s | Container orchestration |
| Go | Kubernetes controller and decision engine |
| Python | ML models, workload services, data processing |
| Prometheus + Grafana | Metrics collection and visualisation |
| Calico | CNI networking |
| Envoy | Service communication telemetry |
| Mininet | Controlled network experiments |

## Project Structure

```
CrossLayer/
├── docs/                    # Research documentation
├── deployments/             # Kubernetes manifests
├── workloads/               # Microservice applications
├── controller/              # Go Kubernetes controller (Month 5)
├── crosslayer-engine/       # Decision engine (Month 4)
├── ml-engine/               # Python ML engine (Month 6)
├── digital-twin/            # Digital twin (Month 8)
├── metrics-collector/       # Metric collection (Month 3)
├── experiments/             # Experiment configs and results
├── dashboards/              # Grafana dashboards (optional JSON)
├── dashboard/               # CrossLayer research UI (React + FastAPI)
├── scripts/                 # Utility scripts
└── tests/                   # Test suites
```

## Development Roadmap

| Month | Milestone |
|-------|-----------|
| 1 | Kubernetes foundation, monitoring, baseline workloads |
| 2 | Network measurement and application dependency discovery |
| 3 | Cross-layer metric collection and feature engineering |
| 4 | Rule-based intelligent node selection |
| 5 | Go-based Kubernetes controller |
| 6 | Python ML-based migration prediction |
| 7 | Network-aware migration implementation |
| 8 | Digital twin and controlled network experiments |
| 9 | Performance evaluation and research comparisons |
| 10 | Paper writing, thesis, results and final demonstration |

## Getting Started

### Prerequisites
- MicroK8s cluster with 4 nodes
- Prometheus + Grafana (observability addon)
- Container registry (localhost:32000)

### Deploy the Document Retrieval Service
```bash
# Create namespaces
microk8s kubectl apply -f deployments/namespaces/crosslayer-namespaces.yaml

# Build and push the image (on master node)
cd workloads/document-retrieval
docker build -t localhost:32000/crosslayer/document-retrieval:v0.1.0 .
docker push localhost:32000/crosslayer/document-retrieval:v0.1.0

# Deploy
microk8s kubectl apply -f deployments/workloads/document-retrieval-deployment.yaml
microk8s kubectl apply -f deployments/workloads/document-retrieval-service.yaml
```

## Degree
Integrated M.Tech – AI/ML

## License
Research project — not for commercial distribution.

## Status
🟢 Day 1 — Foundation established
