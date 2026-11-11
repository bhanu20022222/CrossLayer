"""Explainable network-affinity scoring from observed telemetry."""

import math
from collections import defaultdict
from typing import Any


FEATURE_WEIGHTS = {
    "latency": 0.25,
    "bandwidth": 0.20,
    "loss": 0.10,
    "jitter": 0.10,
    "congestion": 0.15,
}
TOTAL_FEATURE_WEIGHT = sum(FEATURE_WEIGHTS.values())
LATENCY_SCALE_MS = 10.0
JITTER_SCALE_MS = 5.0
IMPROVEMENT_THRESHOLD_POINTS = 5.0
MIN_TRAFFIC_COVERAGE_PERCENT = 80.0
MIN_FEATURE_COVERAGE_PERCENT = 50.0


def _finite_nonnegative(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric < 0:
        return None
    return numeric


def node_link_affinity(
    metrics: dict[str, Any],
    source_utilization_pct: Any = None,
    target_utilization_pct: Any = None,
) -> dict[str, Any]:
    """Return a 0..100 link score, observed feature coverage, and component evidence."""
    components: dict[str, float] = {}
    observed: dict[str, float] = {}

    latency = _finite_nonnegative(metrics.get("latency_p95_ms"))
    if latency is not None:
        observed["latency_p95_ms"] = latency
        components["latency"] = math.exp(-latency / LATENCY_SCALE_MS)

    loss = _finite_nonnegative(metrics.get("loss_percent"))
    if loss is not None and loss <= 100:
        observed["loss_percent"] = loss
        components["loss"] = 1.0 - loss / 100.0

    jitter = _finite_nonnegative(metrics.get("jitter_ms"))
    if jitter is not None:
        observed["jitter_ms"] = jitter
        components["jitter"] = math.exp(-jitter / JITTER_SCALE_MS)

    utilizations = [
        value
        for value in (
            _finite_nonnegative(source_utilization_pct),
            _finite_nonnegative(target_utilization_pct),
        )
        if value is not None and value <= 100
    ]
    if utilizations:
        congestion_pct = max(utilizations)
        observed["congestion_percent"] = congestion_pct
        components["congestion"] = 1.0 - congestion_pct / 100.0

    available_weight = sum(FEATURE_WEIGHTS[name] for name in components)
    if available_weight == 0:
        return {
            "score": None,
            "coverage_percent": 0.0,
            "components": {},
            "observed": {},
        }

    score = sum(FEATURE_WEIGHTS[name] * value for name, value in components.items())
    return {
        "score": round(100.0 * score / available_weight, 3),
        "coverage_percent": round(
            100.0 * available_weight / TOTAL_FEATURE_WEIGHT, 1
        ),
        "components": {name: round(value * 100.0, 3) for name, value in components.items()},
        "observed": observed,
    }


def build_link_matrix(
    node_names: list[str],
    probe_metrics: dict[tuple[str, str], dict[str, Any]],
    node_utilization: dict[str, float],
) -> list[dict[str, Any]]:
    links = []
    for source in sorted(node_names):
        for target in sorted(node_names):
            if source == target:
                continue
            metrics = probe_metrics.get((source, target), {})
            affinity = node_link_affinity(
                metrics,
                node_utilization.get(source),
                node_utilization.get(target),
            )
            if affinity["score"] is None:
                continue
            links.append({"source": source, "target": target, **affinity})
    return links


def rank_pod_placements(
    nodes: list[dict[str, Any]],
    service_endpoints: dict[str, list[dict[str, Any]]],
    edges: list[dict[str, Any]],
    endpoint_request_rates: dict[str, float],
    link_lookup: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rank schedulable nodes using only measured service dependencies and link quality."""
    endpoint_service = {
        str(endpoint.get("pod")): service
        for service, endpoints in service_endpoints.items()
        for endpoint in endpoints
        if endpoint.get("pod")
    }
    node_names = [
        str(node["name"])
        for node in nodes
        if node.get("ready") and not node.get("unschedulable")
    ]
    edges_by_source_pod: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming_by_service: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        rate = _finite_nonnegative(edge.get("frequency_rps"))
        if rate is None or rate <= 0:
            continue
        source_pod = edge.get("source_pod")
        if source_pod:
            edges_by_source_pod[str(source_pod)].append(edge)
        incoming_by_service[str(edge["destination_service"])].append(edge)

    recommendations = []
    for pod_name, service in sorted(endpoint_service.items()):
        pod_edges = list(edges_by_source_pod.get(pod_name, []))
        pod_edges.extend(incoming_by_service.get(service, []))
        if not pod_edges:
            continue

        pod_edges = [
            edge
            for edge in pod_edges
            if (
                edge.get("source_pod") == pod_name
                or edge.get("destination_service") == service
            )
        ]
        pod_node = next(
            (
                endpoint.get("node")
                for endpoint in service_endpoints[service]
                if endpoint.get("pod") == pod_name
            ),
            None,
        )
        if not pod_node:
            continue

        peer_observations = []
        total_traffic = 0.0
        for edge in pod_edges:
            rate = _finite_nonnegative(edge.get("frequency_rps")) or 0.0
            if rate <= 0:
                continue
            outgoing = edge.get("source_pod") == pod_name
            peer_service = (
                str(edge["destination_service"])
                if outgoing
                else str(edge["source_service"])
            )
            if outgoing:
                peer_endpoints = [
                    endpoint
                    for endpoint in service_endpoints.get(peer_service, [])
                    if endpoint.get("node")
                ]
                if not peer_endpoints:
                    continue
                endpoint_rates = [
                    _finite_nonnegative(endpoint_request_rates.get(str(endpoint.get("pod"))))
                    or 0.0
                    for endpoint in peer_endpoints
                ]
                rate_total = sum(endpoint_rates)
                shares = (
                    [value / rate_total for value in endpoint_rates]
                    if rate_total > 0
                    else [1.0 / len(peer_endpoints)] * len(peer_endpoints)
                )
                peers = [
                    (str(endpoint["node"]), rate * share, "outgoing")
                    for endpoint, share in zip(peer_endpoints, shares)
                ]
            else:
                peer_node = edge.get("source_node")
                if not peer_node:
                    continue
                peers = [(str(peer_node), rate, "incoming")]

            for peer_node, weighted_rate, direction in peers:
                if weighted_rate <= 0:
                    continue
                total_traffic += weighted_rate
                peer_observations.append((peer_node, weighted_rate, direction))

        if total_traffic <= 0:
            continue

        candidates = set(node_names)
        candidates.add(str(pod_node))
        ranked = []
        for candidate in candidates:
            weighted_score = 0.0
            weighted_feature_coverage = 0.0
            covered_traffic = 0.0
            local_path_assumptions = 0
            for peer_node, rate, direction in peer_observations:
                if candidate == peer_node:
                    score = 100.0
                    feature_coverage = 0.0
                    local_path_assumptions += 1
                else:
                    key = (
                        (candidate, peer_node)
                        if direction == "outgoing"
                        else (peer_node, candidate)
                    )
                    link = link_lookup.get(key)
                    if not link or link.get("score") is None:
                        continue
                    score = float(link["score"])
                    feature_coverage = float(link["coverage_percent"])
                covered_traffic += rate
                weighted_score += rate * score
                weighted_feature_coverage += rate * feature_coverage

            score = (
                round(weighted_score / covered_traffic, 3)
                if covered_traffic > 0
                else None
            )
            feature_coverage = (
                round(weighted_feature_coverage / total_traffic, 1)
                if total_traffic > 0
                else 0.0
            )
            traffic_coverage = round(100.0 * covered_traffic / total_traffic, 1)
            node = next((item for item in nodes if item["name"] == candidate), None)
            ranked.append(
                {
                    "node": candidate,
                    "score": score,
                    "rank": None,
                    "is_current": candidate == pod_node,
                    "ready": bool(node and node.get("ready")),
                    "schedulable": bool(node and not node.get("unschedulable")),
                    "traffic_coverage_percent": traffic_coverage,
                    "feature_coverage_percent": feature_coverage,
                    "local_path_assumptions": local_path_assumptions,
                    "communication_rps": round(total_traffic, 6),
                }
            )

        ranked.sort(
            key=lambda item: (
                item["score"] is None,
                -(item["score"] or 0.0),
                not item["is_current"],
                item["node"],
            )
        )
        rank = 0
        for candidate in ranked:
            if candidate["score"] is not None:
                rank += 1
                candidate["rank"] = rank
        current = next(
            (candidate for candidate in ranked if candidate["is_current"]), None
        )
        alternatives = [
            candidate
            for candidate in ranked
            if candidate["score"] is not None
            and candidate["node"] != pod_node
            and candidate["ready"]
            and candidate["schedulable"]
            and candidate["traffic_coverage_percent"] >= MIN_TRAFFIC_COVERAGE_PERCENT
            and candidate["feature_coverage_percent"] >= MIN_FEATURE_COVERAGE_PERCENT
        ]
        best_alternative = alternatives[0] if alternatives else None
        improvement = (
            round(best_alternative["score"] - current["score"], 3)
            if best_alternative
            and current
            and best_alternative["score"] is not None
            and current["score"] is not None
            else None
        )
        if (
            current is None
            or current["score"] is None
            or current["traffic_coverage_percent"] < MIN_TRAFFIC_COVERAGE_PERCENT
            or current["feature_coverage_percent"] < MIN_FEATURE_COVERAGE_PERCENT
        ):
            advice = "insufficient_measurements"
        elif (
            best_alternative
            and improvement is not None
            and improvement >= IMPROVEMENT_THRESHOLD_POINTS
        ):
            advice = "consider_network_candidate"
        else:
            advice = "keep_current"
        recommendations.append(
            {
                "namespace": pod_name.split("/", 1)[0] if "/" in pod_name else None,
                "pod": next(
                    (
                        endpoint.get("pod_name")
                        for endpoint in service_endpoints[service]
                        if endpoint.get("pod") == pod_name
                    ),
                    pod_name,
                ),
                "service": service.split("/", 1)[-1],
                "current_node": pod_node,
                "dependencies": sorted(
                    {
                        (
                            edge["source_service"],
                            edge["destination_service"],
                        )
                        for edge in pod_edges
                    }
                ),
                "advice": advice,
                "best_alternative_node": (
                    best_alternative["node"] if best_alternative else None
                ),
                "improvement_points": improvement,
                "candidates": ranked,
            }
        )
    return recommendations
