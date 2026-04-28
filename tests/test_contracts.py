from __future__ import annotations

from perf_agent.memory import MemoryManager
from perf_agent.models.contracts import (
    DiagnosisResult,
    EnvProfile,
    EvidenceItem,
    ExecutionResult,
    MetricSample,
    PerfEventGroup,
    Report,
    SamplingPlan,
    TaskSpec,
)
from perf_agent.models.state import AnalysisState


def test_contract_models_are_json_serializable() -> None:
    task = TaskSpec(goal="IPC is low", command=["./demo"], max_rounds=3)
    env = EnvProfile(os_name="Linux", perf_available=True, available_events=["cycles", "instructions"])
    event_group = PerfEventGroup(
        name="baseline_core",
        events=["cycles", "instructions"],
        purpose="Measure instruction efficiency.",
    )
    plan = SamplingPlan(
        id="plan_1",
        round_index=1,
        phase="baseline",
        rationale="Build baseline counters.",
        tools=["perf_stat"],
        event_groups=[event_group],
        command=["./demo"],
    )
    result = ExecutionResult(
        action_id="act_1",
        tool="perf_stat",
        command=["perf", "stat", "./demo"],
        exit_code=0,
        duration_sec=1.0,
        success=True,
    )
    sample = MetricSample(
        id="met_1",
        metric="cycles",
        value=100.0,
        source="perf_stat",
        scope="process",
    )
    evidence = EvidenceItem(id="ev_1", round_index=1, plan_id=plan.id, metrics=[sample])
    diagnosis = DiagnosisResult(evidence_sufficient=True)
    report = Report(task=task, environment=env, sampling_methods=[plan], evidence_chain=[evidence], diagnosis=diagnosis)

    payload = report.model_dump(mode="json")

    assert payload["task"]["command"] == ["./demo"]
    assert result.model_dump(mode="json")["success"] is True
    assert payload["sampling_methods"][0]["event_groups"][0]["name"] == "baseline_core"


def test_analysis_state_exposes_contract_lifecycle_status() -> None:
    state = AnalysisState(run_id="run_test", status="profiling_environment")

    assert state.lifecycle_status == "ENV_PROBING"
    assert state.model_dump(mode="json")["lifecycle_status"] == "ENV_PROBING"


def test_memory_manager_keeps_context_compact() -> None:
    state = AnalysisState(
        run_id="run_test",
        goal="Find low IPC cause",
        target_cmd=["./demo"],
    )

    context = MemoryManager().short_term_context(state)

    assert context.goal == "Find low IPC cause"
    assert context.target_cmd == ["./demo"]
    assert context.evidence_summaries == []
