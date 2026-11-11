# Research Objectives

## Primary Objective

Design, implement, and evaluate a cross-layer decision framework that improves Kubernetes workload placement by considering application, network, compute, storage, security, and migration-cost information.

## Specific Objectives

### O1: Cross-Layer Monitoring Architecture
Design and implement a monitoring architecture that collects metrics from multiple system layers (application, network, compute, storage) in a Kubernetes environment.

### O2: Application Dependency Discovery
Discover and represent inter-service communication dependencies as a weighted directed graph, capturing communication frequency, latency, traffic volume, and criticality.

### O3: Cross-Layer Feature Extraction
Develop a unified feature extraction mechanism that normalises and combines metrics from all layers into decision-ready feature vectors.

### O4: Multi-Criteria Placement Algorithm
Develop a placement algorithm that evaluates candidate nodes using a weighted scoring model considering CPU, memory, network suitability, application performance, dependency locality, and migration risk.

### O5: Kubernetes Controller
Implement an automated decision controller in Go that integrates with the Kubernetes API, watches workloads, consumes cross-layer metrics, and coordinates controlled rescheduling.

### O6: ML-Enhanced Decision Engine
Develop and evaluate machine learning models (Linear Regression, Random Forest, XGBoost) that predict node suitability and migration benefit.

### O7: Digital Twin
Develop a digital twin that represents the physical cluster topology, workload behaviour, and network conditions for simulation and prediction validation.

### O8: Experimental Evaluation
Experimentally evaluate the framework under 10 different network and workload scenarios, comparing CrossLayer placement with default Kubernetes scheduling and resource-aware placement.
