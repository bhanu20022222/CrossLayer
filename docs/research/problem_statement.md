# Research Problem Statement

## Context

Kubernetes has become the standard platform for container orchestration in cloud and edge computing environments. Its built-in scheduler allocates workloads to nodes based on resource requests, node availability, affinity rules, taints, tolerations, and other scheduling constraints.

However, once a workload is placed on a node, Kubernetes does not automatically re-evaluate and relocate the workload based on changing runtime conditions—particularly network performance between communicating services.

## The Problem

In distributed microservice architectures, application performance depends not only on the computing resources available on a node but also on the network paths connecting communicating services.

Consider this scenario:
- **Pod A** (document-retrieval) runs on **Worker Node 1**
- **Pod B** (document-verification), which communicates frequently with Pod A, runs on **Worker Node 3**
- Network latency between Worker 1 and Worker 3 increases due to congestion
- **Worker Node 2** has sufficient CPU and memory and a better network path to Worker 3

**Kubernetes does not automatically make a migration decision** based on:
- The communication relationship between Pod A and Pod B
- The degraded network conditions
- The availability of a better placement option

## Gap in Current Approaches

Traditional Kubernetes scheduling does not provide a unified, application-aware and network-aware optimisation mechanism that considers:

1. Service dependencies and communication patterns
2. End-to-end application response time
3. Network latency, bandwidth, and packet loss
4. Compute resource availability
5. Storage characteristics
6. Security constraints
7. Workload migration overhead and disruption cost

A workload placed on a computationally powerful node may still experience poor performance if its communication path to dependent services is congested or has high latency.

## Our Approach

We propose **CrossLayer**, a cross-layer digital twin framework that integrates information from the application, network, compute, storage, security, and migration layers to make intelligent Kubernetes workload placement and rescheduling decisions.

The framework will be designed, implemented, and experimentally evaluated against conventional Kubernetes scheduling and resource-aware placement approaches.
