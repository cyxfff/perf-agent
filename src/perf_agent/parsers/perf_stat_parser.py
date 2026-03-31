from __future__ import annotations

from datetime import datetime, timezone
import re
from collections import defaultdict

from perf_agent.models.observation import Observation
from perf_agent.utils.ids import new_id


PATTERNS = [
    ("task_clock_ms", "system", "ms", re.compile(r"([\d,]+(?:\.\d+)?)\s+task-clock")),
    ("cpu_utilization_pct", "cpu", "percent", re.compile(r"([\d,]+(?:\.\d+)?)%\s+CPUs utilized")),
    ("cycles", "cpu", "count", re.compile(r"([\d,]+)\s+cycles")),
    ("instructions", "cpu", "count", re.compile(r"([\d,]+)\s+instructions")),
    ("ipc", "cpu", None, re.compile(r"([\d,]+(?:\.\d+)?)\s+insn per cycle")),
    ("cache_misses", "cache", "count", re.compile(r"([\d,]+)\s+cache-misses")),
    ("branch_misses", "branch", "count", re.compile(r"([\d,]+)\s+branch-misses")),
    (
        "stalled_cycles_frontend_pct",
        "cpu",
        "percent",
        re.compile(r"([\d,]+(?:\.\d+)?)%\s+stalled-cycles-frontend"),
    ),
    (
        "stalled_cycles_backend_pct",
        "memory",
        "percent",
        re.compile(r"([\d,]+(?:\.\d+)?)%\s+stalled-cycles-backend"),
    ),
    ("lock_wait_pct", "lock", "percent", re.compile(r"lock_wait_pct=([\d,]+(?:\.\d+)?)")),
]

GENERIC_COUNTER_PATTERN = re.compile(r"^\s*([\d,]+(?:\.\d+)?)\s+([A-Za-z0-9_./:-]+)\b")
GENERIC_EVENT_MAP = {
    "task-clock": ("task_clock_ms", "system", "ms"),
    "cpu-clock": ("cpu_clock_ms", "cpu", "ms"),
    "cycles": ("cycles", "cpu", "count"),
    "slots": ("slots", "cpu", "count"),
    "instructions": ("instructions", "cpu", "count"),
    "branches": ("branches", "branch", "count"),
    "branch-misses": ("branch_misses", "branch", "count"),
    "cache-references": ("cache_references", "cache", "count"),
    "cache-misses": ("cache_misses", "cache", "count"),
    "context-switches": ("context_switches", "scheduler", "count"),
    "cpu-migrations": ("cpu_migrations", "scheduler", "count"),
    "page-faults": ("page_faults", "memory", "count"),
    "stalled-cycles-frontend": ("stalled_cycles_frontend_pct", "cpu", "percent"),
    "stalled-cycles-backend": ("stalled_cycles_backend_pct", "memory", "percent"),
    "topdown-retiring": ("topdown_retiring_pct", "cpu", "percent"),
    "topdown-bad-spec": ("topdown_bad_spec_pct", "branch", "percent"),
    "topdown-fe-bound": ("topdown_fe_bound_pct", "cpu", "percent"),
    "topdown-be-bound": ("topdown_be_bound_pct", "memory", "percent"),
    "topdown-br-mispredict": ("topdown_br_mispredict_pct", "branch", "percent"),
    "topdown-fetch-lat": ("topdown_fetch_lat_pct", "cpu", "percent"),
    "topdown-heavy-ops": ("topdown_heavy_ops_pct", "cpu", "percent"),
    "topdown-mem-bound": ("topdown_mem_bound_pct", "memory", "percent"),
    "tma_memory_bound": ("tma_memory_bound_pct", "memory", "percent"),
    "tma_fetch_latency": ("tma_fetch_latency_pct", "cpu", "percent"),
    "tma_fetch_bandwidth": ("tma_fetch_bandwidth_pct", "cpu", "percent"),
    "tma_branch_mispredicts": ("tma_branch_mispredicts_pct", "branch", "percent"),
    "tma_lock_latency": ("tma_lock_latency_pct", "lock", "percent"),
    "tma_false_sharing": ("tma_false_sharing_pct", "lock", "percent"),
    "longest_lat_cache.miss": ("llc_miss_count", "cache", "count"),
    "l2_rqsts.miss": ("l2_miss_count", "cache", "count"),
    "mem_load_completed.l1_miss_any": ("l1_miss_count", "memory", "count"),
    "mem_inst_retired.lock_loads": ("lock_loads", "lock", "count"),
}
TIMELINE_SEPARATOR = ","


