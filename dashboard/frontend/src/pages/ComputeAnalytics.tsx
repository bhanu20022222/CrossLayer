import { PageHeader } from "../components/PageHeader";
import { TimeSeriesChart } from "../components/TimeSeriesChart";
import { usePoll } from "../hooks/usePoll";
import type { Series } from "../api/types";

export function ComputeAnalytics() {
  const cpu = usePoll<{ range: string; series: Series[] }>("/api/v1/metrics/cpu");
  const mem = usePoll<{ range: string; series: Series[] }>("/api/v1/metrics/memory");
  return (
    <>
      <PageHeader
        title="CPU and Memory Analytics"
        summary="cAdvisor series from Prometheus for namespace crosslayer-workloads. Empty charts mean scrape failure or no matching metrics, not invented zeros."
        payload={cpu.data ?? mem.data}
        loadError={cpu.loadError ?? mem.loadError}
      />
      <div className="grid charts">
        <div className="panel">
          <h3>Pod CPU (cores)</h3>
          <TimeSeriesChart
            series={cpu.data?.data.series ?? []}
            yLabel="rate(container_cpu_usage_seconds_total[5m])"
            emptyHint="Prometheus did not return CPU series for CrossLayer workload containers."
          />
        </div>
        <div className="panel">
          <h3>Pod memory working set (bytes)</h3>
          <TimeSeriesChart
            series={mem.data?.data.series ?? []}
            yLabel="container_memory_working_set_bytes"
            emptyHint="Prometheus did not return memory series for CrossLayer workload containers."
          />
        </div>
      </div>
    </>
  );
}
