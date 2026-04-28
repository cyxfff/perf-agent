from __future__ import annotations

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.tools.base import BaseCommandTool


class SarTool(BaseCommandTool):
    name = "sar"

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        return ["sar", "-P", "ALL", "1", "1"]
