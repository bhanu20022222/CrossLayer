import math
from unittest.mock import AsyncMock

from app import queries
from app.affinity import build_link_matrix, node_link_affinity, rank_pod_placements
from app.clients.kubernetes import kubernetes_client
from app.clients.prometheus import prometheus_client
from auth_test_utils import authenticated_test_client

client = authenticated_test_client()


def test_link_affinity_normalizes_measured_costs_and_reports_coverage():
    affinity = node_link_affinity(
        {
            "latency_p95_ms": 0,
            "loss_percent": 0,
            "jitter_ms": 0,
        },
        source_utilization_pct=0,
        target_utilization_pct=0,
    )

    assert affinity["score"] == 100
    assert affinity["coverage_percent"] == 75
    assert affinity["components"] == {
        "latency": 100,
        "loss": 100,
        "jitter": 100,
        "congestion": 100,
    }


def test_link_affinity_does_not_invent_missing_or_invalid_metrics():
    missing = node_link_affinity({})
    invalid = node_link_affinity(
        {
            "latency_p95_ms": float("nan"),
            "loss_percent": 101,
            "jitter_ms": -1,
        },
        source_utilization_pct=120,
    )

    assert missing == {
        "score": None,
        "coverage_percent": 0,
        "components": {},
        "observed": {},
    }
    assert invalid["score"] is None


def test_link_affinity_penalizes_latency_loss_jitter_and_congestion():
    affinity = node_link_affinity(
        {
            "latency_p95_ms": 10,
            "loss_percent": 50,
            "jitter_ms": 5,
        },
        source_utilization_pct=70,
        target_utilization_pct=40,
    )

    assert affinity["score"] < 100
    assert math.isclose(
        affinity["components"]["latency"],
        100 * math.exp(-1),
        abs_tol=0.001,
    )
    assert affinity["components"]["loss"] == 50
    assert math.isclose(
        affinity["components"]["jitter"],
        100 * math.exp(-1),
        abs_tol=0.001,
    )
    assert affinity["observed"]["congestion_percent"] == 70


def test_link_matrix_keeps_direction_and_omits_unmeasured_pairs():
    links = build_link_matrix(
        ["node-a", "node-b", "node-c"],
        {("node-a", "node-b"): {"latency_p95_ms": 1}},
        {},
    )

    assert [(link["source"], link["target"]) for link in links] == [
        ("node-a", "node-b")
    ]


def test_affinity_namespace_regex_escapes_for_prometheus():
    query = queries.affinity_downstream_rate(("crosslayer-workloads", "team-a.v1"))

    assert 'namespace=~"crosslayer-workloads|team-a\\.v1"' in query
    assert r"\-" not in query


def test_placement_ranking_uses_traffic_weighted_directed_affinity():
    nodes = [
        {"name": "node-a", "ready": True, "unschedulable": False},
        {"name": "node-b", "ready": True, "unschedulable": False},
        {"name": "node-c", "ready": False, "unschedulable": False},
    ]
    endpoints = {
        "crosslayer-experiments/experiment-api": [
            {
                "pod": "crosslayer-experiments/api-pod",
                "pod_name": "api-pod",
                "node": "node-a",
            }
        ],
        "crosslayer-experiments/experiment-worker": [
            {
                "pod": "crosslayer-experiments/worker-pod",
                "pod_name": "worker-pod",
                "node": "node-b",
            }
        ],
    }
    links = {
        ("node-a", "node-b"): {
            "score": 60,
            "coverage_percent": 75,
        },
        ("node-b", "node-a"): {
            "score": 80,
            "coverage_percent": 75,
        },
    }

    recommendations = rank_pod_placements(
        nodes,
        endpoints,
        [
            {
                "source_service": "crosslayer-experiments/experiment-api",
                "destination_service": "crosslayer-experiments/experiment-worker",
                "source_pod": "crosslayer-experiments/api-pod",
                "source_node": "node-a",
                "frequency_rps": 4,
            }
        ],
        {"crosslayer-experiments/worker-pod": 5},
        links,
    )

    recommendation = next(
        item for item in recommendations if item["pod"] == "api-pod"
    )
    ranked = recommendation["candidates"]
    assert ranked[0]["node"] == "node-b"
    assert ranked[0]["score"] == 100
    assert ranked[0]["traffic_coverage_percent"] == 100
    assert ranked[0]["feature_coverage_percent"] == 0
    assert ranked[0]["local_path_assumptions"] == 1
    assert recommendation["advice"] == "keep_current"
    assert "node-c" not in {candidate["node"] for candidate in ranked}


