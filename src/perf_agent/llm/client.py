from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from perf_agent.config import PromptTemplates, load_prompt_templates
from perf_agent.interaction.models import InteractiveIntentResult
from perf_agent.llm.schemas import (
    AnalyzerOutput,
    EvidenceRequestDraft,
    HypothesisDraft,
    ReporterOutput,
    StrategistOutput,
    StructuredActionInput,
    StructuredObservationInput,
    ToolsmithOutput,
    VerifierOutput,
)
from perf_agent.models.action import PlannedAction
from perf_agent.models.evidence import EvidencePack
from perf_agent.models.hypothesis import Hypothesis
from perf_agent.models.observation import Observation
from perf_agent.models.report import FinalReport
from perf_agent.utils.ids import new_id


class LLMClient:
    def __init__(self, prompt_config_path: str | None = None) -> None:
        self._load_env()
        disabled = os.getenv("PERF_AGENT_DISABLE_LLM", "").lower() in {"1", "true", "yes", "on"}
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        self.model = (
            os.getenv("PERF_AGENT_MODEL")
            or os.getenv("LLM_MODEL_ID")
            or os.getenv("DEEPSEEK_MODEL")
            or "gpt-4.1-mini"
        )
        self.base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL")
        if self.base_url is None and os.getenv("DEEPSEEK_API_KEY"):
            self.base_url = "https://api.deepseek.com"
        self.timeout_sec = float(os.getenv("PERF_AGENT_TIMEOUT_SEC", "20"))
        self.enabled = bool(self.api_key) and not disabled
        self.client = (
            OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout_sec,
                max_retries=1,
            )
            if self.enabled
            else None
        )
        self.prompts: PromptTemplates = load_prompt_templates(prompt_config_path)
        self.last_error: str | None = None
        self.last_transport: str | None = None

    def generate_hypotheses(
        self,
        observations: list[Observation],
        rule_candidates: list[Hypothesis],
        actions_taken: list[PlannedAction],
        evidence_pack: EvidencePack | None = None,
    ) -> list[Hypothesis]:
        self.last_error = None
        self.last_transport = None
        payload = self._build_analyzer_payload(observations, rule_candidates, actions_taken, evidence_pack)
        if self.enabled:
            try:
                parsed = self._parse_structured_output(
                    schema=AnalyzerOutput,
                    system_prompt=self.prompts.analyzer_prompt,
                    user_payload=payload,
                    max_output_tokens=1400,
                )
                validated = self._validate_hypotheses(parsed.hypotheses, observations)
                if validated:
                    return validated
                self.last_error = "Analyzer LLM returned no usable hypotheses; falling back to deterministic output."
            except Exception as exc:
                self.last_error = f"Analyzer LLM call failed: {exc}"
        if not rule_candidates and observations:
            return self._validate_hypotheses(
                [
                    HypothesisDraft(
                        kind="unknown",
                        summary="Current evidence does not yet support a specific bottleneck class.",
                        reasoning_basis=["No rule candidate crossed the confidence threshold."],
                        supporting_observation_ids=[observations[0].id],
                        confidence=0.2,
                        needs_verification=True,
                        suggested_actions=["Collect another round of baseline metrics."],
                    )
                ],
                observations,
            )

        return self._validate_hypotheses(
            [
                HypothesisDraft(
                    kind=candidate.kind,
                    summary=candidate.summary,
                    reasoning_basis=candidate.reasoning_basis,
                    supporting_observation_ids=candidate.supporting_observation_ids,
                    contradicting_observation_ids=candidate.contradicting_observation_ids,
                    confidence=candidate.confidence,
                    needs_verification=candidate.needs_verification or candidate.confidence < 0.8,
                    suggested_actions=candidate.suggested_actions,
                )
                for candidate in rule_candidates
            ],
            observations,
        )

    def review_verification(
        self,
        observations: list[Observation],
        hypotheses: list[Hypothesis],
        actions_taken: list[PlannedAction],
        evidence_pack: EvidencePack | None = None,
    ) -> VerifierOutput:
        self.last_error = None
        self.last_transport = None
        payload = self._build_verifier_payload(observations, hypotheses, actions_taken, evidence_pack)
        if self.enabled:
            try:
                parsed = self._parse_structured_output(
                    schema=VerifierOutput,
                    system_prompt=self.prompts.verifier_prompt,
                    user_payload=payload,
                    max_output_tokens=900,
                )
                if parsed.evidence_sufficient or parsed.requested_actions or parsed.evidence_gaps:
                    return parsed
                self.last_error = "Verifier LLM returned an empty decision; falling back to deterministic output."
            except Exception as exc:
                self.last_error = f"Verifier LLM call failed: {exc}"
        if not hypotheses:
            return VerifierOutput(
                evidence_sufficient=False,
                evidence_gaps=["No supported hypothesis is available yet."],
                requested_actions=["collect_instruction_efficiency"],
            )

        top = max(hypotheses, key=lambda item: item.confidence)
        if top.confidence >= 0.8 and not top.needs_verification:
            return VerifierOutput(evidence_sufficient=True)

        action_map = {
            "cpu_bound": "collect_hot_function_callgraph",
            "memory_bound": "collect_cache_memory_pressure",
            "io_bound": "collect_io_wait_detail",
            "lock_contention": "collect_hot_function_callgraph",
            "scheduler_issue": "collect_scheduler_context",
            "branch_mispredict": "collect_hot_function_callgraph",
            "unknown": "collect_instruction_efficiency",
        }
        return VerifierOutput(
            evidence_sufficient=False,
            evidence_gaps=[f"Evidence is incomplete for hypothesis {top.kind}."],
            requested_actions=[action_map[top.kind]],
        )

    def review_report(
        self,
        observations: list[Observation],
        hypotheses: list[Hypothesis],
        artifacts: list[str],
        draft_report: FinalReport,
        evidence_pack: EvidencePack | None = None,
    ) -> ReporterOutput:
        self.last_error = None
        self.last_transport = None
        payload = self._build_reporter_payload(observations, hypotheses, artifacts, evidence_pack)
        if self.enabled:
            try:
                parsed = self._parse_structured_output(
                    schema=ReporterOutput,
                    system_prompt=self.prompts.reporter_prompt,
                    user_payload=payload,
                    max_output_tokens=1200,
                )
                if parsed.executive_summary.strip():
                    return parsed
                self.last_error = "Reporter LLM returned an empty summary; falling back to deterministic output."
            except Exception as exc:
                self.last_error = f"Reporter LLM call failed: {exc}"
        return ReporterOutput(
            executive_summary=draft_report.executive_summary,
            rejected_alternatives=draft_report.rejected_alternatives,
            recommended_next_steps=draft_report.recommended_next_steps,
        )

    def interpret_interactive_input(
        self,
        normalized_input: dict[str, Any],
        session_context: dict[str, Any],
        query_view: dict[str, Any],
    ) -> InteractiveIntentResult | None:
        self.last_error = None
        self.last_transport = None
        if not self.enabled:
            return None
        payload = {
            "session_context": session_context,
            "normalized_input": normalized_input,
            "query_view": query_view,
        }
        try:
            parsed = self._parse_structured_output(
                schema=InteractiveIntentResult,
                system_prompt=self.prompts.interactive_intake_prompt,
                user_payload=payload,
                max_output_tokens=900,
            )
        except Exception as exc:
            self.last_error = f"Interactive intake LLM call failed: {exc}"
            return None
        return parsed if isinstance(parsed, InteractiveIntentResult) else None

    def structured_completion(
        self,
        schema: type[
            AnalyzerOutput
            | VerifierOutput
            | ReporterOutput
            | InteractiveIntentResult
            | StrategistOutput
            | ToolsmithOutput
            | EvidenceRequestDraft
            | Any
        ],
        system_prompt: str,
        user_payload: dict[str, Any],
        *,
        max_output_tokens: int = 1200,
    ) -> Any:
        self.last_error = None
        self.last_transport = None
        if not self.enabled:
            raise RuntimeError("LLM client is not enabled.")
        return self._parse_structured_output(
            schema=schema,
            system_prompt=system_prompt,
            user_payload=user_payload,
            max_output_tokens=max_output_tokens,
        )

    def _build_analyzer_payload(
        self,
        observations: list[Observation],
        rule_candidates: list[Hypothesis],
        actions_taken: list[PlannedAction],
        evidence_pack: EvidencePack | None,
    ) -> dict[str, Any]:
        return {
            "observations": [self._observation_input(item).model_dump(mode="json") for item in observations],
            "rule_candidates": [item.model_dump(mode="json") for item in rule_candidates],
            "actions_taken": [self._action_input(item).model_dump(mode="json") for item in actions_taken],
            "evidence_pack": evidence_pack.model_dump(mode="json") if evidence_pack is not None else None,
        }

    def _build_verifier_payload(
        self,
        observations: list[Observation],
        hypotheses: list[Hypothesis],
        actions_taken: list[PlannedAction],
        evidence_pack: EvidencePack | None,
    ) -> dict[str, Any]:
        return {
            "observations": [self._observation_input(item).model_dump(mode="json") for item in observations],
            "hypotheses": [item.model_dump(mode="json") for item in hypotheses],
            "actions_taken": [self._action_input(item).model_dump(mode="json") for item in actions_taken],
            "evidence_pack": evidence_pack.model_dump(mode="json") if evidence_pack is not None else None,
        }

    def _build_reporter_payload(
        self,
        observations: list[Observation],
        hypotheses: list[Hypothesis],
        artifacts: list[str],
        evidence_pack: EvidencePack | None,
    ) -> dict[str, Any]:
        return {
            "observations": [self._observation_input(item).model_dump(mode="json") for item in observations],
            "hypotheses": [item.model_dump(mode="json") for item in hypotheses],
            "artifacts": artifacts,
            "evidence_pack": evidence_pack.model_dump(mode="json") if evidence_pack is not None else None,
        }

    def _observation_input(self, observation: Observation) -> StructuredObservationInput:
        return StructuredObservationInput.model_validate(observation.model_dump(mode="json", exclude={"raw_excerpt"}))

    def _action_input(self, action: PlannedAction) -> StructuredActionInput:
        return StructuredActionInput.model_validate(action.model_dump(mode="json"))

    def _validate_hypotheses(
        self,
        hypotheses: list[HypothesisDraft],
        observations: list[Observation],
    ) -> list[Hypothesis]:
        valid_ids = {item.id for item in observations}
        validated: list[Hypothesis] = []
        for draft in hypotheses:
            confidence = max(0.0, min(float(draft.confidence), 1.0))
            kind = draft.kind if draft.kind in {
                "cpu_bound",
                "memory_bound",
                "io_bound",
                "lock_contention",
                "scheduler_issue",
                "branch_mispredict",
                "unknown",
            } else "unknown"
            support = [obs_id for obs_id in draft.supporting_observation_ids if obs_id in valid_ids]
            contradictions = [obs_id for obs_id in draft.contradicting_observation_ids if obs_id in valid_ids]
            if confidence > 0 and not support and observations:
                support = [observations[0].id]
            validated.append(
                Hypothesis(
                    id=new_id("hyp"),
                    kind=kind,
                    summary=draft.summary,
                    reasoning_basis=draft.reasoning_basis,
                    supporting_observation_ids=support,
                    contradicting_observation_ids=contradictions,
                    confidence=confidence,
                    needs_verification=draft.needs_verification,
                    suggested_actions=draft.suggested_actions,
                )
            )
        return validated

    def _parse_structured_output(
        self,
        schema: type[
            AnalyzerOutput
            | VerifierOutput
            | ReporterOutput
            | InteractiveIntentResult
            | StrategistOutput
            | ToolsmithOutput
        ],
        system_prompt: str,
        user_payload: dict[str, Any],
        max_output_tokens: int,
    ) -> AnalyzerOutput | VerifierOutput | ReporterOutput | InteractiveIntentResult:
        if self.client is None:
            raise RuntimeError("LLM client is not configured.")

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=True, indent=2),
            },
        ]

        try:
            response = self.client.responses.parse(
                model=self.model,
                input=messages,
                text_format=schema,
                temperature=0,
                max_output_tokens=max_output_tokens,
            )
            self.last_transport = "responses.parse"
            return response.output_parsed
        except Exception as responses_exc:
            chat_completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=schema,
                temperature=0,
                max_completion_tokens=max_output_tokens,
            )
            self.last_transport = "chat.completions.parse"
            message = chat_completion.choices[0].message
            if message.parsed is None:
                raise RuntimeError(f"No parsed content returned. Responses error was: {responses_exc}")
            return message.parsed

    def _load_env(self) -> None:
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[3]
        load_dotenv(project_root / ".env", override=False)
        load_dotenv(override=False)
