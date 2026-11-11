from typing import Any
import math

import httpx

from app.config import settings
from app.timeutil import parse_range


class PrometheusError(Exception):
    pass


class PrometheusClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self.base_url = (base_url or settings.prometheus_url).rstrip("/")
        self.timeout = timeout or settings.prometheus_timeout_seconds

    async def check(self) -> tuple[bool, str | None]:
        try:
            payload = await self._get("/api/v1/query", params={"query": "up"})
        except PrometheusError as exc:
            return False, str(exc)
        if payload.get("status") != "success":
            return False, f"prometheus status={payload.get('status')}"
        return True, None

    async def query(self, expr: str) -> list[dict[str, Any]]:
        payload = await self._get("/api/v1/query", params={"query": expr})
        self._assert_success(payload)
        return payload.get("data", {}).get("result") or []

    async def query_range(self, expr: str, start: float, end: float, step: str) -> list[dict[str, Any]]:
        payload = await self._get(
            "/api/v1/query_range",
            params={"query": expr, "start": start, "end": end, "step": step},
        )
        self._assert_success(payload)
        return payload.get("data", {}).get("result") or []

    async def range_window(self, range_token: str) -> tuple[float, float, str]:
        local_start, local_end, step = parse_range(range_token)
        samples = await self.query("vector(time())")
        if len(samples) != 1:
            raise PrometheusError("Prometheus time query returned no sample")
        value = samples[0].get("value")
        try:
            end = float(value[1])
        except (TypeError, ValueError, IndexError) as exc:
            raise PrometheusError("Prometheus time query returned an invalid timestamp") from exc
        if not math.isfinite(end):
            raise PrometheusError("Prometheus time query returned a non-finite timestamp")
        return end - (local_end - local_start), end, step

    def _assert_success(self, payload: dict[str, Any]) -> None:
        if payload.get("status") != "success":
            raise PrometheusError(payload.get("error") or "prometheus query failed")

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise PrometheusError(f"prometheus unreachable at {self.base_url}: {exc}") from exc


prometheus_client = PrometheusClient()
