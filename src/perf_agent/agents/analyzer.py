from __future__ import annotations

from perf_agent.evidence.summarizer import EvidenceSummarizer
from perf_agent.llm.client import LLMClient
from perf_agent.models.state import AnalysisState
from perf_agent.rules.classifier import classify_observations


class Analyzer:
    def __init__(self, llm_client: LLMClient | None = None, rule_config_path: str | None = None) -> None:
        self.llm_client = llm_client or LLMClient()
        self.rule_config_path = rule_config_path
        self.summarizer = EvidenceSummarizer()

    def run(self, state: AnalysisState) -> AnalysisState:
        rule_candidates = classify_observations(state.observations, config_path=self.rule_config_path)
        evidence_pack = self.summarizer.build_pack(state, rule_candidates)
        state.evidence_packs.append(evidence_pack)
        state.hypotheses = self.llm_client.generate_hypotheses(
            observations=state.observations,
            rule_candidates=rule_candidates,
            actions_taken=state.actions_taken,
            evidence_pack=evidence_pack,
        )
        if self.llm_client.enabled:
            if self.llm_client.last_error:
                state.record_llm_trace(
                    "analyzer",
                    "analysis",
                    "fallback",
                    self.llm_client.last_error,
                    model=self.llm_client.model,
                    transport=self.llm_client.last_transport,
                )
            else:
                state.record_llm_trace(
                    "analyzer",
                    "analysis",
                    "used",
                    f"Generated {len(state.hypotheses)} hypothesis(es) from structured observations.",
                    model=self.llm_client.model,
                    transport=self.llm_client.last_transport,
                )
        state.add_audit(
            "analyzer",
            "generated hypotheses from rules and structured observations",
            hypothesis_count=len(state.hypotheses),
            evidence_pack_summary=evidence_pack.summary,
        )
        return state
