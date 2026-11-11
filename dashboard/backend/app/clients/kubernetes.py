from typing import Any

from app.config import settings


class KubernetesError(Exception):
    pass


class KubernetesClient:
    def __init__(self) -> None:
        self._loaded = False
        self._error: str | None = "kubernetes client not initialised"
        self._core = None

    def _ensure(self) -> None:
        if settings.kubernetes_disabled:
            self._error = "kubernetes disabled by CROSSLAYER_KUBERNETES_DISABLED"
            return
        if self._loaded:
            return
        try:
            from kubernetes import client, config
        except ImportError as exc:
            self._error = f"kubernetes package missing: {exc}"
            return
        try:
            if settings.kubeconfig:
                config.load_kube_config(config_file=settings.kubeconfig)
            else:
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config()
            self._core = client.CoreV1Api()
            self._loaded = True
            self._error = None
        except Exception as exc:  # noqa: BLE001 — surface kubeconfig problems as unavailable
            self._error = f"kubernetes API unavailable: {exc}"
            self._loaded = False

    def check(self) -> tuple[bool, str | None]:
        self._ensure()
        if not self._loaded or self._core is None:
            return False, self._error
        try:
            self._core.list_node(limit=1)
            return True, None
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def list_nodes(self) -> list[dict[str, Any]]:
        v1 = self._require()
        nodes = []
        for node in v1.list_node().items:
            ready = False
            for cond in node.status.conditions or []:
                if cond.type == "Ready":
                    ready = cond.status == "True"
            labels = node.metadata.labels or {}
            nodes.append(
                {
                    "name": node.metadata.name,
                    "ready": ready,
                    "unschedulable": bool(node.spec.unschedulable),
                    "addresses": {
                        addr.type: addr.address for addr in (node.status.addresses or [])
                    },
                    "cpu_capacity": (node.status.capacity or {}).get("cpu"),
                    "memory_capacity": (node.status.capacity or {}).get("memory"),
                    "cpu_allocatable": (node.status.allocatable or {}).get("cpu"),
                    "memory_allocatable": (node.status.allocatable or {}).get("memory"),
                    "kubelet_version": (node.status.node_info.kubelet_version if node.status.node_info else None),
                    "os_image": (node.status.node_info.os_image if node.status.node_info else None),
                    "zone": labels.get("crosslayer.io/zone"),
                    "role": _role(labels),
                }
            )
        return nodes

    def list_pods(self, namespace: str | None = None) -> list[dict[str, Any]]:
        v1 = self._require()
        if namespace:
            items = v1.list_namespaced_pod(namespace).items
        else:
            items = v1.list_pod_for_all_namespaces().items
        pods = []
        for pod in items:
            pods.append(
                {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "node": pod.spec.node_name,
                    "phase": pod.status.phase,
                    "pod_ip": pod.status.pod_ip,
                    "ready": _pod_ready(pod),
                    "restarts": _restarts(pod),
                    "labels": pod.metadata.labels or {},
                    "app": (pod.metadata.labels or {}).get("app"),
                    "project": (pod.metadata.labels or {}).get("project"),
                }
            )
        return pods

    def list_service_endpoints(self, namespace: str) -> list[dict[str, Any]]:
        v1 = self._require()
        from kubernetes.client.exceptions import ApiException
        from urllib3.exceptions import HTTPError as Urllib3HTTPError

        services = []
        try:
            endpoint_items = v1.list_namespaced_endpoints(namespace).items
        except (ApiException, Urllib3HTTPError) as exc:
            self._error = f"could not list service endpoints in {namespace}: {exc}"
            raise KubernetesError(self._error) from exc
        for endpoints in endpoint_items:
            pods = []
            for subset in endpoints.subsets or []:
                for address in subset.addresses or []:
                    pod_name = (
                        address.target_ref.name
                        if address.target_ref and address.target_ref.kind == "Pod"
                        else None
                    )
                    if address.node_name:
                        pods.append({"pod": pod_name, "node": address.node_name})
            services.append(
                {
                    "namespace": namespace,
                    "name": endpoints.metadata.name,
                    "pods": pods,
                }
            )
        return services

    def namespace_exists(self, name: str) -> bool:
        v1 = self._require()
        try:
            v1.read_namespace(name)
            return True
        except Exception:  # noqa: BLE001
            return False

    def _require(self):
        self._ensure()
        if not self._loaded or self._core is None:
            raise KubernetesError(self._error or "kubernetes API unavailable")
        return self._core


def _role(labels: dict[str, str]) -> str | None:
    if labels.get("node-role.kubernetes.io/control-plane") is not None:
        return "control-plane"
    if labels.get("node-role.kubernetes.io/master") is not None:
        return "control-plane"
    if labels.get("node-role.kubernetes.io/worker") is not None:
        return "worker"
    return labels.get("kubernetes.io/role")


def _pod_ready(pod) -> bool:
    for cond in pod.status.conditions or []:
        if cond.type == "Ready":
            return cond.status == "True"
    return False


def _restarts(pod) -> int:
    total = 0
    for status in pod.status.container_statuses or []:
        total += int(status.restart_count or 0)
    return total


kubernetes_client = KubernetesClient()
