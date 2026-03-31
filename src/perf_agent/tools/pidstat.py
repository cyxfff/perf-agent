from __future__ import annotations

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.tools.base import BaseCommandTool


class PidstatTool(BaseCommandTool):
    name = "pidstat"

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        if state.target_pid is not None:
            return ["pidstat", "-dur", "-p", str(state.target_pid), "-h", "1", "1"]
        return ["pidstat", "-dur", "-h", "1", "1"]
