# Research Questions

## Primary Research Question

> Can a cross-layer decision framework that jointly considers application dependencies, network performance, compute resources, and migration costs improve workload placement compared with conventional Kubernetes scheduling?

## Specific Research Questions

### RQ1: Network Impact on Application Performance
**How does network latency affect Kubernetes application performance?**

We will measure application response time under varying inter-node latency conditions to establish the relationship between network quality and application performance.

### RQ2: Dependency-Aware Placement
**Can application dependency information improve workload placement?**

We will compare placement decisions made with and without service communication graph information to determine if dependency awareness leads to better placements.

### RQ3: Cross-Layer vs Resource-Only Placement
**Does cross-layer placement outperform resource-only placement?**

We will compare our multi-layer approach against a baseline that only considers CPU and memory availability.

### RQ4: Migration Cost Integration
**How much improvement can be obtained by incorporating migration costs into placement decisions?**

We will evaluate whether including migration overhead, expected benefit, and stability constraints produces better outcomes than naive migration.

### RQ5: ML Enhancement
**Can an ML-enhanced decision engine improve placement decisions compared with rule-based scoring?**

We will compare placement accuracy and performance between the rule-based weighted scoring model and trained ML models.

### RQ6: Digital Twin Accuracy
**How accurately can a digital twin represent the behaviour of the physical cluster?**

We will compare digital twin predictions against actual cluster measurements to validate the simulation model.
