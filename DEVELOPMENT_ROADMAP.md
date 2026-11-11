# CrossLayer — Development Roadmap

## 10-Month Development Plan

### Month 1: Infrastructure Foundation (Current)
**Goal**: Working Kubernetes workload and monitoring baseline

- [x] Cluster inspection and verification
- [x] Project repository setup
- [x] Documentation foundation
- [ ] Sample application deployment (document-retrieval)
- [ ] Prometheus connectivity verification
- [ ] Grafana dashboard access
- [ ] Baseline workload performance measurement
- [ ] Day 1 report

#### Week 1 (Days 1-7)
- Cluster inspection and project setup
- Document-retrieval microservice creation
- Namespace creation and deployment

#### Week 2 (Days 8-14)
- Document-verification microservice
- Inter-service communication setup
- Load generator development

#### Week 3 (Days 15-21)
- Prometheus integration and custom metrics
- Grafana dashboard for cluster overview
- Metrics verification

#### Week 4 (Days 22-30)
- Baseline workload performance measurements
- Response time, throughput, resource utilisation
- Month 1 report

### Month 2: Network Observability
- Network topology discovery
- Inter-node latency measurement (ping, TCP probes)
- Pod-to-pod communication measurement
- Throughput and packet loss experiments
- Network metrics exporter
- Network monitoring Grafana dashboard

### Month 3: Application Dependency Discovery
- Service dependency discovery from telemetry
- Communication graph implementation (NetworkX)
- Application telemetry integration
- Cross-layer data schema design
- Metrics collection pipeline

### Month 4: Cross-Layer Engine
- Feature normalisation and alignment
- Node eligibility filtering
- Weighted scoring algorithm implementation
- Migration cost model
- Decision engine unit tests

### Month 5: Go Kubernetes Controller
- Go controller scaffolding (controller-runtime)
- Kubernetes API integration
- Controller reconciliation loop
- Custom Resource Definition (CrossLayerPolicy)
- Observe and dry-run modes

### Month 6: ML Integration
- Synthetic dataset generation
- Feature engineering pipeline
- Model training (Linear Regression, Random Forest, XGBoost)
- ML prediction API (FastAPI)
- Rule-based vs ML comparison

### Month 7: Controlled Migration
- Controlled workload rescheduling mechanism
- Readiness verification
- Migration event tracking
- Migration stability enforcement
- Failure handling and rollback

### Month 8: Digital Twin
- Digital twin topology model
- Workload simulation
- Network emulation (Mininet)
- Predicted vs actual performance validation

### Month 9: Research Evaluation
- 10 experimental scenarios
- Baseline comparison (default K8s vs resource-aware vs CrossLayer)
- Performance evaluation with statistical analysis
- Research graphs, tables, and figures

### Month 10: Final Research
- Thesis preparation
- Literature review completion
- Research paper draft
- System documentation
- Final demonstration and presentation
