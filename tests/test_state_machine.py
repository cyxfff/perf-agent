from __future__ import annotations

from pathlib import Path

from perf_agent.main import build_state
from perf_agent.orchestrator.engine import Orchestrator


def test_orchestrator_runs_cpu_case_to_completion(tmp_path: Path) -> None:
    state = build_state(Path("examples/cpu_bound_case.json"))
    state = Orchestrator(output_root=tmp_path).run(state)

    assert state.status == "done"
    assert state.final_report is not None
    assert state.final_report.detected_bottlenecks
    assert state.final_report.target.source_file_count > 0
    assert state.hypotheses[0].kind == "cpu_bound"
    assert (tmp_path / state.run_id / "state.json").exists()
    assert (tmp_path / state.run_id / "report.md").exists()
    assert (tmp_path / state.run_id / "report.html").exists()
    assert (tmp_path / state.run_id / "target.json").exists()
    assert (tmp_path / state.run_id / "source_manifest.json").exists()
