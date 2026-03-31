from __future__ import annotations

from pydantic import BaseModel, Field


class EvidencePack(BaseModel):
    round_index: int
    summary: str
    top_observation_ids: list[str] = Field(default_factory=list)
    highlighted_metrics: list[str] = Field(default_factory=list)
    hotspot_symbols: list[str] = Field(default_factory=list)
    timeline_metrics: list[str] = Field(default_factory=list)
    top_processes: list[str] = Field(default_factory=list)
    top_threads: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
