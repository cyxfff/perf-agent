from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


LifecycleStatus = Literal[
    "INIT",
    "ENV_PROBING",
    "PLAN_GENERATED",
    "RUNNING",
    "EVIDENCE_BUILT",
    "DIAGNOSING",
    "REPLANNING",
    "REPORT_READY",
    "FAILED",
]

SamplingTool = Literal["time", "perf_stat", "perf_record", "pidstat", "mpstat", "iostat", "sar", "flamegraph"]
BottleneckKind = Literal[
    "cpu_frontend",
    "branch_mispredict",
    "backend_execution",
    "memory_hierarchy",
    "cache_miss",
    "tlb_miss",
    "scheduler",
    "syscall_context_switch",
    "io",
    "lock_contention",
    "cpu_bound",
    "unknown",
]


class TaskSpec(BaseModel):
    """User-facing task contract. It is normalized before entering the orchestrator."""

    goal: str | None = Field(default=None, description="Performance goal or symptom, for example 'IPC is low'.")
    binary_path: str | None = Field(default=None, description="Executable file path when known.")
    command: list[str] = Field(default_factory=list, description="Command tokens used to run the target workload.")
    workload: str | None = Field(default=None, description="Human-readable workload label or scenario.")
    pid: int | None = Field(default=None, description="Existing process id when using attach mode.")
    cwd: str | None = Field(default=None, description="Working directory for command execution.")
    env: dict[str, str] = Field(default_factory=dict, description="Extra environment variables for the target command.")
    source_dir: str | None = Field(default=None, description="Optional source tree for symbol/source correlation.")
    max_rounds: int = Field(default=3, ge=1, le=10, description="Maximum sampling/planning iterations.")
    timeout_sec: int = Field(default=60, ge=1, description="Default timeout for one sampling action.")
    safety_mode: Literal["strict", "normal", "permissive"] = Field(default="normal", description="Command risk policy.")


class EnvProfile(BaseModel):
    """Host and profiler capability snapshot."""

    os_name: str | None = Field(default=None, description="Operating system name.")
    kernel_release: str | None = Field(default=None, description="Kernel release.")
    cpu_model: str | None = Field(default=None, description="CPU model string.")
    arch: str | None = Field(default=None, description="CPU architecture.")
    physical_cores: int | None = Field(default=None, description="Physical core count.")
    logical_cores: int | None = Field(default=None, description="Logical CPU count.")
    perf_available: bool = Field(default=False, description="Whether perf is installed and callable.")
    perf_version: str | None = Field(default=None, description="perf version output.")
    perf_event_paranoid: str | None = Field(default=None, description="/proc/sys/kernel/perf_event_paranoid value.")
    requires_sudo: bool = Field(default=False, description="Whether requested events likely require elevated privileges.")
    callgraph_modes: list[str] = Field(default_factory=list, description="Supported call graph modes, for example fp/dwarf/lbr.")
    available_events: list[str] = Field(default_factory=list, description="Normalized event names from perf list.")
    available_tools: list[str] = Field(default_factory=list, description="Available sampling tools.")
    notes: list[str] = Field(default_factory=list, description="Capability warnings or degradation notes.")


class PerfEventGroup(BaseModel):
    """A coherent event set that should be sampled together."""

    name: str = Field(description="Stable group name, for example baseline_core or cache_hierarchy.")
    events: list[str] = Field(default_factory=list, description="perf event names.")
    purpose: str = Field(description="Question this event group is intended to answer.")
    required: bool = Field(default=False, description="If true, missing support should be reported as a degraded plan.")
    fallback_events: list[str] = Field(default_factory=list, description="Fallback events when preferred events are unsupported.")
    sample_interval_ms: int | None = Field(default=None, description="Interval for time-series perf stat.")


