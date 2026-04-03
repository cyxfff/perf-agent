from __future__ import annotations

import re

from perf_agent.config import EventIntentConfig, ToolConfig, load_event_intent_configs
from perf_agent.models.action import PlannedAction
from perf_agent.models.environment import AnalysisIntent, EventDescriptor, EventMapping
from perf_agent.models.state import AnalysisState
from perf_agent.tools.backend import select_backend, tool_display_label
from perf_agent.tools.runner import ToolRunner
from perf_agent.utils.ids import new_id

ARM_ARCH_EVENT_KEYS = {
    "cycles",
    "instructions",
    "cache-references",
    "cache-misses",
    "branches",
    "branch-misses",
    "bus-cycles",
    "stalled-cycles-frontend",
    "stalled-cycles-backend",
}


class EventMapper:
    def __init__(
        self,
        tool_runner: ToolRunner | None = None,
        tool_configs: dict[str, ToolConfig] | None = None,
        event_config_path: str | None = None,
    ) -> None:
        self.tool_runner = tool_runner or ToolRunner()
        self.tool_configs = tool_configs or {}
        self.intent_configs = load_event_intent_configs(event_config_path)

    def build_actions(
        self,
        state: AnalysisState,
        intents: list[AnalysisIntent],
        round_index: int,
    ) -> tuple[list[PlannedAction], list[EventMapping]]:
        actions: list[PlannedAction] = []
        mappings: list[EventMapping] = []
        seen: set[tuple[str, tuple[str, ...], str | None, str]] = set()

        for intent in intents:
            for action, mapping in self._map_intent(state, intent, round_index):
                key = (action.tool, tuple(action.event_names), action.call_graph_mode, action.phase)
                if key in seen:
                    continue
                seen.add(key)
                tool = self.tool_runner.get_tool(action.tool)
                action.command = tool.build_command(state, action)
                actions.append(action)
                mappings.append(mapping)
        return actions, mappings

    def _map_intent(
        self,
        state: AnalysisState,
        intent: AnalysisIntent,
        round_index: int,
    ) -> list[tuple[PlannedAction, EventMapping]]:
        config = self.intent_configs.get(intent.name, EventIntentConfig())
        if intent.name == "baseline_runtime":
            if not self._tool_enabled("time") or state.environment.execution_target == "device":
                return []
            return [self._build_simple_action(state, intent, round_index, "time", "runtime", "用 /usr/bin/time -v 建立程序运行基线。")]

        if intent.name == "temporal_behavior":
            if not self._tool_enabled("perf_stat") or not state.environment.perf_available:
                return []
            config = self.intent_configs.get(intent.name, EventIntentConfig())
            events, fallback_used, notes = self._select_perf_events(state, config, intent_name=intent.name)
            rationale = "使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。"
            return self._build_perf_stat_actions(
                state,
                intent,
                round_index,
                events,
                rationale,
                fallback_used,
                notes,
                sample_interval_ms=100,
            )

        if intent.name in {"instruction_efficiency", "branch_behavior", "cache_memory_pressure", "frontend_backend_bound", "scheduler_context"}:
            if not self._tool_enabled("perf_stat") or not state.environment.perf_available:
                if intent.name != "scheduler_context":
                    return []
                built: list[tuple[PlannedAction, EventMapping]] = []
                if self._tool_enabled("pidstat"):
                    built.append(self._build_simple_action(state, intent, round_index, "pidstat", "system", "perf 不可用，退化为 pidstat 调度观测。"))
                if self._tool_enabled("mpstat"):
                    built.append(self._build_simple_action(state, intent, round_index, "mpstat", "system", "perf 不可用，退化为 mpstat 系统观测。"))
                return built
            events, fallback_used, notes = self._select_perf_events(state, config, intent_name=intent.name)
            rationale = self._intent_rationale(intent.name, fallback_used, events)
            built = self._build_perf_stat_actions(state, intent, round_index, events, rationale, fallback_used, notes)
            if intent.name == "scheduler_context" and state.environment.execution_target != "device":
                if self._tool_enabled("pidstat"):
                    built.append(self._build_simple_action(state, intent, round_index, "pidstat", "system", "补充进程级 CPU 与等待拆分。"))
                if self._tool_enabled("mpstat"):
                    built.append(self._build_simple_action(state, intent, round_index, "mpstat", "system", "补充系统级 CPU 与调度上下文。"))
            return built

        if intent.name == "io_wait_detail":
            if state.environment.execution_target == "device":
                return []
            built = []
            if self._tool_enabled("pidstat"):
                built.append(self._build_simple_action(state, intent, round_index, "pidstat", "system", "用 pidstat 看进程侧等待与 CPU 时间分布。"))
            if self._tool_enabled("iostat"):
                built.append(self._build_simple_action(state, intent, round_index, "iostat", "system", "用 iostat 看设备利用率和等待延迟。"))
            return built

        if intent.name in {"hot_function_callgraph", "source_correlation"}:
            if not self._tool_enabled("perf_record") or not state.environment.perf_available:
                return []
            mode = self._select_call_graph_mode(state, config)
            rationale = f"使用 perf record 采样热点函数和调用链，调用栈模式为 {mode}。"
            return [self._build_perf_record_action(state, intent, round_index, mode, rationale)]

        return []

    def _build_simple_action(
        self,
        state: AnalysisState,
        intent: AnalysisIntent,
        round_index: int,
        tool_name: str,
        mode: str,
        rationale: str,
    ) -> tuple[PlannedAction, EventMapping]:
        config = self.tool_configs.get(tool_name, ToolConfig())
        backend = select_backend(state)
        action = PlannedAction(
            id=new_id("act"),
            tool=tool_name,
            command=[],
            reason=intent.question,
            expected_output=f"{tool_name} output",
            timeout_sec=config.timeout_sec,
            intent=intent.name,
            phase=intent.phase,
            display_name=self._display_name(state, tool_name, intent.name),
            strategy_note=rationale,
        )
        mapping = EventMapping(
            round_index=round_index,
            phase=intent.phase,
            intent=intent.name,
            tool=tool_name,
            mode=mode,
            rationale=rationale,
            display_name=action.display_name,
        )
        return action, mapping

    def _build_perf_stat_action(
        self,
        state: AnalysisState,
        intent: AnalysisIntent,
        round_index: int,
        events: list[str],
        rationale: str,
        fallback_used: bool,
        notes: list[str],
        sample_interval_ms: int | None = None,
    ) -> tuple[PlannedAction, EventMapping]:
        config = self.tool_configs.get("perf_stat", ToolConfig())
        action = PlannedAction(
            id=new_id("act"),
            tool="perf_stat",
            command=[],
            reason=intent.question,
            expected_output="perf stat event counters",
            timeout_sec=config.timeout_sec,
            intent=intent.name,
            phase=intent.phase,
            event_names=events,
            display_name=self._display_name(state, "perf_stat", intent.name),
            strategy_note=rationale,
            sample_interval_ms=sample_interval_ms,
        )
        mapping = EventMapping(
            round_index=round_index,
            phase=intent.phase,
            intent=intent.name,
            tool="perf_stat",
            mode="stat",
            selected_events=events,
            fallback_used=fallback_used,
            rationale=rationale,
            display_name=action.display_name,
            availability_notes=notes,
        )
        return action, mapping

    def _build_perf_stat_actions(
        self,
        state: AnalysisState,
        intent: AnalysisIntent,
        round_index: int,
        events: list[str],
        rationale: str,
        fallback_used: bool,
        notes: list[str],
        sample_interval_ms: int | None = None,
    ) -> list[tuple[PlannedAction, EventMapping]]:
        batches = self._event_batches(state, events, sample_interval_ms=sample_interval_ms)
        total = len(batches)
        built: list[tuple[PlannedAction, EventMapping]] = []
        for index, batch in enumerate(batches, start=1):
            batch_suffix = f" 第 {index}/{total} 批。" if total > 1 else ""
            batch_notes = list(notes)
            if total > 1:
                batch_notes.append(
                    f"事件总量超出当前平台建议预算，已按 {len(batch)} 个事件一批拆分执行，以减少 multiplex 并保留 access/miss 成对指标。"
                )
            action, mapping = self._build_perf_stat_action(
                state,
                intent,
                round_index,
                batch,
                rationale + batch_suffix,
                fallback_used or total > 1,
                batch_notes,
                sample_interval_ms=sample_interval_ms,
            )
            if total > 1 and action.display_name:
                action.display_name = f"{action.display_name} [{index}/{total}]"
                mapping.display_name = action.display_name
            built.append((action, mapping))
        return built

    def _build_perf_record_action(
        self,
        state: AnalysisState,
        intent: AnalysisIntent,
        round_index: int,
        call_graph_mode: str,
        rationale: str,
    ) -> tuple[PlannedAction, EventMapping]:
        config = self.tool_configs.get("perf_record", ToolConfig(timeout_sec=180))
        record_event = self._select_record_event(state)
        action = PlannedAction(
            id=new_id("act"),
            tool="perf_record",
            command=[],
            reason=intent.question,
            expected_output="perf record callgraph samples",
            timeout_sec=config.timeout_sec,
            intent=intent.name,
            phase=intent.phase,
            event_names=[record_event] if record_event else [],
            call_graph_mode=call_graph_mode,
            display_name=self._display_name(state, "perf_record", intent.name),
            strategy_note=f"{rationale}{f' 采样事件为 {record_event}。' if record_event else ''}",
        )
        mapping = EventMapping(
            round_index=round_index,
            phase=intent.phase,
            intent=intent.name,
            tool="perf_record",
            mode="record",
            selected_events=[record_event] if record_event else [],
            rationale=f"{rationale}{f' 采样事件为 {record_event}。' if record_event else ''}",
            display_name=action.display_name,
        )
        return action, mapping

    def _select_perf_events(
        self,
        state: AnalysisState,
        config: EventIntentConfig,
        intent_name: str | None = None,
    ) -> tuple[list[str], bool, list[str]]:
        if not state.environment.perf_available:
            return config.fallback_events or config.preferred_events, True, ["perf 不可用，事件选择退化到默认模板。"]

        preferred = config.preferred_events or config.fallback_events
        if not state.environment.available_events:
            return preferred, False, ["未拿到完整 perf list，沿用默认事件模板。"]

        notes: list[str] = []
        selected = self._resolve_requested_events(state, preferred, notes, intent_name=intent_name)
        fallback_used = len(selected) != len(preferred)
        if fallback_used and config.fallback_events:
            fallbacks = self._resolve_requested_events(state, config.fallback_events, notes, intent_name=intent_name)
            selected.extend(event for event in fallbacks if event not in selected)
            notes.append("部分首选事件在当前机器上不可用，已自动退化到可用通用事件。")
        if not selected:
            selected = config.fallback_events or preferred
            notes.append("未发现匹配事件，直接使用通用 fallback 事件。")
            fallback_used = True
        if any("topdown" in event or event.startswith("tma_") for event in selected):
            notes.append("本轮事件里包含 top-down / TMA 指标，后续会结合前后端或内存子类拆分解释。")
        return list(dict.fromkeys(selected)), fallback_used, notes

    def _select_call_graph_mode(self, state: AnalysisState, config: EventIntentConfig) -> str:
        available = state.environment.callgraph_modes
        preferred = config.call_graph_modes or ["fp", "dwarf", "lbr"]
        for mode in preferred:
            if mode in available:
                return mode
        return available[0] if available else "fp"

    def _display_name(self, state: AnalysisState, tool_name: str, intent_name: str) -> str:
        tool_label = tool_display_label(tool_name, select_backend(state))
        intent_label = {
            "baseline_runtime": "运行时基线",
            "instruction_efficiency": "指令效率",
            "temporal_behavior": "时间序列行为",
            "branch_behavior": "分支行为",
            "cache_memory_pressure": "缓存与内存压力",
            "frontend_backend_bound": "前后端停顿",
            "scheduler_context": "调度上下文",
            "io_wait_detail": "I/O 等待",
            "hot_function_callgraph": "热点函数调用链",
            "source_correlation": "源码关联",
        }.get(intent_name, intent_name)
        return f"{tool_label} / {intent_label}"

    def _select_record_event(self, state: AnalysisState) -> str | None:
        for candidate in ("cycles", "cpu-cycles", "raw-cpu-cycles", "hw-cpu-cycles", "raw-cnt-cycles"):
            resolved = self._resolve_event_name(state, candidate)
            if resolved is not None:
                return resolved
        return None

    def _intent_rationale(self, intent_name: str, fallback_used: bool, events: list[str]) -> str:
        if intent_name == "instruction_efficiency":
            prefix = "判断 cycles、instructions 和 IPC 的健康度。"
        elif intent_name in {"cache_memory_pressure", "frontend_backend_bound"}:
            prefix = "判断 cache miss、内存压力以及前后端停顿。"
        elif intent_name == "temporal_behavior":
            prefix = "按固定时间间隔观察指标变化，判断瓶颈是否阶段性出现。"
        elif intent_name == "branch_behavior":
            prefix = "判断分支行为是否异常。"
        elif intent_name == "scheduler_context":
            prefix = "判断调度切换、迁移与系统级 CPU 上下文。"
        else:
            prefix = "执行当前分析意图。"
        suffix = "当前使用退化事件组合。" if fallback_used else "当前使用首选事件组合。"
        events_text = f" 事件为 {', '.join(events)}。" if events else ""
        return f"{prefix}{suffix}{events_text}"

    def _tool_enabled(self, tool_name: str) -> bool:
        return self.tool_configs.get(tool_name, ToolConfig()).enabled

    def _resolve_requested_events(
        self,
        state: AnalysisState,
        requested: list[str],
        notes: list[str],
        intent_name: str | None = None,
    ) -> list[str]:
        selected: list[str] = []
        for event_name in requested:
            resolved = self._resolve_event_name(state, event_name)
            if resolved is None:
                notes.append(f"当前机器未发现事件别名 {event_name}。")
                continue
            if not self._event_usable_with_stat_selector(state, resolved):
                notes.append(f"事件 {resolved} 当前不适合直接进入 perf stat 计数路径，本轮跳过。")
                continue
            selected.append(resolved)
        return list(dict.fromkeys(selected))

    def _resolve_event_name(self, state: AnalysisState, requested: str) -> str | None:
        aliases = state.environment.event_aliases
        for key in self._candidate_alias_keys(requested):
            candidates = aliases.get(key)
            if candidates:
                return self._prefer_event_variant(state, candidates, requested)

        requested_lower = requested.lower()
        suffix_matches = [
            item
            for item in state.environment.available_events
            if item.lower().endswith(f"/{requested_lower}/") or item.lower().endswith(requested_lower)
        ]
        if suffix_matches:
            return self._prefer_event_variant(state, suffix_matches, requested)
        return None

    def _candidate_alias_keys(self, requested: str) -> list[str]:
        lowered = requested.lower()
        candidates = [lowered, lowered.strip("/")]
        if "/" in lowered:
            candidates.append(lowered.strip("/").split("/")[-1])
        if lowered.startswith("cpu-"):
            candidates.append(lowered.removeprefix("cpu-"))
        if lowered == "branches":
            candidates.append("branch-instructions")
        return list(dict.fromkeys(candidate for candidate in candidates if candidate))

    def _prefer_event_variant(self, state: AnalysisState, candidates: list[str], requested: str) -> str:
        requested_lower = requested.lower()
        arch = self._active_arch(state)

        def score(candidate: str) -> tuple[int, int, int, int]:
            lowered = candidate.lower()
            descriptor = state.environment.event_catalog.get(candidate, EventDescriptor(name=candidate))
            exact = 0 if lowered == requested_lower or requested_lower in descriptor.semantic_keys else 1
            source_rank = self._source_rank(descriptor, requested_lower, arch)
            portability_rank = -descriptor.portability_score
            generic = 0 if "/" not in lowered and ":" not in lowered else 1
            depth = len(re.split(r"[/.:_-]+", lowered))
            return (exact, source_rank, portability_rank, generic, depth)

        return sorted(candidates, key=score)[0]

    def _active_arch(self, state: AnalysisState) -> str:
        if state.environment.execution_target == "device":
            selected = next(
                (device for device in state.environment.connected_devices if device.serial == state.environment.selected_device_serial),
                None,
            )
            if selected is not None and selected.arch:
                return selected.arch.lower()
            if state.environment.platform_profile in {"android", "harmony", "arm-linux"}:
                return "arm64"
        return (state.environment.arch or "").lower()

    def _event_usable_with_stat_selector(self, state: AnalysisState, event_name: str) -> bool:
        descriptor = state.environment.event_catalog.get(event_name)
        if descriptor is None:
            lowered = event_name.lower().strip()
            return not lowered.startswith("tma_")
        return descriptor.stat_usable

    def _event_batches(self, state: AnalysisState, events: list[str], sample_interval_ms: int | None = None) -> list[list[str]]:
        if not events:
            return [[]]
        budget = state.environment.interval_event_budget if sample_interval_ms else state.environment.stat_event_budget
        budget = max(2, budget or 4)
        bundles: list[list[str]] = []
        current_bundle: list[str] = []
        current_key = None
        for event in events:
            key = self._bundle_key(state, event)
            if current_bundle and key != current_key:
                bundles.append(current_bundle)
                current_bundle = []
            current_bundle.append(event)
            current_key = key
        if current_bundle:
            bundles.append(current_bundle)
        batches: list[list[str]] = []
        active: list[str] = []
        for bundle in bundles:
            if active and len(active) + len(bundle) > budget:
                batches.append(active)
                active = []
            if len(bundle) > budget:
                if active:
                    batches.append(active)
                    active = []
                for start in range(0, len(bundle), budget):
                    batches.append(bundle[start : start + budget])
                continue
            active.extend(bundle)
        if active:
            batches.append(active)
        return [list(dict.fromkeys(batch)) for batch in batches if batch]

    def _bundle_key(self, state: AnalysisState, event_name: str) -> str:
        descriptor = state.environment.event_catalog.get(event_name)
        semantic_keys = set(descriptor.semantic_keys if descriptor is not None else [])
        lowered = event_name.lower()
        if "instructions" in semantic_keys or "cycles" in semantic_keys or lowered in {"instructions", "cycles", "slots"}:
            return "efficiency"
        if "branch-misses" in semantic_keys or "branches" in semantic_keys:
            return "branch"
        if "context-switches" in semantic_keys or "cpu-migrations" in semantic_keys or "page-faults" in semantic_keys:
            return "scheduler"
        if any(key in semantic_keys for key in {"l1d-cache", "l1d-cache-access", "l1d-cache-refill", "l1d-cache-hit", "l1_access", "l1_hit_count", "l1_miss_count"}):
            return "l1-cache"
        if any(key in semantic_keys for key in {"l2d-cache", "l2d-cache-access", "l2d-cache-refill", "l2_access", "l2_miss_count"}):
            return "l2-cache"
        if any(key in semantic_keys for key in {"l3d-cache", "l3d-cache-access", "l3d-cache-refill", "l3_access"}):
            return "l3-cache"
        if any(key in semantic_keys for key in {"llc-access", "llc-miss", "llc_access_count", "llc_miss_count"}):
            return "llc-cache"
        if "cache-references" in semantic_keys or "cache-misses" in semantic_keys:
            return "cache"
        if lowered.startswith("topdown-") or lowered.startswith("tma_"):
            return "topdown"
        return lowered

    def _source_rank(self, descriptor: EventDescriptor, requested_lower: str, arch: str) -> int:
        source_type = descriptor.source_type
        if requested_lower.startswith("topdown-") or requested_lower.startswith("tma_"):
            order = ["metric", "hardware", "pmu", "raw", "software", "tracepoint", "unknown"]
        elif requested_lower in {"context-switches", "cpu-migrations", "page-faults", "task-clock", "cpu-clock"}:
            order = ["software", "tracepoint", "hardware", "raw", "pmu", "metric", "unknown"]
        elif requested_lower in ARM_ARCH_EVENT_KEYS and any(token in arch for token in ("arm", "aarch64")):
            order = ["raw", "hardware", "pmu", "software", "tracepoint", "metric", "unknown"]
        else:
            order = ["hardware", "pmu", "raw", "software", "tracepoint", "metric", "unknown"]
        try:
            return order.index(source_type)
        except ValueError:
            return len(order)
