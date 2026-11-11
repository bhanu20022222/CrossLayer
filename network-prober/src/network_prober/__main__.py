import json
import logging
import os
import signal
import socket
import ssl
import struct
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

LOGGER = logging.getLogger("crosslayer.network_prober")
SERVICE_ACCOUNT = "/var/run/secrets/kubernetes.io/serviceaccount"
PROBE_INTERVAL_SECONDS = float(os.getenv("PROBE_INTERVAL_SECONDS", "10"))
PROBE_TIMEOUT_SECONDS = float(os.getenv("PROBE_TIMEOUT_SECONDS", "1"))
TARGET_REFRESH_SECONDS = float(os.getenv("TARGET_REFRESH_SECONDS", "60"))
HISTORY_SIZE = 60


@dataclass(frozen=True)
class NodeTarget:
    name: str
    address: str


@dataclass
class TargetState:
    observations: Deque[Optional[float]] = field(
        default_factory=lambda: deque(maxlen=HISTORY_SIZE)
    )
    last_rtt_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    previous_rtt_ms: Optional[float] = None
    last_probe_success: bool = False


def parse_node_targets(payload: Dict[str, Any], source_node: str) -> List[NodeTarget]:
    targets = []
    for item in payload.get("items", []):
        metadata = item.get("metadata") or {}
        name = metadata.get("name")
        if not name or name == source_node:
            continue
        addresses = (item.get("status") or {}).get("addresses") or []
        internal = next(
            (address.get("address") for address in addresses if address.get("type") == "InternalIP"),
            None,
        )
        if internal:
            targets.append(NodeTarget(name=name, address=internal))
    return sorted(targets, key=lambda target: target.name)


def checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def icmp_echo_rtt_ms(
    target: str,
    timeout_seconds: float,
    sequence: int,
    socket_factory=socket.socket,
) -> Optional[float]:
    identifier = os.getpid() & 0xFFFF
    payload = struct.pack("!d", time.monotonic())
    header = struct.pack("!BBHHH", 8, 0, 0, identifier, sequence)
    packet_checksum = checksum(header + payload)
    packet = struct.pack("!BBHHH", 8, 0, packet_checksum, identifier, sequence) + payload
    started = time.monotonic()
    deadline = started + timeout_seconds

    with socket_factory(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP) as sock:
        sock.settimeout(timeout_seconds)
        sock.sendto(packet, (target, 1))
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            sock.settimeout(remaining)
            try:
                response, address = sock.recvfrom(65535)
            except socket.timeout:
                return None
            if address[0] != target or len(response) < 20:
                continue
            ip_header_length = (response[0] & 0x0F) * 4
            if len(response) < ip_header_length + 8:
                continue
            kind, code, _, reply_identifier, reply_sequence = struct.unpack(
                "!BBHHH", response[ip_header_length : ip_header_length + 8]
            )
            if kind == 0 and code == 0 and reply_identifier == identifier and reply_sequence == sequence:
                return (time.monotonic() - started) * 1000


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class ProbeRegistry:
    def __init__(self) -> None:
        self._states: Dict[Tuple[str, str], TargetState] = {}
        self._lock = threading.Lock()

    def record(self, target: NodeTarget, rtt_ms: Optional[float]) -> None:
        with self._lock:
            state = self._states.setdefault(
                (target.name, target.address), TargetState()
            )
            state.observations.append(rtt_ms)
            state.last_probe_success = rtt_ms is not None
            if rtt_ms is not None:
                if state.previous_rtt_ms is not None:
                    difference = abs(rtt_ms - state.previous_rtt_ms)
                    if state.jitter_ms is None:
                        state.jitter_ms = difference / 16
                    else:
                        state.jitter_ms += (difference - state.jitter_ms) / 16
                state.previous_rtt_ms = rtt_ms
                state.last_rtt_ms = rtt_ms

    def prune(self, targets: Set[Tuple[str, str]]) -> None:
        with self._lock:
            self._states = {
                key: value for key, value in self._states.items() if key in targets
            }

    def render(self, source_node: str) -> str:
        with self._lock:
            states = list(self._states.items())

        lines = [
            "# HELP crosslayer_network_rtt_ms Last successful ICMP round-trip time in milliseconds",
            "# TYPE crosslayer_network_rtt_ms gauge",
            "# HELP crosslayer_network_loss_percent ICMP packet loss percent over the recent probe window",
            "# TYPE crosslayer_network_loss_percent gauge",
            "# HELP crosslayer_network_jitter_ms RFC 3550 smoothed variation between successful RTT samples in milliseconds",
            "# TYPE crosslayer_network_jitter_ms gauge",
            "# HELP crosslayer_network_probe_success Whether the most recent ICMP probe succeeded",
            "# TYPE crosslayer_network_probe_success gauge",
        ]
        for (target_node, _), state in sorted(states):
            labels = (
                f'source_node="{_escape_label(source_node)}",'
                f'target_node="{_escape_label(target_node)}"'
            )
            observations = list(state.observations)
            loss_percent = (
                100 * sum(value is None for value in observations) / len(observations)
                if observations
                else 0
            )
            lines.append(f"crosslayer_network_loss_percent{{{labels}}} {loss_percent:.6f}")
            lines.append(
                f"crosslayer_network_probe_success{{{labels}}} "
                f"{1 if state.last_probe_success else 0}"
            )
            if state.last_rtt_ms is not None:
                lines.append(f"crosslayer_network_rtt_ms{{{labels}}} {state.last_rtt_ms:.6f}")
            if state.jitter_ms is not None:
                lines.append(f"crosslayer_network_jitter_ms{{{labels}}} {state.jitter_ms:.6f}")
        return "\n".join(lines) + "\n"


