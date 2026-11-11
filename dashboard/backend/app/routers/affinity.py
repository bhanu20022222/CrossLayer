import asyncio
import ipaddress
import math
import statistics
from collections import defaultdict
from typing import Any

from fastapi import APIRouter

from app import queries
from app.affinity import (
    FEATURE_WEIGHTS,
    IMPROVEMENT_THRESHOLD_POINTS,
    JITTER_SCALE_MS,
    LATENCY_SCALE_MS,
    MIN_FEATURE_COVERAGE_PERCENT,
    MIN_TRAFFIC_COVERAGE_PERCENT,
    build_link_matrix,
    rank_pod_placements,
)
from app.clients.kubernetes import KubernetesError, kubernetes_client
from app.clients.prometheus import PrometheusError, prometheus_client
from app.config import settings
from app.envelope import envelope, unavailable

router = APIRouter()

_EMPTY_DATA = {
    "algorithm": {},
    "nodes": [],
    "node_links": [],
    "communications": [],
    "recommendations": [],
    "probe_targets_up": 0,
    "probe_targets_total": 0,
    "partial_errors": [],
    "note": "",
}


def _sample(item: dict[str, Any]) -> float | None:
    value = item.get("value")
    if not value or len(value) != 2:
        return None
    try:
        numeric = float(value[1])
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _node_for_instance(instance: str, address_to_node: dict[str, str]) -> str | None:
    host = instance
    if host.startswith("[") and "]" in host:
        host = host[1 : host.index("]")]
    elif host.count(":") == 1:
        possible_host, possible_port = host.rsplit(":", 1)
        if possible_port.isdigit():
            host = possible_host
    try:
        host = str(ipaddress.ip_address(host))
    except ValueError:
        return None
    return address_to_node.get(host)


def _probe_metrics(
    results: tuple[list[dict[str, Any]], ...]
) -> dict[tuple[str, str], dict[str, float]]:
    grouped: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for metric_name, result in zip(("latency_p95_ms", "jitter_ms", "loss_percent"), results):
        for item in result:
            labels = item.get("metric") or {}
            source = labels.get("source_node")
            target = labels.get("target_node")
            value = _sample(item)
            if source and target and source != target and value is not None:
                grouped[(str(source), str(target))][metric_name].append(value)
    return {
        pair: {
            metric: statistics.median(values)
            for metric, values in metrics.items()
            if values
        }
        for pair, metrics in grouped.items()
    }


