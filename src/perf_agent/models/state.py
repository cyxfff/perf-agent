from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field

from perf_agent.models.action import PlannedAction
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


class AnalysisState(BaseModel):
    run_id: str
    status: Literal[
        "init",
        "running",
        "profiling_environment",
        "planning",
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

    def output_dir(self, root: str | Path) -> Path:
        return Path(root) / self.run_id