def parse_text(text: str, source: str, action_id: str | None = None) -> list[Observation]:
    timestamp = datetime.now(timezone.utc)
    observations: list[Observation] = []
    seen_metrics: set[str] = set()
    timeline_buckets: dict[str, dict[str, float]] = defaultdict(dict)
    for metric, category, unit, pattern in PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        raw_value = match.group(1).replace(",", "")
        value = float(raw_value) if "." in raw_value else int(raw_value)
        observations.append(
            Observation(
                id=new_id("obs"),
                source=source,
                category=category,
                metric=metric,
                value=value,
                unit=unit,
                normalized_value=round(value / 100.0, 4) if unit == "percent" else None,
                scope="process",
                timestamp=timestamp,
                labels={"action_id": action_id or ""},
                raw_excerpt=_find_excerpt(text, pattern),
            )
        )
        seen_metrics.add(metric)
    for line in text.splitlines():
        timeline = _parse_timeline_line(line, timestamp, source, action_id)
        if timeline is not None:
            observations.append(timeline)
            time_key = timeline.labels.get("time_bucket_sec", "")
            event_name = timeline.labels.get("event_name", "")
            if time_key and event_name and isinstance(timeline.value, (int, float)):
                timeline_buckets[time_key][event_name] = timeline_buckets[time_key].get(event_name, 0.0) + float(timeline.value)
            continue
        generic_match = GENERIC_COUNTER_PATTERN.search(line)
        if not generic_match:
            continue
        raw_event = generic_match.group(2).strip()
        normalized_event = _normalize_event_name(raw_event)
        metric_def = _metric_definition(normalized_event, line)
        if metric_def is None:
            continue
        metric, category, unit = metric_def
        if metric in seen_metrics:
            continue
        raw_value = generic_match.group(1).replace(",", "")
        value = float(raw_value) if "." in raw_value else int(raw_value)
        observations.append(
            Observation(
                id=new_id("obs"),
                source=source,
                category=category,
                metric=metric,
                value=value,
                unit=unit,
                normalized_value=round(value / 100.0, 4) if unit == "percent" else None,
                scope="process",
                timestamp=timestamp,
                labels={"action_id": action_id or "", "event_name": normalized_event, "raw_event_name": raw_event},
                raw_excerpt=line.strip(),
            )
        )
        seen_metrics.add(metric)
    observations.extend(_derive_timeline_metrics(timeline_buckets, timestamp, source, action_id))
    return observations


def _find_excerpt(text: str, pattern: re.Pattern[str]) -> str | None:
    for line in text.splitlines():
        if pattern.search(line):
            return line.strip()
    return None


def _parse_timeline_line(
    line: str,
    timestamp: datetime,
    source: str,
    action_id: str | None,
) -> Observation | None:
    if TIMELINE_SEPARATOR not in line:
        return None
    columns = [column.strip() for column in line.split(TIMELINE_SEPARATOR)]
    if len(columns) < 4:
        return None
    try:
        time_bucket = float(columns[0])
    except ValueError:
        return None
    raw_value = columns[1].replace(",", "")
    event_name = columns[3] if columns[2] == "" else columns[2]
    event_name = _normalize_event_name(event_name.strip())
    metric_def = _metric_definition(event_name, line)
    if metric_def is None:
        return None
    if raw_value in {"<not counted>", "<not supported>", ""}:
        return None
    metric, category, unit = metric_def
    value = _timeline_value(raw_value, columns, event_name, unit)
    return Observation(
        id=new_id("obs"),
        source=source,
        category=category,
        metric=metric,
        value=value,
        unit=unit,
        normalized_value=round(value / 100.0, 4) if unit == "percent" else None,
        scope="process",
        timestamp=timestamp,
        labels={
            "action_id": action_id or "",
            "event_name": event_name,
            "series_type": "timeline",
            "time_bucket_sec": f"{time_bucket:.3f}",
        },
        raw_excerpt=line.strip(),
    )


