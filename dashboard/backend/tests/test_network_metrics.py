from unittest.mock import AsyncMock



from app.clients.prometheus import prometheus_client
from auth_test_utils import authenticated_test_client

client = authenticated_test_client()


def test_network_queries_filter_virtual_interfaces():
    from app.queries import (
        node_network_receive_bytes_rate,
        node_network_receive_utilization,
    )

    receive_query = node_network_receive_bytes_rate()
    utilization_query = node_network_receive_utilization()

    assert 'device=~"^(eno' in receive_query
    assert "cali" not in receive_query
    assert "node_network_speed_bytes" in utilization_query
    assert "node_network_up" in utilization_query


def test_network_endpoint_returns_measured_interface_inventory(monkeypatch):
    monkeypatch.setattr(
        prometheus_client,
        "query_range",
        AsyncMock(
            return_value=[
                {
                    "metric": {"instance": "10.2.0.145:9100", "device": "eno1"},
                    "values": [[1000, "125000"]],
                }
            ],
        ),
    )
    monkeypatch.setattr(
        prometheus_client,
        "query",
        AsyncMock(
            side_effect=[
                [{"metric": {}, "value": [1000, "1000"]}],
                [
                    {
                        "metric": {"instance": "10.2.0.145:9100", "device": "eno1"},
                        "value": [1000, "1"],
                    },
                    {
                        "metric": {"instance": "10.2.0.145:9100", "device": "eno2"},
                        "value": [1000, "0"],
                    },
                ],
                [
                    {
                        "metric": {"instance": "10.2.0.145:9100", "device": "eno1"},
                        "value": [1000, "125000000"],
                    },
                    {
                        "metric": {"instance": "10.2.0.145:9100", "device": "eno2"},
                        "value": [1000, "-125000"],
                    },
                ],
                [
                    {
                        "metric": {
                            "instance": "10.2.0.145:9116",
                            "namespace": "crosslayer-system",
                            "service": "crosslayer-network-prober-v2",
                        },
                        "value": [1000, "1"],
                    }
                ],
            ],
        ),
    )

    response = client.get("/api/v1/metrics/network?range=15m")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "prometheus"
    assert body["value_kind"] == "measured"
    assert body["data"]["node_receive"][0]["points"] == [{"t": 1000.0, "v": 125000.0}]
    assert body["data"]["interfaces"] == [
        {
            "instance": "10.2.0.145:9100",
            "device": "eno1",
            "up": True,
            "speed_bytes_per_second": 125000000.0,
        },
        {
            "instance": "10.2.0.145:9100",
            "device": "eno2",
            "up": False,
            "speed_bytes_per_second": None,
        },
    ]
    assert body["data"]["probe_targets"] == [
        {"instance": "10.2.0.145:9116", "up": True}
    ]


def test_network_probe_series_names_disambiguate_replaced_pods(monkeypatch):
    from app import queries

    monkeypatch.setattr(
        prometheus_client,
        "range_window",
        AsyncMock(return_value=(900, 1000, "15s")),
    )

    async def query_range(expr, *_args):
        if expr != queries.node_network_probe_loss():
            return []
        return [
            {
                "metric": {
                    "source_node": "k8s-worker-1",
                    "target_node": "k8s-master-1",
                    "pod": "crosslayer-network-prober-v2-old",
                },
                "values": [[1000, "100"]],
            },
            {
                "metric": {
                    "source_node": "k8s-worker-1",
                    "target_node": "k8s-master-1",
                    "pod": "crosslayer-network-prober-v2-current",
                },
                "values": [[1000, "0"]],
            },
        ]

    monkeypatch.setattr(prometheus_client, "query_range", query_range)
    monkeypatch.setattr(prometheus_client, "query", AsyncMock(return_value=[]))

    response = client.get("/api/v1/metrics/network?range=15m")

    assert response.status_code == 200
    series = response.json()["data"]["inter_node_loss_percent"]
    assert [item["name"] for item in series] == [
        "k8s-worker-1|k8s-master-1|crosslayer-network-prober-v2-old",
        "k8s-worker-1|k8s-master-1|crosslayer-network-prober-v2-current",
    ]


def test_network_endpoint_rejects_unsupported_range():
    response = client.get("/api/v1/metrics/network?range=5m")

    assert response.status_code == 400


def test_network_and_envoy_keep_empty_series_when_prometheus_clock_is_unavailable(monkeypatch):
    from app.clients.prometheus import PrometheusError

    monkeypatch.setattr(
        prometheus_client,
        "range_window",
        AsyncMock(side_effect=PrometheusError("Prometheus unavailable")),
    )

    network_data = client.get("/api/v1/metrics/network?range=15m").json()["data"]
    envoy_data = client.get("/api/v1/metrics/envoy?range=15m").json()["data"]

    network_series = {
        "receive",
        "transmit",
        "node_receive",
        "node_transmit",
        "node_receive_mbps",
        "node_transmit_mbps",
        "node_receive_packets",
        "node_transmit_packets",
        "node_receive_errors",
        "node_transmit_errors",
        "node_receive_drops",
        "node_transmit_drops",
        "node_receive_utilization",
        "node_transmit_utilization",
        "node_tcp_retransmits",
        "inter_node_rtt_ms",
        "inter_node_rtt_p50_ms",
        "inter_node_rtt_p95_ms",
        "inter_node_rtt_p99_ms",
        "inter_node_jitter_ms",
        "inter_node_loss_percent",
    }
    envoy_series = {
        "request_rate",
        "latency_p50_seconds",
        "latency_p95_seconds",
        "latency_p99_seconds",
        "response_4xx_rate",
        "response_5xx_rate",
        "downstream_connections_active",
        "downstream_receive_bytes_rate",
        "downstream_transmit_bytes_rate",
        "upstream_request_rate",
        "upstream_latency_p95_seconds",
        "upstream_connections_active",
        "upstream_connection_failures_rate",
    }
    assert network_data["step"] is None
    assert all(network_data[name] == [] for name in network_series)
    assert network_data["interfaces"] == []
    assert network_data["probe_targets"] == []
    assert envoy_data["step"] is None
    assert all(envoy_data[name] == [] for name in envoy_series)
    assert envoy_data["target_status"] == []


