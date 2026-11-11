import time
from datetime import timedelta


def parse_range(raw: str) -> tuple[float, float, str]:
    """Return unix start, end, and Prometheus step for a dashboard range token."""
    mapping = {
        "15m": (timedelta(minutes=15), "15s"),
        "1h": (timedelta(hours=1), "30s"),
        "6h": (timedelta(hours=6), "2m"),
        "24h": (timedelta(hours=24), "5m"),
    }
    if raw not in mapping:
        raise ValueError("range must be one of 15m, 1h, 6h, 24h")
    delta, step = mapping[raw]
    end = time.time()
    start = end - delta.total_seconds()
    return start, end, step


def matrix_to_series(result: list[dict], name_from: tuple[str, ...]) -> list[dict]:
    series = []
    for item in result:
        metric = item.get("metric") or {}
        label = "|".join(str(metric.get(k) or "") for k in name_from if metric.get(k))
        points = []
        for pair in item.get("values") or []:
            if len(pair) != 2:
                continue
            ts, value = pair
            if value in (None, "NaN", "+Inf", "-Inf"):
                continue
            points.append({"t": float(ts), "v": float(value)})
        series.append({"name": label or "series", "labels": metric, "points": points})
    return series


def vector_to_rows(result: list[dict], fields: tuple[str, ...]) -> list[dict]:
    rows = []
    for item in result:
        metric = item.get("metric") or {}
        value = item.get("value")
        if not value or len(value) != 2 or value[1] in (None, "NaN", "+Inf", "-Inf"):
            numeric = None
        else:
            numeric = float(value[1])
        row = {k: metric.get(k) for k in fields}
        row["value"] = numeric
        rows.append(row)
    return rows
