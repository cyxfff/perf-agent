from __future__ import annotations

from pydantic import BaseModel, Field


class StructuredObservationInput(BaseModel):
    id: str
    source: str
    category: str
    metric: str
    value: float | int | str
    unit: str | None = None
    normalized_value: float | None = None
    scope: str
    labels: dict[str, str] = Field(default_factory=dict)


class StructuredActionInput(BaseModel):
    id: str
    tool: str
    command: list[str] = Field(default_factory=list)
    reason: str
    expected_output: str
    status: str
    intent: str | None = None
    phase: str | None = None
    event_names: list[str] = Field(default_factory=list)


class HypothesisDraft(BaseModel):
    kind: str
    summary: str
    reasoning_basis: list[str] = Field(default_factory=list)
    supporting_observation_ids: list[str] = Field(default_factory=list)
    contradicting_observation_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    needs_verification: bool = True
    suggested_actions: list[str] = Field(default_factory=list)


class AnalyzerOutput(BaseModel):
    hypotheses: list[HypothesisDraft] = Field(default_factory=list)


class EvidenceRequestDraft(BaseModel):
    intent: str
    question: str
    phase: str = "baseline"
    granularity: str = "process"
    priority: int = 100
    preferred_tools: list[str] = Field(default_factory=list)
    rationale: str = ""


class StrategistOutput(BaseModel):
    requests: list[EvidenceRequestDraft] = Field(default_factory=list)
    note: str = ""


class ToolsmithOutput(BaseModel):
    selected_tools: list[str] = Field(default_factory=list)
    fallback_tools: list[str] = Field(default_factory=list)
    rationale: str = ""
    expected_artifacts: list[str] = Field(default_factory=list)
    note: str = ""


class VerifierOutput(BaseModel):
    evidence_sufficient: bool = False
    evidence_gaps: list[str] = Field(default_factory=list)
    requested_actions: list[str] = Field(default_factory=list)


class ReporterOutput(BaseModel):
    executive_summary: str
    rejected_alternatives: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
