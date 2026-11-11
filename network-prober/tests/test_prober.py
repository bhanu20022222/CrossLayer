from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

from network_prober.__main__ import (
    MetricsHandler,
    NodeTarget,
    ProbeRegistry,
    checksum,
    parse_node_targets,
)


def test_node_discovery_uses_internal_ips_and_skips_source_node():
    payload = {
        "items": [
            {
                "metadata": {"name": "node-a"},
                "status": {"addresses": [{"type": "InternalIP", "address": "10.0.0.1"}]},
            },
            {
                "metadata": {"name": "node-b"},
                "status": {"addresses": [{"type": "InternalIP", "address": "10.0.0.2"}]},
            },
            {
                "metadata": {"name": "node-c"},
                "status": {"addresses": [{"type": "Hostname", "address": "node-c"}]},
            },
        ]
    }

    assert parse_node_targets(payload, "node-a") == [
        NodeTarget(name="node-b", address="10.0.0.2")
    ]


def test_checksum_handles_even_and_odd_payload_lengths():
    assert checksum(b"\x08\x00\x00\x00\x00\x01") == 0xF7FE
    assert checksum(b"\x08\x00\x00\x00\x00\x01\xff") == 0xF8FD


def test_registry_exports_real_measurements_and_recent_loss():
    registry = ProbeRegistry()
    peer = NodeTarget(name='node-"b', address="10.0.0.2")

    registry.record(peer, 10.0)
    registry.record(peer, 14.0)
    registry.record(peer, None)

    metrics = registry.render("node-a")
    assert 'Content-Type' not in metrics
    assert 'crosslayer_network_rtt_ms{source_node="node-a",target_node="node-\\"b"} 14.000000' in metrics
    assert 'crosslayer_network_loss_percent{source_node="node-a",target_node="node-\\"b"} 33.333333' in metrics
    assert 'crosslayer_network_jitter_ms{source_node="node-a",target_node="node-\\"b"} 0.250000' in metrics
    assert 'crosslayer_network_probe_success{source_node="node-a",target_node="node-\\"b"} 0' in metrics


def test_registry_omits_rtt_and_jitter_before_successful_samples():
    registry = ProbeRegistry()
    peer = NodeTarget(name="node-b", address="10.0.0.2")

    registry.record(peer, None)

    metrics = registry.render("node-a")
    assert "crosslayer_network_rtt_ms{" not in metrics
    assert "crosslayer_network_jitter_ms{" not in metrics
    assert 'crosslayer_network_loss_percent{source_node="node-a",target_node="node-b"} 100.000000' in metrics


def test_metrics_endpoint_uses_prometheus_text_content_type():
    handler = type(
        "TestMetricsHandler",
        (MetricsHandler,),
        {"registry": ProbeRegistry(), "source_node": "node-a"},
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever)
    thread.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    try:
        connection.request("GET", "/metrics")
        response = connection.getresponse()
        assert response.status == 200
        assert response.getheader("Content-Type") == "text/plain; version=0.0.4; charset=utf-8"
        assert b"# TYPE crosslayer_network_rtt_ms gauge" in response.read()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
