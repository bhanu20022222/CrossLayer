# CrossLayer Dashboard

Research control plane UI for the CrossLayer prototype. This is **not** a Grafana replacement for kube-prom-stack: Grafana stays for operator debugging. This app is the M.Tech interface: cluster state, telemetry, dependency graph, and (later) KEEP/MIGRATE.

**Rules:** every number comes from Prometheus or the Kubernetes API, or the panel is marked `unavailable`. Predicted/simulated series are labelled when those engines exist. No placeholder scores.

## Directory structure

```
dashboard/
├── README.md
├── backend/                 # Python FastAPI
│   ├── requirements.txt
│   ├── tests/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── envelope.py      # measured | derived | predicted | simulated | unavailable
│       ├── queries.py       # PromQL (no invented results)
│       ├── clients/
│       │   ├── prometheus.py
│       │   └── kubernetes.py
│       └── routers/         # one router per dashboard module
└── frontend/                # React + TypeScript + Vite
    ├── src/
    │   ├── api/
    │   ├── components/
    │   ├── layout/
    │   └── pages/           # 11 research modules
    └── package.json
../network-prober/           # Separate, opt-in node-to-node measurement exporter
```

The existing application Pods are not replaced by the Envoy telemetry overlay. The separate `network-prober/` exporter measures node-to-node ICMP health independently of Envoy HTTP metrics. The experiment microservices run only in `crosslayer-experiments`.

## Data sources

| Source | Default (local laptop) | Cluster (on master) |
|--------|------------------------|---------------------|
| Prometheus | `http://127.0.0.1:9091` after SSH tunnel | in-cluster Service URL |
| Kubernetes | kubeconfig if present | in-cluster or `microk8s kubectl` kubeconfig |

Laptop tunnel (Windows PowerShell + Linux master), same method as the project spec:

```bash
# Linux master
microk8s kubectl port-forward -n observability svc/kube-prom-stack-kube-prome-prometheus 9091:9090
```

```powershell
# Windows
ssh -L 9091:127.0.0.1:9091 kadmin@10.2.0.145
```

For live node and Pod inventory from Windows, keep a loopback-only Kubernetes
proxy running:

```powershell
kubectl --kubeconfig "$HOME\.kube\microk8s-config" proxy --address=127.0.0.1 --port=8003
```

Set `CROSSLAYER_KUBECONFIG` to a local kubeconfig whose server is
`http://127.0.0.1:8003` (for example, `C:\Users\HP\.kube\crosslayer-proxy-config`).
If kubeconfig or the proxy is unavailable, node/pod modules show `unavailable` — they
do **not** fall back to the four IPs from the thesis notes.

## API (`/api/v1`)

All JSON bodies use:

```json
{
  "source": "prometheus | kubernetes | derived | none",
  "value_kind": "measured | derived | predicted | simulated | unavailable",
  "as_of": "ISO-8601",
  "error": null,
  "data": {}
}
```

| Method | Path | Backing store | Module |
|--------|------|---------------|--------|
| GET | `/health` | both | connectivity, never metrics |
| GET | `/auth/session` | local session cookie | login state (public bootstrap) |
| POST | `/auth/login` | configured credentials | creates HTTP-only dashboard session |
| POST | `/auth/logout` | local session cookie | clears dashboard session |
| GET | `/cluster/overview` | Kubernetes + Prometheus `up` | 1 |
| GET | `/nodes` | Kubernetes Node objects | 2 |
| GET | `/pods` | Kubernetes Pods | 3 |
| GET | `/metrics/cpu?range=15m` | Prometheus | 4 |
| GET | `/metrics/memory?range=15m` | Prometheus | 4 |
| GET | `/metrics/network?range=15m` | Prometheus node-exporter + cAdvisor + optional network probe | 5 |
| GET | `/metrics/envoy?range=15m` | Prometheus Envoy proxy stats | 5 |
| GET | `/experiments/metrics?range=15m` | Prometheus experiment-service metrics | 11 |
| GET | `/experiments/load/status` | local bounded load-run controller | 11 |
| POST | `/experiments/load/start` | starts a capped run against the experiment API | 11 |
| POST | `/experiments/load/stop` | stops the active run | 11 |
| GET | `/application/traffic?range=15m` | Prometheus `crosslayer_*` | 6 |
| GET | `/graph/dependencies` | Prometheus downstream series | 7 |
| GET | `/affinity/network` | Kubernetes endpoints + Prometheus probes and service metrics | Network Affinity |
| GET | `/twin/state` | stub until twin exists | 8 |
| GET | `/decisions` | stub until engine exists | 9 |
| GET | `/migrations` | stub until controller exists | 10 |
| GET | `/experiments` | dashboard page for bounded experiment control and results | 11 |

