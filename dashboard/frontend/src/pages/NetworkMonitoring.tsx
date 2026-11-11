import { PageHeader } from "../components/PageHeader";
import { TimeSeriesChart } from "../components/TimeSeriesChart";
import { usePoll } from "../hooks/usePoll";
import type { EnvoyData, NetworkData, Series } from "../api/types";

export function NetworkMonitoring() {
  const net = usePoll<NetworkData>("/api/v1/metrics/network");
  const envoy = usePoll<EnvoyData>("/api/v1/metrics/envoy");
  const data = net.data?.data;
  const envoyData = envoy.data?.data;
  const probeTargets = data?.probe_targets ?? [];
  return (
    <>
      <PageHeader
        title="Network Monitoring"
        summary="Measured Pod and physical-interface traffic, plus Envoy HTTP request metrics when traffic traverses the instrumented Services."
        payload={net.data}
        loadError={net.loadError}
      />
      {data?.note ? <p className="empty">{data.note}</p> : null}
      {envoyData?.note ? <p className="empty">{envoyData.note}</p> : null}
      <div className="panel">
        <h3>Physical node interfaces</h3>
        <InterfaceTable interfaces={data?.interfaces ?? []} />
      </div>
      <div className="grid charts">
        <NetworkChart
          title="Pod receive throughput (bytes/s)"
          series={data?.receive ?? []}
          yLabel="rate(container_network_receive_bytes_total[5m])"
          emptyHint="No Pod receive throughput series from Prometheus."
        />
        <NetworkChart
          title="Pod transmit throughput (bytes/s)"
          series={data?.transmit ?? []}
          yLabel="rate(container_network_transmit_bytes_total[5m])"
          emptyHint="No Pod transmit throughput series from Prometheus."
        />
        <NetworkChart
          title="Node receive throughput (Mbps)"
          series={data?.node_receive_mbps ?? []}
          yLabel="rate(node_network_receive_bytes_total[5m]) * 8 / 1,000,000"
          emptyHint="No physical-interface receive counters from Prometheus."
        />
        <NetworkChart
          title="Node transmit throughput (Mbps)"
          series={data?.node_transmit_mbps ?? []}
          yLabel="rate(node_network_transmit_bytes_total[5m]) * 8 / 1,000,000"
          emptyHint="No physical-interface transmit counters from Prometheus."
        />
        <NetworkChart
          title="Receive link utilization (%)"
          series={data?.node_receive_utilization ?? []}
          yLabel="receive bytes/s ÷ reported link bytes/s × 100"
          emptyHint="No valid up-interface speed is available to calculate receive utilization."
        />
        <NetworkChart
          title="Transmit link utilization (%)"
          series={data?.node_transmit_utilization ?? []}
          yLabel="transmit bytes/s ÷ reported link bytes/s × 100"
          emptyHint="No valid up-interface speed is available to calculate transmit utilization."
        />
        <NetworkChart
          title="Node receive packet rate (packets/s)"
          series={data?.node_receive_packets ?? []}
          yLabel="rate(node_network_receive_packets_total[5m])"
          emptyHint="No physical-interface receive packet counters from Prometheus."
        />
        <NetworkChart
          title="Node transmit packet rate (packets/s)"
          series={data?.node_transmit_packets ?? []}
          yLabel="rate(node_network_transmit_packets_total[5m])"
          emptyHint="No physical-interface transmit packet counters from Prometheus."
        />
        <NetworkChart
          title="Node receive drops (drops/s)"
          series={data?.node_receive_drops ?? []}
          yLabel="rate(node_network_receive_drop_total[5m])"
          emptyHint="No physical-interface receive drop counters from Prometheus."
        />
        <NetworkChart
          title="Node transmit drops (drops/s)"
          series={data?.node_transmit_drops ?? []}
          yLabel="rate(node_network_transmit_drop_total[5m])"
          emptyHint="No physical-interface transmit drop counters from Prometheus."
        />
        <NetworkChart
          title="Node receive errors (errors/s)"
          series={data?.node_receive_errors ?? []}
          yLabel="rate(node_network_receive_errs_total[5m])"
          emptyHint="No physical-interface receive error counters from Prometheus."
        />
        <NetworkChart
          title="Node transmit errors (errors/s)"
          series={data?.node_transmit_errors ?? []}
          yLabel="rate(node_network_transmit_errs_total[5m])"
          emptyHint="No physical-interface transmit error counters from Prometheus."
        />
        <NetworkChart
          title="Node TCP retransmits (segments/s)"
          series={data?.node_tcp_retransmits ?? []}
          yLabel="rate(node_netstat_Tcp_RetransSegs[5m])"
          emptyHint="No TCP retransmission counters from Prometheus."
        />
        <NetworkChart
          title="Inter-node RTT p50 (ms)"
          series={data?.inter_node_rtt_p50_ms ?? []}
          yLabel="quantile_over_time(0.50, crosslayer_network_rtt_ms[5m])"
          emptyHint="No successful measured RTT samples are available yet."
        />
        <NetworkChart
          title="Inter-node RTT p95 (ms)"
          series={data?.inter_node_rtt_p95_ms ?? []}
          yLabel="quantile_over_time(0.95, crosslayer_network_rtt_ms[5m])"
          emptyHint="No successful measured RTT samples are available yet."
        />
        <NetworkChart
          title="Inter-node RTT p99 (ms)"
          series={data?.inter_node_rtt_p99_ms ?? []}
          yLabel="quantile_over_time(0.99, crosslayer_network_rtt_ms[5m])"
          emptyHint="No successful measured RTT samples are available yet."
        />
        <NetworkChart
          title="Inter-node jitter (ms)"
          series={data?.inter_node_jitter_ms ?? []}
          yLabel="crosslayer_network_jitter_ms (RFC 3550 smoothed RTT variation)"
          emptyHint="Jitter requires successive successful measured RTT samples."
        />
        <NetworkChart
          title="Inter-node packet loss (%)"
          series={data?.inter_node_loss_percent ?? []}
          yLabel="crosslayer_network_loss_percent"
          emptyHint="No packet-loss window has been reported by the active node probes yet."
        />
        <div className="panel">
          <h3>Inter-node probe status</h3>
          {probeTargets.length ? (
            <p className="empty">
              Prometheus reports {probeTargets.filter((target) => target.up).length} of{" "}
              {probeTargets.length} active probe targets up. RTT, jitter, and loss are measured
              between Kubernetes nodes; successful samples appear after probes run.
            </p>
          ) : (
            <p className="empty">
              No active probe targets are being scraped. Check the network-prober DaemonSet and
              ServiceMonitor in the cluster.
            </p>
          )}
        </div>
      </div>
      <h2>Envoy service telemetry</h2>
      <p className="empty">
        {envoy.loadError
          ? `Unable to load Envoy telemetry: ${envoy.loadError}`
          : envoyData?.target_status.length
            ? `Prometheus reports ${envoyData.target_status.filter((target) => target.up).length} of ${envoyData.target_status.length} Envoy scrape targets up.`
            : "No Envoy scrape targets are visible yet. Request charts populate only from real HTTP traffic."}
      </p>
      <div className="grid charts">
        <NetworkChart
          title="Service request rate (requests/s)"
          series={envoyData?.request_rate ?? []}
          yLabel="rate(envoy_http_downstream_rq_total[5m])"
          emptyHint="No Envoy request counter samples are available yet."
        />
        <NetworkChart
          title="Service response latency p50 (s)"
          series={envoyData?.latency_p50_seconds ?? []}
          yLabel="histogram_quantile(0.50, envoy_http_downstream_rq_time_bucket)"
          emptyHint="No request latency observations yet."
        />
        <NetworkChart
          title="Service response latency p95 (s)"
          series={envoyData?.latency_p95_seconds ?? []}
          yLabel="histogram_quantile(0.95, envoy_http_downstream_rq_time_bucket)"
          emptyHint="No request latency observations yet."
        />
        <NetworkChart
          title="Service response latency p99 (s)"
          series={envoyData?.latency_p99_seconds ?? []}
          yLabel="histogram_quantile(0.99, envoy_http_downstream_rq_time_bucket)"
          emptyHint="No request latency observations yet."
        />
        <NetworkChart
          title="HTTP 4xx responses (responses/s)"
          series={envoyData?.response_4xx_rate ?? []}
          yLabel={'rate(envoy_http_downstream_rq_xx{envoy_response_code_class="4"}[5m])'}
          emptyHint="No HTTP 4xx response samples yet."
        />
        <NetworkChart
          title="HTTP 5xx responses (responses/s)"
          series={envoyData?.response_5xx_rate ?? []}
          yLabel={'rate(envoy_http_downstream_rq_xx{envoy_response_code_class="5"}[5m])'}
          emptyHint="No HTTP 5xx response samples yet."
        />
        <NetworkChart
          title="Active client connections"
          series={envoyData?.downstream_connections_active ?? []}
          yLabel="envoy_http_downstream_cx_active"
          emptyHint="No Envoy downstream connection samples yet."
        />
        <NetworkChart
          title="Client-to-service bytes (bytes/s)"
          series={envoyData?.downstream_receive_bytes_rate ?? []}
          yLabel="rate(envoy_http_downstream_cx_rx_bytes_total[5m])"
          emptyHint="No Envoy downstream receive samples yet."
        />
        <NetworkChart
          title="Service-to-client bytes (bytes/s)"
          series={envoyData?.downstream_transmit_bytes_rate ?? []}
          yLabel="rate(envoy_http_downstream_cx_tx_bytes_total[5m])"
          emptyHint="No Envoy downstream transmit samples yet."
        />
        <NetworkChart
          title="Proxy-to-workload request rate (requests/s)"
          series={envoyData?.upstream_request_rate ?? []}
          yLabel="rate(envoy_cluster_upstream_rq_total[5m])"
          emptyHint="No Envoy upstream request samples yet."
        />
        <NetworkChart
          title="Proxy-to-workload latency p95 (s)"
          series={envoyData?.upstream_latency_p95_seconds ?? []}
          yLabel="histogram_quantile(0.95, envoy_cluster_upstream_rq_time_bucket)"
          emptyHint="No Envoy upstream latency observations yet."
        />
        <NetworkChart
          title="Active proxy-to-workload connections"
          series={envoyData?.upstream_connections_active ?? []}
          yLabel="envoy_cluster_upstream_cx_active"
          emptyHint="No Envoy upstream connection samples yet."
        />
        <NetworkChart
          title="Upstream connection failures (failures/s)"
          series={envoyData?.upstream_connection_failures_rate ?? []}
          yLabel="rate(envoy_cluster_upstream_cx_connect_fail[5m])"
          emptyHint="No Envoy upstream connection failure samples yet."
        />
      </div>
    </>
  );
}

function NetworkChart({
  title,
  series,
  yLabel,
  emptyHint,
}: {
  title: string;
  series: Series[];
  yLabel: string;
  emptyHint: string;
}) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      <TimeSeriesChart series={series} yLabel={yLabel} emptyHint={emptyHint} />
    </div>
  );
}

function InterfaceTable({ interfaces }: { interfaces: NetworkData["interfaces"] }) {
  if (interfaces.length === 0) {
    return <p className="empty">No physical interface inventory from Prometheus.</p>;
  }
  return (
    <table>
      <thead>
        <tr>
          <th>Node exporter</th>
          <th>Interface</th>
          <th>Link</th>
          <th>Reported capacity</th>
        </tr>
      </thead>
      <tbody>
        {interfaces.map((item) => (
          <tr key={`${item.instance}/${item.device}`}>
            <td>{item.instance}</td>
            <td>{item.device}</td>
            <td>{item.up == null ? "Unknown" : item.up ? "Up" : "Down"}</td>
            <td>
              {item.speed_bytes_per_second == null
                ? "Unavailable"
                : `${((item.speed_bytes_per_second * 8) / 1_000_000).toFixed(0)} Mbps`}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
