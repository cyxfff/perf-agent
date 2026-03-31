from __future__ import annotations

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.tools.base import BaseCommandTool


class IostatTool(BaseCommandTool):
    name = "iostat"

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        return ["iostat", "-dx", "1", "1"]