Stubs return `value_kind: unavailable` and empty `data`, not demo KEEP/MIGRATE rows.

## Dashboard login

The dashboard API protects all `/api/v1` data and experiment-control routes with a
signed, time-limited, HTTP-only session cookie. Login credentials and a signing secret
must be supplied by the operator at backend startup; there are no default accounts.
If authentication is not configured, protected API routes fail closed and the UI shows
the setup instructions instead of exposing cluster data.

In the same PowerShell window used to run Uvicorn, configure a private account and a
random session-signing secret:

```powershell
$env:CROSSLAYER_AUTH_USERNAME = Read-Host "Dashboard username"
$securePassword = Read-Host "Dashboard password" -AsSecureString
$env:CROSSLAYER_AUTH_PASSWORD = [Net.NetworkCredential]::new("", $securePassword).Password
$secretBytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($secretBytes)
$env:CROSSLAYER_AUTH_SECRET = [Convert]::ToBase64String($secretBytes)
```

Keep the credentials in the process environment; do not commit them or put them in
source files. The default cookie setting supports loopback HTTP development only.
For access from other machines, terminate HTTPS at a trusted reverse proxy and set
`CROSSLAYER_AUTH_COOKIE_SECURE=true`; do not expose the development server directly to
an untrusted network. Sessions expire after eight hours by default.

The network endpoint retains Pod receive/transmit rates and adds physical-node-interface
receive/transmit rates, packet rates, errors, drops, link state/speed, and directional
throughput in Mbps, utilization, and TCP retransmission rates. Physical interfaces are
selected by common Ethernet interface names and must be up for rate charts; loopback,
Calico, and other virtual interfaces are excluded. Utilization is unavailable when the
link is down or Prometheus has no positive speed measurement.

Inter-node RTT p50/p95/p99, rolling packet loss, and RFC 3550 jitter use the `network-prober/`
DaemonSet. It discovers Kubernetes Node InternalIPs with read-only RBAC, sends one ICMP probe
to each peer about every 10 seconds, and exports Prometheus text-format metrics. It runs as
UID 0 with only `NET_RAW` added because the cluster runtime dropped that capability for a
non-root process; it is not privileged and retains the default seccomp profile. The exporter does not invent RTT samples when a probe fails. Chart series include
the exporting Pod in their names so measurements from replaced DaemonSet Pods remain
distinguishable from current probes.

## Network Affinity Generator (NAG-v1)

The **Network Affinity** page and `GET /api/v1/affinity/network` provide an explainable,
derived placement comparison. Directed link scores use measured five-minute RTT p95, packet
loss, jitter, and the maximum observed receive/transmit utilization at either node. The
current starting weights are 0.25, 0.10, 0.10, and 0.15 respectively. RTT and jitter are
normalized as `exp(-value / scale)` (10 ms and 5 ms); loss and congestion are normalized as
`1 - percent / 100`. Available feature weights are renormalized for the score, while coverage
reports what share of the 0.80 network-feature weight was actually measured. The remaining
0.20 bandwidth weight is unavailable because available-bandwidth telemetry is not collected;
it is never guessed or treated as zero.

Workload placement scores are the measured request-rate-weighted mean of directed link
affinities to communicating Service endpoints. Outgoing requests are distributed across
destination replicas using observed per-Pod request rates, or equally if those rates are
unavailable; this equal-share fallback is an explicit modeling approximation. Incoming calls
retain their observed source node and direction. Same-node peers receive a topology-only score
of 100, but contribute zero measured-feature coverage because no inter-node probe measures
that path. Thus the score is not presented as measured link quality, and the coverage gate
prevents that assumption alone from producing advice.

Only Ready, schedulable nodes are placement candidates; the existing node remains in the
comparison. An alternative is surfaced only when the current and alternative placements have
at least 80% traffic coverage, 50% measured link-feature coverage, and a five-point score
improvement. These are uncalibrated research thresholds. Current metrics identify
same-namespace downstream services; cross-namespace caller attribution is not available in
the current metric schema.

