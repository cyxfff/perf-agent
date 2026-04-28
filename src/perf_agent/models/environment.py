from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EventSourceType = Literal["hardware", "software", "tracepoint", "raw", "metric", "pmu", "unknown"]
ExecutionTarget = Literal["host", "device", "pid_attach"]

IntentName = Literal[
    "baseline_runtime",
    "system_cpu_profile",
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


class EventDescriptor(BaseModel):
    name: str
    source_type: EventSourceType = "unknown"
    semantic_keys: list[str] = Field(default_factory=list)
    stat_usable: bool = True
    record_usable: bool = True
    interval_usable: bool = True
    portability_score: int = 50
    notes: list[str] = Field(default_factory=list)


class ConnectedDevice(BaseModel):
    serial: str
    status: str
    transport_id: str | None = None
    product: str | None = None
    model: str | None = None
    device_name: str | None = None
    is_remote: bool = False
    host: str | None = None
    port: int | None = None
    arch: str | None = None
    os_release: str | None = None
    sdk: str | None = None
    backend_tools: list[str] = Field(default_factory=list)
    platform_hint: str | None = None
    selectable: bool = False
    selection_score: int = 0
    notes: list[str] = Field(default_factory=list)


class EnvironmentCapability(BaseModel):
    os_name: str | None = None
    kernel_release: str | None = None
    arch: str | None = None
    platform_profile: str | None = None
    cpu_model: str | None = None
    cpu_max_mhz: str | None = None
    cpu_min_mhz: str | None = None
    cpu_scaling_mhz: str | None = None
    logical_cores: int | None = None
    physical_cores: int | None = None
    l1d_cache: str | None = None
    l1i_cache: str | None = None
    l2_cache: str | None = None
    l3_cache: str | None = None
    numa_nodes: int | None = None
    perf_available: bool = False
    perf_version: str | None = None
    adb_available: bool = False
    execution_target: ExecutionTarget = "host"
    profiling_backend_name: str | None = None
    profiling_backend_tool: str | None = None
    profiling_backend_summary: str | None = None
    available_tools: list[str] = Field(default_factory=list)
    available_events: list[str] = Field(default_factory=list)
    event_aliases: dict[str, list[str]] = Field(default_factory=dict)
    event_catalog: dict[str, EventDescriptor] = Field(default_factory=dict)
    event_probe_results: dict[str, bool] = Field(default_factory=dict)
    event_sources: list[str] = Field(default_factory=list)
    connected_devices: list[ConnectedDevice] = Field(default_factory=list)
    selected_device_serial: str | None = None
    selected_device_summary: str | None = None
    callgraph_modes: list[str] = Field(default_factory=list)
    stat_event_budget: int = 4
    interval_event_budget: int = 4
    topdown_supported: bool = False
    topdown_events: list[str] = Field(default_factory=list)
    tma_metrics: list[str] = Field(default_factory=list)
    hybrid_pmus: list[str] = Field(default_factory=list)
    perf_permissions: str | None = None
    executable_kind: str | None = None
    executable_stripped: bool | None = None
    executable_has_symbols: bool | None = None
    supports_addr2line: bool = False
    sandbox_enabled: bool = False
    available_sandbox_runtimes: list[str] = Field(default_factory=list)
    configured_sandbox_runtime: str | None = None
    selected_sandbox_runtime: str | None = None
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
    request_id: str | None = None
    tool: str
    mode: Literal["runtime", "stat", "record", "system"]
    selected_events: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    rationale: str
    display_name: str | None = None
    availability_notes: list[str] = Field(default_factory=list)
