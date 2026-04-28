from __future__ import annotations

from perf_agent.models.environment import AnalysisIntent
from perf_agent.models.hypothesis import Hypothesis
from perf_agent.models.state import AnalysisState


def build_baseline_intents(state: AnalysisState) -> list[AnalysisIntent]:
    haystack = " ".join([*(state.target_cmd or []), state.workload_label or "", state.goal or ""]).lower()
    intents = [
        AnalysisIntent(
            name="baseline_runtime",
            question="先拿到运行时长、CPU 占用、内存占用和上下文切换基线。",
            priority=10,
        ),
        AnalysisIntent(
            name="system_cpu_profile",
            question="先拿到程序运行期间的系统级 CPU 占用率、iowait 和 busiest core 基线。",
            priority=15,
        ),
        AnalysisIntent(
            name="instruction_efficiency",
            question="判断指令退休效率、cycles 和 IPC 是否异常。",
            priority=20,
        ),
        AnalysisIntent(
            name="cache_memory_pressure",
            question="判断 cache miss、前后端停顿和内存压力是否明显。",
            priority=30,
        ),
        AnalysisIntent(
            name="frontend_backend_bound",
            question="如果平台支持，进一步区分 frontend、backend、bad speculation 与 retiring。",
            priority=35,
        ),
        AnalysisIntent(
            name="scheduler_context",
            question="观察调度、上下文切换和迁移情况。",
            priority=40,
        ),
    ]
    if any(token in haystack for token in ("branch", "predict", "if", "switch")):
        intents.append(
            AnalysisIntent(
                name="branch_behavior",
                question="补充判断分支预测是否带来额外开销。",
                priority=45,
            )
        )
    if any(token in haystack for token in ("io", "disk", "read", "write", "storage")):
        intents.append(
            AnalysisIntent(
                name="io_wait_detail",
                question="补充系统层 I/O 等待和设备利用率信息。",
                priority=50,
            )
        )
    return sorted(intents, key=lambda item: item.priority)


def build_follow_up_intents(state: AnalysisState, hypotheses: list[Hypothesis]) -> list[AnalysisIntent]:
    if not hypotheses:
        return [
            AnalysisIntent(
                name="instruction_efficiency",
                question="上一轮证据不足，再补一轮基线计数器。",
                phase="verification",
                requested_by="verifier",
                priority=10,
            )
        ]

    top = max(hypotheses, key=lambda item: item.confidence)
    follow_up: list[AnalysisIntent] = []
    runtime_seconds = _runtime_seconds(state)
    if top.kind in {"cpu_bound", "branch_mispredict", "lock_contention"}:
        follow_up.append(
            AnalysisIntent(
                name="hot_function_callgraph",
                question="需要定位热点函数和主要调用链。",
                phase="verification",
                requested_by="verifier",
                priority=10,
            )
        )
        if runtime_seconds >= 0.08:
            follow_up.append(
                AnalysisIntent(
                    name="temporal_behavior",
                    question="需要判断热点和效率问题是否集中在某个时间阶段。",
                    phase="verification",
                    requested_by="verifier",
                    priority=15,
                )
            )
    if top.kind in {"memory_bound", "branch_mispredict"}:
        follow_up.append(
            AnalysisIntent(
                name="cache_memory_pressure",
                question="需要进一步确认 cache / memory pressure 与停顿来源。",
                phase="verification",
                requested_by="verifier",
                priority=20,
            )
        )
        if runtime_seconds >= 0.08:
            follow_up.append(
                AnalysisIntent(
                    name="temporal_behavior",
                    question="需要确认 cache / IPC 波动是否集中在特定时间窗口。",
                    phase="verification",
                    requested_by="verifier",
                    priority=25,
                )
            )
    if top.kind in {"io_bound"}:
        follow_up.append(
            AnalysisIntent(
                name="io_wait_detail",
                question="需要补充系统 I/O 等待和设备层证据。",
                phase="verification",
                requested_by="verifier",
                priority=20,
            )
        )
        if runtime_seconds >= 0.08:
            follow_up.append(
                AnalysisIntent(
                    name="temporal_behavior",
                    question="需要判断 I/O 等待是否呈阶段性尖峰。",
                    phase="verification",
                    requested_by="verifier",
                    priority=25,
                )
            )
    if top.kind in {"lock_contention", "scheduler_issue"}:
        follow_up.append(
            AnalysisIntent(
                name="scheduler_context",
                question="需要强化调度与上下文切换证据。",
                phase="verification",
                requested_by="verifier",
                priority=30,
            )
        )
        if runtime_seconds >= 0.08:
            follow_up.append(
                AnalysisIntent(
                    name="temporal_behavior",
                    question="需要判断上下文切换和锁竞争是否随时间波动。",
                    phase="verification",
                    requested_by="verifier",
                    priority=35,
                )
            )
    if not follow_up:
        follow_up.append(
            AnalysisIntent(
                name="instruction_efficiency",
                question="结论仍不够稳，回到基线事件重新确认。",
                phase="verification",
                requested_by="verifier",
                priority=40,
            )
        )
    return sorted(follow_up, key=lambda item: item.priority)


def _runtime_seconds(state: AnalysisState) -> float:
    elapsed = 0.0
    total = 0.0
    for observation in state.observations:
        if observation.metric == "elapsed_time_sec" and isinstance(observation.value, (int, float)):
            elapsed = max(elapsed, float(observation.value))
        if observation.metric in {"user_time_sec", "system_time_sec"} and isinstance(observation.value, (int, float)):
            total += float(observation.value)
    return max(elapsed, total)
