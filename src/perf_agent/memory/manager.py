from __future__ import annotations

from pydantic import BaseModel, Field

from perf_agent.models.state import AnalysisState


class ShortTermContext(BaseModel):
    """Compact task-scoped context for planners and LLM prompts."""

    goal: str | None = None
    target_cmd: list[str] = Field(default_factory=list)
    workload_label: str | None = None
    environment_notes: list[str] = Field(default_factory=list)
    completed_rounds: int = 0
    evidence_summaries: list[str] = Field(default_factory=list)
    current_hypotheses: list[str] = Field(default_factory=list)
    rejected_causes: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class LongTermPattern(BaseModel):
    """Small reusable diagnosis pattern. This is not raw run history."""

    name: str
    trigger_metrics: list[str] = Field(default_factory=list)
    bottleneck_kind: str
    recommended_intents: list[str] = Field(default_factory=list)
    rationale: str


DEFAULT_PATTERNS = [
    LongTermPattern(
        name="low_ipc_high_cache_miss",
        trigger_metrics=["ipc", "cache_miss_rate_pct", "cache_mpki"],
        bottleneck_kind="memory_hierarchy",
        recommended_intents=["cache_memory_pressure", "hot_function_callgraph", "temporal_behavior"],
        rationale="Low IPC with high cache miss pressure usually needs cache hierarchy and hotspot validation.",
    ),
    LongTermPattern(
        name="low_ipc_high_branch_miss",
        trigger_metrics=["ipc", "branch_miss_rate_pct", "branch_mpki"],
        bottleneck_kind="branch_mispredict",
        recommended_intents=["branch_behavior", "hot_function_callgraph"],
        rationale="Branch miss pressure should be tied to hot control-flow paths before proposing code changes.",
    ),
    LongTermPattern(
        name="high_context_switch",
        trigger_metrics=["context_switches", "context_switches_per_sec", "voluntary_context_switches"],
        bottleneck_kind="scheduler",
        recommended_intents=["scheduler_context", "temporal_behavior"],
        rationale="High context switching needs scheduler/process-level evidence before blaming CPU execution.",
    ),
]


class MemoryManager:
    """Separates compact short-term context from curated long-term patterns."""

    def __init__(self, patterns: list[LongTermPattern] | None = None) -> None:
        self.patterns = patterns or list(DEFAULT_PATTERNS)

    def short_term_context(self, state: AnalysisState) -> ShortTermContext:
        rejected: list[str] = []
        if state.final_report is not None:
            rejected = list(state.final_report.rejected_alternatives)
        return ShortTermContext(
            goal=state.goal,
            target_cmd=state.target_cmd,
            workload_label=state.workload_label,
            environment_notes=list(state.environment.notes[-5:]),
            completed_rounds=state.planning_rounds_done,
            evidence_summaries=[pack.summary for pack in state.evidence_packs[-3:]],
            current_hypotheses=[
                f"{hypothesis.kind}:{hypothesis.confidence:.2f}"
                for hypothesis in sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True)[:5]
            ],
            rejected_causes=rejected[-5:],
            open_questions=[question for pack in state.evidence_packs[-2:] for question in pack.unresolved_questions][:8],
        )

    def relevant_patterns(self, state: AnalysisState, limit: int = 5) -> list[LongTermPattern]:
        metric_names = {observation.metric for observation in state.observations}
        scored: list[tuple[int, LongTermPattern]] = []
        for pattern in self.patterns:
            score = len(metric_names.intersection(pattern.trigger_metrics))
            if score:
                scored.append((score, pattern))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [pattern for _, pattern in scored[:limit]]