def test_affinity_endpoint_combines_live_network_and_communication_metrics(monkeypatch):
    nodes = [
        {
            "name": "node-a",
            "ready": True,
            "unschedulable": False,
            "addresses": {"InternalIP": "10.0.0.1"},
        },
        {
            "name": "node-b",
            "ready": True,
            "unschedulable": False,
            "addresses": {"InternalIP": "10.0.0.2"},
        },
    ]
    services = {
        "crosslayer-experiments": [
            {
                "namespace": "crosslayer-experiments",
                "name": "experiment-api",
                "pods": [{"pod": "api-pod", "node": "node-a"}],
            },
            {
                "namespace": "crosslayer-experiments",
                "name": "experiment-worker",
                "pods": [{"pod": "worker-pod", "node": "node-b"}],
            },
        ],
        "crosslayer-workloads": [],
    }
    monkeypatch.setattr(kubernetes_client, "list_nodes", lambda: nodes)
    monkeypatch.setattr(
        kubernetes_client,
        "list_service_endpoints",
        lambda namespace: services[namespace],
    )

    query_results = {
        queries.affinity_probe_rtt_p95(): [
            {
                "metric": {"source_node": "node-a", "target_node": "node-b"},
                "value": [1000, "2"],
            },
            {
                "metric": {"source_node": "node-b", "target_node": "node-a"},
                "value": [1000, "3"],
            },
        ],
        queries.affinity_probe_jitter(): [
            {
                "metric": {"source_node": "node-a", "target_node": "node-b"},
                "value": [1000, "0.5"],
            }
        ],
        queries.affinity_probe_loss(): [
            {
                "metric": {"source_node": "node-a", "target_node": "node-b"},
                "value": [1000, "0"],
            }
        ],
        queries.node_network_receive_utilization(): [
            {"metric": {"instance": "10.0.0.1:9100"}, "value": [1000, "20"]},
            {"metric": {"instance": "10.0.0.2:9100"}, "value": [1000, "30"]},
        ],
        queries.node_network_transmit_utilization(): [],
        queries.affinity_downstream_rate(
            ("crosslayer-workloads", "crosslayer-experiments")
        ): [
            {
                "metric": {
                    "namespace": "crosslayer-experiments",
                    "service": "experiment-api",
                    "dst_service": "experiment-worker",
                    "pod": "api-pod",
                    "node": "node-a",
                },
                "value": [1000, "4"],
            }
        ],
        queries.affinity_service_request_rate(
            ("crosslayer-workloads", "crosslayer-experiments")
        ): [
            {
                "metric": {
                    "namespace": "crosslayer-experiments",
                    "service": "experiment-worker",
                    "pod": "worker-pod",
                    "node": "node-b",
                },
                "value": [1000, "5"],
            }
        ],
        queries.node_network_probe_targets(): [
            {"metric": {"instance": "10.0.0.1:9116"}, "value": [1000, "1"]}
        ],
    }

    async def query(expr):
        return query_results[expr]

    monkeypatch.setattr(prometheus_client, "query", query)

    response = client.get("/api/v1/affinity/network")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "derived"
    assert body["value_kind"] == "derived"
    assert body["data"]["probe_targets_up"] == 1
    assert body["data"]["node_links"][0]["score"] > 0
    assert body["data"]["communications"] == [
        {
            "source": "experiment-api",
            "destination": "experiment-worker",
            "requests_per_second": 4,
            "value_kind": "measured",
        }
    ]
    recommendation = body["data"]["recommendations"][0]
    assert recommendation["pod"] == "api-pod"
    assert recommendation["service"] == "experiment-api"
    assert recommendation["candidates"][0]["node"] == "node-b"


def test_affinity_endpoint_reports_prometheus_failure(monkeypatch):
    from app.clients.prometheus import PrometheusError

    monkeypatch.setattr(kubernetes_client, "list_nodes", lambda: [])
    monkeypatch.setattr(kubernetes_client, "list_service_endpoints", lambda _ns: [])
    monkeypatch.setattr(
        prometheus_client,
        "query",
        AsyncMock(side_effect=PrometheusError("Prometheus unavailable")),
    )

    response = client.get("/api/v1/affinity/network")

    assert response.status_code == 200
    body = response.json()
    assert body["value_kind"] == "unavailable"
    assert body["error"] == "Prometheus unavailable"
    assert body["data"]["recommendations"] == []
