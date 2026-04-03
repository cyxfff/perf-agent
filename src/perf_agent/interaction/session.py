from __future__ import annotations

import json
import os
from pathlib import Path
import shlex

from perf_agent.interaction.models import (
    AnalysisRunSummary,
    InteractiveIntentResult,
    InteractiveSessionState,
    MessageBlock,
    PendingApproval,
    SessionContext,
    SessionMessage,
)
from perf_agent.interaction.prompt_processor import PromptProcessor
from perf_agent.interaction.query import QueryAssembler, RequestBuilder, default_system_segments, default_tool_specs
from perf_agent.interaction.tool_policy import ToolPolicy
from perf_agent.llm.client import LLMClient
from perf_agent.main import build_state, build_state_from_inputs, run_state
from perf_agent.utils.ids import new_id


class InteractivePerfSession:
    def __init__(
        self,
        output_root: str | Path = "runs",
        tool_config_path: str | None = None,
        safety_config_path: str | None = None,
        rule_config_path: str | None = None,
        prompt_config_path: str | None = None,
        event_config_path: str | None = None,
        show_progress: bool = True,
    ) -> None:
        self.output_root = Path(output_root)
        self.tool_config_path = tool_config_path
        self.safety_config_path = safety_config_path
        self.rule_config_path = rule_config_path
        self.prompt_config_path = prompt_config_path
        self.event_config_path = event_config_path
        self.show_progress = show_progress
        llm_client = LLMClient(prompt_config_path=prompt_config_path)
        self.processor = PromptProcessor(llm_client=llm_client)
        self.query_assembler = QueryAssembler()
        self.request_builder = RequestBuilder()
        self.tool_policy = ToolPolicy()
        self.state = InteractiveSessionState(
            session_id=new_id("session"),
            context=SessionContext(cwd=os.getcwd()),
        )
        self._append_system_message(
            "已进入 perf_agent 交互模式。你可以直接说“分析 ./bin/demo，源码在 ./src”，也可以用 /set、/run、/show、/history、/compact。",
            tags=["welcome"],
        )
        self._persist()

    def welcome_text(self) -> str:
        return self._message_text(self.state.history[-1]) if self.state.history else "已进入 perf_agent 交互模式。"

    def handle_input(self, raw_text: str) -> tuple[str, bool]:
        approval_output = self._handle_pending_approval(raw_text)
        if approval_output is not None:
            output, should_exit = approval_output
            self._persist()
            return output, should_exit

        normalized = self.processor.process_user_input_base(raw_text, self.state.context)
        if normalized.slash_command is not None:
            self._append_user_message(raw_text, tags=["slash_command"])
            output, should_exit = self._dispatch_slash_command(normalized.slash_command.name, normalized.slash_command.args)
            self._append_assistant_message(output, tags=["slash_response"])
            self._persist()
            return output, should_exit

        for message in normalized.messages:
            self.state.history.append(message)

        query_view = self.query_assembler.build(self.state.history, [], self.state.compact_summary)
        self.state.last_query_view = query_view
        self.state.compact_summary = query_view.compact_summary
        self.state.last_prepared_request = self.request_builder.build(
            query_view=query_view,
            system_segments=default_system_segments(self._dynamic_system_block()),
            tools=default_tool_specs(),
        )

        interpretation = self.processor.interpret(normalized, self.state.context, query_view)
        output, should_exit = self._apply_interpretation(interpretation, normalized.inferred_fields)
        self._append_assistant_message(output, tags=["interactive_response"])
        self._persist()
        return output, should_exit

    def run_loop(self) -> None:
        print(self.welcome_text(), flush=True)
        while True:
            try:
                raw_text = input("perf-agent> ")
            except EOFError:
                print("", flush=True)
                break
            output, should_exit = self.handle_input(raw_text)
            if output:
                print(output, flush=True)
            if should_exit:
                break

    def _dispatch_slash_command(self, name: str, args: list[str]) -> tuple[str, bool]:
        if name in {"exit", "quit"}:
            return "已退出交互模式。", True
        if name == "approve":
            if self.state.pending_approval is None:
                return "当前没有等待确认的中风险命令。", False
            return self._run_current_context(approved=True)
        if name == "deny":
            if self.state.pending_approval is None:
                return "当前没有等待确认的中风险命令。", False
            preview = self.state.pending_approval.command_preview
            self.state.pending_approval = None
            return f"已取消这次执行请求: {preview}", False
        if name == "help":
            return self._help_text(), False
        if name in {"show", "status"}:
            return self._status_text(), False
        if name == "history":
            return self._history_text(), False
        if name == "compact":
            query_view = self.query_assembler.build(self.state.history, [], self.state.compact_summary)
            self.state.compact_summary = query_view.compact_summary
            self.state.last_query_view = query_view
            return self._compact_text(query_view), False
        if name == "clear":
            self.state.context = SessionContext(cwd=os.getcwd())
            self.state.compact_summary = None
            return "已清空当前会话上下文，但保留历史消息。", False
        if name == "run" or name == "analyze":
            return self._run_current_context()
        if name == "attach":
            if not args:
                return "用法: /attach <路径>", False
            return self._attach_path(" ".join(args)), False
        if name == "debug":
            return self._debug_text(args), False
        if name == "set":
            if len(args) < 2:
                return "用法: /set <exe|source|cmd|pid|label|goal|cwd> <值>", False
            return self._set_context(args[0], " ".join(args[1:])), False
        if name == "use":
            if not args:
                return "用法: /use <文件或目录路径>", False
            return self._use_path(" ".join(args)), False
        return f"未知命令 /{name}。可用命令: /help", False

    def _apply_interpretation(self, interpretation: InteractiveIntentResult, inferred_fields: dict[str, object]) -> tuple[str, bool]:
        self._update_context_from_interpretation(interpretation, inferred_fields)
        if interpretation.intent == "quit":
            return "已退出交互模式。", True
        if interpretation.intent == "show_status":
            return self._status_text(), False
        if interpretation.intent == "help":
            return self._help_text(), False
        if interpretation.intent == "clarify":
            return interpretation.clarification_question or "我还需要更多上下文后才能继续。", False
        if interpretation.intent == "analyze" and interpretation.should_run_analysis:
            return self._run_current_context()
        if interpretation.intent == "set_context":
            return self._context_update_text(interpretation), False
        return interpretation.summary or "我先记下这条输入了。", False

    def _run_current_context(self, approved: bool = False) -> tuple[str, bool]:
        decision = self.tool_policy.wrapper_can_use_tool("launch_analysis", self.state.context)
        if not decision.allowed:
            return self._blocked_run_text(decision), False
        if decision.requires_confirmation and not approved:
            self.state.pending_approval = PendingApproval(
                kind="launch_analysis",
                assessment=decision.safety.model_copy(),
                command_preview=decision.command_preview or self._current_command_preview(),
            )
            return self._confirmation_prompt_text(decision), False

        if self.state.context.attachments:
            source_dirs = [item.path for item in self.state.context.attachments if item.kind == "directory"]
            if not self.state.context.source_dir and source_dirs:
                self.state.context.source_dir = source_dirs[0]

        if self.state.context.target_pid is not None and not self.state.context.target_cmd:
            analysis_state = build_state_from_inputs(
                pid=self.state.context.target_pid,
                source_dir=self.state.context.source_dir,
                workload_label=self.state.context.workload_label,
                goal=self.state.context.goal,
                cwd=self.state.context.cwd,
                env=self.state.context.env,
            )
        else:
            analysis_state = build_state_from_inputs(
                executable_path=self.state.context.executable_path,
                target_cmd=self.state.context.target_cmd or None,
                source_dir=self.state.context.source_dir,
                workload_label=self.state.context.workload_label,
                goal=self.state.context.goal,
                cwd=self.state.context.cwd,
                env=self.state.context.env,
            )

        final_state = run_state(
            analysis_state,
            output_root=self.output_root,
            tool_config_path=self.tool_config_path,
            safety_config_path=self.safety_config_path,
            rule_config_path=self.rule_config_path,
            prompt_config_path=self.prompt_config_path,
            event_config_path=self.event_config_path,
            show_progress=self.show_progress,
        )
        summary = final_state.final_report.executive_summary if final_state.final_report is not None else f"分析结束，状态 {final_state.status}"
        run_summary = AnalysisRunSummary(
            run_id=final_state.run_id,
            status=final_state.status,
            summary=summary,
            report_md=final_state.artifacts.get("report.md"),
            report_html=final_state.artifacts.get("report.html"),
        )
        self.state.pending_approval = None
        self.state.runs.append(run_summary)
        tool_text = self._run_summary_text(run_summary)
        self._append_tool_message(tool_text, tags=["tool_result", "analysis_result"])
        return tool_text, False

    def _update_context_from_interpretation(
        self,
        interpretation: InteractiveIntentResult,
        inferred_fields: dict[str, object],
    ) -> None:
        context = self.state.context
        self.state.pending_approval = None
        if interpretation.goal:
            context.goal = interpretation.goal
        elif isinstance(inferred_fields.get("goal"), str):
            context.goal = str(inferred_fields["goal"])

        if interpretation.executable_path:
            context.executable_path = interpretation.executable_path
        elif isinstance(inferred_fields.get("executable_path"), str):
            context.executable_path = str(inferred_fields["executable_path"])

        if interpretation.target_cmd:
            context.target_cmd = interpretation.target_cmd
        elif isinstance(inferred_fields.get("target_cmd"), list):
            context.target_cmd = list(inferred_fields["target_cmd"])
        elif context.executable_path and not context.target_cmd:
            context.target_cmd = [context.executable_path]

        if interpretation.source_dir:
            context.source_dir = interpretation.source_dir
        elif isinstance(inferred_fields.get("source_dir"), str):
            context.source_dir = str(inferred_fields["source_dir"])

        if interpretation.target_pid is not None:
            context.target_pid = interpretation.target_pid
        elif isinstance(inferred_fields.get("target_pid"), int):
            context.target_pid = int(inferred_fields["target_pid"])

        if interpretation.workload_label:
            context.workload_label = interpretation.workload_label

    def _context_update_text(self, interpretation: InteractiveIntentResult) -> str:
        lines = ["我先把当前上下文更新好了："]
        context = self.state.context
        if context.executable_path:
            lines.append(f"- 可执行文件: {context.executable_path}")
        if context.target_cmd:
            lines.append(f"- 目标命令: {' '.join(context.target_cmd)}")
        if context.target_pid is not None:
            lines.append(f"- PID: {context.target_pid}")
        if context.source_dir:
            lines.append(f"- 源码目录: {context.source_dir}")
        if context.goal:
            lines.append(f"- 目标说明: {context.goal}")
        if interpretation.should_run_analysis:
            lines.append("上下文已经够了，你可以直接输入 /run 开始分析。")
        else:
            lines.append("准备好后直接输入“开始分析”或 /run。")
        return "\n".join(lines)

    def _set_context(self, key: str, value: str) -> str:
        context = self.state.context
        self.state.pending_approval = None
        lowered = key.lower()
        if lowered in {"exe", "executable"}:
            path = str(Path(value).expanduser())
            context.executable_path = path
            context.target_cmd = [path]
            return f"已设置可执行文件: {path}"
        if lowered in {"source", "src"}:
            path = str(Path(value).expanduser())
            context.source_dir = path
            return f"已设置源码目录: {path}"
        if lowered == "cmd":
            context.target_cmd = shlex.split(value)
            if context.target_cmd:
                candidate = Path(context.target_cmd[0]).expanduser()
                if candidate.exists():
                    context.executable_path = str(candidate)
            return f"已设置目标命令: {' '.join(context.target_cmd)}"
        if lowered == "pid":
            context.target_pid = int(value)
            return f"已设置 PID: {context.target_pid}"
        if lowered == "label":
            context.workload_label = value
            return f"已设置工作负载标签: {value}"
        if lowered == "goal":
            context.goal = value
            return f"已设置分析目标: {value}"
        if lowered == "cwd":
            context.cwd = str(Path(value).expanduser())
            return f"已设置工作目录: {context.cwd}"
        return f"不支持的上下文字段: {key}"

    def _attach_path(self, value: str) -> str:
        normalized = self.processor.process_user_input_base(value, self.state.context)
        if not normalized.attachments:
            return f"没有识别到可附加的路径: {value}"
        self.state.pending_approval = None
        self.state.context.attachments.extend(normalized.attachments)
        details = [f"- {item.kind}: {item.path}" for item in normalized.attachments]
        return "已附加以下上下文：\n" + "\n".join(details)

    def _use_path(self, value: str) -> str:
        normalized = self.processor.process_user_input_base(value, self.state.context)
        interpreted = self.processor.interpret(normalized, self.state.context, self.query_assembler.build(self.state.history, normalized.messages, self.state.compact_summary))
        self._update_context_from_interpretation(interpreted, normalized.inferred_fields)
        return self._context_update_text(interpreted)

    def _debug_text(self, args: list[str]) -> str:
        mode = args[0] if args else "query"
        if mode == "query":
            if self.state.last_query_view is None:
                return "当前还没有准备好的 query 视图。"
            payload = self.state.last_query_view.model_dump(mode="json")
            return json.dumps(payload, ensure_ascii=False, indent=2)
        if mode == "request":
            if self.state.last_prepared_request is None:
                return "当前还没有准备好的请求预览。"
            payload = self.state.last_prepared_request.model_dump(mode="json")
            return json.dumps(payload, ensure_ascii=False, indent=2)
        return "用法: /debug <query|request>"

    def _status_text(self) -> str:
        context = self.state.context
        lines = [
            "当前会话上下文：",
            f"- 可执行文件: {context.executable_path or '未设置'}",
            f"- 目标命令: {' '.join(context.target_cmd) if context.target_cmd else '未设置'}",
            f"- PID: {context.target_pid if context.target_pid is not None else '未设置'}",
            f"- 源码目录: {context.source_dir or '未设置'}",
            f"- 工作目录: {context.cwd or '未设置'}",
            f"- 目标说明: {context.goal or '未设置'}",
            f"- 已附加上下文: {len(context.attachments)} 项",
            f"- 历史消息: {len(self.state.history)} 条",
            f"- 最近分析运行: {self.state.runs[-1].run_id if self.state.runs else '无'}",
        ]
        return "\n".join(lines)

    def _history_text(self) -> str:
        lines = ["最近消息："]
        for message in self.state.history[-10:]:
            lines.append(f"- {message.role}: {self._message_text(message)}")
        return "\n".join(lines)

    def _compact_text(self, query_view) -> str:
        lines = ["当前 compact 视图："]
        if query_view.compact_summary:
            lines.append(f"- compact_summary: {query_view.compact_summary}")
        lines.append(f"- token_estimate: {query_view.token_estimate}")
        for stage in query_view.stages:
            lines.append(f"- {stage.name}: {stage.detail} ({stage.token_estimate})")
        return "\n".join(lines)

    def _run_summary_text(self, run_summary: AnalysisRunSummary) -> str:
        lines = [
            f"分析完成: {run_summary.run_id}",
            f"- 状态: {run_summary.status}",
            f"- 摘要: {run_summary.summary}",
        ]
        if run_summary.report_md:
            lines.append(f"- Markdown 报告: {run_summary.report_md}")
        if run_summary.report_html:
            lines.append(f"- HTML 报告: {run_summary.report_html}")
        return "\n".join(lines)

    def _help_text(self) -> str:
        return (
            "可用命令：\n"
            "- /set exe <路径>\n"
            "- /set source <目录>\n"
            "- /set cmd \"python app.py --input data.txt\"\n"
            "- /set pid <数字>\n"
            "- /show\n"
            "- /run\n"
            "- /approve\n"
            "- /deny\n"
            "- /attach <路径>\n"
            "- /use <路径>\n"
            "- /history\n"
            "- /compact\n"
            "- /debug query\n"
            "- /debug request\n"
            "- /clear\n"
            "- /exit"
        )

    def _dynamic_system_block(self) -> str:
        context = self.state.context
        return (
            f"Current session context: exe={context.executable_path or ''}; "
            f"cmd={' '.join(context.target_cmd)}; pid={context.target_pid or ''}; "
            f"source={context.source_dir or ''}; goal={context.goal or ''}."
        )

    def _append_user_message(self, text: str, tags: list[str] | None = None) -> None:
        self.state.history.append(
            SessionMessage(
                id=new_id("msg"),
                role="user",
                blocks=[MessageBlock(type="text", text=text)],
                tags=tags or [],
            )
        )

    def _append_assistant_message(self, text: str, tags: list[str] | None = None) -> None:
        self.state.history.append(
            SessionMessage(
                id=new_id("msg"),
                role="assistant",
                blocks=[MessageBlock(type="text", text=text)],
                tags=tags or [],
            )
        )

    def _append_tool_message(self, text: str, tags: list[str] | None = None) -> None:
        self.state.history.append(
            SessionMessage(
                id=new_id("msg"),
                role="tool",
                blocks=[MessageBlock(type="text", text=text)],
                tags=tags or [],
            )
        )

    def _append_system_message(self, text: str, tags: list[str] | None = None) -> None:
        self.state.history.append(
            SessionMessage(
                id=new_id("msg"),
                role="system",
                blocks=[MessageBlock(type="text", text=text)],
                tags=tags or [],
            )
        )

    def _message_text(self, message: SessionMessage) -> str:
        parts = []
        for block in message.blocks:
            if block.text:
                parts.append(block.text)
            elif block.attachment is not None:
                parts.append(f"[{block.attachment.kind}] {block.attachment.path}")
        return " ".join(parts).strip()

    def _persist(self) -> None:
        root = self.output_root / "interactive_sessions"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{self.state.session_id}.json"
        path.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")

    def _handle_pending_approval(self, raw_text: str) -> tuple[str, bool] | None:
        pending = self.state.pending_approval
        if pending is None:
            return None

        cleaned = raw_text.strip().lower()
        if cleaned in {"/approve", "approve", "yes", "y", "确认", "继续", "是", "好", "ok"}:
            self._append_user_message(raw_text, tags=["approval_response"])
            output, should_exit = self._run_current_context(approved=True)
            self._append_assistant_message(output, tags=["approval_result"])
            return output, should_exit
        if cleaned in {"/deny", "deny", "no", "n", "取消", "否", "不要", "stop"}:
            self._append_user_message(raw_text, tags=["approval_response"])
            preview = pending.command_preview
            self.state.pending_approval = None
            output = f"已取消这次执行请求: {preview}"
            self._append_assistant_message(output, tags=["approval_result"])
            return output, False
        return None

    def _blocked_run_text(self, decision) -> str:
        lines = [f"还不能开始分析: {decision.reason}"]
        if decision.command_preview:
            lines.append(f"- 目标命令: {decision.command_preview}")
        if decision.matched_rules:
            lines.append(f"- 风险规则: {', '.join(decision.matched_rules)}")
        return "\n".join(lines)

    def _confirmation_prompt_text(self, decision) -> str:
        lines = [
            "检测到中风险目标，默认不会直接执行。",
            f"- 目标命令: {decision.command_preview or self._current_command_preview()}",
            f"- 原因: {decision.reason}",
        ]
        if decision.matched_rules:
            lines.append(f"- 风险规则: {', '.join(decision.matched_rules)}")
        lines.append("如果你确认要继续，请输入 /approve；如果不继续，输入 /deny。")
        return "\n".join(lines)

    def _current_command_preview(self) -> str:
        if self.state.context.target_cmd:
            return " ".join(self.state.context.target_cmd)
        if self.state.context.executable_path:
            return self.state.context.executable_path
        if self.state.context.target_pid is not None:
            return f"pid={self.state.context.target_pid}"
        return "<unset>"
