from __future__ import annotations

from pydantic import BaseModel, Field


class TargetSummary(BaseModel):
    command: list[str] = Field(default_factory=list)
    executable_path: str | None = None
    source_dir: str | None = None
    source_file_count: int = 0
    runtime_notes: list[str] = Field(default_factory=list)


class SourceFinding(BaseModel):
    file_path: str
    line_no: int
    line_end: int | None = None
    symbol_hint: str | None = None
    issue_type: str
    rationale: str
    snippet: str
    related_hypothesis: str | None = None
    mapping_method: str | None = None
    confidence: float | None = None


class ChartSpec(BaseModel):
    chart_id: str
    title: str
    chart_type: str
    metrics: list[str] = Field(default_factory=list)
    rationale: str
    focus: str | None = None


class FinalReport(BaseModel):
    executive_summary: str
    target: TargetSummary
    environment_summary: list[str] = Field(default_factory=list)
    experiment_history: list[str] = Field(default_factory=list)
    evidence_summary: list[str] = Field(default_factory=list)
    chart_specs: list[ChartSpec] = Field(default_factory=list)
    detected_bottlenecks: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    rejected_alternatives: list[str] = Field(default_factory=list)
    source_findings: list[SourceFinding] = Field(default_factory=list)
    confidence_overall: float
    recommended_next_steps: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
