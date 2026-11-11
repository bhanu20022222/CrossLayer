# CrossLayer Controller

## Status: Month 5 Milestone

The Go-based Kubernetes controller will be implemented in Month 5 of the development roadmap.

## Planned Architecture

```
Kubernetes API
      │
      ▼
CrossLayer Controller
      │
      ├── Cluster Observer
      ├── Metric Client
      ├── Decision Client
      ├── Policy Validator
      ├── Migration Coordinator
      └── Audit Logger
```

## Planned Features
- Kubernetes API integration using controller-runtime or client-go
- Watch workloads and cluster events
- Consume cross-layer metrics from Prometheus
- Request placement recommendations from the decision engine
- Validate candidate nodes
- Execute controlled rescheduling
- Record migration decisions and outcomes

## Operating Modes
1. **Observe** — Collect metrics and monitor workloads
2. **Recommend** — Generate placement recommendations
3. **Dry-run** — Evaluate and validate proposed actions
4. **Controlled** — Execute approved rescheduling
5. **Autonomous** — Execute policies automatically (after extensive validation)
