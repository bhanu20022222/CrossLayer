"""PromQL used by the dashboard. Results are never filled in if Prometheus is empty."""

import re

WORKLOAD_NS = 'namespace="crosslayer-workloads"'
CONTAINER = 'container!="", image!=""'
PHYSICAL_INTERFACE = (
    'device=~"^(eno[0-9]+|ens[0-9]+|enp[0-9a-z.]+|eth[0-9]+)$"'
)


def cpu_by_pod() -> str:
    return f"""
sum by (pod, node) (
  rate(container_cpu_usage_seconds_total{{{WORKLOAD_NS}, {CONTAINER}}}[5m])
)
""".strip()


def memory_by_pod() -> str:
    return f"""
sum by (pod, node) (
  container_memory_working_set_bytes{{{WORKLOAD_NS}, {CONTAINER}}}
)
""".strip()


def net_rx_by_pod() -> str:
    return f"""
sum by (pod, node) (
  rate(container_network_receive_bytes_total{{{WORKLOAD_NS}}}[5m])
)
""".strip()


def net_tx_by_pod() -> str:
    return f"""
sum by (pod, node) (
  rate(container_network_transmit_bytes_total{{{WORKLOAD_NS}}}[5m])
)
""".strip()


def _node_network_rate(metric: str) -> str:
    return f"""
(
  sum by (instance, device) (
    rate({metric}{{{PHYSICAL_INTERFACE}}}[5m])
  )
)
and on (instance, device)
(node_network_up{{{PHYSICAL_INTERFACE}}} == 1)
""".strip()


def node_network_receive_bytes_rate() -> str:
    return _node_network_rate("node_network_receive_bytes_total")


def node_network_transmit_bytes_rate() -> str:
    return _node_network_rate("node_network_transmit_bytes_total")


def _node_network_mbps(metric: str) -> str:
    return f"(8e-6 * ({_node_network_rate(metric)}))"


def node_network_receive_mbps() -> str:
    return _node_network_mbps("node_network_receive_bytes_total")


def node_network_transmit_mbps() -> str:
    return _node_network_mbps("node_network_transmit_bytes_total")


def node_network_receive_packets_rate() -> str:
    return _node_network_rate("node_network_receive_packets_total")


def node_network_transmit_packets_rate() -> str:
    return _node_network_rate("node_network_transmit_packets_total")


def node_network_receive_errors_rate() -> str:
    return _node_network_rate("node_network_receive_errs_total")


def node_network_transmit_errors_rate() -> str:
    return _node_network_rate("node_network_transmit_errs_total")


def node_network_receive_drops_rate() -> str:
    return _node_network_rate("node_network_receive_drop_total")


def node_network_transmit_drops_rate() -> str:
    return _node_network_rate("node_network_transmit_drop_total")


def _node_network_utilization(direction: str) -> str:
    metric = f"node_network_{direction}_bytes_total"
    return f"""
(
  100 *
  sum by (instance, device) (
    rate({metric}{{{PHYSICAL_INTERFACE}}}[5m])
  )
  / on (instance, device)
  (node_network_speed_bytes{{{PHYSICAL_INTERFACE}}} > 0)
)
and on (instance, device)
(node_network_up{{{PHYSICAL_INTERFACE}}} == 1)
""".strip()


def node_network_receive_utilization() -> str:
    return _node_network_utilization("receive")


def node_network_transmit_utilization() -> str:
    return _node_network_utilization("transmit")


def node_network_interface_up() -> str:
    return f"node_network_up{{{PHYSICAL_INTERFACE}}}"


def node_network_interface_speed() -> str:
    return f"node_network_speed_bytes{{{PHYSICAL_INTERFACE}}}"


def node_network_probe_rtt() -> str:
    return "crosslayer_network_rtt_ms"


def node_network_probe_rtt_p50() -> str:
    return "quantile_over_time(0.50, crosslayer_network_rtt_ms[5m])"


def node_network_probe_rtt_p95() -> str:
    return "quantile_over_time(0.95, crosslayer_network_rtt_ms[5m])"


def node_network_probe_rtt_p99() -> str:
    return "quantile_over_time(0.99, crosslayer_network_rtt_ms[5m])"


def node_network_probe_jitter() -> str:
    return "crosslayer_network_jitter_ms"


def node_network_probe_loss() -> str:
    return "crosslayer_network_loss_percent"


def node_network_probe_targets() -> str:
    return 'up{namespace="crosslayer-system",service="crosslayer-network-prober-v2"}'


def affinity_probe_rtt_p95() -> str:
    return """
quantile_over_time(
  0.95,
  crosslayer_network_rtt_ms{namespace="crosslayer-system"}[5m]
)
and on (pod)
(up{namespace="crosslayer-system",service="crosslayer-network-prober-v2"} == 1)
""".strip()


def affinity_probe_jitter() -> str:
    return """
crosslayer_network_jitter_ms{namespace="crosslayer-system"}
and on (pod)
(up{namespace="crosslayer-system",service="crosslayer-network-prober-v2"} == 1)
""".strip()


def affinity_probe_loss() -> str:
    return """
crosslayer_network_loss_percent{namespace="crosslayer-system"}
and on (pod)
(up{namespace="crosslayer-system",service="crosslayer-network-prober-v2"} == 1)
""".strip()


def _namespace_regex(namespaces: tuple[str, ...]) -> str:
    return "|".join(
        re.escape(namespace).replace(r"\-", "-") for namespace in namespaces
    )


