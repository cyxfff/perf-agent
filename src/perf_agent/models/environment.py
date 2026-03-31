from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


IntentName = Literal[
    "baseline_runtime",
    "instruction_efficiency",
    "temporal_behavior",
    "branch_behavior",
    "cache_memory_pressure",
    "frontend_backend_bound",
    "scheduler_context",
    "io_wait_detail",
    "hot_function_callgraph",
    "source_correlation",
]


class EnvironmentCapability(BaseModel):
    os_name: str | None = None
    kernel_release: str | None = None
    arch: str | None = None
    cpu_model: str | None = None
    logical_cores: int | None = None
    physical_cores: int | None = None
    perf_available: bool = False
    perf_version: str | None = None
    available_events: list[str] = Field(default_factory=list)
    event_aliases: dict[str, list[str]] = Field(default_factory=dict)
    event_sources: list[str] = Field(default_factory=list)
    callgraph_modes: list[str] = Field(default_factory=list)
    topdown_supported: bool = False
    topdown_events: list[str] = Field(default_factory=list)
    tma_metrics: list[str] = Field(default_factory=list)
    hybrid_pmus: list[str] = Field(default_factory=list)
    perf_permissions: str | None = None
    executable_kind: str | None = None
    executable_stripped: bool | None = None
    executable_has_symbols: bool | None = None
    supports_addr2line: bool = False
    notes: list[str] = Field(default_factory=list)


class AnalysisIntent(BaseModel):
    name: IntentName
    question: str
    phase: Literal["baseline", "verification", "source_correlation"] = "baseline"
    priority: int = 100
    requested_by: str = "planner"


class EventMapping(BaseModel):
    round_index: int
    phase: str
    intent: str
    tool: str
    mode: Literal["runtime", "stat", "record", "system"]
    selected_events: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    rationale: str
    display_name: str | None = None
    availability_notes: list[str] = Field(default_factory=list)
