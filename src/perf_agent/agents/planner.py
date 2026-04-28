from __future__ import annotations

from perf_agent.config import load_event_intent_configs
from perf_agent.llm.client import LLMClient
from perf_agent.llm.schemas import StrategistOutput
from perf_agent.memory import MemoryManager
from perf_agent.planning.intents import build_baseline_intents
from perf_agent.models.state import AnalysisState
from perf_agent.models.state import EvidenceRequest
from perf_agent.utils.ids import new_id


class Planner:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        tool_config_path: str | None = None,
        event_config_path: str | None = None,
        memory_manager: MemoryManager | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.intent_configs = load_event_intent_configs(event_config_path)
        self.memory_manager = memory_manager or MemoryManager()

    def run(self, state: AnalysisState) -> AnalysisState:
        if state.pending_actions or state.pending_evidence_requests():
            state.add_audit("planner", "requests or actions already pending")
            return state

        if state.actions_taken:
            state.add_audit("planner", "baseline planning already finished")
            return state

        intents = build_baseline_intents(state)
        round_index = state.planning_rounds_done + 1
        requests = self._plan_requests(state, intents, round_index)
        state.evidence_requests.extend(requests)
        state.planned_intents = [
            intent for intent in intents if any(request.intent == intent.name for request in requests)
        ]
        state.planning_rounds_done = round_index
        state.add_audit(
            "planner",
            "planned baseline experiment round",
            round_index=round_index,
            intents=[request.intent for request in requests],
        )
        return state

    def _plan_requests(self, state: AnalysisState, intents, round_index: int) -> list[EvidenceRequest]:
        if self.llm_client.enabled:
            try:
                allowed = [self._request_from_intent(intent, round_index) for intent in intents]
                parsed = self.llm_client.structured_completion(
                    schema=StrategistOutput,
                    system_prompt=self.llm_client.prompts.strategist_prompt,
                    user_payload={
                        "phase": "baseline",
                        "target_cmd": state.target_cmd,
                        "goal": state.goal,
                        "workload_label": state.workload_label,
                        "environment": {
                            "execution_target": state.environment.execution_target,
                            "profiling_backend": state.environment.profiling_backend_name,
                            "available_tools": state.environment.available_tools,
                            "perf_available": state.environment.perf_available,
                            "callgraph_modes": state.environment.callgraph_modes,
                            "platform_profile": state.environment.platform_profile,
                            "arch": state.environment.arch,
                        },
                        "allowed_requests": [request.model_dump(mode="json") for request in allowed],
                        "existing_requests": [request.model_dump(mode="json") for request in state.evidence_requests],
                        "short_term_memory": self.memory_manager.short_term_context(state).model_dump(mode="json"),
                        "long_term_patterns": [
                            pattern.model_dump(mode="json")
                            for pattern in self.memory_manager.relevant_patterns(state)
                        ],
                    },
                    max_output_tokens=1200,
                )
                selected: list[EvidenceRequest] = []
                allowed_map = {request.intent: request for request in allowed}
                for item in parsed.requests:
                    if item.intent not in allowed_map:
                        continue
                    template = allowed_map[item.intent]
                    selected.append(
                        template.model_copy(
                            update={
                                "question": item.question or template.question,
                                "granularity": item.granularity or template.granularity,
                                "priority": item.priority or template.priority,
                                "preferred_tools": item.preferred_tools or template.preferred_tools,
                                "rationale": item.rationale or template.rationale,
                            }
                        )
                    )
                if selected:
                    state.record_llm_trace(
                        "planner",
                        "planning",
                        "used",
                        parsed.note or f"Planned {len(selected)} baseline evidence request(s).",
                        model=self.llm_client.model,
                        transport=self.llm_client.last_transport,
                    )
                    return selected
                state.record_llm_trace(
                    "planner",
                    "planning",
                    "fallback",
                    "LLM returned no valid baseline requests; using heuristic planning.",
                    model=self.llm_client.model,
                    transport=self.llm_client.last_transport,
                )
            except Exception as exc:
                state.record_llm_trace(
                    "planner",
                    "planning",
                    "fallback",
                    f"LLM baseline planning failed; using heuristic planning: {exc}",
                    model=self.llm_client.model,
                    transport=self.llm_client.last_transport,
                )
        return [self._request_from_intent(intent, round_index) for intent in intents]

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
        rationale = {
            "baseline_runtime": "先建立 wall time、RSS 和粗粒度 CPU / scheduler 基线。",
            "system_cpu_profile": "先确认主机整体 CPU 与 iowait 压力，区分局部热点和全局繁忙。",
            "instruction_efficiency": "先判断 cycles、instructions 和 IPC 是否异常。",
            "cache_memory_pressure": "先判断 cache miss、memory pressure 和 backend 停顿。",
            "frontend_backend_bound": "如果平台支持，补充 top-down 前后端细分。",
            "scheduler_context": "先判断调度、上下文切换和迁移压力。",
            "branch_behavior": "补充分支预测和错误预测成本。",
            "io_wait_detail": "补充系统层 I/O 等待与设备利用率证据。",
            "hot_function_callgraph": "需要将热点定位到函数和主要调用链。",
            "source_correlation": "需要把热点进一步映射到源码位置。",
            "temporal_behavior": "需要确认瓶颈是稳定存在还是阶段性尖峰。",
        }.get(intent.name, intent.question)
        return EvidenceRequest(
            id=new_id("req"),
            intent=intent.name,
            question=intent.question,
            phase=intent.phase,
            granularity=granularity,
            priority=intent.priority,
            requested_by=intent.requested_by,
            rationale=rationale,
            preferred_tools=list(config.preferred_tools if config is not None else []),
            round_index=round_index,
        )
