from __future__ import annotations

from datetime import datetime, timezone

from perf_agent.models.observation import Observation
from perf_agent.utils.ids import new_id


def parse_text(text: str, source: str, action_id: str | None = None) -> list[Observation]:
    timestamp = datetime.now(timezone.utc)
    observations: list[Observation] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        separator = "=" if "=" in line else ":"
        if separator not in line:
            continue
        key, value = [piece.strip() for piece in line.split(separator, 1)]
        metric = _normalize_metric_name(key)
        coerced = _coerce_value(value)
        category, unit, scope, normalized_value = _describe_metric(metric, coerced, source)
        observations.append(
            Observation(
                id=new_id("obs"),
                source=source,
                category=category,
                metric=metric,
                value=coerced,
                unit=unit,
                normalized_value=normalized_value,
                scope=scope,
                timestamp=timestamp,
                labels={"action_id": action_id or "", "source": source},
                raw_excerpt=line,
            )
        )
    return observations


def _coerce_value(value: str) -> float | int | str:
    cleaned = value.replace(",", "")
    try:
        if "." in cleaned:
            return float(cleaned)
        return int(cleaned)
    except ValueError:
        return value


def _normalize_metric_name(name: str) -> str:
    normalized = name.strip().lower().replace(" ", "_").replace("-", "_")
    mapping = {
        "avg_cpu": "cpu_utilization_pct",
        "iowait": "iowait_pct",
        "disk_util": "disk_util_pct",
        "cswch_per_sec": "context_switches_per_sec",
    }
    return mapping.get(normalized, normalized)


def _describe_metric(
    metric: str,
    value: float | int | str,
    source: str,
) -> tuple[str, str | None, str, float | None]:
    unit: str | None = None
    normalized_value: float | None = None
    scope = "system" if source in {"mpstat", "iostat", "flamegraph"} else "process"

    if metric in {"cpu_utilization_pct"}:
        unit = "percent"
        normalized_value = _to_ratio(value)
        return "cpu", unit, scope, normalized_value
    if metric in {"iowait_pct", "wait_pct", "disk_util_pct", "read_wait_pct"}:
        unit = "percent"
        normalized_value = _to_ratio(value)
        return "io", unit, scope, normalized_value
    if metric in {"context_switches_per_sec", "run_queue"}:
        unit = "per_sec" if metric == "context_switches_per_sec" else None
        return "scheduler", unit, scope, None
    if metric in {"lock_wait_pct"}:
        unit = "percent"
        normalized_value = _to_ratio(value)
        return "lock", unit, scope, normalized_value
    if metric in {"rss_mb", "major_faults"}:
        unit = "mb" if metric == "rss_mb" else "count"
        return "memory", unit, scope, None
    if metric in {"await_ms"}:
        return "io", "ms", scope, None
    if metric in {"read_mb_s", "write_mb_s"}:
        return "io", "mb_per_sec", scope, None
    return "system", unit, scope, None


def _to_ratio(value: float | int | str) -> float | None:
    if isinstance(value, (int, float)):
        return round(float(value) / 100.0, 4)
    return None
