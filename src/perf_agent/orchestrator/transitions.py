from __future__ import annotations

from perf_agent.orchestrator.state_machine import RunStatus


def next_status(current: RunStatus) -> RunStatus:
    transitions: dict[RunStatus, RunStatus] = {
        "init": "running",
        "running": "profiling_environment",
        "profiling_environment": "planning",
        "planning": "collecting",
        "collecting": "parsing",
        "parsing": "analyzing",
        "analyzing": "verifying",
        "verifying": "source_analyzing",
        "source_analyzing": "reporting",
        "reporting": "done",
        "done": "done",
        "failed": "failed",
    }
    return transitions[current]
