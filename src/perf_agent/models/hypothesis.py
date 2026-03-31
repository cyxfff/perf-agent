from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Hypothesis(BaseModel):
    id: str
    kind: Literal[
        "cpu_bound",
        "memory_bound",
        "io_bound",
        "lock_contention",
        "scheduler_issue",
        "branch_mispredict",
        "unknown",
    ]
    summary: str
    reasoning_basis: list[str] = Field(default_factory=list)
    supporting_observation_ids: list[str] = Field(default_factory=list)
    contradicting_observation_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    needs_verification: bool = True
    suggested_actions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_support(self) -> "Hypothesis":
        if self.confidence > 0 and not self.supporting_observation_ids:
            raise ValueError("Hypotheses with non-zero confidence must cite observations.")
        return self
