# CrossLayer — Project Specification

## 1. Project Identity

- **Title**: CrossLayer: A Cross-Layer Digital Twin Framework for Network-Aware Workload Migration in Kubernetes Across Cloud and Edge Environments
- **Subtitle**: Cloud-Native Workload Orchestration at the Edge: A Deployment Review and Future Directions
- **Degree**: Integrated M.Tech – AI/ML
- **Duration**: 10 months
- **Start Date**: November 2026

## 2. Problem Statement

Traditional Kubernetes scheduling primarily considers resource requests, node availability, affinity, taints, and scheduling constraints. It does not inherently optimise workload placement using a unified understanding of:

- Application response time
- Service communication dependencies
- Network latency
- Bandwidth utilisation
- Packet loss
- CPU and memory utilisation
- Storage locality
- Security constraints
- Workload migration costs

**Scenario**: Pod A runs on Worker Node 1. Pod B, which communicates frequently with Pod A, runs on Worker Node 3. Network latency between the two nodes increases. Worker Node 2 has sufficient CPU and memory and offers a better network path. Kubernetes does not automatically make a migration decision based on the complete communication relationship and network conditions.

## 3. Proposed Solution

CrossLayer collects information from multiple layers:

| Layer | Information Collected |
|-------|----------------------|
| Application | Response time, service dependencies, request rate |
| Network | Latency, bandwidth, packet loss, throughput, jitter |
| Compute | CPU, memory, node availability |
| Storage | Volume requirements, storage locality |
| Security | Network policies, placement constraints |
| Migration | Migration cost, downtime, rescheduling overhead |

The framework uses these parameters to determine whether a workload should remain on its current node or move to another suitable node.

## 4. Research Objectives

1. Design a cross-layer monitoring architecture for Kubernetes environments
2. Collect application, network, compute, storage, and security-related information
3. Discover and represent inter-service communication dependencies
4. Develop a unified cross-layer feature extraction mechanism
5. Develop a multi-criteria workload placement algorithm
6. Implement an automated decision controller using Go
7. Integrate an ML-based decision enhancement using Python
8. Develop a digital twin for modelling cluster topology and workload behaviour
9. Implement controlled workload rescheduling
10. Experimentally evaluate the framework under different network and workload conditions

## 5. Research Questions

| ID | Research Question |
|----|------------------|
| RQ1 | How does network latency affect Kubernetes application performance? |
| RQ2 | Can application dependency information improve workload placement? |
| RQ3 | Does cross-layer placement outperform resource-only placement? |
| RQ4 | How much improvement can be obtained by incorporating migration costs? |
| RQ5 | Can an ML-enhanced decision engine improve placement decisions? |
| RQ6 | How accurately can a digital twin represent the behaviour of the physical cluster? |

## 6. Proposed Contributions

1. **Cross-layer metric integration** — A unified framework for collecting and combining application, network, compute, storage, and migration information
2. **Application dependency awareness** — A service dependency graph representing communication relationships and intensity
3. **Network-aware placement algorithm** — A multi-criteria placement algorithm using network and compute conditions
4. **Migration-cost-aware decision-making** — A mechanism that avoids unnecessary migration and considers migration overhead
5. **Digital twin-assisted experimentation** — A cluster representation enabling repeatable experiments
6. **ML-enhanced placement** — An ML-based model predicting node suitability, compared with a rule-based baseline

## 7. Infrastructure

| Node | Role | IP | CPU | RAM | OS |
|------|------|----|-----|-----|----|
| k8s-master-1 | Control Plane | 10.2.0.145 | 24 cores | ~64 GB | Ubuntu 24.04.3 LTS |
| k8s-worker-1 | Worker | 10.2.0.131 | 24 cores | ~64 GB | Ubuntu 24.04.3 LTS |
| k8s-worker-2 | Worker | 10.2.0.132 | 24 cores | ~64 GB | Ubuntu 24.04.3 LTS |
| k8s-worker-3 | Worker | 10.2.0.133 | 24 cores | ~64 GB | Ubuntu 24.04.3 LTS |

- **Kubernetes**: MicroK8s v1.33.13
- **Container Runtime**: containerd 1.7.29
- **CNI**: Calico
- **Monitoring**: kube-prom-stack (Prometheus, Grafana, Loki, Tempo)
- **Metrics Server**: Enabled
- **Registry**: localhost:32000
- **Storage**: microk8s-hostpath

## 8. Evaluation Plan

Compare three approaches under identical conditions:

| Approach | Description |
|----------|-------------|
| Baseline 1 | Default Kubernetes scheduling |
| Baseline 2 | Resource-aware rule-based placement |
| Proposed | CrossLayer network-aware placement |

**Metrics**: Average response time, P95/P99 latency, throughput, packet loss, inter-node latency, CPU/memory utilisation, migration duration, downtime, migration frequency, decision stability.

## 9. Critical Constraints

- Kubernetes does not natively support live migration of running container processes
- Initial implementation uses controlled rescheduling for stateless workloads
- Stateful migration is a separate research challenge
- Never delete existing cluster resources without approval
- Never change the CNI plugin
- Never restart MicroK8s without approval
- Never expose Kubernetes credentials or secrets
- Never generate fake experimental results
