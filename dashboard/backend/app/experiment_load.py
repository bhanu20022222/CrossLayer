import asyncio
import threading
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.config import settings


MAX_REQUESTS_PER_SECOND = 30
MAX_DURATION_SECONDS = 300
MAX_IN_FLIGHT_REQUESTS = 8
REQUEST_TIMEOUT_SECONDS = 1.5


class LoadAlreadyRunning(Exception):
    pass


class LoadTargetUnavailable(Exception):
    pass


class ExperimentLoadManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._current = None

    def status(self):
        with self._lock:
            run = self._current
            if run is None:
                return {
                    "state": "idle",
                    "max_requests_per_second": MAX_REQUESTS_PER_SECOND,
                    "max_duration_seconds": MAX_DURATION_SECONDS,
                }
            now = run["ended_monotonic"] or run["traffic_stopped_monotonic"]
            if now is None:
                now = time.monotonic()
            return {
                key: value
                for key, value in run.items()
                if key
                not in (
                    "stop_event",
                    "task",
                    "started_monotonic",
                    "ended_monotonic",
                    "traffic_stopped_monotonic",
                )
            } | {
                "elapsed_seconds": round(now - run["started_monotonic"], 1),
                "max_requests_per_second": MAX_REQUESTS_PER_SECOND,
                "max_duration_seconds": MAX_DURATION_SECONDS,
            }

    async def start(self, requests_per_second, duration_seconds):
        if not 1 <= requests_per_second <= MAX_REQUESTS_PER_SECOND:
            raise ValueError(
                "requests_per_second must be between 1 and %d"
                % MAX_REQUESTS_PER_SECOND
            )
        if not 1 <= duration_seconds <= MAX_DURATION_SECONDS:
            raise ValueError(
                "duration_seconds must be between 1 and %d" % MAX_DURATION_SECONDS
            )

        with self._lock:
            if self._current is not None and self._current["state"] == "running":
                raise LoadAlreadyRunning("An experiment load run is already active.")

        target = urlsplit(settings.experiment_target_url)
        health_url = urlunsplit((target.scheme, target.netloc, "/health", "", ""))
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT_SECONDS,
                trust_env=False,
            ) as client:
                response = await client.get(health_url)
                response.raise_for_status()
        except (httpx.HTTPError, ValueError) as exc:
            raise LoadTargetUnavailable(
                "The experiment service health check failed; no load was started."
            ) from exc

        with self._lock:
            if self._current is not None and self._current["state"] == "running":
                raise LoadAlreadyRunning("An experiment load run is already active.")
            started = time.monotonic()
            run = {
                "run_id": str(uuid.uuid4()),
                "state": "running",
                "requests_per_second": requests_per_second,
                "duration_seconds": duration_seconds,
                "attempted": 0,
                "succeeded": 0,
                "failed": 0,
                "skipped": 0,
                "last_error": None,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": None,
                "started_monotonic": started,
                "traffic_stopped_monotonic": None,
                "ended_monotonic": None,
                "stop_event": threading.Event(),
                "task": None,
            }
            self._current = run
            run["task"] = asyncio.create_task(self._run(run))
        return self.status()

    async def stop(self):
        with self._lock:
            run = self._current
            if run is not None and run["state"] == "running":
                run["stop_event"].set()
                task = run["task"]
            else:
                task = None
        if task is not None:
            await task
        return self.status()

    async def _send_one(self, run, client):
        try:
            response = await client.get(settings.experiment_target_url)
            if response.is_success:
                run["succeeded"] += 1
            else:
                run["failed"] += 1
                run["last_error"] = "Experiment service returned HTTP %d" % response.status_code
        except httpx.HTTPError as exc:
            run["failed"] += 1
            run["last_error"] = "%s: %s" % (type(exc).__name__, str(exc))

    async def _run(self, run):
        pending = set()
        interval = 1.0 / run["requests_per_second"]
        deadline = run["started_monotonic"] + run["duration_seconds"]
        next_slot = 0
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            trust_env=False,
        ) as client:
            while not run["stop_event"].is_set():
                now = time.monotonic()
                if now >= deadline:
                    break
                elapsed = now - run["started_monotonic"]
                slot = int(elapsed / interval)
                if slot >= next_slot:
                    missed = slot - next_slot
                    run["skipped"] += missed
                    if len(pending) < MAX_IN_FLIGHT_REQUESTS:
                        run["attempted"] += 1
                        task = asyncio.create_task(self._send_one(run, client))
                        pending.add(task)
                        task.add_done_callback(pending.discard)
                    else:
                        run["skipped"] += 1
                    next_slot = slot + 1
                sleep_until = min(
                    deadline,
                    run["started_monotonic"] + next_slot * interval,
                    now + 0.02,
                )
                await asyncio.sleep(max(0.001, sleep_until - now))
            run["traffic_stopped_monotonic"] = time.monotonic()
            if pending:
                await asyncio.gather(*pending)

        with self._lock:
            run["state"] = (
                "stopped" if run["stop_event"].is_set() else "completed"
            )
            run["ended_monotonic"] = time.monotonic()
            run["ended_at"] = datetime.now(timezone.utc).isoformat()


experiment_load_manager = ExperimentLoadManager()
