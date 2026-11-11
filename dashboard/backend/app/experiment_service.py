import hashlib
import json
import os
import socket
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Tuple
from urllib.error import URLError
from urllib.parse import urlsplit


SERVICE_NAME = os.getenv("SERVICE_NAME", "experiment-api")
SERVICE_ROLE = os.getenv("SERVICE_ROLE", "api")
NODE_NAME = os.getenv("NODE_NAME", socket.gethostname())
WORKER_URL = os.getenv(
    "WORKER_URL",
    "http://experiment-worker.crosslayer-experiments.svc.cluster.local.:8080/process",
)
STORE_URL = os.getenv(
    "STORE_URL",
    "http://experiment-store.crosslayer-experiments.svc.cluster.local.:8080/read",
)
HASH_ITERATIONS = 50000
HISTOGRAM_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)


def _escape_label(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class Histogram:
    def __init__(self):
        self.count = 0
        self.total = 0.0
        self.buckets = dict((bound, 0) for bound in HISTOGRAM_BUCKETS)
        self.infinity_count = 0

    def observe(self, value):
        self.count += 1
        self.total += value
        self.infinity_count += 1
        for bound in HISTOGRAM_BUCKETS:
            if value <= bound:
                self.buckets[bound] += 1


class ExperimentMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._requests: Dict[str, int] = {}
        self._request_histogram = Histogram()
        self._downstream: Dict[str, int] = {}
        self._downstream_histograms: Dict[Tuple[str, str], Histogram] = {}

    def record_request(self, status_code, duration_seconds):
        with self._lock:
            self._requests[str(status_code)] = self._requests.get(str(status_code), 0) + 1
            self._request_histogram.observe(duration_seconds)

    def record_downstream(self, destination, duration_seconds):
        with self._lock:
            self._downstream[destination] = self._downstream.get(destination, 0) + 1
            histogram = self._downstream_histograms.setdefault(
                (SERVICE_NAME, destination), Histogram()
            )
            histogram.observe(duration_seconds)

    def render(self):
        service = _escape_label(SERVICE_NAME)
        node = _escape_label(NODE_NAME)
        lines = [
            "# HELP crosslayer_request_total Total experiment service HTTP requests",
            "# TYPE crosslayer_request_total counter",
            "# HELP crosslayer_request_duration_seconds Experiment service request duration",
            "# TYPE crosslayer_request_duration_seconds histogram",
            "# HELP crosslayer_downstream_request_total Calls from one experiment service to another",
            "# TYPE crosslayer_downstream_request_total counter",
            "# HELP crosslayer_downstream_request_duration_seconds Experiment downstream call duration",
            "# TYPE crosslayer_downstream_request_duration_seconds histogram",
        ]
        with self._lock:
            for status, count in sorted(self._requests.items()):
                lines.append(
                    'crosslayer_request_total{service="%s",node="%s",status="%s"} %d'
                    % (service, node, status, count)
                )
            self._append_histogram(
                lines,
                "crosslayer_request_duration_seconds",
                'service="%s",node="%s"' % (service, node),
                self._request_histogram,
            )
            for destination, count in sorted(self._downstream.items()):
                lines.append(
                    'crosslayer_downstream_request_total{service="%s",dst_service="%s",node="%s"} %d'
                    % (service, _escape_label(destination), node, count)
                )
            for (source, destination), histogram in sorted(
                self._downstream_histograms.items()
            ):
                labels = 'service="%s",dst_service="%s",node="%s"' % (
                    _escape_label(source),
                    _escape_label(destination),
                    node,
                )
                self._append_histogram(
                    lines,
                    "crosslayer_downstream_request_duration_seconds",
                    labels,
                    histogram,
                )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _append_histogram(lines, metric, labels, histogram):
        for bound in HISTOGRAM_BUCKETS:
            lines.append(
                '%s_bucket{%s,le="%s"} %d'
                % (metric, labels, bound, histogram.buckets[bound])
            )
        lines.append(
            '%s_bucket{%s,le="+Inf"} %d'
            % (metric, labels, histogram.infinity_count)
        )
        lines.append("%s_sum{%s} %s" % (metric, labels, histogram.total))
        lines.append("%s_count{%s} %d" % (metric, labels, histogram.count))


METRICS = ExperimentMetrics()


def _get_json(url, destination):
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            body = response.read()
    except (URLError, OSError):
        METRICS.record_downstream(destination, time.monotonic() - started)
        raise
    duration = time.monotonic() - started
    METRICS.record_downstream(destination, duration)
    return body, duration


def _compute_and_call_store():
    digest = b"crosslayer-experiment"
    for iteration in range(HASH_ITERATIONS):
        digest = hashlib.sha256(digest + str(iteration).encode("ascii")).digest()
    body, _ = _get_json(STORE_URL, "experiment-store")
    return {"worker": "experiment-worker", "digest": digest.hex()[:16], "store": json.loads(body)}


class ExperimentHandler(BaseHTTPRequestHandler):
    def _respond(self, status, body, content_type):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/metrics":
            self._respond(
                200,
                METRICS.render(),
                "text/plain; version=0.0.4; charset=utf-8",
            )
            return
        if path == "/health":
            self._respond(200, '{"status":"ok"}', "application/json")
            return

        started = time.monotonic()
        status = 200
        try:
            if SERVICE_ROLE == "api" and path == "/work":
                body, _ = _get_json(WORKER_URL, "experiment-worker")
                result = {"service": SERVICE_NAME, "chain": json.loads(body)}
            elif SERVICE_ROLE == "worker" and path == "/process":
                result = _compute_and_call_store()
            elif SERVICE_ROLE == "store" and path == "/read":
                result = {"service": SERVICE_NAME, "record": "measured"}
            else:
                status = 404
                result = {"error": "not found"}
        except (URLError, OSError, ValueError, json.JSONDecodeError) as exc:
            status = 503
            result = {"error": str(exc)}
        METRICS.record_request(status, time.monotonic() - started)
        self._respond(
            status,
            json.dumps(result, separators=(",", ":")),
            "application/json",
        )

    def log_message(self, format, *args):
        return


def main():
    port = int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), ExperimentHandler)
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
