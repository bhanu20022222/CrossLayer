import { PageHeader } from "../components/PageHeader";
import { TimeSeriesChart } from "../components/TimeSeriesChart";
import { usePoll } from "../hooks/usePoll";
import type { Series } from "../api/types";

export function ApplicationTraffic() {
  const { data, loadError } = usePoll<{
    range: string;
    request_rate: Series[];
    latency_p95: Series[];
    note: string;
  }>("/api/v1/application/traffic");
  return (
    <>
      <PageHeader
        title="Application Latency and Throughput"
        summary="crosslayer_request_total and request duration histograms from workload /metrics. Requires a working ServiceMonitor."
        payload={data}
        loadError={loadError}
      />
      {data?.data.note ? <p className="empty">{data.data.note}</p> : null}
      <div className="grid charts">
        <div className="panel">
          <h3>Request rate</h3>
          <TimeSeriesChart
            series={data?.data.request_rate ?? []}
            yLabel="rate(crosslayer_request_total[5m])"
            emptyHint="No crosslayer_request_total series. The Flask /metrics path may not be scraped yet."
          />
        </div>
        <div className="panel">
          <h3>P95 latency (seconds)</h3>
          <TimeSeriesChart
            series={data?.data.latency_p95 ?? []}
            yLabel="histogram_quantile(0.95, crosslayer_request_duration_seconds_bucket)"
            emptyHint="No latency histogram in Prometheus."
          />
        </div>
      </div>
    </>
  );
}
