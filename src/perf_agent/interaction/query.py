from __future__ import annotations

from typing import Any

from perf_agent.interaction.models import (
    PreparedModelRequest,
    QueryStage,
    QueryView,
    SessionMessage,
    SystemPromptSegments,
    ToolSchemaSpec,
)


def estimate_message_tokens(messages: list[SessionMessage]) -> int:
    return sum(_estimate_text_tokens(_message_text(item)) for item in messages)


class QueryAssembler:
    def __init__(
        self,
        max_context_tokens: int = 2400,
        tool_result_budget_tokens: int = 500,
        visible_history_messages: int = 10,
    ) -> None:
        self.max_context_tokens = max_context_tokens
        self.tool_result_budget_tokens = tool_result_budget_tokens
        self.visible_history_messages = visible_history_messages

    def build(
        self,
        history: list[SessionMessage],
        incoming: list[SessionMessage],
        compact_summary: str | None = None,
    ) -> QueryView:
        messages = [*history, *incoming]
        stages: list[QueryStage] = [QueryStage(name="initial", detail="原始消息视图。", token_estimate=estimate_message_tokens(messages))]

        messages = self.apply_tool_result_budget(messages)
        stages.append(QueryStage(name="applyToolResultBudget", detail="限制工具输出与分析结果进入上下文的体积。", token_estimate=estimate_message_tokens(messages)))

        messages = self.snip_compact_if_needed(messages)
        stages.append(QueryStage(name="snipCompactIfNeeded", detail="优先保留最近可见上下文。", token_estimate=estimate_message_tokens(messages)))

        messages = self.microcompact(messages)
        stages.append(QueryStage(name="microcompact", detail="对长消息做细粒度压缩。", token_estimate=estimate_message_tokens(messages)))

        messages = self.apply_collapses_if_needed(messages)
        stages.append(QueryStage(name="contextCollapse", detail="折叠重复进度和相邻工具结果。", token_estimate=estimate_message_tokens(messages)))

        compact = compact_summary
        if estimate_message_tokens(messages) > self.max_context_tokens:
            compact, messages = self.autocompact(messages, compact_summary=compact_summary)
            stages.append(QueryStage(name="autocompact", detail="上下文仍过大，生成正式 compact 摘要。", token_estimate=estimate_message_tokens(messages)))

        return QueryView(messages=messages, compact_summary=compact, token_estimate=estimate_message_tokens(messages), stages=stages)

    def apply_tool_result_budget(self, messages: list[SessionMessage]) -> list[SessionMessage]:
        budget = 0
        limited: list[SessionMessage] = []
        for message in messages:
            if "tool_result" not in message.tags and "analysis_result" not in message.tags:
                limited.append(message)
                continue
            text = _message_text(message)
            tokens = _estimate_text_tokens(text)
            if budget + tokens <= self.tool_result_budget_tokens:
                budget += tokens
                limited.append(message)
                continue
            limited.append(_truncate_message(message, 220))
            budget += _estimate_text_tokens(_message_text(limited[-1]))
        return limited

    def snip_compact_if_needed(self, messages: list[SessionMessage]) -> list[SessionMessage]:
        if len(messages) <= self.visible_history_messages:
            return messages
        preserved = [message for message in messages if message.role == "system"]
        tail = [message for message in messages if message.role != "system"][-self.visible_history_messages :]
        return [*preserved, *tail]

    def microcompact(self, messages: list[SessionMessage]) -> list[SessionMessage]:
        compacted: list[SessionMessage] = []
        for index, message in enumerate(messages):
            if index < max(0, len(messages) - 4):
                compacted.append(_truncate_message(message, 180))
            else:
                compacted.append(message)
        return compacted

    def apply_collapses_if_needed(self, messages: list[SessionMessage]) -> list[SessionMessage]:
        collapsed: list[SessionMessage] = []
        tool_buffer: list[SessionMessage] = []
        for message in messages:
            if message.role == "tool" or "tool_result" in message.tags:
                tool_buffer.append(message)
                continue
            if tool_buffer:
                collapsed.append(_collapse_tool_messages(tool_buffer))
                tool_buffer = []
            collapsed.append(message)
        if tool_buffer:
            collapsed.append(_collapse_tool_messages(tool_buffer))
        return collapsed

    def autocompact(
        self,
        messages: list[SessionMessage],
        compact_summary: str | None = None,
    ) -> tuple[str, list[SessionMessage]]:
        user_texts = [_message_text(item) for item in messages if item.role == "user"]
        assistant_texts = [_message_text(item) for item in messages if item.role == "assistant"]
        summary_parts = []
        if compact_summary:
            summary_parts.append(compact_summary)
        if user_texts:
            summary_parts.append(f"用户最近关心: {'；'.join(user_texts[-3:])}")
        if assistant_texts:
            summary_parts.append(f"系统最近确认: {'；'.join(assistant_texts[-3:])}")
        compact = " ".join(part for part in summary_parts if part).strip()
        summary_message = SessionMessage(
            id="compact_summary",
            role="system",
            blocks=[{"type": "text", "text": compact or "历史上下文已压缩。"}],
            tags=["compact_summary"],
            token_estimate=_estimate_text_tokens(compact or "历史上下文已压缩。"),
        )
        recent = messages[-4:]
        return compact or "历史上下文已压缩。", [summary_message, *recent]


