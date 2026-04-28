from __future__ import annotations

from pathlib import Path

from perf_agent.config import load_event_intent_configs, project_root
from perf_agent.llm.client import LLMClient
from perf_agent.llm.schemas import ToolsmithOutput
from perf_agent.models.state import AnalysisState, ExecutionPlan
from perf_agent.planning.event_mapper import EventMapper
from perf_agent.tools.runner import ToolRunner


TOOL_DOCS_DIR = project_root() / "tool_docs"


class Toolsmith:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        tool_runner: ToolRunner | None = None,
        tool_config_path: str | None = None,
        event_config_path: str | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.tool_runner = tool_runner or ToolRunner()
        self.intent_configs = load_event_intent_configs(event_config_path)
        self.event_mapper = EventMapper(
            tool_runner=self.tool_runner,
            tool_configs=None,
            event_config_path=event_config_path,
            tool_config_path=tool_config_path,
        )

    def run(self, state: AnalysisState) -> AnalysisState:
        pending = state.pending_evidence_requests()
        if not pending:
            state.add_audit("toolsmith", "no pending evidence requests")
            return state

        built_actions = 0
        for request in pending:
            plan = self._select_plan(state, request.id)
            selected_tools = set(plan.selected_tools)
            actions, mappings = self.event_mapper.build_actions_for_request(
                state,
                request,
                round_index=request.round_index or max(state.planning_rounds_done, 1),
                selected_tools=selected_tools,
            )
            actions = [action for action in actions if not self._action_already_seen(state, action)]
            if not actions:
                request.status = "cancelled"
                plan.status = "cancelled"
                state.upsert_execution_plan(plan)
                state.add_audit(
                    "toolsmith",
                    "request produced no executable actions",
                    request_id=request.id,
                    intent=request.intent,
                    selected_tools=plan.selected_tools,
                )
                continue
            for action in actions:
                action.request_id = request.id
            for mapping in mappings:
                mapping.request_id = request.id
            state.pending_actions.extend(actions)
            state.event_mappings.extend(mappings)
            request.status = "tool_selected"
            plan.status = "actions_created"
            state.upsert_execution_plan(plan)
            built_actions += len(actions)
            state.add_audit(
                "toolsmith",
                "planned execution for request",
                request_id=request.id,
                intent=request.intent,
                selected_tools=plan.selected_tools,
                action_count=len(actions),
            )

        if built_actions == 0 and not state.pending_actions:
            state.add_error("No executable actions could be produced from the current evidence requests.")
        return state

    def _select_plan(self, state: AnalysisState, request_id: str) -> ExecutionPlan:
        request = state.find_request(request_id)
        if request is None:
            raise ValueError(f"Unknown evidence request: {request_id}")
        candidates = self._candidate_tools(state, request.intent, request.preferred_tools)

        if self.llm_client.enabled:
            try:
                parsed = self.llm_client.structured_completion(
                    schema=ToolsmithOutput,
                    system_prompt=self.llm_client.prompts.toolsmith_prompt,
                    user_payload={
                        "request": request.model_dump(mode="json"),
                        "environment": self._environment_payload(state),
                        "candidate_tools": candidates,
                        "tool_docs": {item["tool"]: self._tool_doc(item["tool"]) for item in candidates},
                    },
                    max_output_tokens=900,
                )
                selected = [tool for tool in parsed.selected_tools if tool in {item["tool"] for item in candidates}]
                if selected:
                    state.record_llm_trace(
                        "toolsmith",
                        "execution_planning",
                        "used",
                        parsed.note or f"Selected tools {', '.join(selected)} for {request.intent}.",
                        model=self.llm_client.model,
                        transport=self.llm_client.last_transport,
                    )
                    return ExecutionPlan(
                        request_id=request.id,
                        round_index=request.round_index,
                        selected_tools=selected,
                        fallback_tools=[tool for tool in parsed.fallback_tools if tool in {item["tool"] for item in candidates}],
                        rationale=parsed.rationale or request.rationale,
                        expected_artifacts=parsed.expected_artifacts,
                    )
                state.record_llm_trace(
                    "toolsmith",
                    "execution_planning",
                    "fallback",
                    "LLM returned no valid tool selection; using heuristic execution planning.",
                    model=self.llm_client.model,
                    transport=self.llm_client.last_transport,
                )
            except Exception as exc:
                state.record_llm_trace(
                    "toolsmith",
                    "execution_planning",
                    "fallback",
                    f"LLM execution planning failed; using heuristic execution planning: {exc}",
                    model=self.llm_client.model,
                    transport=self.llm_client.last_transport,
                )
        selected = self._heuristic_tools(request.intent, candidates, request.preferred_tools)
        return ExecutionPlan(
            request_id=request.id,
            round_index=request.round_index,
            selected_tools=selected,
            rationale=request.rationale or request.question,
        )

    def _candidate_tools(self, state: AnalysisState, intent: str, preferred_tools: list[str]) -> list[dict[str, str]]:
        available = set(state.environment.available_tools)
        config = self.intent_configs.get(intent)
        hinted = list(preferred_tools or (config.preferred_tools if config is not None else []))
        if intent == "system_cpu_profile" and not hinted:
            hinted = ["sar", "mpstat"]
        if intent == "baseline_runtime" and not hinted:
            hinted = ["time"]
        notes = {
            "time": "Cheap wall-time, RSS, and context-switch baseline.",
            "perf_stat": "Process-level cycles, instructions, IPC, cache, and optional interval counters.",
            "perf_record": "Function-level hotspot and callgraph attribution.",
            "pidstat": "Process or thread CPU, wait, and context-switch view.",
            "mpstat": "Host-wide CPU pressure fallback.",
            "iostat": "Device utilization and await breakdown.",
            "sar": "Host-wide CPU utilization and iowait with per-core visibility.",
        }
        candidates: list[dict[str, str]] = []
        for tool in hinted:
            if tool in available:
                candidates.append({"tool": tool, "note": notes.get(tool, tool)})
        if not candidates:
            for tool in ("time", "perf_stat", "perf_record", "pidstat", "mpstat", "iostat", "sar"):
                if tool in available:
                    candidates.append({"tool": tool, "note": notes.get(tool, tool)})
        return candidates

    def _heuristic_tools(self, intent: str, candidates: list[dict[str, str]], preferred_tools: list[str]) -> list[str]:
        candidate_names = [item["tool"] for item in candidates]
        if intent == "baseline_runtime":
            return ["time"] if "time" in candidate_names else candidate_names[:1]
        if intent == "system_cpu_profile":
            if "sar" in candidate_names:
                return ["sar"]
            if "mpstat" in candidate_names:
                return ["mpstat"]
        if intent == "scheduler_context":
            if "pidstat" in candidate_names:
                return ["pidstat"]
            if "perf_stat" in candidate_names:
                return ["perf_stat"]
            if "mpstat" in candidate_names:
                return ["mpstat"]
        if intent == "io_wait_detail":
            if "iostat" in candidate_names:
                return ["iostat"]
            if "pidstat" in candidate_names:
                return ["pidstat"]
        if intent == "hot_function_callgraph":
            return ["perf_record"] if "perf_record" in candidate_names else candidate_names[:1]
        if intent == "temporal_behavior":
            return ["perf_stat"] if "perf_stat" in candidate_names else candidate_names[:1]
        for tool in preferred_tools:
            if tool in candidate_names:
                return [tool]
        if not candidate_names:
            return []
        if "perf_stat" in candidate_names:
            return ["perf_stat"]
        if "sar" in candidate_names:
            return ["sar"]
        return [candidate_names[0]]

    def _tool_doc(self, tool_name: str) -> str:
        path = TOOL_DOCS_DIR / f"{tool_name}.Tool.md"
        return path.read_text(encoding="utf-8", errors="replace")[:1600] if path.exists() else ""

    def _environment_payload(self, state: AnalysisState) -> dict[str, object]:
        return {
            "execution_target": state.environment.execution_target,
            "profiling_backend": state.environment.profiling_backend_name,
            "available_tools": state.environment.available_tools,
            "perf_available": state.environment.perf_available,
            "callgraph_modes": state.environment.callgraph_modes,
            "platform_profile": state.environment.platform_profile,
            "arch": state.environment.arch,
        }

    def _action_already_seen(self, state: AnalysisState, candidate) -> bool:
        all_actions = [*state.actions_taken, *state.pending_actions]
        return any(
            action.tool == candidate.tool
            and action.event_names == candidate.event_names
            and action.call_graph_mode == candidate.call_graph_mode
            and action.intent == candidate.intent
            and action.phase == candidate.phase
            for action in all_actions
        )