class SamplingPlan(BaseModel):
    """Executable but not yet executed sampling plan."""

    id: str = Field(description="Plan id.")
    round_index: int = Field(ge=1, description="Sampling round number.")
    phase: Literal["baseline", "verification", "source_correlation"] = Field(description="Analysis phase.")
    rationale: str = Field(description="Why this plan should run now.")
    tools: list[SamplingTool] = Field(default_factory=list, description="Tools selected for this plan.")
    event_groups: list[PerfEventGroup] = Field(default_factory=list, description="Event groups for perf-based tools.")
    command: list[str] = Field(default_factory=list, description="Target command tokens.")
    timeout_sec: int = Field(default=60, ge=1, description="Per-action timeout.")
    warmup_runs: int = Field(default=0, ge=0, description="Warmup repetitions before measured runs.")
    repeat_runs: int = Field(default=1, ge=1, description="Measured repetitions for stability.")
    cpu_affinity: list[int] = Field(default_factory=list, description="CPU list for optional taskset binding.")
    call_graph: bool = Field(default=False, description="Whether perf record should collect call graph.")
    call_graph_mode: str | None = Field(default=None, description="Selected call graph mode.")
    max_record_mb: int = Field(default=256, ge=1, description="Maximum acceptable perf.data size before truncation/degradation.")


class ExecutionResult(BaseModel):
    """Structured Executor output. Raw text is referenced by artifact paths."""

    action_id: str = Field(description="Action id that produced this result.")
    tool: str | None = Field(default=None, description="Tool name.")
    command: list[str] = Field(default_factory=list, description="Exact command tokens executed.")
    exit_code: int = Field(description="Process exit code, 124 for timeout, 127 for missing executable.")
    stdout_path: str | None = Field(default=None, description="Path to captured stdout.")
    stderr_path: str | None = Field(default=None, description="Path to captured stderr.")
    artifact_paths: list[str] = Field(default_factory=list, description="Additional generated artifact paths.")
    duration_sec: float = Field(ge=0, description="Wall-clock execution duration.")
    success: bool = Field(description="True when the command completed successfully.")
    timed_out: bool = Field(default=False, description="True when timeout handling was triggered.")
    error_message: str | None = Field(default=None, description="Structured failure summary.")
    risk_checked: bool = Field(default=False, description="Whether command risk policy was applied before execution.")


class MetricSample(BaseModel):
    """One parsed fact from a command result."""

    id: str = Field(description="Metric sample id.")
    metric: str = Field(description="Normalized metric name.")
    value: float | int | str = Field(description="Metric value.")
    unit: str | None = Field(default=None, description="Metric unit.")
    source: str = Field(description="Tool/parser source.")
    scope: Literal["process", "thread", "system", "function", "callchain"] = Field(description="Metric scope.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Parse timestamp.")
    labels: dict[str, str] = Field(default_factory=dict, description="Structured dimensions such as pid/tid/symbol.")
    raw_artifact_path: str | None = Field(default=None, description="Raw artifact that backs this sample.")
    parse_status: Literal["ok", "missing_event", "unsupported_event", "permission_denied", "unparsed"] = Field(
        default="ok",
        description="Parser status for this sample.",
    )


class DerivedMetric(BaseModel):
    """Metric computed from one or more MetricSample values."""

    name: str = Field(description="Derived metric name, for example ipc or cache_mpki.")
    value: float = Field(description="Computed value.")
    formula: str = Field(description="Formula used to compute the value.")
    input_metric_ids: list[str] = Field(default_factory=list, description="MetricSample ids used as inputs.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in the derived value.")
    notes: list[str] = Field(default_factory=list, description="Warnings such as divide-by-zero or missing input.")


class EvidenceItem(BaseModel):
    """A factual evidence packet for one sampling round."""

    id: str = Field(description="Evidence id.")
    round_index: int = Field(ge=1, description="Sampling round number.")
    plan_id: str | None = Field(default=None, description="SamplingPlan id.")
    sampling_command: list[str] = Field(default_factory=list, description="Representative command tokens.")
    environment: EnvProfile | None = Field(default=None, description="Environment snapshot used by this evidence.")
    raw_artifact_paths: list[str] = Field(default_factory=list, description="Raw data files.")
    metrics: list[MetricSample] = Field(default_factory=list, description="Direct parsed facts.")
    derived_metrics: list[DerivedMetric] = Field(default_factory=list, description="Computed facts.")
    anomalies: list[str] = Field(default_factory=list, description="Factual anomalies observed in this evidence.")
    diff_from_previous: dict[str, float] = Field(default_factory=dict, description="Metric deltas from previous evidence.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Evidence reliability, not diagnosis confidence.")
    notes: list[str] = Field(default_factory=list, description="Collection/parser degradation notes.")


