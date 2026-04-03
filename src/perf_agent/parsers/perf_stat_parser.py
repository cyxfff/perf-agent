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
    "l1d-cache": ("l1_access_count", "cache", "count"),
    "l1d-cache-access": ("l1_access_count", "cache", "count"),
    "l1d-cache-hit": ("l1_hit_count", "cache", "count"),
    "l1d-cache-refill": ("l1_miss_count", "cache", "count"),
    "l2d-cache": ("l2_access_count", "cache", "count"),
    "l2d-cache-access": ("l2_access_count", "cache", "count"),
    "l2d-cache-refill": ("l2_miss_count", "cache", "count"),
    "l3d-cache": ("l3_access_count", "cache", "count"),
    "l3d-cache-access": ("l3_access_count", "cache", "count"),
    "l3d-cache-refill": ("l3_miss_count", "cache", "count"),
    "llc-access": ("llc_access_count", "cache", "count"),
    "llc-miss": ("llc_miss_count", "cache", "count"),
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
    "longest_lat_cache.reference": ("llc_access_count", "cache", "count"),
    "l2_rqsts.miss": ("l2_miss_count", "cache", "count"),
    "l2_rqsts.references": ("l2_access_count", "cache", "count"),
    "mem_load_completed.l1_miss_any": ("l1_miss_count", "memory", "count"),
    "mem_load_retired.l1_hit": ("l1_hit_count", "memory", "count"),
    "mem_load_retired.l1_miss": ("l1_miss_count", "memory", "count"),
    "mem_inst_retired.lock_loads": ("lock_loads", "lock", "count"),
    "l1-dcache-loads": ("l1_access_count", "cache", "count"),
    "l1-dcache-load-misses": ("l1_miss_count", "cache", "count"),
    "l1-icache-loads": ("l1i_access_count", "cache", "count"),
    "l1-icache-load-misses": ("l1i_miss_count", "cache", "count"),
    "llc-load-misses": ("llc_miss_count", "cache", "count"),
    "llc-loads": ("llc_access_count", "cache", "count"),
}
TIMELINE_SEPARATOR = ","
SIMPLEPERF_SECTION_HEADER = "Performance counter statistics,"
SIMPLEPERF_COUNTER_PATTERN = re.compile(r"^\s*([\d,]+(?:\.\d+)?),([^,]+),([^,]*),([^,]*),?\s*$")
SIMPLEPERF_TOTAL_TIME_PATTERN = re.compile(r"^\s*Total test time,([\d.]+),seconds,?\s*$")


def parse_text(text: str, source: str, action_id: str | None = None) -> list[Observation]:
    timestamp = datetime.now(timezone.utc)
    observations: list[Observation] = []
    seen_metrics: set[str] = set()
    timeline_buckets: dict[str, dict[str, float]] = defaultdict(dict)
    aggregate_metrics: dict[str, float] = {}
    observations.extend(_parse_simpleperf_timeline(text, timestamp, source, action_id, timeline_buckets))
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
        if isinstance(value, (int, float)):
            aggregate_metrics[metric] = float(value)
    for line in text.splitlines():
        timeline = _parse_timeline_line(line, timestamp, source, action_id)
        if timeline is not None:
            observations.append(timeline)
            time_key = timeline.labels.get("time_bucket_sec", "")
            metric_name = timeline.metric
            if time_key and metric_name and isinstance(timeline.value, (int, float)):
                timeline_buckets[time_key][metric_name] = timeline_buckets[time_key].get(metric_name, 0.0) + float(timeline.value)
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
        if isinstance(value, (int, float)):
            aggregate_metrics[metric] = float(value)
    observations.extend(_derive_aggregate_metrics(aggregate_metrics, timestamp, source, action_id))
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
    if columns[1] and not re.fullmatch(r"[\d,]+(?:\.\d+)?|<not counted>|<not supported>", columns[1]):
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


