from __future__ import annotations

from perf_agent.config import RuleConfig, load_rule_configs
from perf_agent.models.hypothesis import Hypothesis
from perf_agent.models.observation import Observation
from perf_agent.rules.confidence import score_from_observations
from perf_agent.rules.heuristics import (
    detect_branch_mispredict,
    detect_cpu_bound,
    detect_io_bound,
    detect_lock_contention,
    detect_memory_bound,
    detect_scheduler_pressure,
    latest_numeric_metrics,
)
from perf_agent.utils.ids import new_id


SUGGESTED_ACTIONS = {
    "cpu_bound": ["建议追加 perf record -g，定位最热函数和调用栈。"],
    "memory_bound": ["建议再采一轮 perf stat，重点核查 backend stall 和 cache miss。"],
    "io_bound": ["建议补充 iostat，确认磁盘延迟与利用率。"],
    "lock_contention": ["建议采集 perf record 调用栈，检查锁持有者和等待热点。"],
    "scheduler_issue": ["建议补充 mpstat 或调度跟踪，检查上下文切换和运行队列压力。"],
    "branch_mispredict": ["建议检查高频分支代码并结合调用栈定位热点分支。"],
    "unknown": ["建议补充一轮基线采样后再做结论。"],
}


def classify_observations(
    observations: list[Observation],
    config_path: str | None = None,
) -> list[Hypothesis]:
    rule_configs = load_rule_configs(config_path)
    metrics = latest_numeric_metrics(observations)
    hypotheses: list[Hypothesis] = []

    if detect_memory_bound(metrics):
        support = _select_support(
            observations,
            {"ipc", "stalled_cycles_backend_pct", "topdown_be_bound_pct", "tma_memory_bound_pct", "cache_misses", "llc_miss_count", "l2_miss_count"},
        )
        hypotheses.append(
            _build_hypothesis(
                "memory_bound",
                "IPC 偏低且 backend stall、cache miss 偏高，疑似存在内存侧瓶颈。",
                support,
                strength=0.15,
                needs_verification=True,
                min_confidence=rule_configs.get("memory_bound", RuleConfig()).min_confidence,
            )
        )

    if detect_io_bound(metrics):
        support = _select_support(observations, {"cpu_utilization_pct", "iowait_pct", "wait_pct", "disk_util_pct", "await_ms"})
        hypotheses.append(
            _build_hypothesis(
                "io_bound",
                "有效 CPU 推进不足且等待时间偏高，疑似存在 I/O 瓶颈。",
                support,
                strength=0.10,
                needs_verification=True,
                min_confidence=rule_configs.get("io_bound", RuleConfig()).min_confidence,
            )
        )

    if detect_lock_contention(metrics):
        support = _select_support(
            observations,
            {"lock_wait_pct", "context_switches_per_sec", "voluntary_context_switches", "context_switches", "callgraph_samples", "tma_lock_latency_pct", "lock_loads"},
        )
        hypotheses.append(
            _build_hypothesis(
                "lock_contention",
                "锁等待或高频上下文切换特征明显，疑似存在锁竞争。",
                support,
                strength=0.12,
                needs_verification=True,
                min_confidence=rule_configs.get("lock_contention", RuleConfig()).min_confidence,
            )
        )

    if detect_scheduler_pressure(metrics):
        support = _select_support(
            observations,
            {"context_switches_per_sec", "run_queue", "involuntary_context_switches", "voluntary_context_switches"},
        )
        hypotheses.append(
            _build_hypothesis(
                "scheduler_issue",
                "上下文切换或运行队列压力偏高，疑似存在调度问题。",
                support,
                strength=0.08,
                needs_verification=True,
                min_confidence=rule_configs.get("scheduler_issue", RuleConfig()).min_confidence,
            )
        )

    if detect_branch_mispredict(metrics):
        support = _select_support(observations, {"branch_misses", "topdown_bad_spec_pct", "tma_branch_mispredicts_pct"})
        hypotheses.append(
            _build_hypothesis(
                "branch_mispredict",
                "branch miss 较高，疑似存在分支预测失误开销。",
                support,
                strength=0.09,
                needs_verification=True,
                min_confidence=rule_configs.get("branch_mispredict", RuleConfig()).min_confidence,
            )
        )

    if detect_cpu_bound(metrics):
        support = _select_support(observations, {"cpu_utilization_pct", "usr_pct", "system_pct", "ipc", "topdown_retiring_pct", "process_sample_pct", "thread_sample_pct"})
        hypotheses.append(
            _build_hypothesis(
                "cpu_bound",
                "活跃 CPU 利用率很高，疑似属于 CPU 密集型瓶颈。",
                support,
                strength=0.15,
                needs_verification=False,
                min_confidence=rule_configs.get("cpu_bound", RuleConfig()).min_confidence,
            )
        )

    if not hypotheses:
        support = observations[:1]
        if support:
            hypotheses.append(
                _build_hypothesis(
                    "unknown",
                    "当前证据不足，暂时无法明确瓶颈方向。",
                    support,
                    strength=-0.15,
                    needs_verification=True,
                    min_confidence=rule_configs.get("unknown", RuleConfig(min_confidence=0.2)).min_confidence,
                )
            )

    hypotheses.sort(key=lambda item: item.confidence, reverse=True)
    return hypotheses


def _select_support(observations: list[Observation], metrics: set[str]) -> list[Observation]:
    selected = [item for item in observations if item.metric in metrics]
    return selected or observations[:1]


def _build_hypothesis(
    kind: str,
    summary: str,
    support: list[Observation],
    strength: float,
    needs_verification: bool,
    min_confidence: float,
) -> Hypothesis:
    supporting_ids = [item.id for item in support]
    return Hypothesis(
        id=new_id("hyp"),
        kind=kind,
        summary=summary,
        reasoning_basis=[f"依据观测指标: {', '.join(item.metric for item in support)}"],
        supporting_observation_ids=supporting_ids,
        confidence=max(min_confidence, score_from_observations(support, strength=strength)),
        needs_verification=needs_verification,
        suggested_actions=SUGGESTED_ACTIONS[kind],
    )