def _service_endpoint_map(
    service_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in service_rows:
        service_key = f"{row['namespace']}/{row['name']}"
        for endpoint in row.get("pods", []):
            pod_name = endpoint.get("pod")
            node = endpoint.get("node")
            if pod_name and node:
                grouped[service_key].append(
                    {
                        "pod": f"{row['namespace']}/{pod_name}",
                        "pod_name": pod_name,
                        "node": node,
                    }
                )
    return dict(grouped)


def _dependency_edges(
    result: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    edges = []
    for item in result:
        metric = item.get("metric") or {}
        namespace = metric.get("namespace")
        service = metric.get("service")
        destination = metric.get("dst_service")
        pod = metric.get("pod")
        node = metric.get("node")
        rate = _sample(item)
        if (
            namespace
            and service
            and destination
            and pod
            and node
            and rate is not None
            and rate > 0
        ):
            edges.append(
                {
                    "namespace": namespace,
                    "source_service": f"{namespace}/{service}",
                    "destination_service": f"{namespace}/{destination}",
                    "source_pod": f"{namespace}/{pod}",
                    "source_node": node,
                    "frequency_rps": rate,
                }
            )
    return edges


def _communication_summary(
    edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    summary: dict[tuple[str, str], float] = defaultdict(float)
    for edge in edges:
        source = edge["source_service"].split("/", 1)[-1]
        destination = edge["destination_service"].split("/", 1)[-1]
        summary[(source, destination)] += edge["frequency_rps"]
    return [
        {
            "source": source,
            "destination": destination,
            "requests_per_second": round(rate, 6),
            "value_kind": "measured",
        }
        for (source, destination), rate in sorted(summary.items())
    ]


@router.get("/affinity/network")
async def network_affinity():
    try:
        nodes = kubernetes_client.list_nodes()
    except KubernetesError as exc:
        return unavailable("kubernetes", str(exc), data=_EMPTY_DATA)

    namespaces = tuple(
        dict.fromkeys((settings.workload_namespace, "crosslayer-experiments"))
    )
    service_rows = []
    partial_errors = []
    for namespace in namespaces:
        try:
            service_rows.extend(kubernetes_client.list_service_endpoints(namespace))
        except KubernetesError as exc:
            partial_errors.append(str(exc))

    try:
        (
            rtt_result,
            jitter_result,
            loss_result,
            receive_util_result,
            transmit_util_result,
            edge_result,
            endpoint_rate_result,
        ) = await asyncio.gather(
            prometheus_client.query(queries.affinity_probe_rtt_p95()),
            prometheus_client.query(queries.affinity_probe_jitter()),
            prometheus_client.query(queries.affinity_probe_loss()),
            prometheus_client.query(queries.node_network_receive_utilization()),
            prometheus_client.query(queries.node_network_transmit_utilization()),
            prometheus_client.query(queries.affinity_downstream_rate(namespaces)),
            prometheus_client.query(queries.affinity_service_request_rate(namespaces)),
        )
        probe_targets = await prometheus_client.query(queries.node_network_probe_targets())
    except PrometheusError as exc:
        return unavailable(
            "prometheus",
            str(exc),
            data={**_EMPTY_DATA, "partial_errors": partial_errors},
        )

    address_to_node = {}
    node_by_name = {}
    for node in nodes:
        node_name = node["name"]
        node_by_name[node_name] = node
        for address in (node.get("addresses") or {}).values():
            try:
                address_to_node[str(ipaddress.ip_address(address))] = node_name
            except ValueError:
                continue

    utilization_samples: dict[str, list[float]] = defaultdict(list)
    for result in (receive_util_result, transmit_util_result):
        for item in result:
            instance = (item.get("metric") or {}).get("instance")
            value = _sample(item)
            if instance and value is not None and 0 <= value <= 100:
                node_name = _node_for_instance(str(instance), address_to_node)
                if node_name:
                    utilization_samples[node_name].append(value)
    utilization = {
        node: max(samples) for node, samples in utilization_samples.items()
    }

    probe_metrics = _probe_metrics((rtt_result, jitter_result, loss_result))
    node_names = sorted(node_by_name)
    link_rows = build_link_matrix(node_names, probe_metrics, utilization)
    link_lookup = {(row["source"], row["target"]): row for row in link_rows}
    service_endpoints = _service_endpoint_map(service_rows)
    edges = _dependency_edges(edge_result)
    endpoint_rates = {}
    for item in endpoint_rate_result:
        labels = item.get("metric") or {}
        namespace = labels.get("namespace")
        pod = labels.get("pod")
        value = _sample(item)
        if namespace and pod and value is not None and value > 0:
            endpoint_rates[f"{namespace}/{pod}"] = value
    recommendations = rank_pod_placements(
        nodes,
        service_endpoints,
        edges,
        endpoint_rates,
        link_lookup,
    )

    target_values = [_sample(item) for item in probe_targets]
    target_values = [value for value in target_values if value is not None]
    data = {
        "algorithm": {
            "name": "Network Affinity Generator",
            "version": "NAG-v1",
            "method": "Traffic-weighted directed link quality with missing-feature weight renormalization",
            "window": "5m",
            "feature_weights": FEATURE_WEIGHTS,
            "normalization": {
                "latency": f"exp(-RTT_p95_ms / {LATENCY_SCALE_MS:g})",
                "loss": "1 - packet_loss_percent / 100",
                "jitter": f"exp(-jitter_ms / {JITTER_SCALE_MS:g})",
                "congestion": "1 - max(source, destination physical-interface utilization percent) / 100",
                "bandwidth": "not scored until available-bandwidth telemetry is collected",
            },
            "placement": "traffic-weighted mean of measured directed link affinity to communicating service endpoints",
            "advisory_policy": {
                "minimum_improvement_points": IMPROVEMENT_THRESHOLD_POINTS,
                "minimum_traffic_coverage_percent": MIN_TRAFFIC_COVERAGE_PERCENT,
                "minimum_feature_coverage_percent": MIN_FEATURE_COVERAGE_PERCENT,
            },
        },
        "nodes": [
            {
                "name": node["name"],
                "ready": bool(node.get("ready")),
                "schedulable": bool(node.get("ready") and not node.get("unschedulable")),
                "network_utilization_percent": utilization.get(node["name"]),
            }
            for node in nodes
        ],
        "node_links": link_rows,
        "communications": _communication_summary(edges),
        "recommendations": recommendations,
        "probe_targets_up": sum(value == 1 for value in target_values),
        "probe_targets_total": len(target_values),
        "partial_errors": partial_errors,
        "note": (
            "Scores are derived from measured telemetry and are advisory only. Candidate nodes "
            "are filtered for Node Ready and unschedulable status; CPU/memory fit, taints, "
            "volumes, security policy, migration cost, and application SLOs are not yet evaluated. "
            "No Kubernetes placement or migration action is performed."
        ),
    }
    if not link_rows and not recommendations:
        return unavailable(
            "none",
            "Affinity is unavailable because no active inter-node probe or measured service dependency data is available.",
            data=data,
        )
    return envelope(source="derived", value_kind="derived", data=data)
