from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from perf_agent.models.action import PlannedAction
from perf_agent.models.contracts import LifecycleStatus
from perf_agent.models.evidence import EvidencePack
from perf_agent.models.environment import AnalysisIntent, EnvironmentCapability, EventMapping
from perf_agent.models.hypothesis import Hypothesis
from perf_agent.models.observation import Observation
from perf_agent.models.report import FinalReport, SourceFinding


class AnalysisTask(BaseModel):
    goal: str | None = None
    executable_path: str | None = None
    target_args: list[str] = Field(default_factory=list)
    target_cmd: list[str] = Field(default_factory=list)
    target_pid: int | None = None
    workload_label: str | None = None
    source_dir: str | None = None
    build_cmd: list[str] = Field(default_factory=list)
    max_verification_rounds: int = 2
    mock_outputs: dict[str, str] = Field(default_factory=dict)
    cwd: str | None = None
    env: dict[str, str] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    node: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    persisted: bool = Field(default=False, exclude=True)


class EvidenceRequest(BaseModel):
    id: str
    intent: str
    question: str
    phase: Literal["baseline", "verification", "source_correlation"] = "baseline"
    granularity: Literal["process", "system", "thread", "function", "timeline"] = "process"
    priority: int = 100
    requested_by: str = "planner"
    rationale: str = ""
    preferred_tools: list[str] = Field(default_factory=list)
    round_index: int = 0
    status: Literal["planned", "tool_selected", "collecting", "completed", "failed", "cancelled"] = "planned"


class ExecutionPlan(BaseModel):
    request_id: str
    round_index: int = 0
    selected_tools: list[str] = Field(default_factory=list)
    fallback_tools: list[str] = Field(default_factory=list)
    rationale: str = ""
    expected_artifacts: list[str] = Field(default_factory=list)
    planned_by: str = "toolsmith"
    status: Literal["planned", "actions_created", "completed", "failed", "cancelled"] = "planned"


class LLMTrace(BaseModel):
    agent: str
    prompt_kind: str
    status: Literal["used", "fallback", "error"]
    note: str
    model: str | None = None
    transport: str | None = None


class AnalysisState(BaseModel):
    run_id: str
    status: Literal[
        "init",
        "running",
        "profiling_environment",
        "planning",
        "tool_selecting",
        "collecting",
        "parsing",
        "analyzing",
        "verifying",
        "source_analyzing",
        "reporting",
        "done",
        "failed",
    ] = "init"
    executable_path: str | None = None
    target_args: list[str] = Field(default_factory=list)
    target_cmd: list[str] = Field(default_factory=list)
    target_pid: int | None = None
    workload_label: str | None = None
    source_dir: str | None = None
    build_cmd: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)
    source_language_hints: list[str] = Field(default_factory=list)
    source_findings: list[SourceFinding] = Field(default_factory=list)
    environment: EnvironmentCapability = Field(default_factory=EnvironmentCapability)
    planned_intents: list[AnalysisIntent] = Field(default_factory=list)
    evidence_requests: list[EvidenceRequest] = Field(default_factory=list)
    execution_plans: list[ExecutionPlan] = Field(default_factory=list)
    event_mappings: list[EventMapping] = Field(default_factory=list)
    planning_rounds_done: int = 0
    evidence_packs: list[EvidencePack] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    actions_taken: list[PlannedAction] = Field(default_factory=list)
    pending_actions: list[PlannedAction] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    final_report: FinalReport | None = None
    max_verification_rounds: int = 2
    verification_rounds_done: int = 0
    error_message: str | None = None
    audit_log: list[AuditEvent] = Field(default_factory=list)
    llm_traces: list[LLMTrace] = Field(default_factory=list)
    parsed_action_ids: list[str] = Field(default_factory=list)
    goal: str | None = None
    mock_outputs: dict[str, str] = Field(default_factory=dict)
    cwd: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    progress_messages: list[str] = Field(default_factory=list)

    @classmethod
    def from_task(cls, task: AnalysisTask, run_id: str) -> "AnalysisState":
        return cls(
            run_id=run_id,
            executable_path=task.executable_path,
            target_args=task.target_args,
            target_cmd=task.target_cmd,
            target_pid=task.target_pid,
            workload_label=task.workload_label,
            source_dir=task.source_dir,
            build_cmd=task.build_cmd,
            max_verification_rounds=task.max_verification_rounds,
            goal=task.goal,
            mock_outputs=task.mock_outputs,
            cwd=task.cwd,
            env=task.env,
        )

    def add_audit(self, node: str, message: str, **details: Any) -> None:
        self.audit_log.append(AuditEvent(node=node, message=message, details=details))

    def add_error(self, message: str) -> None:
        self.error_message = message
        self.add_audit("system", "error", error=message)

    def add_progress(self, message: str) -> None:
        self.progress_messages.append(message)

    def record_llm_trace(
        self,
        agent: str,
        prompt_kind: str,
        status: Literal["used", "fallback", "error"],
        note: str,
        model: str | None = None,
        transport: str | None = None,
    ) -> None:
        trace = LLMTrace(
            agent=agent,
            prompt_kind=prompt_kind,
            status=status,
            note=note,
            model=model,
            transport=transport,
        )
        self.llm_traces.append(trace)
        self.add_audit(agent, f"llm:{prompt_kind}", status=status, note=note, model=model, transport=transport)

    def pending_evidence_requests(self) -> list[EvidenceRequest]:
        return [request for request in self.evidence_requests if request.status == "planned"]

    @computed_field
    @property
    def lifecycle_status(self) -> LifecycleStatus:
        mapping: dict[str, LifecycleStatus] = {
            "init": "INIT",
            "running": "INIT",
            "profiling_environment": "ENV_PROBING",
            "planning": "PLAN_GENERATED",
            "tool_selecting": "PLAN_GENERATED",
            "collecting": "RUNNING",
            "parsing": "EVIDENCE_BUILT",
            "analyzing": "DIAGNOSING",
            "verifying": "REPLANNING",
            "source_analyzing": "REPORT_READY",
            "reporting": "REPORT_READY",
            "done": "REPORT_READY",
            "failed": "FAILED",
        }
        return mapping[self.status]

    def find_request(self, request_id: str) -> EvidenceRequest | None:
        return next((request for request in self.evidence_requests if request.id == request_id), None)

    def find_execution_plan(self, request_id: str) -> ExecutionPlan | None:
        return next((plan for plan in self.execution_plans if plan.request_id == request_id), None)

    def upsert_execution_plan(self, candidate: ExecutionPlan) -> None:
        existing = self.find_execution_plan(candidate.request_id)
        if existing is None:
            self.execution_plans.append(candidate)
            return
        existing.round_index = candidate.round_index
        existing.selected_tools = list(candidate.selected_tools)
        existing.fallback_tools = list(candidate.fallback_tools)
        existing.rationale = candidate.rationale
        existing.expected_artifacts = list(candidate.expected_artifacts)
        existing.planned_by = candidate.planned_by
        existing.status = candidate.status

    def output_dir(self, root: str | Path) -> Path:
        return Path(root) / self.run_id
