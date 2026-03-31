from __future__ import annotations

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.tools.base import BaseCommandTool


class TimeTool(BaseCommandTool):
    name = "time"

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        if state.target_pid is not None and not state.target_cmd:
            return ["sh", "-c", f"/usr/bin/time -v sh -c 'kill -0 {state.target_pid}'"]
        return ["/usr/bin/time", "-v", *state.target_cmd]