All recommendations are **advisory and network-only**. The scorer does not validate CPU or
memory fit, taints/tolerations, storage, security or data locality, migration cost, or
application SLOs; it never schedules, migrates, or writes to Kubernetes. Graph clustering,
adaptive weights, prediction/ML, TOPSIS, and automated placement remain future experiments,
not capabilities claimed by this baseline.

## Cluster experiment traffic

`deployments/experiments/microservices.yaml` adds three resource-limited Python services in
`crosslayer-experiments`: `experiment-api` calls `experiment-worker`, which calls
`experiment-store`. They export measured request counters, latency histograms, and dependency
call metrics for Prometheus. The API remains a ClusterIP service, not a NodePort. It does not
route to or generate traffic for the existing CrossLayer, ETL,
or migration workloads.

Run `.\deployments\experiments\deploy-experiment.ps1` from the workspace root to create the
source ConfigMaps and deploy the experiment services and inter-node probe. The script validates
the manifests and waits for readiness; it does not start load traffic. It uses the existing
Python 3.7 runtime image pinned by digest in the manifests, so it does not require Docker on
the Windows workstation.

For the local load controller, start a loopback-only port-forward in a separate PowerShell
terminal and leave it running:

```powershell
kubectl --kubeconfig "$HOME\.kube\microk8s-config" -n crosslayer-experiments port-forward --address 127.0.0.1 service/experiment-api 8082:8080
```

The Experimental Evaluation page requires an explicit Start click and a successful service
health check. The backend enforces a hard maximum of 30 requests/second, 300 seconds per run,
and 8 concurrent requests. Runs stop automatically at the selected duration and can be stopped
earlier. The request generator targets only `experiment-api` through `127.0.0.1:8082`. These
are real measurements from the cluster, not Mininet-emulated results. No load is generated by
opening the dashboard.

## Envoy HTTP telemetry

`deployments/envoy/telemetry-infrastructure.yaml` adds two Envoy reverse-proxy Deployments,
private upstream Services, metrics Services, and a ServiceMonitor for the current
`document-retrieval` and `document-verification` Services. Apply this file first, wait for
both Envoy Deployments to become Ready, confirm their Prometheus targets are up, and only
then apply `deployments/envoy/route-services.yaml` to route the existing Service and
NodePort traffic through Envoy. The original Nginx workload Pods remain unchanged.

The Network Monitoring page displays request rate, downstream response latency p50/p95/p99,
4xx/5xx rates, active connections, request/response bytes, proxy-to-workload request rate
and p95, upstream connections, and upstream connection failures. Empty latency/error series
are not treated as zero. Only HTTP requests that traverse the existing Services are measured.
The live Pods are currently Nginx placeholders and do not call each other, so Envoy alone
cannot produce a retrieval-to-verification dependency edge; real downstream calls and caller
identity require application traffic/metadata.

The overlay uses a pinned upstream Envoy image and does not install a service mesh, modify
the CNI, or add privileges to workload Pods. To roll back routing, restore the original
Service selectors (`app: document-retrieval` / `app: document-verification`) and restore
`document-verification`'s target port to `8081` before removing the Envoy resources. No
synthetic requests are generated by the dashboard or deployment.

## Run locally

Backend (port 8006; avoids the Windows-reserved local port encountered in this setup):

```powershell
cd dashboard\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:CROSSLAYER_PROMETHEUS_URL="http://127.0.0.1:9091"
$env:CROSSLAYER_KUBECONFIG="$HOME\.kube\crosslayer-proxy-config"
$env:CROSSLAYER_EXPERIMENT_TARGET_URL="http://127.0.0.1:8082/work"
# Set the login environment variables from the Dashboard login section above.
uvicorn app.main:app --reload --port 8006
```

Frontend (port 5173, proxies `/api` → 8006):

```powershell
cd dashboard\frontend
npm install
npm run dev
```

If the backend uses another local port, set `VITE_API_PROXY_TARGET` before starting Vite;
for example, `http://127.0.0.1:8007`.

Open `http://127.0.0.1:5173` (or `http://127.0.0.1:5174` if port 5173 is occupied).

## Persistent deployment

