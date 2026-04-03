from __future__ import annotations

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.tools.base import BaseCommandTool


class PerfStatTool(BaseCommandTool):
    name = "perf_stat"

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        backend = self.profiling_backend(state)
        events = list(dict.fromkeys(action.event_names))
        event_args: list[str] = ["-e", ",".join(events)] if events else []

        if backend.tool_name == "simpleperf":
            interval_args: list[str] = []
            if action.sample_interval_ms:
                interval_args = ["--csv", "--interval", str(action.sample_interval_ms), "--interval-only-values"]
            target_command = self.remote_target_command(state, action)
            remote = [backend.tool_name, "stat", *interval_args, *event_args, *target_command]
            return self.build_device_command(backend, remote)

        if backend.tool_name == "hiperf":
            target_command = self.remote_target_command(state, action)
            # hiperf 更常见的是 attach 到远端 pid，这里先走命令执行路径；时间序列采样暂时退化为单次统计。
            remote = [backend.tool_name, "stat", *event_args, *target_command]
            return self.build_device_command(backend, remote)

        interval_args: list[str] = []
        if action.sample_interval_ms:
            interval_args = ["-x,", "-I", str(action.sample_interval_ms)]
        if state.target_pid is not None and not state.target_cmd:
            return ["perf", "stat", *interval_args, *event_args, "-p", str(state.target_pid), "--", "sleep", "1"]
        target_command = self.sandbox_target_command(state, action)
        if event_args:
            return ["perf", "stat", *interval_args, *event_args, "--", *target_command]
        return ["perf", "stat", "-d", "--", *target_command]