def _derive_timeline_metrics(
    timeline_buckets: dict[str, dict[str, float]],
    timestamp: datetime,
    source: str,
    action_id: str | None,
) -> list[Observation]:
    derived: list[Observation] = []
    for time_key, metrics in timeline_buckets.items():
        instructions = metrics.get("instructions")
        cycles = metrics.get("cycles")
        if instructions is not None and cycles not in {None, 0.0}:
            ipc = instructions / cycles
            derived.append(
                Observation(
                    id=new_id("obs"),
                    source=source,
                    category="cpu",
                    metric="ipc",
                    value=round(ipc, 4),
                    unit=None,
                    normalized_value=round(ipc, 4),
                    scope="process",
                    timestamp=timestamp,
                    labels={
                        "action_id": action_id or "",
                        "series_type": "timeline",
                        "time_bucket_sec": time_key,
                        "derived_from": "instructions,cycles",
                    },
                    evidence_level="derived",
                    raw_excerpt=f"time={time_key}s ipc={ipc:.4f}",
                )
            )
    return derived


def _normalize_event_name(raw_event: str) -> str:
    candidate = raw_event.strip()
    if candidate in GENERIC_EVENT_MAP:
        return candidate
    if candidate.endswith("/") and "/" in candidate:
        core = candidate.strip("/").split("/")[-1]
        if core in GENERIC_EVENT_MAP:
            return core
    for event_name in GENERIC_EVENT_MAP:
        if candidate.endswith(event_name):
            return event_name
        if candidate.endswith(f"/{event_name}/"):
            return event_name
    return candidate


def _timeline_value(raw_value: str, columns: list[str], event_name: str, unit: str | None) -> float | int:
    if unit == "percent":
        for candidate in reversed(columns):
            numeric = candidate.strip()
            if not numeric:
                continue
            try:
                return float(numeric)
            except ValueError:
                continue
    return float(raw_value) if "." in raw_value else int(raw_value)


def _metric_definition(event_name: str, line: str) -> tuple[str, str, str | None] | None:
    if event_name in GENERIC_EVENT_MAP:
        return GENERIC_EVENT_MAP[event_name]

    metric = _sanitize_metric_name(event_name)
    if not metric:
        return None
    return (metric, _infer_category(event_name), _infer_unit(event_name, line))


def _sanitize_metric_name(event_name: str) -> str:
    metric = event_name.strip().strip("/").lower()
    if "/" in metric:
        metric = metric.split("/")[-1]
    metric = re.sub(r"[^a-z0-9]+", "_", metric).strip("_")
    if not metric:
        return ""
    if metric.startswith("topdown_") or metric.startswith("tma_"):
        return f"{metric}_pct"
    return metric


def _infer_category(event_name: str) -> str:
    lowered = event_name.lower()
    if any(token in lowered for token in ("branch", "mispredict")):
        return "branch"
    if any(token in lowered for token in ("lock", "futex", "sharing")):
        return "lock"
    if any(token in lowered for token in ("context", "migration", "sched")):
        return "scheduler"
    if any(token in lowered for token in ("cache", "llc", "l1", "l2", "l3")):
        return "cache"
    if any(token in lowered for token in ("mem", "dram", "load", "store", "tlb")):
        return "memory"
    return "cpu"


def _infer_unit(event_name: str, line: str) -> str | None:
    lowered = event_name.lower()
    if "%" in line or lowered.startswith("topdown-") or lowered.startswith("tma_"):
        return "percent"
    if lowered.endswith("clock") or "clock" in lowered:
        return "ms"
    return "count"
