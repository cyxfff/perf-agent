from __future__ import annotations

import sys

from perf_agent.models.action import PlannedAction
from perf_agent.tools.base import ToolResult


class ConsoleProgress:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def stage(self, title: str, detail: str | None = None) -> None:
        if not self.enabled:
            return
        line = f"[{title}]"
        if detail:
            line = f"{line} {detail}"
        print(line, flush=True)

    def info(self, detail: str) -> None:
        if not self.enabled:
            return
        print(f"  - {detail}", flush=True)

    def action_start(self, action: PlannedAction) -> None:
        if not self.enabled:
            return
        label = action.display_name or action.tool
        print(f"[执行] {label}", flush=True)
        if action.strategy_note:
            self.info(action.strategy_note)
        if action.event_names:
            self.info(f"事件: {', '.join(action.event_names)}")
        if action.call_graph_mode:
            self.info(f"调用栈模式: {action.call_graph_mode}")
        if action.sample_interval_ms:
            self.info(f"时间间隔: {action.sample_interval_ms}ms")
        if action.sandbox_runtime:
            self.info(f"隔离运行时: {action.sandbox_runtime}")
        if action.sandbox_summary:
            self.info(f"隔离说明: {action.sandbox_summary}")
        if action.command:
            self.info(f"命令: {' '.join(action.command)}")

    def action_end(self, action: PlannedAction, result: ToolResult) -> None:
        if not self.enabled:
            return
        status = "完成" if result.success else "失败"
        detail = f"[{status}] {action.display_name or action.tool}，退出码 {result.exit_code}，耗时 {result.duration_sec:.2f}s"
        print(detail, flush=True)
        if result.error_message:
            self.info(f"错误: {result.error_message}")

    def blank(self) -> None:
        if not self.enabled:
            return
        sys.stdout.write("")
