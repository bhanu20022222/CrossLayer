# Evaluation Metrics

## Experiment Design

### Approaches to Compare
| Approach | Description |
|----------|-------------|
| Baseline 1 | Default Kubernetes scheduling |
| Baseline 2 | Resource-aware rule-based placement |
| Proposed | CrossLayer network-aware placement |

### Experiment Scenarios
| ID | Scenario | Conditions |
|----|----------|------------|
| E1 | Normal | Normal network conditions |
| E2 | High latency | Elevated inter-node latency |
| E3 | Packet loss | Packet loss on specific links |
| E4 | Limited bandwidth | Bandwidth constraints |
| E5 | High CPU | High CPU utilisation on target nodes |
| E6 | High memory | High memory pressure |
| E7 | High communication | High inter-service request rate |
| E8 | Combined stress | Network + compute congestion |
| E9 | Dynamic workload | Changing workload patterns |
| E10 | Migration stability | Migration cost and oscillation evaluation |

## Primary Metrics

### Application Performance
| Metric | Unit | Direction |
|--------|------|-----------|
| Average response time | ms | Lower is better |
| P95 response time | ms | Lower is better |
| P99 response time | ms | Lower is better |
| Throughput | requests/sec | Higher is better |
| Error rate | % | Lower is better |

### Network Performance
| Metric | Unit | Direction |
|--------|------|-----------|
| Inter-node latency | ms | Lower is better |
| Packet loss | % | Lower is better |
| Network throughput | Mbps | Higher is better |
| Jitter | ms | Lower is better |

### Resource Utilisation
| Metric | Unit |
|--------|------|
| CPU utilisation | % |
| Memory utilisation | % |

### Migration Quality
| Metric | Unit | Direction |
|--------|------|-----------|
| Migration duration | seconds | Lower is better |
| Downtime | seconds | Lower is better |
| Migration frequency | count | Lower is better |
| Decision stability | % | Higher is better |

## Performance Improvement Calculation

For lower-is-better metrics:
```
Improvement(%) = (Baseline - Proposed) / Baseline × 100
```

For throughput (higher-is-better):
```
Improvement(%) = (Proposed - Baseline) / Baseline × 100
```

Report absolute measurements, variability, confidence intervals, and statistical significance.
