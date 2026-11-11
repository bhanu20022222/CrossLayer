import asyncio

from fastapi import APIRouter, HTTPException, Query

from app.clients.prometheus import PrometheusError, prometheus_client
from app.envelope import envelope, unavailable
from app import queries
from app.timeutil import matrix_to_series, parse_range, vector_to_rows

router = APIRouter()


async def _range_payload(expr: str, range_token: str, name_from: tuple[str, ...]):
    try:
        start, end, step = await prometheus_client.range_window(range_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PrometheusError as exc:
        return unavailable("prometheus", str(exc), data={"series": []})
    try:
        result = await prometheus_client.query_range(expr, start, end, step)
    except PrometheusError as exc:
        return unavailable("prometheus", str(exc), data={"series": []})
    return envelope(
        source="prometheus",
        value_kind="measured",
        data={"range": range_token, "step": step, "series": matrix_to_series(result, name_from)},
    )


@router.get("/metrics/cpu")
async def cpu(range: str = Query(default="15m", alias="range")):
    return await _range_payload(queries.cpu_by_pod(), range, ("pod", "node"))


@router.get("/metrics/memory")
async def memory(range: str = Query(default="15m", alias="range")):
    return await _range_payload(queries.memory_by_pod(), range, ("pod", "node"))


@router.get("/metrics/network")
async def network(range: str = Query(default="15m", alias="range")):
    range_queries = {
        "receive": (queries.net_rx_by_pod(), ("pod", "node")),
        "transmit": (queries.net_tx_by_pod(), ("pod", "node")),
        "node_receive": (queries.node_network_receive_bytes_rate(), ("instance", "device")),
        "node_transmit": (queries.node_network_transmit_bytes_rate(), ("instance", "device")),
        "node_receive_mbps": (queries.node_network_receive_mbps(), ("instance", "device")),
        "node_transmit_mbps": (queries.node_network_transmit_mbps(), ("instance", "device")),
        "node_receive_packets": (queries.node_network_receive_packets_rate(), ("instance", "device")),
        "node_transmit_packets": (queries.node_network_transmit_packets_rate(), ("instance", "device")),
        "node_receive_errors": (queries.node_network_receive_errors_rate(), ("instance", "device")),
        "node_transmit_errors": (queries.node_network_transmit_errors_rate(), ("instance", "device")),
        "node_receive_drops": (queries.node_network_receive_drops_rate(), ("instance", "device")),
        "node_transmit_drops": (queries.node_network_transmit_drops_rate(), ("instance", "device")),
        "node_receive_utilization": (queries.node_network_receive_utilization(), ("instance", "device")),
        "node_transmit_utilization": (queries.node_network_transmit_utilization(), ("instance", "device")),
        "node_tcp_retransmits": (queries.node_tcp_retransmit_rate(), ("instance",)),
        "inter_node_rtt_ms": (
            queries.node_network_probe_rtt(),
            ("source_node", "target_node", "pod"),
        ),
        "inter_node_rtt_p50_ms": (
            queries.node_network_probe_rtt_p50(),
            ("source_node", "target_node", "pod"),
        ),
        "inter_node_rtt_p95_ms": (
            queries.node_network_probe_rtt_p95(),
            ("source_node", "target_node", "pod"),
        ),
        "inter_node_rtt_p99_ms": (
            queries.node_network_probe_rtt_p99(),
            ("source_node", "target_node", "pod"),
        ),
        "inter_node_jitter_ms": (
            queries.node_network_probe_jitter(),
            ("source_node", "target_node", "pod"),
        ),
        "inter_node_loss_percent": (
            queries.node_network_probe_loss(),
            ("source_node", "target_node", "pod"),
        ),
    }

    note = (
        "Node interface rates use physical Ethernet interfaces only; virtual Calico and loopback "
        "interfaces are excluded. Utilization is unavailable for links that are down or have "
        "no valid reported speed. Inter-node probe series appear only when the probe exports samples. "
        "Chart range timestamps follow the Prometheus server clock."
    )
    try:
        start, end, step = await prometheus_client.range_window(range)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PrometheusError as exc:
        return unavailable(
            "prometheus",
            str(exc),
            data={
                "range": range,
                "step": None,
                **{name: [] for name in range_queries},
                "interfaces": [],
                "probe_targets": [],
                "note": "Prometheus network metrics are unavailable.",
            },
        )

    try:
        results = await asyncio.gather(
            *(
                prometheus_client.query_range(expr, start, end, step)
                for expr, _ in range_queries.values()
            ),
            prometheus_client.query(queries.node_network_interface_up()),
            prometheus_client.query(queries.node_network_interface_speed()),
            prometheus_client.query(queries.node_network_probe_targets()),
        )
    except PrometheusError as exc:
        return unavailable(
            "prometheus",
            str(exc),
            data={
                "range": range,
                "step": step,
                **{name: [] for name in range_queries},
                "interfaces": [],
                "probe_targets": [],
                "note": "Prometheus network metrics are unavailable.",
            },
        )

    series_data = {
        name: matrix_to_series(result, labels)
        for (name, (_, labels)), result in zip(range_queries.items(), results[: len(range_queries)])
    }
    interface_rows: dict[tuple[str, str], dict] = {}
    for row in vector_to_rows(results[-3], ("instance", "device")):
        key = (row["instance"], row["device"])
        interface_rows[key] = {
            "instance": row["instance"],
            "device": row["device"],
            "up": row["value"] == 1,
            "speed_bytes_per_second": None,
        }
    for row in vector_to_rows(results[-2], ("instance", "device")):
        key = (row["instance"], row["device"])
        interface = interface_rows.setdefault(
            key,
            {
                "instance": row["instance"],
                "device": row["device"],
                "up": None,
                "speed_bytes_per_second": None,
            },
        )
        if row["value"] is not None and row["value"] > 0:
            interface["speed_bytes_per_second"] = row["value"]
    probe_targets = [
        {
            "instance": row["instance"],
            "up": row["value"] == 1,
        }
        for row in vector_to_rows(results[-1], ("instance",))
        if row["value"] is not None
    ]

    return envelope(
        source="prometheus",
        value_kind="measured",
        data={
            "range": range,
            "step": step,
            **series_data,
            "interfaces": sorted(
                interface_rows.values(), key=lambda row: (row["instance"], row["device"])
            ),
            "probe_targets": probe_targets,
            "note": note,
        },
    )


@router.get("/metrics/envoy")
async def envoy_metrics(range: str = Query(default="15m", alias="range")):
    range_queries = {
        "request_rate": (queries.envoy_downstream_request_rate(), ("envoy_service",)),
        "latency_p50_seconds": (queries.envoy_downstream_latency_p50(), ("envoy_service",)),
        "latency_p95_seconds": (queries.envoy_downstream_latency_p95(), ("envoy_service",)),
        "latency_p99_seconds": (queries.envoy_downstream_latency_p99(), ("envoy_service",)),
        "response_4xx_rate": (queries.envoy_downstream_4xx_rate(), ("envoy_service",)),
        "response_5xx_rate": (queries.envoy_downstream_5xx_rate(), ("envoy_service",)),
        "downstream_connections_active": (
            queries.envoy_downstream_connections_active(),
            ("envoy_service",),
        ),
        "downstream_receive_bytes_rate": (
            queries.envoy_downstream_receive_bytes_rate(),
            ("envoy_service",),
        ),
        "downstream_transmit_bytes_rate": (
            queries.envoy_downstream_transmit_bytes_rate(),
            ("envoy_service",),
        ),
        "upstream_request_rate": (
            queries.envoy_upstream_request_rate(),
            ("envoy_service", "envoy_cluster_name"),
        ),
        "upstream_latency_p95_seconds": (
            queries.envoy_upstream_latency_p95(),
            ("envoy_service", "envoy_cluster_name"),
        ),
        "upstream_connections_active": (
            queries.envoy_upstream_connections_active(),
            ("envoy_service", "envoy_cluster_name"),
        ),
        "upstream_connection_failures_rate": (
            queries.envoy_upstream_connection_failures_rate(),
            ("envoy_service", "envoy_cluster_name"),
        ),
    }

    try:
        start, end, step = await prometheus_client.range_window(range)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PrometheusError as exc:
        return unavailable(
            "prometheus",
            str(exc),
            data={
                "range": range,
                "step": None,
                **{name: [] for name in range_queries},
                "target_status": [],
                "note": "Envoy telemetry is unavailable from Prometheus.",
            },
        )

    try:
        results = await asyncio.gather(
            *(
                prometheus_client.query_range(expr, start, end, step)
                for expr, _ in range_queries.values()
            ),
            prometheus_client.query(queries.envoy_scrape_up()),
        )
    except PrometheusError as exc:
        return unavailable(
            "prometheus",
            str(exc),
            data={
                "range": range,
                "step": step,
                **{name: [] for name in range_queries},
                "target_status": [],
                "note": "Envoy telemetry is unavailable from Prometheus.",
            },
        )

    target_status = [
        {
            "envoy_service": row["envoy_service"],
            "instance": row["instance"],
            "up": row["value"] == 1,
        }
        for row in vector_to_rows(results[-1], ("envoy_service", "instance"))
        if row["value"] is not None
    ]
    return envelope(
        source="prometheus",
        value_kind="measured",
        data={
            "range": range,
            "step": step,
            **{
                name: matrix_to_series(result, labels)
                for (name, (_, labels)), result in zip(range_queries.items(), results)
            },
            "target_status": target_status,
            "note": (
                "Envoy metrics measure HTTP requests that traverse the CrossLayer Services. "
                "Latency percentiles require observed requests; absent series are not fabricated. "
                "The current Nginx workload placeholders do not make downstream service calls. "
                "Chart range timestamps follow the Prometheus server clock."
            ),
        },
    )


@router.get("/metrics/node-cpu")
async def node_cpu():
    try:
        rows = vector_to_rows(await prometheus_client.query(queries.node_cpu_idle_ratio()), ("instance", "job"))
    except PrometheusError as exc:
        return unavailable("prometheus", str(exc), data=[])
    return envelope(source="prometheus", value_kind="measured", data=rows)
