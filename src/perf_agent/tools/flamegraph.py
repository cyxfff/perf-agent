from __future__ import annotations

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.tools.base import BaseCommandTool


class FlamegraphTool(BaseCommandTool):
    name = "flamegraph"

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        return ["sh", "-c", "echo flamegraph generation placeholder"]
