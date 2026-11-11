from fastapi import APIRouter

from app.clients.kubernetes import kubernetes_client
from app.clients.prometheus import prometheus_client
from app.config import settings
from app.envelope import envelope

router = APIRouter()


@router.get("/health")
async def health():
    prom_ok, prom_err = await prometheus_client.check()
    kube_ok, kube_err = kubernetes_client.check()
    overall = "ok" if prom_ok or kube_ok else "degraded"
    return envelope(
        source="derived",
        value_kind="derived",
        data={
            "status": overall,
            "prometheus": {
                "ok": prom_ok,
                "url": settings.prometheus_url,
                "error": prom_err,
            },
            "kubernetes": {
                "ok": kube_ok,
                "error": kube_err,
            },
        },
    )