def test_network_and_envoy_keep_complete_shapes_when_prometheus_queries_fail(monkeypatch):
    from app.clients.prometheus import PrometheusError

    monkeypatch.setattr(
        prometheus_client,
        "range_window",
        AsyncMock(return_value=(1000, 1900, "15s")),
    )
    monkeypatch.setattr(
        prometheus_client,
        "query_range",
        AsyncMock(side_effect=PrometheusError("Prometheus unavailable")),
    )
    monkeypatch.setattr(prometheus_client, "query", AsyncMock(return_value=[]))

    network_data = client.get("/api/v1/metrics/network?range=15m").json()["data"]
    envoy_data = client.get("/api/v1/metrics/envoy?range=15m").json()["data"]

    assert network_data["interfaces"] == []
    assert network_data["probe_targets"] == []
    assert all(
        network_data[name] == []
        for name in (
            "receive",
            "transmit",
            "node_receive",
            "node_transmit",
            "node_receive_mbps",
            "node_transmit_mbps",
            "node_receive_packets",
            "node_transmit_packets",
            "node_receive_errors",
            "node_transmit_errors",
            "node_receive_drops",
            "node_transmit_drops",
            "node_receive_utilization",
            "node_transmit_utilization",
            "node_tcp_retransmits",
            "inter_node_rtt_ms",
            "inter_node_rtt_p50_ms",
            "inter_node_rtt_p95_ms",
            "inter_node_rtt_p99_ms",
            "inter_node_jitter_ms",
            "inter_node_loss_percent",
        )
    )
    assert envoy_data["target_status"] == []
    assert all(
        envoy_data[name] == []
        for name in (
            "request_rate",
            "latency_p50_seconds",
            "latency_p95_seconds",
            "latency_p99_seconds",
            "response_4xx_rate",
            "response_5xx_rate",
            "downstream_connections_active",
            "downstream_receive_bytes_rate",
            "downstream_transmit_bytes_rate",
            "upstream_request_rate",
            "upstream_latency_p95_seconds",
            "upstream_connections_active",
            "upstream_connection_failures_rate",
        )
    )


def test_envoy_queries_expose_http_service_metrics():
    from app.queries import (
        envoy_downstream_latency_p95,
        envoy_downstream_request_rate,
        envoy_downstream_5xx_rate,
        envoy_upstream_latency_p95,
    )

    assert 'envoy_service=~".+"' in envoy_downstream_request_rate()
    assert "envoy_http_downstream_rq_time_bucket" in envoy_downstream_latency_p95()
    assert 'envoy_response_code_class="5"' in envoy_downstream_5xx_rate()
    assert "envoy_cluster_upstream_rq_time_bucket" in envoy_upstream_latency_p95()


def test_envoy_endpoint_returns_measured_series(monkeypatch):
    monkeypatch.setattr(
        prometheus_client,
        "query",
        AsyncMock(
            side_effect=[
                [{"metric": {}, "value": [1000, "1000"]}],
                [
                    {
                        "metric": {
                            "envoy_service": "document-retrieval",
                            "instance": "10.1.1.2:9901",
                        },
                        "value": [1000, "1"],
                    }
                ],
            ]
        ),
    )
    monkeypatch.setattr(
        prometheus_client,
        "query_range",
        AsyncMock(
            return_value=[
                {
                    "metric": {"envoy_service": "document-retrieval"},
                    "values": [[1000, "0.5"]],
                }
            ],
        ),
    )

    response = client.get("/api/v1/metrics/envoy?range=15m")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "prometheus"
    assert body["value_kind"] == "measured"
    assert body["data"]["request_rate"][0]["labels"]["envoy_service"] == "document-retrieval"
    assert body["data"]["latency_p95_seconds"][0]["points"] == [
        {"t": 1000.0, "v": 0.5}
    ]
    assert "do not make downstream service calls" in body["data"]["note"]
    assert body["data"]["target_status"] == [
        {
            "envoy_service": "document-retrieval",
            "instance": "10.1.1.2:9901",
            "up": True,
        }
    ]


def test_envoy_endpoint_rejects_unsupported_range():
    response = client.get("/api/v1/metrics/envoy?range=5m")

    assert response.status_code == 400


def test_prometheus_range_window_uses_prometheus_clock(monkeypatch):
    from app.clients.prometheus import PrometheusError

    monkeypatch.setattr(
        prometheus_client,
        "query",
        AsyncMock(return_value=[{"metric": {}, "value": [20000, "20000"]}]),
    )

    import asyncio

    start, end, step = asyncio.run(prometheus_client.range_window("15m"))

    assert end == 20000
    assert start == 19100
    assert step == "15s"
