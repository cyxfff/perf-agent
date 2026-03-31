from __future__ import annotations

from perf_agent.config import load_tool_configs
from perf_agent.llm.client import LLMClient
from perf_agent.planning.event_mapper import EventMapper
from perf_agent.planning.intents import build_follow_up_intents
from perf_agent.models.state import AnalysisState
from perf_agent.tools.runner import ToolRunner


class Verifier:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        tool_runner: ToolRunner | None = None,
        tool_config_path: str | None = None,
        event_config_path: str | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.tool_runner = tool_runner or ToolRunner()
        self.tool_configs = load_tool_configs(tool_config_path)
        self.event_mapper = EventMapper(
            tool_runner=self.tool_runner,
            tool_configs=self.tool_configs,
            event_config_path=event_config_path,
        )

    def should_verify(self, state: AnalysisState) -> bool:
        if state.verification_rounds_done >= state.max_verification_rounds:
            return False
        if not state.hypotheses:
            return True
        return any(hypothesis.needs_verification for hypothesis in state.hypotheses)

    def run(self, state: AnalysisState) -> AnalysisState:
        if state.verification_rounds_done >= state.max_verification_rounds:
            state.add_audit("verifier", "verification limit reached")
            state.pending_actions = []
            return state

        decision = self.llm_client.review_verification(
            observations=state.observations,
            hypotheses=state.hypotheses,
            actions_taken=state.actions_taken,
            evidence_pack=state.evidence_packs[-1] if state.evidence_packs else None,
        )
        if decision.evidence_sufficient:
            state.pending_actions = []
            state.add_audit("verifier", "current evidence is sufficient")
            return state

        intents = self._resolve_follow_up_intents(state, decision.requested_actions)
        if not intents:
            state.pending_actions = []
            state.add_audit("verifier", "no follow-up intent could be mapped")
            return state

        round_index = state.planning_rounds_done + 1
        actions, mappings = self.event_mapper.build_actions(state, intents, round_index=round_index)
        actions = [action for action in actions if not self._action_already_seen(state, action)]
        if not actions:
            state.pending_actions = []
            state.add_audit("verifier", "all follow-up actions were already executed or pending")
            return state

        state.pending_actions = actions
        state.planned_intents = intents
        state.event_mappings.extend(mappings)
        state.planning_rounds_done = round_index
        state.verification_rounds_done += 1
        state.add_audit(
            "verifier",
            "scheduled follow-up verification round",
            intents=[intent.name for intent in intents],
            tools=[action.tool for action in actions],
            evidence_gaps=decision.evidence_gaps,
        )
        return state

    def _resolve_follow_up_intents(self, state: AnalysisState, requested_actions: list[str]) -> list:
        mapping = {
            "run_perf_record_callgraph": "hot_function_callgraph",
            "run_iostat_sample": "io_wait_detail",
            "run_mpstat_sample": "scheduler_context",
            "run_perf_stat_baseline": "instruction_efficiency",
            "collect_hot_function_callgraph": "hot_function_callgraph",
            "collect_cache_memory_pressure": "cache_memory_pressure",
            "collect_scheduler_context": "scheduler_context",
            "collect_io_wait_detail": "io_wait_detail",
            "collect_instruction_efficiency": "instruction_efficiency",
        }
        defaults = build_follow_up_intents(state, state.hypotheses)
        if requested_actions:
            allowed = {intent.name: intent for intent in defaults}
            selected = [allowed[mapping[name]] for name in requested_actions if name in mapping and mapping[name] in allowed]
            if selected:
                selected_names = {intent.name for intent in selected}
                for intent in defaults:
                    if intent.name == "temporal_behavior" and intent.name not in selected_names:
                        selected.append(intent)
                return selected
        return defaults

    def _action_already_seen(self, state: AnalysisState, candidate) -> bool:
        all_actions = [*state.actions_taken, *state.pending_actions]
        return any(
            action.tool == candidate.tool
            and action.event_names == candidate.event_names
            and action.call_graph_mode == candidate.call_graph_mode
            and action.intent == candidate.intent
            for action in all_actions
        )
