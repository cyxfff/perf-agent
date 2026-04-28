from __future__ import annotations

import shutil
from pathlib import Path

from perf_agent.llm.client import LLMClient
from perf_agent.models.report import ChartSpec, FinalReport, TargetSummary
from perf_agent.models.state import AnalysisState
from perf_agent.visualizer.html_report import render_html_report


class Reporter:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: AnalysisState) -> AnalysisState:
        observation_map = {item.id: item for item in state.observations}
        ordered = sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True)

        supporting_evidence: list[str] = []
        for hypothesis in ordered:
            for obs_id in hypothesis.supporting_observation_ids:
                observation = observation_map.get(obs_id)
                if observation is not None:
                    supporting_evidence.append(
                        f"{self._kind_label(hypothesis.kind)}: {observation.source}.{observation.metric}={observation.value}"
                    )

        report = FinalReport(
            executive_summary=self._build_summary(ordered),
            target=TargetSummary(
                command=state.target_cmd,
                executable_path=state.executable_path,
                source_dir=state.source_dir,
                source_file_count=len(state.source_files),
                runtime_notes=[
                    f"verification_rounds={state.verification_rounds_done}",
                    f"actions_executed={len(state.actions_taken)}",
                    f"evidence_requests={len(state.evidence_requests)}",
                    f"execution_plans={len(state.execution_plans)}",
                    f"llm_traces={len(state.llm_traces)}",
                ],
            ),
            environment_summary=self._build_environment_summary(state),
            experiment_history=self._build_experiment_history(state),
            evidence_summary=self._build_evidence_summary(state),
            chart_specs=self._build_chart_specs(state),
            detected_bottlenecks=[hypothesis.kind for hypothesis in ordered],
            supporting_evidence=supporting_evidence,
            rejected_alternatives=self._build_rejected_alternatives(ordered),
            source_findings=state.source_findings,
            confidence_overall=ordered[0].confidence if ordered else 0.0,
            recommended_next_steps=[action for hypothesis in ordered for action in hypothesis.suggested_actions],
            artifacts=sorted(set(state.artifacts.values())),
        )
        reviewed = self.llm_client.review_report(
            observations=state.observations,
            hypotheses=state.hypotheses,
            artifacts=sorted(set(state.artifacts.values())),
            draft_report=report,
            evidence_pack=state.evidence_packs[-1] if state.evidence_packs else None,
        )
        if self.llm_client.enabled:
            if self.llm_client.last_error:
                state.record_llm_trace(
                    "reporter",
                    "reporting",
                    "fallback",
                    self.llm_client.last_error,
                    model=self.llm_client.model,
                    transport=self.llm_client.last_transport,
                )
            else:
                state.record_llm_trace(
                    "reporter",
                    "reporting",
                    "used",
                    "Generated final executive summary from structured report payload.",
                    model=self.llm_client.model,
                    transport=self.llm_client.last_transport,
                )
        state.final_report = report.model_copy(
            update={
                "executive_summary": reviewed.executive_summary,
                "rejected_alternatives": reviewed.rejected_alternatives,
                "recommended_next_steps": reviewed.recommended_next_steps,
            }
        )
        state.add_audit("reporter", "generated final report", hypothesis_count=len(ordered))
        return state

    def render_markdown(self, state: AnalysisState) -> str:
        report = state.final_report
        if report is None:
            return "# 性能分析报告\n\n未生成报告。\n"

        lines = [
            "# 性能分析报告",
            "",
            "## 1. 执行摘要",
            report.executive_summary,
            "",
            "## 2. 分析目标",
            f"- 命令: {' '.join(report.target.command) if report.target.command else '（PID 附着模式）'}",
            f"- 可执行文件: {report.target.executable_path or '未提供'}",
            f"- 源码目录: {report.target.source_dir or '未提供'}",
            f"- 运行信息: {', '.join(report.target.runtime_notes) or '无'}",
            f"- 工作目录: {state.cwd or ''}",
            "",
            "## 3. 运行环境",
        ]
        for item in report.environment_summary:
            lines.append(f"- {item}")

        lines.extend(["", "## 4. 实验设计与执行"])
        for item in report.experiment_history:
            lines.append(f"- {item}")

        lines.extend(["", "## 5. 证据摘要"])
        for item in report.evidence_summary:
            lines.append(f"- {item}")

        lines.extend(["", "## 6. 关键观测"])
        for observation in state.observations:
            lines.append(f"- {observation.id}: {observation.source}.{observation.metric}={observation.value}")

        lines.extend(["", "## 7. 候选瓶颈"])
        for index, hypothesis in enumerate(sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True), start=1):
            lines.extend(
                [
                    f"### 7.{index} {self._kind_label(hypothesis.kind)}",
                    f"- 置信度: {hypothesis.confidence:.2f}",
                    f"- 支持证据: {', '.join(hypothesis.supporting_observation_ids) or '无'}",
                    f"- 反证: {', '.join(hypothesis.contradicting_observation_ids) or '无'}",
                    f"- 验证状态: {'需要进一步验证' if hypothesis.needs_verification else '证据基本充分'}",
                ]
            )

        lines.extend(["", "## 8. 源码定位"])
        if report.source_findings:
            for finding in report.source_findings:
                lines.extend(
                    [
                        f"### {finding.issue_type}: {finding.file_path}:{finding.line_no}",
                        f"- 依据: {finding.rationale}",
                        f"- 映射方式: {finding.mapping_method or '未知'}",
                        f"- 置信度: {finding.confidence:.2f}" if finding.confidence is not None else "- 置信度: 未提供",
                        "```cpp",
                        finding.snippet,
                        "```",
                    ]
                )
        else:
            lines.append("- 未发现可直接关联的源码位置。")

        lines.extend(["", "## 9. 二次验证", "- 已执行动作:"])
        for action in state.actions_taken:
            lines.append(f"- {action.id}: {action.display_name or action.tool} [{action.status}]")
        lines.append("- 新证据:")
        for evidence in report.supporting_evidence:
            lines.append(f"- {evidence}")

        lines.extend(["", "## 10. 建议"])
        for item in report.recommended_next_steps:
            lines.append(f"- {item}")

        return "\n".join(lines).rstrip() + "\n"

    def render_html(self, state: AnalysisState) -> str:
        return render_html_report(state, kind_labeler=self._kind_label)

    def _build_summary(self, hypotheses: list) -> str:
        if not hypotheses:
            return "当前证据还不足以形成高置信度瓶颈结论。"
        top = hypotheses[0]
        return f"当前最可能的瓶颈方向是 {self._kind_label(top.kind)}，置信度为 {top.confidence:.2f}。"

    def _build_rejected_alternatives(self, hypotheses: list) -> list[str]:
        if len(hypotheses) <= 1:
            return []
        return [f"{self._kind_label(item.kind)} 的证据强度低于首要候选。" for item in hypotheses[1:]]

    def _build_environment_summary(self, state: AnalysisState) -> list[str]:
        environment = state.environment
        selected_device = next(
            (device for device in environment.connected_devices if device.serial == environment.selected_device_serial),
            None,
        )
        memory_gb = self._read_total_memory_gb()
        tool_list = self._detect_tool_availability()
        lines = [
            f"架构: {environment.arch or '未知'}",
            f"内核: {environment.kernel_release or '未知'}",
            f"CPU: {environment.cpu_model or '未知'}",
            f"CPU 配置: 物理核 {environment.physical_cores or '未知'} / 逻辑核 {environment.logical_cores or '未知'}",
            f"内存: {memory_gb if memory_gb is not None else '未知'} GB",
            f"CPU 频率: {self._format_cpu_frequency(environment)}",
            f"Cache: {self._format_cache_summary(environment)}",
            f"NUMA: {environment.numa_nodes if environment.numa_nodes is not None else '未知'} 节点",
            f"perf: {'可用' if environment.perf_available else '不可用'} {environment.perf_version or ''}".strip(),
            f"调用栈模式: {', '.join(environment.callgraph_modes) or '未探测到'}",
            f"可用工具: {', '.join(tool_list) if tool_list else '未探测到'}",
        ]
        if environment.execution_target == "device" and selected_device is not None:
            lines.extend(
                [
                    f"目标执行位置: 设备端",
                    f"目标设备: {selected_device.serial} / {selected_device.model or '未知型号'}",
                    f"设备架构: {selected_device.arch or '未知'}",
                    f"设备系统: Android {selected_device.os_release or '未知'} (SDK {selected_device.sdk or '未知'})",
                    f"设备后端能力: {', '.join(selected_device.backend_tools) or '未探测到'}",
                ]
            )
        if environment.profiling_backend_name:
            lines.append(f"采样后端: {environment.profiling_backend_name}")
        if environment.profiling_backend_summary:
            lines.append(f"后端选择: {environment.profiling_backend_summary}")
        if environment.adb_available:
            lines.append(f"ADB: 可用，已发现 {len(environment.connected_devices)} 台设备")
        if environment.selected_device_serial:
            lines.append(f"目标设备: {environment.selected_device_serial}")
        if environment.selected_device_summary:
            lines.append(f"设备选择: {environment.selected_device_summary}")
        if environment.hybrid_pmus:
            lines.append(f"PMU: {', '.join(environment.hybrid_pmus)}")
        if environment.supports_addr2line:
            lines.append("源码映射: addr2line 可用")
        return lines

    def _build_experiment_history(self, state: AnalysisState) -> list[str]:
        history: list[str] = []
        for mapping in state.event_mappings:
            fallback = "，已退化到当前机器可用方案" if mapping.fallback_used else ""
            history.append(
                f"第 {mapping.round_index} 轮 [{mapping.phase}] {mapping.display_name or mapping.tool}: {mapping.rationale}{fallback}"
            )
        return history

    def _build_evidence_summary(self, state: AnalysisState) -> list[str]:
        if not state.evidence_packs:
            return ["当前还没有生成证据压缩摘要。"]
        latest = state.evidence_packs[-1]
        lines = [latest.summary]
        if latest.highlighted_metrics:
            lines.append(f"重点指标: {', '.join(latest.highlighted_metrics[:8])}")
        hotspot_symbols = [symbol for symbol in latest.hotspot_symbols if self._keep_hotspot_symbol(symbol)]
        if hotspot_symbols:
            lines.append(f"热点符号: {', '.join(hotspot_symbols[:5])}")
        if latest.timeline_metrics:
            lines.append(f"时间序列指标: {', '.join(latest.timeline_metrics[:6])}")
        if latest.top_processes:
            lines.append(f"进程级样本拆账: {', '.join(latest.top_processes[:4])}")
        if latest.top_threads:
            lines.append(f"线程级样本拆账: {', '.join(latest.top_threads[:4])}")
        max_cpu_util = max(
            (
                float(observation.value)
                for observation in state.observations
                if observation.metric == "cpu_utilization_pct" and isinstance(observation.value, (int, float))
            ),
            default=0.0,
        )
        if max_cpu_util > 100.0:
            lines.append("观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。")
        issue_types = {finding.issue_type for finding in state.source_findings}
        if "并发工作函数" in issue_types:
            lines.append("源码中存在并发工作函数入口，建议结合热点和调度证据一起判断线程或子进程的贡献。")
        if "多进程分发" in issue_types or "多进程调度压力" in issue_types:
            lines.append("源码中存在多进程 fanout / 回收逻辑，后续应注意区分父子进程的开销贡献。")
        if any(observation.metric == "topdown_be_bound_pct" for observation in state.observations):
            lines.append("已采集到 top-down 前后端指标，可进一步区分 frontend / backend / bad speculation / retiring。")
        lines.extend(latest.unresolved_questions[:3])
        return lines

    def _build_chart_specs(self, state: AnalysisState) -> list[ChartSpec]:
        specs: list[ChartSpec] = [
            ChartSpec(
                chart_id="hypothesis-confidence",
                title="候选瓶颈置信度对比",
                chart_type="bar",
                metrics=["hypothesis_confidence"],
                rationale="所有报告都应先展示当前最主要的瓶颈候选及其相对置信度。",
                focus="overall_diagnosis",
            )
        ]
        if any(observation.metric == "process_sample_pct" for observation in state.observations):
            specs.append(
                ChartSpec(
                    chart_id="process-sample-breakdown",
                    title="进程级样本拆账",
                    chart_type="bar",
                    metrics=["process_sample_pct"],
                    rationale="并发程序需要先看每个进程或子进程贡献了多少热点样本。",
                    focus="process_breakdown",
                )
            )
        if any(observation.metric == "thread_sample_pct" for observation in state.observations):
            specs.append(
                ChartSpec(
                    chart_id="thread-sample-breakdown",
                    title="线程级样本拆账",
                    chart_type="bar",
                    metrics=["thread_sample_pct"],
                    rationale="多线程程序需要拆出主线程与工作线程的样本占比。",
                    focus="thread_breakdown",
                )
            )
        if any(observation.metric == "hot_symbol_pct" for observation in state.observations):
            specs.append(
                ChartSpec(
                    chart_id="hotspot-symbols",
                    title="热点函数占比",
                    chart_type="bar",
                    metrics=["hot_symbol_pct"],
                    rationale="已经拿到热点函数样本后，应展示最热函数分布，帮助验证热点是否集中。",
                    focus="hotspot_distribution",
                )
            )
        if self._available_topdown_metrics(state):
            specs.append(
                ChartSpec(
                    chart_id="topdown-breakdown",
                    title="Top-Down / TMA 拆分",
                    chart_type="bar",
                    metrics=sorted(self._available_topdown_metrics(state))[:4],
                    rationale="如果平台支持 Top-Down 或 TMA，就优先展示前后端、投机失败和内存子类占比。",
                    focus="topdown",
                )
            )
        timeline_metrics = self._available_timeline_metrics(state)
        miss_rate_metrics = [
            metric
            for metric in ("cache_miss_rate_pct", "l1_miss_rate_pct", "l2_miss_rate_pct", "l3_miss_rate_pct", "llc_miss_rate_pct")
            if metric in timeline_metrics
        ]
        if miss_rate_metrics:
            specs.append(
                ChartSpec(
                    chart_id="timeline-cache-miss-rates",
                    title="Cache Miss Rate 时间序列",
                    chart_type="multiline",
                    metrics=miss_rate_metrics[:4],
                    rationale="优先展示各级 cache miss-rate 的时间变化，便于识别哪一级缓存开始成为瓶颈。",
                    focus="temporal_behavior",
                )
            )
        mpki_metrics = [
            metric
            for metric in ("cache_mpki", "l1_mpki", "l2_mpki", "l3_mpki", "llc_mpki", "branch_mpki")
            if metric in timeline_metrics
        ]
        if mpki_metrics:
            specs.append(
                ChartSpec(
                    chart_id="timeline-mpki",
                    title="MPKI 时间序列",
                    chart_type="multiline",
                    metrics=mpki_metrics[:5],
                    rationale="MPKI 可以把 miss 开销按千条指令归一化，便于跨阶段比较真实压力强度。",
                    focus="temporal_behavior",
                )
            )
        for metric, title, rationale in (
            ("ipc", "IPC 时间序列", "IPC 趋势可以帮助识别阶段性效率下降。"),
            ("cpi", "CPI 时间序列", "CPI 与 IPC 互补，能更直观看出每条指令平均消耗的周期数。"),
            ("branch_miss_rate_pct", "Branch Miss Rate 时间序列", "分支 miss-rate 的突增通常意味着控制流或数据相关性变化。"),
            ("branch_mpki", "Branch MPKI 时间序列", "Branch MPKI 更适合对比分支预测代价在各阶段的真实强度。"),
            ("context_switches", "上下文切换时间序列", "上下文切换抖动适合用来识别并发调度干扰。"),
        ):
            if metric in timeline_metrics:
                specs.append(
                    ChartSpec(
                        chart_id=f"timeline-{metric}",
                        title=title,
                        chart_type="line",
                        metrics=[metric],
                        rationale=rationale,
                        focus="temporal_behavior",
                    )
                )
        return specs[:12]

    def _read_total_memory_gb(self) -> int | None:
        path = Path("/proc/meminfo")
        if not path.exists():
            return None
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("MemTotal:"):
                continue
            digits = "".join(ch for ch in line if ch.isdigit())
            if not digits:
                return None
            return round(int(digits) / 1024 / 1024)
        return None

    def _detect_tool_availability(self) -> list[str]:
        detected = []
        for name in ("perf", "pidstat", "mpstat", "iostat", "addr2line"):
            if shutil.which(name):
                detected.append(name)
        return detected

    def _format_cpu_frequency(self, environment) -> str:
        max_mhz = self._compact_frequency(environment.cpu_max_mhz)
        min_mhz = self._compact_frequency(environment.cpu_min_mhz)
        current = self._sanitize_frequency(environment.cpu_scaling_mhz)
        if max_mhz and min_mhz:
            summary = f"{min_mhz} - {max_mhz}"
        elif max_mhz:
            summary = f"最高 {max_mhz}"
        elif min_mhz:
            summary = f"最低 {min_mhz}"
        else:
            summary = "未知"
        if current and current.endswith("%"):
            summary = f"{summary}，当前缩放 {current}"
        elif current and current != summary:
            summary = f"{summary}，当前 {self._compact_frequency(current)}"
        return summary

    def _sanitize_frequency(self, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    def _compact_frequency(self, value: str | None) -> str | None:
        text = self._sanitize_frequency(value)
        if text is None:
            return None
        if text.endswith("%"):
            return text
        try:
            mhz = float(text)
        except ValueError:
            return text
        if mhz >= 1000:
            return f"{mhz / 1000:.2f} GHz"
        return f"{mhz:.0f} MHz"

    def _format_cache_summary(self, environment) -> str:
        parts = []
        for label, value in (
            ("L1d", environment.l1d_cache),
            ("L1i", environment.l1i_cache),
            ("L2", environment.l2_cache),
            ("L3", environment.l3_cache),
        ):
            if value:
                parts.append(f"{label} {value}")
        return " / ".join(parts) if parts else "未知"

    def _keep_hotspot_symbol(self, symbol: str) -> bool:
        lowered = symbol.lower()
        if lowered.startswith("_start") or lowered.startswith("__libc") or "@@glibc" in lowered:
            return False
        if lowered.startswith("__") or lowered.startswith("std::"):
            return False
        if lowered.startswith("0x"):
            return False
        if "__cos" in lowered or "__sin" in lowered or "libm" in lowered:
            return False
        return True

    def _available_timeline_metrics(self, state: AnalysisState) -> set[str]:
        counts: dict[str, int] = {}
        for observation in state.observations:
            if observation.labels.get("series_type") != "timeline":
                continue
            counts[observation.metric] = counts.get(observation.metric, 0) + 1
        return {metric for metric, count in counts.items() if count >= 2}

    def _available_topdown_metrics(self, state: AnalysisState) -> set[str]:
        wanted = {
            "topdown_fe_bound_pct",
            "topdown_be_bound_pct",
            "topdown_retiring_pct",
            "topdown_bad_spec_pct",
            "tma_memory_bound_pct",
            "tma_fetch_latency_pct",
            "tma_branch_mispredicts_pct",
            "tma_lock_latency_pct",
        }
        return {
            observation.metric
            for observation in state.observations
            if observation.metric in wanted and isinstance(observation.value, (int, float))
        }

    def _kind_label(self, kind: str) -> str:
        mapping = {
            "cpu_bound": "CPU 瓶颈",
            "memory_bound": "内存瓶颈",
            "io_bound": "I/O 瓶颈",
            "lock_contention": "锁竞争",
            "scheduler_issue": "调度压力",
            "branch_mispredict": "分支预测失误",
            "unknown": "未知瓶颈",
        }
        return mapping.get(kind, kind)
