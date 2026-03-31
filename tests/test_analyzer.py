from __future__ import annotations

from datetime import datetime, timezone

from perf_agent.agents.analyzer import Analyzer
from perf_agent.agents.verifier import Verifier
from perf_agent.models.hypothesis import Hypothesis
from perf_agent.models.observation import Observation
from perf_agent.models.state import AnalysisState


def test_analyzer_generates_cpu_hypothesis_with_suggested_actions() -> None:
    now = datetime.now(timezone.utc)
    state = AnalysisState(
        run_id="run_test",
        goal="Diagnose CPU bottleneck",
        target_cmd=["python", "demo.py"],
        observations=[
            Observation(
                id="obs_1",
                source="perf_stat",
                category="cpu",
                metric="cpu_utilization_pct",
                value=98.7,
                unit="percent",
                normalized_value=0.987,
                scope="process",
                timestamp=now,
            ),
            Observation(
                id="obs_2",
                source="pidstat",
                category="cpu",
                metric="usr_pct",
                value=94.0,
                unit="percent",
                normalized_value=0.94,
                scope="process",
                timestamp=now,
            ),
        ],
    )

    Analyzer().run(state)

    assert state.hypotheses
    assert state.hypotheses[0].kind == "cpu_bound"
    assert state.hypotheses[0].suggested_actions
    assert "perf record" in state.hypotheses[0].suggested_actions[0].lower()


def test_verifier_requests_follow_up_collection_for_low_confidence_cpu_case() -> None:
    state = AnalysisState(
        run_id="run_test",
        goal="Diagnose CPU bottleneck",
        target_cmd=["python", "demo.py"],
        max_verification_rounds=2,
        hypotheses=[
            Hypothesis(
                id="hyp_2",
                kind="cpu_bound",
                summary="CPU utilization is somewhat high.",
                reasoning_basis=["High CPU utilization was observed."],
                confidence=0.6,
                supporting_observation_ids=["obs_1"],
                needs_verification=True,
            )
        ],
    )

    Verifier().run(state)

    assert any(action.tool == "perf_record" for action in state.pending_actions)
    assert state.verification_rounds_done == 1
