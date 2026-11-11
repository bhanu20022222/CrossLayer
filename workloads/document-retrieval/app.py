"""
CrossLayer - Document Retrieval Service
Research workload for network-aware pod migration experiments.
"""

import os
import time
import json
import uuid
import socket
import logging
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST
)

# ── Configuration ──────────────────────────────────────────────
SERVICE_NAME = os.getenv("SERVICE_NAME", "document-retrieval")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")
POD_NAME = os.getenv("POD_NAME", "unknown")
NODE_NAME = os.getenv("NODE_NAME", "unknown")
POD_IP = os.getenv("POD_IP", "unknown")
NAMESPACE = os.getenv("POD_NAMESPACE", "unknown")

# ── Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","service":"' + SERVICE_NAME + '","pod":"' + POD_NAME + '","node":"' + NODE_NAME + '","msg":"%(message)s"}'
)
logger = logging.getLogger(__name__)

# ── Prometheus Metrics ─────────────────────────────────────────
REQUEST_COUNT = Counter(
    'crosslayer_request_total',
    'Total requests',
    ['service', 'method', 'endpoint', 'status', 'node']
)
REQUEST_LATENCY = Histogram(
    'crosslayer_request_duration_seconds',
    'Request latency in seconds',
    ['service', 'method', 'endpoint', 'node'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)
ACTIVE_REQUESTS = Gauge(
    'crosslayer_active_requests',
    'Currently active requests',
    ['service', 'node']
)

# ── Sample Documents ───────────────────────────────────────────
DOCUMENTS = {
    "DOC-001": {"id": "DOC-001", "title": "Kubernetes Scheduling Architecture",    "category": "infrastructure", "size_kb": 245},
    "DOC-002": {"id": "DOC-002", "title": "Network-Aware Workload Placement",      "category": "research",        "size_kb": 189},
    "DOC-003": {"id": "DOC-003", "title": "Cross-Layer Optimisation Techniques",    "category": "research",        "size_kb": 312},
    "DOC-004": {"id": "DOC-004", "title": "Container Migration Strategies",         "category": "infrastructure", "size_kb": 156},
    "DOC-005": {"id": "DOC-005", "title": "Digital Twin for Cloud Systems",         "category": "research",        "size_kb": 278},
    "DOC-006": {"id": "DOC-006", "title": "eBPF-Based Network Observability",      "category": "networking",      "size_kb": 198},
    "DOC-007": {"id": "DOC-007", "title": "ML-Enhanced Resource Management",       "category": "ml",             "size_kb": 334},
    "DOC-008": {"id": "DOC-008", "title": "Edge Computing Workload Distribution",  "category": "edge",           "size_kb": 221},
}

# ── Flask App ──────────────────────────────────────────────────
app = Flask(__name__)

def measure(endpoint):
    """Decorator to measure request latency and count."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            ACTIVE_REQUESTS.labels(service=SERVICE_NAME, node=NODE_NAME).inc()
            start = time.perf_counter()
            try:
                result = f(*args, **kwargs)
                status = result[1] if isinstance(result, tuple) else 200
                REQUEST_COUNT.labels(
                    service=SERVICE_NAME, method=request.method,
                    endpoint=endpoint, status=status, node=NODE_NAME
                ).inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(
                    service=SERVICE_NAME, method=request.method,
                    endpoint=endpoint, status=500, node=NODE_NAME
                ).inc()
                raise e
            finally:
                duration = time.perf_counter() - start
                REQUEST_LATENCY.labels(
                    service=SERVICE_NAME, method=request.method,
                    endpoint=endpoint, node=NODE_NAME
                ).observe(duration)
                ACTIVE_REQUESTS.labels(service=SERVICE_NAME, node=NODE_NAME).dec()
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator


# ── Health & Readiness ─────────────────────────────────────────
@app.route('/health')
@measure('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

@app.route('/ready')
@measure('/ready')
def ready():
    return jsonify({
        "status": "ready",
        "service": SERVICE_NAME,
        "pod": POD_NAME,
        "node": NODE_NAME,
        "pod_ip": POD_IP,
        "namespace": NAMESPACE
    })


# ── Document API ───────────────────────────────────────────────
@app.route('/api/documents', methods=['GET'])
@measure('/api/documents')
def list_documents():
    category = request.args.get('category')
    docs = list(DOCUMENTS.values())
    if category:
        docs = [d for d in docs if d['category'] == category]
    return jsonify({
        "documents": docs,
        "count": len(docs),
        "served_by": {"pod": POD_NAME, "node": NODE_NAME}
    })

@app.route('/api/documents/<doc_id>', methods=['GET'])
@measure('/api/documents/:id')
def get_document(doc_id):
    doc = DOCUMENTS.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found", "id": doc_id}), 404
    return jsonify({
        "document": doc,
        "request_id": str(uuid.uuid4()),
        "served_by": {"pod": POD_NAME, "node": NODE_NAME},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


# ── Placement Info (for CrossLayer research) ───────────────────
@app.route('/api/placement', methods=['GET'])
@measure('/api/placement')
def placement_info():
    return jsonify({
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "pod": POD_NAME,
        "node": NODE_NAME,
        "pod_ip": POD_IP,
        "namespace": NAMESPACE,
        "hostname": socket.gethostname(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


# ── Prometheus Metrics Endpoint ────────────────────────────────
@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


# ── Main ───────────────────────────────────────────────────────
if __name__ == '__main__':
    logger.info(f"Starting {SERVICE_NAME} v{SERVICE_VERSION} on node={NODE_NAME} pod={POD_NAME}")
    app.run(host='0.0.0.0', port=8080)