def _parse_simpleperf_timeline(
    text: str,
    timestamp: datetime,
    source: str,
    action_id: str | None,
    timeline_buckets: dict[str, dict[str, float]],
) -> list[Observation]:
    observations: list[Observation] = []
    pending: list[tuple[str, float | int, str | None, str, str]] = []
    in_simpleperf_block = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == SIMPLEPERF_SECTION_HEADER:
            in_simpleperf_block = True
            pending = []
            continue
        if not in_simpleperf_block:
            continue
        total_match = SIMPLEPERF_TOTAL_TIME_PATTERN.match(stripped)
        if total_match:
            time_key = f"{float(total_match.group(1)):.3f}"
            for metric, value, unit, category, raw_excerpt in pending:
                observations.append(
                    Observation(
                        id=new_id("obs"),
                        source=source,
                        category=category,
                        metric=metric,
                        value=value,
                        unit=unit,
                        normalized_value=round(float(value) / 100.0, 4) if unit == "percent" else None,
                        scope="process",
                        timestamp=timestamp,
                        labels={
                            "action_id": action_id or "",
                            "series_type": "timeline",
                            "time_bucket_sec": time_key,
                        },
                        raw_excerpt=raw_excerpt,
                    )
                )
                timeline_buckets[time_key][metric] = timeline_buckets[time_key].get(metric, 0.0) + float(value)
            pending = []
            in_simpleperf_block = False
            continue

        counter_match = SIMPLEPERF_COUNTER_PATTERN.match(stripped)
        if not counter_match:
            continue
        raw_value = counter_match.group(1).replace(",", "")
        event_name = _normalize_event_name(counter_match.group(2))
        metric_def = _metric_definition(event_name, stripped)
        if metric_def is None:
            continue
        metric, category, unit = metric_def
        value: float | int = float(raw_value) if "." in raw_value else int(raw_value)
        pending.append((metric, value, unit, category, stripped))

    return observations


def _derive_timeline_metrics(
    timeline_buckets: dict[str, dict[str, float]],
    timestamp: datetime,
    source: str,
    action_id: str | None,
) -> list[Observation]:
    derived: list[Observation] = []
    for time_key, metrics in timeline_buckets.items():
        derived.extend(_derive_ratio_metrics(metrics, timestamp, source, action_id, time_key=time_key))
    return derived


def _derive_aggregate_metrics(
    aggregate_metrics: dict[str, float],
    timestamp: datetime,
    source: str,
    action_id: str | None,
) -> list[Observation]:
    return _derive_ratio_metrics(aggregate_metrics, timestamp, source, action_id, time_key=None)


def _derive_ratio_metrics(
    metrics: dict[str, float],
    timestamp: datetime,
    source: str,
    action_id: str | None,
    *,
    time_key: str | None,
) -> list[Observation]:
    derived: list[Observation] = []
    labels = {"action_id": action_id or ""}
    if time_key is not None:
        labels["series_type"] = "timeline"
        labels["time_bucket_sec"] = time_key

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
                labels={**labels, "derived_from": "instructions,cycles"},
                evidence_level="derived",
                raw_excerpt=(f"time={time_key}s ipc={ipc:.4f}" if time_key is not None else f"ipc={ipc:.4f}"),
            )
        )
    if cycles is not None and instructions not in {None, 0.0}:
        cpi = cycles / instructions
        derived.append(
            Observation(
                id=new_id("obs"),
                source=source,
                category="cpu",
                metric="cpi",
                value=round(cpi, 4),
                unit=None,
                normalized_value=round(cpi, 4),
                scope="process",
                timestamp=timestamp,
                labels={**labels, "derived_from": "cycles,instructions"},
                evidence_level="derived",
                raw_excerpt=(f"time={time_key}s cpi={cpi:.4f}" if time_key is not None else f"cpi={cpi:.4f}"),
            )
        )

    branch_count = metrics.get("branches")
    branch_miss = metrics.get("branch_misses")
    derived.extend(
        _ratio_observation(
            metric="branch_miss_rate_pct",
            category="branch",
            numerator=branch_miss,
            denominator=branch_count,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="branch_misses/branches",
        )
    )
    derived.extend(
        _per_kilo_observation(
            metric="branch_mpki",
            category="branch",
            numerator=branch_miss,
            denominator=instructions,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="branch_misses/instructions*1000",
        )
    )

    cache_ref = metrics.get("cache_references")
    cache_miss = metrics.get("cache_misses")
    derived.extend(
        _ratio_observation(
            metric="cache_miss_rate_pct",
            category="cache",
            numerator=cache_miss,
            denominator=cache_ref,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="cache_misses/cache_references",
        )
    )
    derived.extend(
        _per_kilo_observation(
            metric="cache_mpki",
            category="cache",
            numerator=cache_miss,
            denominator=instructions,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="cache_misses/instructions*1000",
        )
    )

    l1_access = metrics.get("l1_access_count")
    l1_hit = metrics.get("l1_hit_count")
    l1_miss = metrics.get("l1_miss_count")
    if l1_access in {None, 0.0} and l1_hit is not None and l1_miss is not None:
        l1_access = l1_hit + l1_miss
    derived.extend(
        _ratio_observation(
            metric="l1_miss_rate_pct",
            category="cache",
            numerator=l1_miss,
            denominator=l1_access,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="l1_miss/l1_access",
        )
    )
    derived.extend(
        _per_kilo_observation(
            metric="l1_mpki",
            category="cache",
            numerator=l1_miss,
            denominator=instructions,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="l1_miss/instructions*1000",
        )
    )

    l2_access = metrics.get("l2_access_count")
    l2_miss = metrics.get("l2_miss_count")
    derived.extend(
        _ratio_observation(
            metric="l2_miss_rate_pct",
            category="cache",
            numerator=l2_miss,
            denominator=l2_access,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="l2_miss/l2_access",
        )
    )
    derived.extend(
        _per_kilo_observation(
            metric="l2_mpki",
            category="cache",
            numerator=l2_miss,
            denominator=instructions,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="l2_miss/instructions*1000",
        )
    )

    l3_access = metrics.get("l3_access_count")
    l3_miss = metrics.get("l3_miss_count")
    derived.extend(
        _ratio_observation(
            metric="l3_miss_rate_pct",
            category="cache",
            numerator=l3_miss,
            denominator=l3_access,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="l3_miss/l3_access",
        )
    )
    derived.extend(
        _per_kilo_observation(
            metric="l3_mpki",
            category="cache",
            numerator=l3_miss,
            denominator=instructions,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="l3_miss/instructions*1000",
        )
    )

    llc_access = metrics.get("llc_access_count") or l3_access
    llc_miss = metrics.get("llc_miss_count") or l3_miss
    derived.extend(
        _ratio_observation(
            metric="llc_miss_rate_pct",
            category="cache",
            numerator=llc_miss,
            denominator=llc_access,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="llc_miss/llc_access",
        )
    )
    derived.extend(
        _per_kilo_observation(
            metric="llc_mpki",
            category="cache",
            numerator=llc_miss,
            denominator=instructions,
            timestamp=timestamp,
            source=source,
            labels=labels,
            raw_excerpt="llc_miss/instructions*1000",
        )
    )
    return derived


