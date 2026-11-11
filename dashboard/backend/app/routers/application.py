from fastapi import APIRouter, Query

from app.clients.prometheus import PrometheusError, prometheus_client
from app.envelope import envelope, unavailable
from app import queries
from app.timeutil import matrix_to_series, parse_range

router = APIRouter()


@router.get("/application/traffic")
async def application_traffic(range: str = Query(default="15m", alias="range")):
    try:
        start, end, step = await prometheus_client.range_window(range)
    except ValueError as exc:
        return unavailable("prometheus", str(exc), data={})
    except PrometheusError as exc:
        return unavailable(
            "prometheus",
            str(exc),
            data={"range": range, "request_rate": [], "latency_p95": []},
        )
    try:
        rate = await prometheus_client.query_range(queries.app_request_rate(), start, end, step)
        latency = await prometheus_client.query_range(queries.app_latency_p95(), start, end, step)
    except PrometheusError as exc:
        return unavailable("prometheus", str(exc), data={"request_rate": [], "latency_p95": []})
    return envelope(
        source="prometheus",
        value_kind="measured",
        data={
            "range": range,
            "note": "Empty series mean crosslayer_* metrics are not scraped yet, not that traffic is zero unless Prometheus returned zeros.",
            "request_rate": matrix_to_series(rate, ("service", "node")),
            "latency_p95": matrix_to_series(latency, ("service", "node")),
        },
    )


@router.get("/graph/dependencies")
async def dependencies():
    try:
        rate = await prometheus_client.query(queries.downstream_rate())
        p95 = await prometheus_client.query(queries.downstream_p95())
    except PrometheusError as exc:
        return unavailable("prometheus", str(exc), data={"nodes": [], "edges": []})

    latency = {}
    for item in p95:
        metric = item.get("metric") or {}
        key = (metric.get("service"), metric.get("dst_service"))
        val = item.get("value")
        if val and val[1] not in (None, "NaN", "+Inf", "-Inf"):
            latency[key] = float(val[1])

    nodes: set[str] = set()
    edges = []
    for item in rate:
        metric = item.get("metric") or {}
        src = metric.get("service")
        dst = metric.get("dst_service")
        val = item.get("value")
        if not src or not dst or not val or val[1] in (None, "NaN"):
            continue
        freq = float(val[1])
        nodes.add(src)
        nodes.add(dst)
        edges.append(
            {
                "source": src,
                "target": dst,
                "frequency_rps": freq,
                "p95_seconds": latency.get((src, dst)),
                "value_kind": "measured",
            }
        )

    return envelope(
        source="prometheus",
        value_kind="measured",
        data={
            "nodes": [{"id": n} for n in sorted(nodes)],
            "edges": edges,
            "note": "Graph is empty until crosslayer_downstream_* series exist.",
        },
    )
