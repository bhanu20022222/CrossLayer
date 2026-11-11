# CrossLayer Microservice Contract

Every research workload (retrieval, verification, load generator, future services) must follow this contract **before** extra features. This is how L7 network/application parameters enter Prometheus without a service mesh.

## 1. Identity

| Field | Rule | Example |
|-------|------|---------|
| Kubernetes `app` label | Equals service name | `document-verification` |
| `project` label | Always `crosslayer` | `crosslayer` |
| `component` label | `workload` | `workload` |
| Env `SERVICE_NAME` | Same as `app` | `document-verification` |
| Env `SERVICE_VERSION` | Semver | `0.1.0` |
| Downward API | `POD_NAME`, `NODE_NAME`, `POD_IP`, `POD_NAMESPACE` | required |

Namespace: `crosslayer-workloads` only.

## 2. Process and ports

| Item | Value |
|------|--------|
| Language (Phase A) | Python Flask + `prometheus-client` + gunicorn |
| Listen | `0.0.0.0` |
| Container port | **8080 HTTP** for all app services (verification uses 8080 in-container; Service can map 80→8080). Do **not** invent 8081 inside the container unless a second process exists. NodePort 30081 can still be used on the Service. |
| Metrics | Same process, path `/metrics`, not a sidecar yet |
| Health | `GET /health` → 200 JSON `{"status":"healthy"}` |
| Ready | `GET /ready` → 200 JSON including `pod`, `node` |
| Placement | `GET /api/placement` → pod, node, ip, hostname |

Why one container port: ServiceMonitor, probes, and dashboards stay uniform.

## 3. Mandatory HTTP routes

```
GET /health
GET /ready
GET /metrics
GET /api/placement
```

Business routes are service-specific (documents, verify, …). They must go through the same metrics decorator as retrieval already does.

## 4. Mandatory Prometheus metrics

Copy the same names and histogram buckets as `workloads/document-retrieval/app.py`.

**Server-side (every service)**

- `crosslayer_request_total{service,method,endpoint,status,node}`
- `crosslayer_request_duration_seconds{service,method,endpoint,node}`
- `crosslayer_active_requests{service,node}`

**Client-side (only services that call another service)**

- `crosslayer_downstream_request_total{service,dst_service,status,node}`
- `crosslayer_downstream_request_duration_seconds{service,dst_service,node}`

Downstream calls **must** use Kubernetes DNS:

```
http://document-verification.crosslayer-workloads.svc.cluster.local/api/verify
```

Never hardcode Pod IPs. Never hardcode node IPs for app traffic.

## 5. Kubernetes object shape

Deployment:

- Replicas: 3 for research workloads unless an experiment says otherwise
- `topologySpreadConstraints` on `kubernetes.io/hostname`, `maxSkew: 1`
- Resource requests/limits set (start: `100m/128Mi` request, `500m/256Mi` limit)
- Liveness: `/health`; readiness: `/ready`
- Image: `localhost:32000/crosslayer/<name>:<version>`
- `imagePullPolicy: IfNotPresent` (campus Docker Hub is unreliable)

Service (ClusterIP) + optional NodePort:

- Labels include `project: crosslayer` and `app: <name>`
- Port **name must be `http`**
- `targetPort: 8080`

Do not rely on `prometheus.io/scrape` annotations alone.

## 6. Dockerfile rules

- Prefer a base image **already present** on the cluster (`python:3.12-slim` only if it is already cached or mirrored to `localhost:32000`).
- Pin pip packages in `requirements.txt`.
- Run gunicorn, not `flask run`, in the container.
- Do not `docker pull` from Docker Hub on the master until TLS is confirmed working.

## 7. Logging

One JSON line per request-ish event is enough:

`time, level, service, pod, node, msg`

Do not log secrets. Do not log full document bodies.

## 8. What this service must **not** do

- Embed the decision engine
- Call `kubectl`
- Talk to the Kubernetes API
- Apply `tc netem`
- Invent latency numbers
- Require Istio labels (`app.kubernetes.io/name` is optional extra; `app` is required)

## 9. First two services (when we implement them)

| Service | Role | Downstream |
|---------|------|------------|
| `document-retrieval` | Read documents; **calls verification** on a configurable fraction of GETs | `document-verification` |
| `document-verification` | CPU-light verify stub; returns `{valid, latency_hint}` | none |

Load generator (later): in-cluster Deployment hitting retrieval, not a laptop `for` loop, so RPS is a cluster metric.

## 10. Definition of done for a new microservice

1. Image in `localhost:32000`.
2. 3/3 pods Ready, spread across nodes.
3. `/health`, `/ready`, `/metrics` work from inside a pod.
4. Prometheus target **UP** for that Service.
5. Grafana panel or Explore query shows `crosslayer_request_total`.
6. If it calls another service: `crosslayer_downstream_*` series exist with real `dst_service`.
