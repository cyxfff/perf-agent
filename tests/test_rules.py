from __future__ import annotations

from datetime import datetime, timezone

from perf_agent.models.observation import Observation
from perf_agent.rules.classifier import classify_observations


def test_classifier_prioritizes_io_bound_when_wait_and_disk_util_are_high() -> None:
    now = datetime.now(timezone.utc)
    observations = [
        Observation(
            id="obs_1",
            source="pidstat",
            category="io",
            metric="wait_pct",
            value=42.0,
            unit="percent",
            normalized_value=0.42,
            scope="process",
            timestamp=now,
        ),
        Observation(
            id="obs_2",
            source="iostat",
            category="io",
            metric="disk_util_pct",
            value=89.0,
            unit="percent",
            normalized_value=0.89,
            scope="system",
            timestamp=now,
        ),
        Observation(
            id="obs_3",
            source="pidstat",
            category="cpu",
            metric="cpu_utilization_pct",
            value=25.0,
            unit="percent",
            normalized_value=0.25,
            scope="process",
            timestamp=now,
        ),
    ]

    hypotheses = classify_observations(observations)

    assert hypotheses
    assert hypotheses[0].kind == "io_bound"
    assert hypotheses[0].supporting_observation_ids == ["obs_1", "obs_2", "obs_3"]
