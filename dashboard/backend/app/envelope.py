from datetime import datetime, timezone
from typing import Any, Literal

Source = Literal["prometheus", "kubernetes", "derived", "none"]
ValueKind = Literal["measured", "derived", "predicted", "simulated", "unavailable"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def envelope(
    *,
    source: Source,
    value_kind: ValueKind,
    data: Any,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "value_kind": value_kind,
        "as_of": utc_now(),
        "error": error,
        "data": data,
    }


def unavailable(source: Source, error: str, data: Any = None) -> dict[str, Any]:
    return envelope(source=source, value_kind="unavailable", data=data, error=error)
