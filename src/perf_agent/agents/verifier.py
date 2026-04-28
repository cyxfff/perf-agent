from __future__ import annotations

from perf_agent.llm.client import LLMClient
from perf_agent.config import load_event_intent_configs
from perf_agent.planning.intents import build_follow_up_intents
from perf_agent.models.state import AnalysisState
from perf_agent.models.state import EvidenceRequest
from perf_agent.utils.ids import new_id


class Verifier:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        tool_config_path: str | None = None,
        event_config_path: str | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.intent_configs = load_event_intent_configs(event_config_path)

    def should_verify(self, state: AnalysisState) -> bool:
        if state.verification_rounds_done >= state.max_verification_rounds:
            return False
        if not state.hypotheses:
            return True
        return any(hypothesis.needs_verification for hypothesis in state.hypotheses)

    def run(self, state: AnalysisState) -> AnalysisState:
        if state.verification_rounds_done >= state.max_verification_rounds:
            state.add_audit("verifier", "verification limit reached")
            return state

        decision = self.llm_client.review_verification(
            observations=state.observations,
            hypotheses=state.hypotheses,
            actions_taken=state.actions_taken,
            evidence_pack=state.evidence_packs[-1] if state.evidence_packs else None,
        )
        if self.llm_client.enabled:
            if self.llm_client.last_error:
                state.record_llm_trace(
                    "verifier",
                    "verification",
                    "fallback",
                    self.llm_client.last_error,
                    model=self.llm_client.model,
                    transport=self.llm_client.last_transport,
                )
            else:
                state.record_llm_trace(
                    "verifier",
                    "verification",
                    "used",
                    "Verification decision consumed structured observations and hypotheses.",
                    model=self.llm_client.model,
                    transport=self.llm_client.last_transport,
                )
        if decision.evidence_sufficient:
            state.add_audit("verifier", "current evidence is sufficient")
            return state

        intents = self._resolve_follow_up_intents(state, decision.requested_actions)
        if not intents:
            state.add_audit("verifier", "no follow-up intent could be mapped")
            return state

        round_index = state.planning_rounds_done + 1
        requests = [self._request_from_intent(intent, round_index) for intent in intents]
        requests = [request for request in requests if not self._request_already_seen(state, request)]
        if not requests:
            state.add_audit("verifier", "all follow-up evidence requests were already executed or pending")
            return state

        state.evidence_requests.extend(requests)
        state.planned_intents = intents
        state.planning_rounds_done = round_index
        state.verification_rounds_done += 1
        state.add_audit(
            "verifier",
            "scheduled follow-up verification round",
            intents=[intent.name for intent in intents],
            requests=[request.intent for request in requests],
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

    def _request_from_intent(self, intent, round_index: int) -> EvidenceRequest:
        config = self.intent_configs.get(intent.name)
        granularity = {
            "baseline_runtime": "process",
            "system_cpu_profile": "system",
            "instruction_efficiency": "process",
            "cache_memory_pressure": "process",
            "frontend_backend_bound": "process",
            "scheduler_context": "thread",
            "branch_behavior": "process",
            "io_wait_detail": "system",
            "hot_function_callgraph": "function",
            "source_correlation": "function",
            "temporal_behavior": "timeline",
        }.get(intent.name, "process")
        return EvidenceRequest(
            id=new_id("req"),
            intent=intent.name,
            question=intent.question,
            phase=intent.phase,
            granularity=granularity,
            priority=intent.priority,
            requested_by=intent.requested_by,
            rationale=intent.question,
            preferred_tools=list(config.preferred_tools if config is not None else []),
            round_index=round_index,
        )

    def _request_already_seen(self, state: AnalysisState, candidate: EvidenceRequest) -> bool:
        return any(
            request.intent == candidate.intent
            and request.phase == candidate.phase
            and request.status not in {"failed", "cancelled"}
            for request in state.evidence_requests
        )