class Hypothesis(BaseModel):
    """Diagnosis candidate. It must cite evidence and may request validation."""

    id: str = Field(description="Hypothesis id.")
    kind: BottleneckKind = Field(description="Candidate bottleneck class.")
    summary: str = Field(description="Human-readable candidate explanation.")
    evidence_ids: list[str] = Field(default_factory=list, description="EvidenceItem ids supporting this candidate.")
    metric_ids: list[str] = Field(default_factory=list, description="Metric or derived metric ids supporting this candidate.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Diagnosis confidence.")
    reasoning: list[str] = Field(default_factory=list, description="Evidence-driven reasoning steps.")
    contradicting_evidence_ids: list[str] = Field(default_factory=list, description="Evidence that weakens this candidate.")
    verification_suggestions: list[str] = Field(default_factory=list, description="Next measurements to confirm or reject it.")
    verified: bool = Field(default=False, description="True after a validation round confirms this hypothesis.")


class DiagnosisResult(BaseModel):
    """Analyst output for one reasoning step."""

    hypotheses: list[Hypothesis] = Field(default_factory=list, description="Ranked bottleneck candidates.")
    evidence_sufficient: bool = Field(default=False, description="Whether final reporting can proceed.")
    missing_evidence: list[str] = Field(default_factory=list, description="Questions that still need measurement.")
    rejected_causes: list[str] = Field(default_factory=list, description="Causes ruled out by evidence.")
    stability_notes: list[str] = Field(default_factory=list, description="Noise/repetition assessment.")


class ReplanRequest(BaseModel):
    """Structured request from Analyst/Replanner to Planner/Toolsmith."""

    reason: str = Field(description="Why another sampling round is needed.")
    missing_evidence: list[str] = Field(default_factory=list, description="Evidence gaps to close.")
    target_hypothesis_ids: list[str] = Field(default_factory=list, description="Hypotheses this replan validates.")
    preferred_event_groups: list[PerfEventGroup] = Field(default_factory=list, description="Recommended event groups.")
    preferred_tools: list[SamplingTool] = Field(default_factory=list, description="Recommended tools.")
    max_extra_rounds: int = Field(default=1, ge=0, description="Budget requested by the replanner.")


class Report(BaseModel):
    """Machine-readable final report contract."""

    task: TaskSpec = Field(description="Original normalized task.")
    environment: EnvProfile = Field(description="Environment used for profiling.")
    sampling_methods: list[SamplingPlan] = Field(default_factory=list, description="Plans that were executed.")
    evidence_chain: list[EvidenceItem] = Field(default_factory=list, description="Ordered evidence packets.")
    diagnosis: DiagnosisResult = Field(description="Final diagnosis result.")
    key_metrics: list[MetricSample | DerivedMetric] = Field(default_factory=list, description="Metrics highlighted in the report.")
    optimization_suggestions: list[str] = Field(default_factory=list, description="Evidence-backed optimization suggestions.")
    next_steps: list[str] = Field(default_factory=list, description="Recommended follow-up work.")
    raw_data_index: dict[str, str] = Field(default_factory=dict, description="Artifact logical name to file path.")
    markdown_path: str | None = Field(default=None, description="Rendered Markdown report path.")
    json_path: str | None = Field(default=None, description="Rendered JSON report path.")


def artifact_exists(path: str | Path | None) -> bool:
    if path is None:
        return False
    return Path(path).exists()


def compact_jsonable(model: BaseModel) -> dict[str, Any]:
    """Return a JSON-ready dict suitable for prompts and persisted artifacts."""

    return model.model_dump(mode="json", exclude_none=True)
