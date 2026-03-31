from __future__ import annotations

from perf_agent.models.observation import Observation


def latest_numeric_metrics(observations: list[Observation]) -> dict[str, float]:
    aggregated: dict[str, float] = {}
    for observation in observations:
        if isinstance(observation.value, (int, float)):
            aggregated[observation.metric] = float(observation.value)
    return aggregated


def detect_memory_bound(metrics: dict[str, float]) -> bool:
    return (
        metrics.get("ipc", 1.0) <= 0.8
        and max(
            metrics.get("stalled_cycles_backend_pct", 0.0),
            metrics.get("topdown_be_bound_pct", 0.0),
            metrics.get("topdown_mem_bound_pct", 0.0),
            metrics.get("tma_memory_bound_pct", 0.0),
        )
        >= 20
        and max(
            metrics.get("cache_misses", 0.0),
            metrics.get("llc_miss_count", 0.0),
            metrics.get("l2_miss_count", 0.0),
            metrics.get("l1_miss_count", 0.0),
        )
        >= 10000
    )


def detect_io_bound(metrics: dict[str, float]) -> bool:
    return (
        metrics.get("cpu_utilization_pct", 100.0) <= 50
        and (metrics.get("iowait_pct", 0.0) >= 10 or metrics.get("wait_pct", 0.0) >= 15)
    ) or (
        metrics.get("disk_util_pct", 0.0) >= 70 and metrics.get("await_ms", 0.0) >= 10
    )


def detect_lock_contention(metrics: dict[str, float]) -> bool:
    return (
        metrics.get("lock_wait_pct", 0.0) >= 10 and metrics.get("context_switches_per_sec", 0.0) >= 5000
    ) or (
        metrics.get("voluntary_context_switches", 0.0) >= 5000 and metrics.get("cpu_utilization_pct", 100.0) <= 30
    ) or (
        metrics.get("context_switches", 0.0) >= 5000 and metrics.get("cpu_utilization_pct", 100.0) <= 30
    ) or (
        metrics.get("tma_lock_latency_pct", 0.0) >= 8
    ) or (
        metrics.get("lock_loads", 0.0) >= 1000 and metrics.get("context_switches", 0.0) >= 1000
    )


def detect_scheduler_pressure(metrics: dict[str, float]) -> bool:
    return (
        metrics.get("context_switches_per_sec", 0.0) >= 10000
        or metrics.get("run_queue", 0.0) >= 8
        or metrics.get("voluntary_context_switches", 0.0) >= 12000
    )


def detect_branch_mispredict(metrics: dict[str, float]) -> bool:
    return (
        metrics.get("branch_misses", 0.0) >= 10000
        or metrics.get("topdown_bad_spec_pct", 0.0) >= 12
        or metrics.get("tma_branch_mispredicts_pct", 0.0) >= 8
    )


def detect_cpu_bound(metrics: dict[str, float]) -> bool:
    return (
        metrics.get("cpu_utilization_pct", 0.0) >= 80
        or (
            metrics.get("ipc", 0.0) >= 1.0
            and metrics.get("topdown_retiring_pct", 0.0) >= 25
        )
    )
