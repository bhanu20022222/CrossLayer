import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/EmptyState";
import { usePoll } from "../hooks/usePoll";
import type {
  AffinityCandidate,
  NetworkAffinityData,
  PodAffinityRecommendation,
} from "../api/types";

function scoreText(score: number | null) {
  return score == null ? "Unavailable" : `${score.toFixed(1)} / 100`;
}

function linkEvidence(observed: Record<string, number>) {
  const labels: Record<string, string> = {
    latency_p95_ms: "RTT p95",
    loss_percent: "Packet loss",
    jitter_ms: "Jitter",
    congestion_percent: "Max endpoint utilization",
  };
  return Object.entries(observed)
    .map(([key, value]) => `${labels[key] ?? key}: ${value.toFixed(3)}`)
    .join("\n");
}

function candidateExplanation(candidate: AffinityCandidate) {
  const localAssumption = candidate.local_path_assumptions
    ? `${candidate.local_path_assumptions} co-located peer path(s) use a topology assumption, not a probe`
    : null;
  const coverage =
    candidate.score == null
      ? "Insufficient measured link data"
      : `${candidate.traffic_coverage_percent.toFixed(0)}% traffic coverage; ${candidate.feature_coverage_percent.toFixed(0)}% measured-feature coverage`;
  return [
    candidate.is_current ? "Current placement" : null,
    !candidate.ready ? "Node is not Ready" : null,
    candidate.ready && !candidate.schedulable ? "Node is unschedulable" : null,
    coverage,
    localAssumption,
  ]
    .filter(Boolean)
    .join("; ");
}

function adviceText(recommendation: PodAffinityRecommendation) {
  if (recommendation.advice === "consider_network_candidate") {
    return `Network-only candidate: ${recommendation.best_alternative_node} improves affinity by ${recommendation.improvement_points?.toFixed(1)} points. This is not a migration command.`;
  }
  if (recommendation.advice === "keep_current") {
    return "No alternative clears the measured improvement and coverage thresholds; keep the current placement in this network-only comparison.";
  }
  return "Not enough measured dependency or link data to compare the current placement safely.";
}

function ScoreCell({
  score,
  coverage,
  title,
}: {
  score: number | null;
  coverage?: number;
  title?: string;
}) {
  if (score == null) {
    return <td className="affinity-empty" title="No measured link data">—</td>;
  }
  const opacity = 0.15 + (Math.max(0, Math.min(100, score)) / 100) * 0.7;
  return (
    <td
      className="affinity-score"
      title={title}
      style={{ backgroundColor: `rgba(61, 154, 138, ${opacity})` }}
    >
      <strong>{score.toFixed(1)}</strong>
      {coverage != null ? <small>{coverage.toFixed(0)}% data</small> : null}
    </td>
  );
}

