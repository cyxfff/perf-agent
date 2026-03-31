from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Observation(BaseModel):
    id: str
    source: str
    category: Literal["cpu", "memory", "cache", "branch", "io", "lock", "scheduler", "callgraph", "system"]
    metric: str
    value: float | int | str
    unit: str | None = None
    normalized_value: float | None = None
    scope: Literal["process", "thread", "system", "function", "callchain"]
    timestamp: datetime
    labels: dict[str, str] = Field(default_factory=dict)
    raw_excerpt: str | None = None
    evidence_level: Literal["direct", "derived"] = "direct"
    parser_version: str = "v1"