def _load_node_targets(source_node: str) -> List[NodeTarget]:
    host = os.environ["KUBERNETES_SERVICE_HOST"]
    port = os.getenv("KUBERNETES_SERVICE_PORT_HTTPS", "443")
    token_path = os.path.join(SERVICE_ACCOUNT, "token")
    ca_path = os.path.join(SERVICE_ACCOUNT, "ca.crt")
    with open(token_path, encoding="utf-8") as token_file:
        token = token_file.read().strip()
    context = ssl.create_default_context(cafile=ca_path)
    request = urllib.request.Request(
        f"https://{host}:{port}/api/v1/nodes",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=5, context=context) as response:
        payload = json.load(response)
    return parse_node_targets(payload, source_node)


class MetricsHandler(BaseHTTPRequestHandler):
    registry: ProbeRegistry
    source_node: str

    def do_GET(self) -> None:
        if self.path != "/metrics":
            self.send_error(404)
            return
        body = self.registry.render(self.source_node).encode("utf-8")
        self.send_response(200)
        self.send_header(
            "Content-Type", "text/plain; version=0.0.4; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)


def _probe_loop(
    source_node: str,
    registry: ProbeRegistry,
    stop: threading.Event,
) -> None:
    sequence = 0
    next_refresh = 0.0
    targets: List[NodeTarget] = []
    while not stop.is_set():
        now = time.monotonic()
        if now >= next_refresh:
            try:
                targets = _load_node_targets(source_node)
                registry.prune(
                    {(target.name, target.address) for target in targets}
                )
                next_refresh = now + TARGET_REFRESH_SECONDS
                if not targets:
                    LOGGER.warning("No peer Kubernetes Nodes with InternalIP were found")
            except (OSError, KeyError, ValueError, urllib.error.URLError):
                LOGGER.exception("Could not refresh peer Nodes from the Kubernetes API")
                next_refresh = now + TARGET_REFRESH_SECONDS

        for target in targets:
            if stop.is_set():
                break
            sequence = (sequence + 1) & 0xFFFF
            try:
                rtt_ms = icmp_echo_rtt_ms(
                    target.address, PROBE_TIMEOUT_SECONDS, sequence
                )
            except OSError:
                LOGGER.exception("ICMP probe to node %s failed", target.name)
                rtt_ms = None
            registry.record(target, rtt_ms)
        stop.wait(PROBE_INTERVAL_SECONDS)


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    source_node = os.environ["NODE_NAME"]
    port = int(os.getenv("METRICS_PORT", "9116"))
    registry = ProbeRegistry()
    stop = threading.Event()
    worker = threading.Thread(
        target=_probe_loop,
        args=(source_node, registry, stop),
        daemon=True,
        name="icmp-probe-loop",
    )
    worker.start()

    handler = type(
        "NodeMetricsHandler",
        (MetricsHandler,),
        {"registry": registry, "source_node": source_node},
    )
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    server.daemon_threads = True
    LOGGER.info("Serving Prometheus metrics on port %d for node %s", port, source_node)
    try:
        server.serve_forever()
    finally:
        stop.set()
        server.server_close()
        worker.join(timeout=2)


if __name__ == "__main__":
    main()