def affinity_downstream_rate(namespaces: tuple[str, ...]) -> str:
    namespace_regex = _namespace_regex(namespaces)
    return """
sum by (namespace, service, dst_service, pod, node) (
  rate(crosslayer_downstream_request_total{
    namespace=~"%s"
  }[5m])
)
""".strip() % namespace_regex


def affinity_service_request_rate(namespaces: tuple[str, ...]) -> str:
    namespace_regex = _namespace_regex(namespaces)
    return """
sum by (namespace, service, pod, node) (
  rate(crosslayer_request_total{
    namespace=~"%s"
  }[5m])
)
""".strip() % namespace_regex


def node_tcp_retransmit_rate() -> str:
    return """
sum by (instance) (
  rate(node_netstat_Tcp_RetransSegs[5m])
)
""".strip()


def node_cpu_idle_ratio() -> str:
    return """
1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))
""".strip()


def up_targets() -> str:
    return "up"


def app_request_rate() -> str:
    return """
sum by (service, node) (rate(crosslayer_request_total[5m]))
""".strip()


def app_latency_p95() -> str:
    return """
histogram_quantile(
  0.95,
  sum by (le, service, node) (rate(crosslayer_request_duration_seconds_bucket[5m]))
)
""".strip()


def downstream_rate() -> str:
    return """
sum by (service, dst_service) (rate(crosslayer_downstream_request_total[5m]))
""".strip()


def downstream_p95() -> str:
    return """
histogram_quantile(
  0.95,
  sum by (le, service, dst_service) (rate(crosslayer_downstream_request_duration_seconds_bucket[5m]))
)
""".strip()


def experiment_request_rate() -> str:
    return """
sum by (service, node) (
  rate(crosslayer_request_total{service=~"experiment-(api|worker|store)"}[5m])
)
""".strip()


def experiment_latency_p95() -> str:
    return """
histogram_quantile(
  0.95,
  sum by (le, service, node) (
    rate(crosslayer_request_duration_seconds_bucket{service=~"experiment-(api|worker|store)"}[5m])
  )
)
""".strip()


def experiment_downstream_rate() -> str:
    return """
sum by (service, dst_service) (
  rate(crosslayer_downstream_request_total{service=~"experiment-(api|worker|store)"}[5m])
)
""".strip()


def experiment_downstream_latency_p95() -> str:
    return """
histogram_quantile(
  0.95,
  sum by (le, service, dst_service) (
    rate(crosslayer_downstream_request_duration_seconds_bucket{service=~"experiment-(api|worker|store)"}[5m])
  )
)
""".strip()


ENVOY_SERVICE = 'envoy_service=~".+"'


def envoy_downstream_request_rate() -> str:
    return f"""
sum by (envoy_service) (
  rate(envoy_http_downstream_rq_total{{{ENVOY_SERVICE}}}[5m])
)
""".strip()


def _envoy_downstream_latency(quantile: float) -> str:
    return f"""
histogram_quantile(
  {quantile},
  sum by (le, envoy_service) (
    rate(envoy_http_downstream_rq_time_bucket{{{ENVOY_SERVICE}}}[5m])
  )
)
""".strip()


def envoy_downstream_latency_p50() -> str:
    return _envoy_downstream_latency(0.50)


def envoy_downstream_latency_p95() -> str:
    return _envoy_downstream_latency(0.95)


def envoy_downstream_latency_p99() -> str:
    return _envoy_downstream_latency(0.99)


def envoy_downstream_4xx_rate() -> str:
    return f"""
sum by (envoy_service) (
  rate(envoy_http_downstream_rq_xx{{{ENVOY_SERVICE}, envoy_response_code_class="4"}}[5m])
)
""".strip()


def envoy_downstream_5xx_rate() -> str:
    return f"""
sum by (envoy_service) (
  rate(envoy_http_downstream_rq_xx{{{ENVOY_SERVICE}, envoy_response_code_class="5"}}[5m])
)
""".strip()


def envoy_downstream_connections_active() -> str:
    return f"""
sum by (envoy_service) (
  envoy_http_downstream_cx_active{{{ENVOY_SERVICE}}}
)
""".strip()


def envoy_downstream_receive_bytes_rate() -> str:
    return f"""
sum by (envoy_service) (
  rate(envoy_http_downstream_cx_rx_bytes_total{{{ENVOY_SERVICE}}}[5m])
)
""".strip()


def envoy_downstream_transmit_bytes_rate() -> str:
    return f"""
sum by (envoy_service) (
  rate(envoy_http_downstream_cx_tx_bytes_total{{{ENVOY_SERVICE}}}[5m])
)
""".strip()


def envoy_upstream_request_rate() -> str:
    return f"""
sum by (envoy_service, envoy_cluster_name) (
  rate(envoy_cluster_upstream_rq_total{{{ENVOY_SERVICE}}}[5m])
)
""".strip()


def envoy_upstream_latency_p95() -> str:
    return f"""
histogram_quantile(
  0.95,
  sum by (le, envoy_service, envoy_cluster_name) (
    rate(envoy_cluster_upstream_rq_time_bucket{{{ENVOY_SERVICE}}}[5m])
  )
)
""".strip()


def envoy_upstream_connections_active() -> str:
    return f"""
sum by (envoy_service, envoy_cluster_name) (
  envoy_cluster_upstream_cx_active{{{ENVOY_SERVICE}}}
)
""".strip()


def envoy_upstream_connection_failures_rate() -> str:
    return f"""
sum by (envoy_service, envoy_cluster_name) (
  rate(envoy_cluster_upstream_cx_connect_fail{{{ENVOY_SERVICE}}}[5m])
)
""".strip()


def envoy_scrape_up() -> str:
    return 'up{envoy_service=~".+"}'
