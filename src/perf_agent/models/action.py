from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PlannedAction(BaseModel):
    id: str
    request_id: str | None = None
    tool: str
    command: list[str]
    reason: str
    expected_output: str
    timeout_sec: int = 60
    retryable: bool = True
    status: Literal["pending", "running", "done", "failed", "skipped"] = "pending"
    intent: str | None = None
    phase: str = "baseline"
    event_names: list[str] = Field(default_factory=list)
    call_graph_mode: str | None = None
    display_name: str | None = None
    strategy_note: str | None = None
    sample_interval_ms: int | None = None
    sandbox_runtime: str | None = None
    sandbox_summary: str | None = None