The production layout serves the React app from Netlify and runs the API inside the
always-on Kubernetes cluster. Netlify proxies `/api/*` to the API over HTTPS, so
browser sessions remain same-origin. A Tailscale Funnel on the cluster master provides
the public HTTPS endpoint without requiring a custom domain. The cluster must remain
powered on and connected to the internet; do not expose Kubernetes' API server.

### Netlify

The repository root `netlify.toml` configures the frontend build and API function.
Connect the private GitHub repository `bhanu20022222/CrossLayer` to Netlify and deploy
the `main` branch. Netlify assigns a `*.netlify.app` address; a `*.netlify.in` address
is not a Netlify-provided subdomain. The API origin is configured after Funnel is
running.

### Build the API image

The GitHub Actions workflow publishes
`ghcr.io/bhanu20022222/crosslayer-dashboard-backend:latest` whenever the backend or
workflow changes. The image is private. On GitHub, create a classic personal access
token with only `read:packages`; never commit it or share it in chat.

On the MicroK8s master, authenticate to GitHub Container Registry and create the image
pull secret:

```bash
read -r -p "GitHub username: " GHCR_USER
read -r -s -p "GitHub token (read:packages): " GHCR_TOKEN
printf '\n'
microk8s kubectl create namespace crosslayer-dashboard
microk8s kubectl -n crosslayer-dashboard create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username="$GHCR_USER" \
  --docker-password="$GHCR_TOKEN"
unset GHCR_USER GHCR_TOKEN
```

Create a new dashboard login and signing secret on the master. Do not reuse the
development password or put these values in Git:

```bash
read -r -p "Dashboard username: " DASHBOARD_USER
read -r -s -p "New strong dashboard password: " DASHBOARD_PASSWORD
printf '\n'
DASHBOARD_SECRET="$(openssl rand -base64 48)"
USER_B64="$(printf %s "$DASHBOARD_USER" | base64 -w0)"
PASSWORD_B64="$(printf %s "$DASHBOARD_PASSWORD" | base64 -w0)"
SECRET_B64="$(printf %s "$DASHBOARD_SECRET" | base64 -w0)"
cat <<EOF | microk8s kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: crosslayer-dashboard-auth
  namespace: crosslayer-dashboard
type: Opaque
data:
  username: ${USER_B64}
  password: ${PASSWORD_B64}
  auth-secret: ${SECRET_B64}
EOF
unset DASHBOARD_USER DASHBOARD_PASSWORD DASHBOARD_SECRET USER_B64 PASSWORD_B64 SECRET_B64
```

Apply the deployment after the GitHub Actions image build has succeeded:

```bash
microk8s kubectl apply -f deployments/dashboard/kubernetes.yaml
microk8s kubectl -n crosslayer-dashboard rollout status deployment/crosslayer-dashboard
```

The API uses a read-only Kubernetes service account, the in-cluster Prometheus service,
and the experiment API service. Its NodePort is for the private cluster network; do not
add a router port-forward for it.

### Publish the API with Tailscale Funnel

On the MicroK8s master, install Tailscale from its official package instructions, then
sign the master into your Tailscale account:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Complete the sign-in flow using the URL printed by the command. In the Tailscale
admin console, enable Funnel for the master if prompted. Then publish only the dashboard
NodePort over HTTPS:

```bash
sudo tailscale funnel --bg --https=443 http://10.2.0.145:30080
sudo tailscale funnel status
```

Copy the `https://…ts.net` URL reported by Funnel. In Netlify, set the site environment
variable `CROSSLAYER_API_ORIGIN` to that HTTPS origin (without a path or trailing
slash), then trigger a new deploy. The Netlify function rejects non-HTTPS origins and
does not forward browser requests to arbitrary hosts.

The Tailscale daemon and Funnel configuration persist on the master across laptop
restarts. Kubernetes restarts the API Pod automatically. The master and cluster still
need to remain online. If the API image is updated, restart its Deployment to pull the
new image:

```bash
microk8s kubectl -n crosslayer-dashboard rollout restart deployment/crosslayer-dashboard
```

## Implementation order

1. Envelope + health + Prometheus/K8s clients (fail closed).
2. Cluster / nodes / pods (Kubernetes).
3. CPU, memory, network charts (Prometheus).
4. Envoy and experiment application traffic + measured dependency graphs.
5. Twin / decisions / history remain unavailable until their respective engines exist.