function Recommendation({ item }: { item: PodAffinityRecommendation }) {
  return (
    <section className="panel affinity-recommendation">
      <div className="affinity-recommendation-head">
        <div>
          <h3>{item.service}</h3>
          <p>
            {item.namespace} · {item.pod}
          </p>
        </div>
        <span className={`badge ${item.advice === "consider_network_candidate" ? "derived" : ""}`}>
          {item.advice.replace(/_/g, " ")}
        </span>
      </div>
      <p className="empty">
        Current node: <strong>{item.current_node}</strong>. {adviceText(item)}
      </p>
      <div className="affinity-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Candidate node</th>
              <th>Affinity</th>
              <th>Traffic covered</th>
              <th>Link-feature coverage</th>
              <th>Assessment</th>
            </tr>
          </thead>
          <tbody>
            {item.candidates.map((candidate) => (
              <tr key={candidate.node}>
                <td>{candidate.rank ?? "—"}</td>
                <td>
                  {candidate.node}
                  {candidate.is_current ? " (current)" : ""}
                </td>
                <td>{scoreText(candidate.score)}</td>
                <td>{candidate.traffic_coverage_percent.toFixed(0)}%</td>
                <td>{candidate.feature_coverage_percent.toFixed(0)}%</td>
                <td>{candidateExplanation(candidate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function NetworkAffinity() {
  const { data, loadError } = usePoll<NetworkAffinityData>(
    "/api/v1/affinity/network",
    30000,
  );
  const result = data?.data;
  const links = new Map(
    (result?.node_links ?? []).map((link) => [`${link.source}|${link.target}`, link]),
  );

  return (
    <>
      <PageHeader
        title="Network Affinity Generator"
        summary="Explainable, traffic-aware affinity scores from live node probes, physical-interface utilization, Kubernetes endpoints, and measured service calls. Recommendations are advisory; no placement changes are made."
        payload={data}
        loadError={loadError}
      />
      {result?.note ? <p className="empty">{result.note}</p> : null}
      {result?.partial_errors.map((error) => (
        <p className="error" key={error}>
          Partial Kubernetes telemetry: {error}
        </p>
      ))}

      <div className="grid kpis">
        <div className="panel kpi">
          <div className="value">{result?.nodes.length ?? "—"}</div>
          <div className="hint">Measured cluster nodes</div>
        </div>
        <div className="panel kpi">
          <div className="value">
            {result ? `${result.probe_targets_up}/${result.probe_targets_total}` : "—"}
          </div>
          <div className="hint">Active network-probe targets</div>
        </div>
        <div className="panel kpi">
          <div className="value">{result?.node_links.length ?? "—"}</div>
          <div className="hint">Directed links with measured features</div>
        </div>
        <div className="panel kpi">
          <div className="value">{result?.recommendations.length ?? "—"}</div>
          <div className="hint">Workloads with measured dependencies</div>
        </div>
      </div>

      <section className="panel">
        <h3>Directed node-to-node affinity matrix</h3>
        {!result || result.nodes.length === 0 ? (
          <EmptyState
            title="No node data"
            detail="Kubernetes node inventory is unavailable; affinity scores cannot be produced."
          />
        ) : (
          <div className="affinity-table-wrap">
            <table className="affinity-matrix">
              <thead>
                <tr>
                  <th>Source → target</th>
                  {result.nodes.map((node) => (
                    <th key={node.name}>{node.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.nodes.map((source) => (
                  <tr key={source.name}>
                    <th scope="row">{source.name}</th>
                    {result.nodes.map((target) => {
                      const link = links.get(`${source.name}|${target.name}`);
                      if (source.name === target.name) {
                        return (
                          <td className="affinity-empty" key={target.name} title="Same-node placement">
                            Local
                          </td>
                        );
                      }
                      return (
                        <ScoreCell
                          key={target.name}
                          score={link?.score ?? null}
                          coverage={link?.coverage_percent}
                          title={link ? linkEvidence(link.observed) : "No measured link data"}
                        />
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="hint">
          Scores are directed. Cell values show affinity / 100; data coverage is the share of
          model feature weight supported by measurements. “Local” is same-node placement, not a
          probe result.
        </p>
      </section>

      <section className="panel">
        <h3>Measured communication edges</h3>
        {result?.communications.length ? (
          <div className="affinity-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Source service</th>
                  <th>Destination service</th>
                  <th>Measured request rate</th>
                </tr>
              </thead>
              <tbody>
                {result.communications.map((edge) => (
                  <tr key={`${edge.source}-${edge.destination}`}>
                    <td>{edge.source}</td>
                    <td>{edge.destination}</td>
                    <td>{edge.requests_per_second.toFixed(4)} requests/s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No measured service dependencies"
            detail="Communication affinity is not inferred from pod proximity. It appears when Prometheus observes crosslayer_downstream_request_total."
          />
        )}
      </section>

      <section className="panel">
        <h3>Scoring method · {result?.algorithm.version ?? "NAG-v1"}</h3>
        <p className="empty">
          For each directed link, normalize measured latency and jitter with exponential decay;
          normalize packet loss and endpoint utilization to 0–1. Combine available link
          components with the configured weights, renormalized over observed components. Rank a
          workload’s destinations by the request-rate-weighted mean affinity to its measured
          communicating endpoints.
        </p>
        <p className="hint">
          Same-node peers receive a topology-only score of 100 because no inter-node hop is
          required, but contribute 0% measured link-feature coverage. This assumption alone
          cannot pass the recommendation coverage threshold.
        </p>
        <div className="affinity-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Component</th>
                <th>Initial weight</th>
                <th>Normalization / status</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(result?.algorithm.feature_weights ?? {}).map(([name, weight]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td>{(weight * 100).toFixed(0)}%</td>
                  <td>{result?.algorithm.normalization[name] ?? "Not measured in this version"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {result?.algorithm.advisory_policy ? (
          <p className="hint">
            A network-only candidate is surfaced only with at least{" "}
            {result.algorithm.advisory_policy.minimum_traffic_coverage_percent}% traffic coverage,
            at least {result.algorithm.advisory_policy.minimum_feature_coverage_percent}% link-feature
            coverage, and a {result.algorithm.advisory_policy.minimum_improvement_points}-point
            improvement over the current placement. These are initial research thresholds, not
            validated production policy.
          </p>
        ) : null}
        <p className="hint">
          Bandwidth capacity and migration cost are not measured here. Graph clustering,
          workload-adaptive weights, prediction, and TOPSIS are later research comparisons; this
          baseline does not claim trained or predicted results.
        </p>
      </section>

      <h2>Pod-to-destination recommendations</h2>
      {result?.recommendations.length ? (
        <div className="affinity-recommendations">
          {result.recommendations.map((recommendation) => (
            <Recommendation
              key={`${recommendation.namespace}/${recommendation.pod}`}
              item={recommendation}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No placement recommendations yet"
          detail="The generator needs measured service dependencies and matching ready Kubernetes Service endpoints. It never substitutes illustrative or synthetic traffic."
        />
      )}
    </>
  );
}
