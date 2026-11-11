import asyncio
from unittest.mock import AsyncMock

import pytest

from app.clients.prometheus import prometheus_client
from app.config import settings
from app.experiment_load import (
    ExperimentLoadManager,
    LoadTargetUnavailable,
    experiment_load_manager,
)
from auth_test_utils import authenticated_test_client

client = authenticated_test_client()


def test_experiment_load_limits_are_enforced_without_starting_traffic(monkeypatch):
    start = AsyncMock(
        side_effect=lambda requests_per_second, duration_seconds: {
            "state": "running",
            "requests_per_second": requests_per_second,
            "duration_seconds": duration_seconds,
        }
    )
    monkeypatch.setattr(
        experiment_load_manager,
        "start",
        start,
    )

    accepted = client.post(
        "/api/v1/experiments/load/start",
        json={"requests_per_second": 30, "duration_seconds": 300},
    )
    over_rate = client.post(
        "/api/v1/experiments/load/start",
        json={"requests_per_second": 31, "duration_seconds": 300},
    )
    over_duration = client.post(
        "/api/v1/experiments/load/start",
        json={"requests_per_second": 30, "duration_seconds": 301},
    )

    assert accepted.status_code == 202
    assert accepted.json()["data"]["requests_per_second"] == 30
    assert over_rate.status_code == 422
    assert over_duration.status_code == 422


def test_experiment_load_rejects_a_second_active_run(monkeypatch):
    from app.experiment_load import LoadAlreadyRunning

    monkeypatch.setattr(
        experiment_load_manager,
        "start",
        AsyncMock(side_effect=(
            LoadAlreadyRunning("An experiment load run is already active.")
        )),
    )

    response = client.post(
        "/api/v1/experiments/load/start",
        json={"requests_per_second": 30, "duration_seconds": 300},
    )

    assert response.status_code == 409
    assert "already active" in response.json()["detail"]


def test_experiment_load_stop_is_explicit(monkeypatch):
    monkeypatch.setattr(
        experiment_load_manager,
        "stop",
        AsyncMock(return_value={"state": "stopped", "attempted": 4}),
    )

    response = client.post("/api/v1/experiments/load/stop")

    assert response.status_code == 200
    assert response.json()["data"] == {"state": "stopped", "attempted": 4}


def test_experiment_service_exports_request_and_dependency_histograms():
    from app.experiment_service import ExperimentMetrics

    metrics = ExperimentMetrics()
    metrics.record_request(200, 0.02)
    metrics.record_downstream("experiment-worker", 0.03)
    exposition = metrics.render()

    assert 'crosslayer_request_total{service="experiment-api"' in exposition
    assert 'crosslayer_request_duration_seconds_bucket{service="experiment-api"' in exposition
    assert 'le="0.025"} 1' in exposition
    assert (
        'crosslayer_downstream_request_total{service="experiment-api",'
        'dst_service="experiment-worker"'
    ) in exposition
    assert "crosslayer_downstream_request_duration_seconds_count" in exposition


def test_experiment_load_health_check_failure_never_starts_a_run(monkeypatch):
    manager = ExperimentLoadManager()
    monkeypatch.setattr(settings, "experiment_target_url", "http://127.0.0.1:1/work")

    with pytest.raises(LoadTargetUnavailable):
        asyncio.run(manager.start(1, 1))

    assert manager.status()["state"] == "idle"


def test_experiment_metrics_returns_measured_series(monkeypatch):
    monkeypatch.setattr(
        prometheus_client,
        "range_window",
        AsyncMock(return_value=(1000, 1900, "15s")),
    )
    monkeypatch.setattr(
        prometheus_client,
        "query_range",
        AsyncMock(
            side_effect=[
                [
                    {
                        "metric": {"service": "experiment-api", "node": "worker-a"},
                        "values": [[1000, "2"]],
                    }
                ],
                [
                    {
                        "metric": {"service": "experiment-api", "node": "worker-a"},
                        "values": [[1000, "0.03"]],
                    }
                ],
                [
                    {
                        "metric": {
                            "service": "experiment-api",
                            "dst_service": "experiment-worker",
                        },
                        "values": [[1000, "2"]],
                    }
                ],
                [
                    {
                        "metric": {
                            "service": "experiment-api",
                            "dst_service": "experiment-worker",
                        },
                        "values": [[1000, "0.02"]],
                    }
                ],
            ]
        ),
    )

    response = client.get("/api/v1/experiments/metrics?range=15m")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["request_rate"][0]["labels"] == {
        "service": "experiment-api",
        "node": "worker-a",
    }
    assert data["downstream_rate"] == [
        {
            "name": "experiment-api|experiment-worker",
            "labels": {
                "service": "experiment-api",
                "dst_service": "experiment-worker",
            },
            "points": [{"t": 1000.0, "v": 2.0}],
        }
    ]


def test_experiment_metrics_preserves_empty_series_when_prometheus_is_unavailable(
    monkeypatch,
):
    from app.clients.prometheus import PrometheusError

    monkeypatch.setattr(
        prometheus_client,
        "range_window",
        AsyncMock(side_effect=PrometheusError("Prometheus unavailable")),
    )

    response = client.get("/api/v1/experiments/metrics?range=15m")

    assert response.status_code == 200
    assert response.json()["value_kind"] == "unavailable"
    assert response.json()["data"]["step"] is None
    assert response.json()["data"]["request_rate"] == []
    assert response.json()["data"]["downstream_rate"] == []