def _ratio_observation(
    *,
    metric: str,
    category: str,
    numerator: float | None,
    denominator: float | None,
    timestamp: datetime,
    source: str,
    labels: dict[str, str],
    raw_excerpt: str,
) -> list[Observation]:
    if numerator in {None} or denominator in {None, 0.0}:
        return []
    rate = float(numerator) / float(denominator) * 100.0
    return [
        Observation(
            id=new_id("obs"),
            source=source,
            category=category,
            metric=metric,
            value=round(rate, 4),
            unit="percent",
            normalized_value=round(rate / 100.0, 4),
            scope="process",
            timestamp=timestamp,
            labels={**labels, "derived_from": raw_excerpt},
            evidence_level="derived",
            raw_excerpt=raw_excerpt,
        )
    ]


def _per_kilo_observation(
    *,
    metric: str,
    category: str,
    numerator: float | None,
    denominator: float | None,
    timestamp: datetime,
    source: str,
    labels: dict[str, str],
    raw_excerpt: str,
) -> list[Observation]:
    if numerator in {None} or denominator in {None, 0.0}:
        return []
    value = float(numerator) / float(denominator) * 1000.0
    return [
        Observation(
            id=new_id("obs"),
            source=source,
            category=category,
            metric=metric,
            value=round(value, 4),
            unit="mpki",
            normalized_value=round(value, 4),
            scope="process",
            timestamp=timestamp,
            labels={**labels, "derived_from": raw_excerpt},
            evidence_level="derived",
            raw_excerpt=raw_excerpt,
        )
    ]


def _normalize_event_name(raw_event: str) -> str:
    candidate = raw_event.strip()
    if ":" in candidate and not candidate.startswith(("sched:", "syscall:", "irq:", "raw_syscalls:", "kprobes:", "uprobes:")):
        candidate = candidate.split(":", 1)[0]
    candidate_lower = candidate.lower()
    alias_map = {
        "raw-cpu-cycles": "cycles",
        "raw-cnt-cycles": "cycles",
        "raw-inst-retired": "instructions",
        "inst-retired": "instructions",
        "raw-br-retired": "branches",
        "raw-br-mis-pred": "branch-misses",
        "raw-br-mis-pred-retired": "branch-misses",
        "raw-ll-cache-rd": "cache-references",
        "raw-ll-cache-miss-rd": "cache-misses",
    }
    if candidate_lower in alias_map:
        return alias_map[candidate_lower]
    if candidate_lower in GENERIC_EVENT_MAP:
        return candidate_lower
    if candidate_lower.endswith("/") and "/" in candidate_lower:
        core = candidate_lower.strip("/").split("/")[-1]
        if core in GENERIC_EVENT_MAP:
            return core
    for event_name in GENERIC_EVENT_MAP:
        if candidate_lower.endswith(event_name):
            return event_name
        if candidate_lower.endswith(f"/{event_name}/"):
            return event_name
    return candidate_lower


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
