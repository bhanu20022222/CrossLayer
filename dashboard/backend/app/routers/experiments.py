import asyncio

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app import queries
from app.clients.prometheus import PrometheusError, prometheus_client
from app.envelope import envelope
from app.experiment_load import (
    MAX_DURATION_SECONDS,
    MAX_REQUESTS_PER_SECOND,
    LoadAlreadyRunning,
    LoadTargetUnavailable,
    experiment_load_manager,
)
from app.timeutil import matrix_to_series

router = APIRouter()

EXPERIMENT_RANGE_QUERIES = {
    "request_rate": (queries.experiment_request_rate(), ("service", "node")),
    "latency_p95": (queries.experiment_latency_p95(), ("service", "node")),
    "downstream_rate": (
        queries.experiment_downstream_rate(),
        ("service", "dst_service"),
    ),
    "downstream_latency_p95": (
        queries.experiment_downstream_latency_p95(),
        ("service", "dst_service"),
    ),
}


class LoadStartRequest(BaseModel):
    requests_per_second: int = Field(ge=1, le=MAX_REQUESTS_PER_SECOND)
    duration_seconds: int = Field(ge=1, le=MAX_DURATION_SECONDS)


@router.get("/experiments/metrics")
async def experiment_metrics(range: str = Query(default="15m", alias="range")):
    try:
        start, end, step = await prometheus_client.range_window(range)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PrometheusError as exc:
        return envelope(
            source="none",
            value_kind="unavailable",
            error=str(exc),
            data={
                "range": range,
                "step": None,
                **{name: [] for name in EXPERIMENT_RANGE_QUERIES},
                "note": "Experiment service metrics are unavailable from Prometheus.",
            },
        )

    try:
        results = await asyncio.gather(
            *(
                prometheus_client.query_range(expression, start, end, step)
                for expression, _ in EXPERIMENT_RANGE_QUERIES.values()
            )
        )
    except PrometheusError as exc:
        return envelope(
            source="prometheus",
            value_kind="unavailable",
            error=str(exc),
            data={
                "range": range,
                "step": step,
                **{name: [] for name in EXPERIMENT_RANGE_QUERIES},
                "note": "Experiment service metrics are unavailable from Prometheus.",
            },
        )

    return envelope(
        source="prometheus",
        value_kind="measured",
        data={
            "range": range,
            "step": step,
            **{
                name: matrix_to_series(result, labels)
                for (name, (_, labels)), result in zip(
                    EXPERIMENT_RANGE_QUERIES.items(), results
                )
            },
            "note": (
                "These are measured metrics from the isolated experiment microservices. "
                "Empty series mean no samples have been scraped yet."
            ),
        },
    )


@router.get("/experiments/load/status")
async def load_status():
    return envelope(
        source="derived",
        value_kind="derived",
        data=experiment_load_manager.status(),
    )


@router.post("/experiments/load/start", status_code=202)
async def start_load(request: LoadStartRequest):
    try:
        status = await experiment_load_manager.start(
            request.requests_per_second,
            request.duration_seconds,
        )
    except LoadAlreadyRunning as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LoadTargetUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return envelope(source="derived", value_kind="derived", data=status)


@router.post("/experiments/load/stop")
async def stop_load():
    status = await experiment_load_manager.stop()
    return envelope(source="derived", value_kind="derived", data=status)
