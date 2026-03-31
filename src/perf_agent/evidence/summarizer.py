from __future__ import annotations

from perf_agent.models.evidence import EvidencePack
from perf_agent.models.hypothesis import Hypothesis
from perf_agent.models.observation import Observation
from perf_agent.models.state import AnalysisState


class EvidenceSummarizer:
    def build_pack(
        self,
        state: AnalysisState,
        rule_candidates: list[Hypothesis],
    ) -> EvidencePack:
        observations = list(state.observations)
        top_observations = self._top_observations(observations)
        timeline_metrics = sorted(
            {
                observation.metric
                for observation in observations
                if observation.labels.get("series_type") == "timeline"
            }
        )
        hotspot_symbols = []
        for observation in observations:
            symbol = observation.labels.get("symbol")
            if symbol and not symbol.startswith("0x") and symbol not in hotspot_symbols:
                hotspot_symbols.append(symbol)
        top_processes = []
        top_threads = []
        for observation in observations:
            if observation.metric == "process_sample_pct":
                top_processes.append(
                    f"{observation.labels.get('comm', 'unknown')} pid={observation.labels.get('pid', '?')} {float(observation.value):.2f}%"
                )
            if observation.metric == "thread_sample_pct":
                top_threads.append(
                    f"{observation.labels.get('comm', 'unknown')} pid/tid={observation.labels.get('pid', '?')}/{observation.labels.get('tid', '?')} {float(observation.value):.2f}%"
                )
        ordered = sorted(rule_candidates, key=lambda item: item.confidence, reverse=True)
        top_hypothesis = ordered[0].kind if ordered else "unknown"
        unresolved = [
            f"是否需要进一步区分 {top_hypothesis} 与其他候选瓶颈。",
        ]
        if not timeline_metrics:
            unresolved.append("当前还缺少时间序列证据，尚不能判断瓶颈是否阶段性出现。")
        if not hotspot_symbols:
            unresolved.append("当前还缺少热点函数级证据，尚不能稳定映射到调用路径。")
        if not top_processes and not top_threads:
            unresolved.append("当前还缺少线程级 / 子进程级样本拆账，尚不能量化并发单元的开销分布。")

        summary = (
            f"第 {state.planning_rounds_done} 轮后，当前最强规则候选为 {top_hypothesis}。"
            f" 重点 observation 数量 {len(top_observations)}，"
            f"热点符号 {len(hotspot_symbols)} 个，"
            f"时间序列指标 {len(timeline_metrics)} 个，"
            f"进程拆账 {len(top_processes)} 条，线程拆账 {len(top_threads)} 条。"
        )
        return EvidencePack(
            round_index=max(state.planning_rounds_done, 1),
            summary=summary,
            top_observation_ids=[item.id for item in top_observations],
            highlighted_metrics=list(dict.fromkeys(item.metric for item in top_observations)),
            hotspot_symbols=hotspot_symbols[:5],
            timeline_metrics=timeline_metrics[:8],
            top_processes=top_processes[:5],
            top_threads=top_threads[:5],
            unresolved_questions=unresolved[:4],
        )

    def _top_observations(self, observations: list[Observation]) -> list[Observation]:
        preferred_metrics = {
            "cpu_utilization_pct",
            "ipc",
            "cache_misses",
            "branch_misses",
            "context_switches",
            "voluntary_context_switches",
            "hot_symbol_pct",
            "hot_frame_sample_pct",
            "callgraph_samples",
            "process_sample_pct",
            "thread_sample_pct",
            "topdown_fe_bound_pct",
            "topdown_be_bound_pct",
            "tma_memory_bound_pct",
        }
        scored: list[tuple[int, Observation]] = []
        for observation in observations:
            score = 0
            if observation.metric in preferred_metrics:
                score += 5
            if observation.category in {"callgraph", "scheduler", "cache"}:
                score += 2
            if observation.labels.get("series_type") == "timeline":
                score += 1
            scored.append((score, observation))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:10]]
