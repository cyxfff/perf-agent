from __future__ import annotations

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.security.sandbox import SandboxManager
from perf_agent.storage.artifact_store import ArtifactStore
from perf_agent.tools.base import Tool, ToolResult
from perf_agent.tools.flamegraph import FlamegraphTool
from perf_agent.tools.iostat import IostatTool
from perf_agent.tools.mpstat import MpstatTool
from perf_agent.tools.perf_record import PerfRecordTool
from perf_agent.tools.perf_stat import PerfStatTool
from perf_agent.tools.pidstat import PidstatTool
from perf_agent.tools.time_tool import TimeTool


class ToolRunner:
    def __init__(self, sandbox_manager: SandboxManager | None = None) -> None:
        self.registry: dict[str, Tool] = {
            "time": TimeTool(sandbox_manager=sandbox_manager),
            "perf_stat": PerfStatTool(sandbox_manager=sandbox_manager),
            "perf_record": PerfRecordTool(sandbox_manager=sandbox_manager),
            "pidstat": PidstatTool(sandbox_manager=sandbox_manager),
            "mpstat": MpstatTool(sandbox_manager=sandbox_manager),
            "iostat": IostatTool(sandbox_manager=sandbox_manager),
            "flamegraph": FlamegraphTool(sandbox_manager=sandbox_manager),
        }

    def get_tool(self, name: str) -> Tool:
        if name not in self.registry:
            raise KeyError(f"Unknown tool: {name}")
        return self.registry[name]

    def run_action(self, action: PlannedAction, state: AnalysisState, store: ArtifactStore) -> ToolResult:
        tool = self.get_tool(action.tool)
        action.status = "running"
        result = tool.run(state, action, store)
        action.command = tool.build_command(state, action)
        action.status = "done" if result.success else "failed"
        return result
