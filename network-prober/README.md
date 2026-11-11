# CrossLayer Network Prober

This standalone Prometheus exporter is intended to collect low-rate IPv4 ICMP
measurements between Kubernetes nodes. It is separate from the dashboard backend.

## Measurements

Each node agent discovers peer node InternalIPs through a read-only Kubernetes
service account and probes each peer once per configured interval (10 seconds in
the cluster manifest). Metrics include:

- `crosslayer_network_rtt_ms`: last successful measured round-trip time
- `crosslayer_network_loss_percent`: loss over the most recent 60 attempts
- `crosslayer_network_jitter_ms`: RFC 3550 smoothed variation between successful RTT samples
- `crosslayer_network_probe_success`: success/failure of the most recent attempt

No sample is emitted for RTT or jitter before a successful probe. A failed probe is
not represented as a zero-millisecond latency. The exporter responds with the
Prometheus text exposition content type.

## Local checks

```powershell
python -m pytest
python -m py_compile src\network_prober\__main__.py
```

The tests do not send ICMP traffic or require cluster credentials.

## Cluster deployment

From the workspace root, run:

```powershell
.\deployments\experiments\deploy-experiment.ps1
```

The deployment script mounts this package's source in a ConfigMap and uses the
existing Python 3.7 runtime image pinned by digest in `kubernetes.yaml`; a local
Docker daemon is not required. The `-v2` DaemonSet has read-only Node RBAC, uses
host networking and only the `NET_RAW` capability for ICMP, and exposes metrics
on port 9116. The container runs as UID 0 because this cluster runtime did not
grant the raw-socket capability to a non-root process; it is not privileged, drops
all other capabilities, disables privilege escalation, and retains the default
seccomp profile. Probe traffic is low-rate and separate from the optional HTTP
load experiment. Unit tests do not send ICMP or HTTP traffic.
