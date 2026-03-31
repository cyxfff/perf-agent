from __future__ import annotations

from perf_agent.config import load_tool_configs
from perf_agent.planning.event_mapper import EventMapper
from perf_agent.planning.intents import build_baseline_intents
from perf_agent.models.state import AnalysisState
from perf_agent.tools.runner import ToolRunner


class Planner:
    def __init__(
        self,
        tool_runner: ToolRunner | None = None,
        tool_config_path: str | None = None,
        event_config_path: str | None = None,
    ) -> None:
        self.tool_runner = tool_runner or ToolRunner()
        self.tool_configs = load_tool_configs(tool_config_path)
        self.event_mapper = EventMapper(
            tool_runner=self.tool_runner,
            tool_configs=self.tool_configs,
            event_config_path=event_config_path,
        )

    def run(self, state: AnalysisState) -> AnalysisState:
        if state.pending_actions:
            state.add_audit("planner", "actions already pending")
            return state

        if state.actions_taken:
            state.add_audit("planner", "baseline planning already finished")
            return state

        intents = build_baseline_intents(state)
        round_index = state.planning_rounds_done + 1
        actions, mappings = self.event_mapper.build_actions(state, intents, round_index=round_index)
        state.pending_actions.extend(actions)
        state.planned_intents = intents
        state.event_mappings.extend(mappings)
        state.planning_rounds_done = round_index
        state.add_audit(
            "planner",
            "planned baseline experiment round",
            round_index=round_index,
            intents=[intent.name for intent in intents],
            tools=[action.tool for action in actions],
        )
        return state
