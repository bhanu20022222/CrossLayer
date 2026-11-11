# Proposed Research Contributions

> **Note**: These are proposed contributions to investigate, not claims of already-proven novelty.

## Contribution 1: Cross-Layer Metric Integration
A unified framework for collecting and combining application, network, compute, storage, and migration information in a Kubernetes environment. Unlike approaches that consider only resource utilisation, our framework provides a holistic view of the factors affecting workload performance.

## Contribution 2: Application Dependency Awareness
A service dependency graph that represents communication relationships, communication intensity, observed latency, and traffic volume. This graph enables placement decisions that consider the actual communication patterns of microservice applications.

## Contribution 3: Network-Aware Placement Algorithm
A multi-criteria placement algorithm that evaluates candidate nodes using network conditions (latency, bandwidth, packet loss) alongside compute resources. The algorithm uses configurable weights and supports sensitivity analysis.

## Contribution 4: Migration-Cost-Aware Decision-Making
A mechanism that avoids unnecessary migration by considering migration overhead, expected performance benefit, disruption cost, and stability constraints. This includes a hysteresis threshold, cooldown periods, and consecutive decision confirmation to prevent migration oscillations.

## Contribution 5: Digital Twin-Assisted Experimentation
A cluster representation that enables repeatable experiments with varying workloads, network conditions, and resource availability. The digital twin can simulate alternative placements and predict expected performance before executing actual rescheduling.

## Contribution 6: ML-Enhanced Placement
An ML-based model that predicts node suitability or expected placement benefit and is compared with a transparent rule-based baseline. We prioritise interpretable models to support research analysis.
