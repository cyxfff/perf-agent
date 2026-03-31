from __future__ import annotations

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.tools.base import BaseCommandTool


class PerfStatTool(BaseCommandTool):
    name = "perf_stat"

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        events = list(dict.fromkeys(action.event_names))
        event_args: list[str] = []
        if events:
            event_args = ["-e", ",".join(events)]
        interval_args: list[str] = []
        if action.sample_interval_ms:
            interval_args = ["-x,", "-I", str(action.sample_interval_ms)]
        if state.target_pid is not None and not state.target_cmd:
            return ["perf", "stat", *interval_args, *event_args, "-p", str(state.target_pid), "--", "sleep", "1"]
        if event_args:
            return ["perf", "stat", *interval_args, *event_args, "--", *state.target_cmd]
        return ["perf", "stat", "-d", "--", *state.target_cmd]
