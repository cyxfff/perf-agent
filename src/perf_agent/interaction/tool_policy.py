from __future__ import annotations

from pathlib import Path

from perf_agent.interaction.models import SessionContext, ToolPermissionDecision
from perf_agent.interaction.safety import CommandSafetyClassifier


class ToolPolicy:
    def __init__(self) -> None:
        self.safety = CommandSafetyClassifier()

    def wrapper_can_use_tool(
        self,
        tool_name: str,
        session_context: SessionContext,
    ) -> ToolPermissionDecision:
        if tool_name == "launch_analysis":
            if session_context.target_pid is not None:
                safety = self.safety.assess_context(session_context)
                return ToolPermissionDecision(
                    allowed=True,
                    tool_name=tool_name,
                    reason="已提供 PID，可直接附着分析。",
                    risk_level=safety.risk_level,
                    requires_confirmation=safety.decision == "confirm",
                    matched_rules=safety.matched_rules,
                    safety=safety,
                )
            if session_context.target_cmd:
                exists, reason = self.safety.command_exists(session_context.target_cmd, cwd=session_context.cwd)
                if not exists:
                    return ToolPermissionDecision(allowed=False, tool_name=tool_name, reason=reason)
                safety = self.safety.assess_context(session_context)
                if safety.decision == "deny":
                    return ToolPermissionDecision(
                        allowed=False,
                        tool_name=tool_name,
                        reason=safety.reason,
                        risk_level=safety.risk_level,
                        matched_rules=safety.matched_rules,
                        command_preview=" ".join(session_context.target_cmd),
                        safety=safety,
                    )
                return ToolPermissionDecision(
                    allowed=True,
                    tool_name=tool_name,
                    reason=safety.reason if safety.decision == "confirm" else reason,
                    risk_level=safety.risk_level,
                    requires_confirmation=safety.decision == "confirm",
                    matched_rules=safety.matched_rules,
                    command_preview=" ".join(session_context.target_cmd),
                    safety=safety,
                )
            if session_context.executable_path:
                target = Path(session_context.executable_path).expanduser()
                if target.exists():
                    safety = self.safety.assess_context(session_context)
                    if safety.decision == "deny":
                        return ToolPermissionDecision(
                            allowed=False,
                            tool_name=tool_name,
                            reason=safety.reason,
                            risk_level=safety.risk_level,
                            matched_rules=safety.matched_rules,
                            command_preview=session_context.executable_path,
                            safety=safety,
                        )
                    return ToolPermissionDecision(
                        allowed=True,
                        tool_name=tool_name,
                        reason=safety.reason if safety.decision == "confirm" else "已提供可执行文件。",
                        risk_level=safety.risk_level,
                        requires_confirmation=safety.decision == "confirm",
                        matched_rules=safety.matched_rules,
                        command_preview=session_context.executable_path,
                        safety=safety,
                    )
                return ToolPermissionDecision(allowed=False, tool_name=tool_name, reason=f"可执行文件不存在: {target}")
            return ToolPermissionDecision(allowed=False, tool_name=tool_name, reason="当前还没有分析目标。")

        if tool_name == "set_source_context":
            if session_context.source_dir is None:
                return ToolPermissionDecision(allowed=False, tool_name=tool_name, reason="当前没有源码目录。")
            candidate = Path(session_context.source_dir).expanduser()
            return ToolPermissionDecision(
                allowed=candidate.exists() and candidate.is_dir(),
                tool_name=tool_name,
                reason="源码目录可用。" if candidate.exists() and candidate.is_dir() else f"源码目录无效: {candidate}",
            )

        return ToolPermissionDecision(allowed=True, tool_name=tool_name, reason="本地交互工具默认允许。")