class RequestBuilder:
    def build(
        self,
        query_view: QueryView,
        system_segments: SystemPromptSegments,
        tools: list[ToolSchemaSpec] | None = None,
        max_tokens: int = 1200,
    ) -> PreparedModelRequest:
        tool_specs = tools or []
        messages = [_message_to_api_dict(item) for item in query_view.messages]
        return PreparedModelRequest(
            messages=messages,
            system=[
                system_segments.attribution_header,
                system_segments.cli_prefix,
                system_segments.static_block,
                system_segments.dynamic_block,
            ],
            tools=[_tool_to_api_dict(item) for item in tool_specs],
            tool_choice="auto" if tool_specs else None,
            max_tokens=max_tokens,
            thinking={"type": "none"},
            output_config={"format": "json_object"},
            cache_markers=["interactive-intake", "compacted-context" if query_view.compact_summary else "full-context"],
        )


def default_system_segments(dynamic_block: str) -> SystemPromptSegments:
    return SystemPromptSegments(
        attribution_header="perf_agent interactive intake",
        cli_prefix="You are operating inside a terminal-style performance analysis assistant.",
        static_block="Prefer structured interpretation, local slash-command interception, and conservative clarification when user intent is ambiguous.",
        dynamic_block=dynamic_block,
    )


def default_tool_specs() -> list[ToolSchemaSpec]:
    return [
        ToolSchemaSpec(
            name="set_analysis_target",
            description="Update executable path, command, PID, or workload label in the local interactive session.",
            input_schema={
                "type": "object",
                "properties": {
                    "executable_path": {"type": "string"},
                    "target_cmd": {"type": "array", "items": {"type": "string"}},
                    "target_pid": {"type": "integer"},
                    "workload_label": {"type": "string"},
                },
            },
        ),
        ToolSchemaSpec(
            name="set_source_context",
            description="Attach or update the source directory used for later source-side correlation.",
            input_schema={"type": "object", "properties": {"source_dir": {"type": "string"}}},
        ),
        ToolSchemaSpec(
            name="launch_analysis",
            description="Launch a new analysis run when the session already has enough target context.",
            input_schema={"type": "object", "properties": {"goal": {"type": "string"}}},
        ),
    ]


def _collapse_tool_messages(messages: list[SessionMessage]) -> SessionMessage:
    labels = [_message_text(item) for item in messages]
    summary = f"已折叠 {len(messages)} 条工具/运行结果消息: " + "；".join(labels[:3])
    return SessionMessage(
        id=f"collapsed_{messages[-1].id}",
        role="tool",
        blocks=[{"type": "text", "text": summary}],
        tags=["tool_result", "collapsed"],
        token_estimate=_estimate_text_tokens(summary),
    )


def _truncate_message(message: SessionMessage, limit: int) -> SessionMessage:
    text = _message_text(message)
    if len(text) <= limit:
        return message
    truncated = text[: max(40, limit - 3)] + "..."
    return SessionMessage(
        id=message.id,
        role=message.role,
        blocks=[{"type": "text", "text": truncated}],
        tags=message.tags,
        token_estimate=_estimate_text_tokens(truncated),
        meta=message.meta,
    )


def _message_text(message: SessionMessage) -> str:
    parts: list[str] = []
    for block in message.blocks:
        if block.text:
            parts.append(block.text)
        elif block.attachment is not None:
            parts.append(f"[{block.attachment.kind}] {block.attachment.path}")
    return " ".join(part for part in parts if part).strip()


def _estimate_text_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _message_to_api_dict(message: SessionMessage) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    for block in message.blocks:
        if block.text:
            content.append({"type": "text", "text": block.text})
        elif block.attachment is not None:
            content.append(
                {
                    "type": block.attachment.kind,
                    "path": block.attachment.path,
                    "summary": block.attachment.summary,
                }
            )
    return {"role": message.role, "content": content}


def _tool_to_api_dict(tool: ToolSchemaSpec) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
        "strict": tool.strict,
    }
    if tool.defer_loading:
        payload["defer_loading"] = True
    if tool.cache_control:
        payload["cache_control"] = tool.cache_control
    return payload
