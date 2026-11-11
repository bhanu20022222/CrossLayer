from fastapi import APIRouter

from app.clients.kubernetes import KubernetesError, kubernetes_client
from app.clients.prometheus import PrometheusError, prometheus_client
from app.config import settings
from app.envelope import envelope, unavailable
from app.queries import up_targets
from app.timeutil import vector_to_rows

router = APIRouter()


@router.get("/cluster/overview")
async def cluster_overview():
    kube_error = None
    nodes: list = []
    pods: list = []
    try:
        nodes = kubernetes_client.list_nodes()
        pods = kubernetes_client.list_pods()
    except KubernetesError as exc:
        kube_error = str(exc)

    prom_error = None
    up_rows: list = []
    try:
        up_rows = vector_to_rows(await prometheus_client.query(up_targets()), ("job", "instance"))
    except PrometheusError as exc:
        prom_error = str(exc)

    if kube_error and prom_error:
        return unavailable(
            "none",
            f"{kube_error}; {prom_error}",
            data={"nodes": [], "pods": [], "prometheus_up": []},
        )

    workload_pods = [p for p in pods if p.get("namespace") == settings.workload_namespace]
    ready_nodes = [n for n in nodes if n.get("ready")]
    return envelope(
        source="kubernetes" if not kube_error else "prometheus",
        value_kind="measured",
        error="; ".join(e for e in (kube_error, prom_error) if e) or None,
        data={
            "node_count": len(nodes) if not kube_error else None,
            "ready_node_count": len(ready_nodes) if not kube_error else None,
            "pod_count": len(pods) if not kube_error else None,
            "workload_pod_count": len(workload_pods) if not kube_error else None,
            "workload_namespace": settings.workload_namespace,
            "nodes": nodes,
            "workload_pods": workload_pods,
            "prometheus_up": up_rows,
            "partial_errors": {"kubernetes": kube_error, "prometheus": prom_error},
        },
    )
