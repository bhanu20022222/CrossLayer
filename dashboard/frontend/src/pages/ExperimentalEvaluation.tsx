import { useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { TimeSeriesChart } from "../components/TimeSeriesChart";
import { usePoll } from "../hooks/usePoll";
import type {
  ExperimentLoadStatus,
  ExperimentMetricsData,
} from "../api/types";

type ActionResponse = {
  data?: ExperimentLoadStatus;
  detail?: string;
};

export function ExperimentalEvaluation() {
  const load = usePoll<ExperimentLoadStatus>(
    "/api/v1/experiments/load/status",
    1000,
  );
  const metrics = usePoll<ExperimentMetricsData>(
    "/api/v1/experiments/metrics",
    5000,
  );
  const [requestsPerSecond, setRequestsPerSecond] = useState(30);
  const [durationSeconds, setDurationSeconds] = useState(300);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const status = load.data?.data;
  const running = status?.state === "running";

  async function sendAction(path: string, body?: object) {
    const response = await fetch(path, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const payload = (await response.json()) as ActionResponse;
    if (!response.ok) {
      throw new Error(payload.detail ?? `HTTP ${response.status}`);
    }
  }

  async function startLoad() {
    setBusy(true);
    setActionError(null);
    try {
      await sendAction("/api/v1/experiments/load/start", {
        requests_per_second: requestsPerSecond,
        duration_seconds: durationSeconds,
      });
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Could not start the load run.");
    } finally {
      setBusy(false);
    }
  }

  async function stopLoad() {
    setBusy(true);
    setActionError(null);
    try {
      await sendAction("/api/v1/experiments/load/stop");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Could not stop the load run.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Experimental Evaluation"
        summary="Run a bounded request-rate experiment against isolated CrossLayer microservices and compare measured throughput, latency, and service dependencies."
        payload={metrics.data}
        loadError={metrics.loadError}
      />
      {metrics.data?.data.note ? <p className="empty">{metrics.data.data.note}</p> : null}
      <section className="panel" aria-labelledby="load-control-heading">
        <h3 id="load-control-heading">Controlled cluster load</h3>
        <p className="empty">
          Traffic goes only to the experiment API in the crosslayer-experiments namespace.
          Each run is capped at {status?.max_requests_per_second ?? 30} requests/second and{" "}
          {status?.max_duration_seconds ?? 300} seconds, with at most 8 concurrent requests.
          Runs do not start automatically.
        </p>
        <div className="experiment-controls">
          <label>
            Request rate: <strong>{requestsPerSecond} requests/second</strong>
            <input
              type="range"
              min={1}
              max={status?.max_requests_per_second ?? 30}
              step={1}
              value={requestsPerSecond}
              disabled={running || busy}
              onChange={(event) => setRequestsPerSecond(Number(event.target.value))}
            />
          </label>
          <label>
            Maximum run time
            <select
              value={durationSeconds}
              disabled={running || busy}
              onChange={(event) => setDurationSeconds(Number(event.target.value))}
            >
              <option value={60}>1 minute</option>
              <option value={180}>3 minutes</option>
              <option value={300}>5 minutes (maximum)</option>
            </select>
          </label>
          <div className="experiment-actions">
            <button type="button" disabled={running || busy} onClick={startLoad}>
              {busy && !running ? "Starting..." : "Start bounded run"}
            </button>
            <button type="button" disabled={!running || busy} onClick={stopLoad}>
              {busy && running ? "Stopping..." : "Stop"}
            </button>
          </div>
        </div>
        {load.loadError ? <p className="error">{load.loadError}</p> : null}
        {actionError ? <p className="error">{actionError}</p> : null}
        {status ? (
          <div className="experiment-status" aria-live="polite">
            <strong>Run status: {status.state}</strong>
            {status.run_id ? <span>Run ID: {status.run_id}</span> : null}
            {status.requests_per_second != null ? (
              <span>
                Requested: {status.requests_per_second} requests/s for{" "}
                {status.duration_seconds} seconds
              </span>
            ) : null}
            {status.elapsed_seconds != null ? (
              <span>Elapsed: {status.elapsed_seconds.toFixed(1)} seconds</span>
            ) : null}
            {status.attempted != null ? (
              <span>
                Requests: {status.succeeded ?? 0} succeeded, {status.failed ?? 0} failed,{" "}
                {status.skipped ?? 0} skipped ({status.attempted} attempted)
              </span>
            ) : null}
            {status.last_error ? <span className="error">{status.last_error}</span> : null}
            {running ? (
              <progress
                max={status.duration_seconds ?? 1}
                value={Math.min(status.elapsed_seconds ?? 0, status.duration_seconds ?? 1)}
              />
            ) : null}
          </div>
        ) : null}
      </section>

      <div className="grid charts">
        <div className="panel">
          <h3>Experiment service request rate</h3>
          <TimeSeriesChart
            series={metrics.data?.data.request_rate ?? []}
            yLabel="rate(crosslayer_request_total[5m])"
            emptyHint="No experiment-service request samples have been scraped yet."
          />
        </div>
        <div className="panel">
          <h3>Experiment service latency p95 (seconds)</h3>
          <TimeSeriesChart
            series={metrics.data?.data.latency_p95 ?? []}
            yLabel="histogram_quantile(0.95, crosslayer_request_duration_seconds_bucket)"
            emptyHint="No experiment-service latency samples have been scraped yet."
          />
        </div>
        <div className="panel">
          <h3>Service-to-service request rate</h3>
          <TimeSeriesChart
            series={metrics.data?.data.downstream_rate ?? []}
            yLabel="rate(crosslayer_downstream_request_total[5m])"
            emptyHint="Dependency edges appear after measured calls pass through the service chain."
          />
        </div>
        <div className="panel">
          <h3>Service-to-service latency p95 (seconds)</h3>
          <TimeSeriesChart
            series={metrics.data?.data.downstream_latency_p95 ?? []}
            yLabel="histogram_quantile(0.95, crosslayer_downstream_request_duration_seconds_bucket)"
            emptyHint="No measured downstream latency observations yet."
          />
        </div>
      </div>
    </>
  );
}
