from __future__ import annotations

from perf_agent.models.observation import Observation


def score_from_observations(observations: list[Observation], base: float = 0.4, strength: float = 0.0) -> float:
    score = base + 0.07 * len(observations) + strength
    return round(max(0.0, min(score, 0.95)), 2)
