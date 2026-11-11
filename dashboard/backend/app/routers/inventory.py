from fastapi import APIRouter, Query

from app.clients.kubernetes import KubernetesError, kubernetes_client
from app.config import settings
from app.envelope import envelope, unavailable

router = APIRouter()


@router.get("/nodes")
def nodes():
    try:
        data = kubernetes_client.list_nodes()
    except KubernetesError as exc:
        return unavailable("kubernetes", str(exc), data=[])
    return envelope(source="kubernetes", value_kind="measured", data=data)


@router.get("/pods")
def pods(namespace: str | None = Query(default=None)):
    ns = namespace or settings.workload_namespace
    try:
        data = kubernetes_client.list_pods(namespace=ns)
    except KubernetesError as exc:
        return unavailable("kubernetes", str(exc), data=[])
    return envelope(
        source="kubernetes",
        value_kind="measured",
        data={"namespace": ns, "pods": data},
    )
