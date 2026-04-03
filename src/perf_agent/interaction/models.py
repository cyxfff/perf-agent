from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class AttachmentRef(BaseModel):
    id: str
    kind: Literal["file", "directory", "local_image"]
    path: str
    exists: bool = False
    media_type: str | None = None
    summary: str | None = None


class MessageBlock(BaseModel):
    type: Literal["text", "attachment"]
    text: str | None = None
    attachment: AttachmentRef | None = None


class SessionMessage(BaseModel):
    id: str
    role: Literal["system", "user", "assistant", "tool"]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    blocks: list[MessageBlock] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    token_estimate: int = 0
    meta: dict[str, Any] = Field(default_factory=dict)


class SlashCommand(BaseModel):
    name: str
    args: list[str] = Field(default_factory=list)
    raw: str


class InteractiveIntentResult(BaseModel):
    intent: Literal[
        "analyze",
        "set_context",
        "show_status",
        "help",
        "clarify",
        "quit",
        "unknown",
    ] = "unknown"
    summary: str = ""
    goal: str | None = None
    executable_path: str | None = None
    source_dir: str | None = None
    target_cmd: list[str] = Field(default_factory=list)
    target_pid: int | None = None
    workload_label: str | None = None
    should_run_analysis: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    clarification_question: str | None = None


class NormalizedUserInput(BaseModel):
    raw_text: str
    cleaned_text: str
    slash_command: SlashCommand | None = None
    attachments: list[AttachmentRef] = Field(default_factory=list)
    inferred_fields: dict[str, Any] = Field(default_factory=dict)
    messages: list[SessionMessage] = Field(default_factory=list)
    should_query: bool = True


class QueryStage(BaseModel):
    name: str
    detail: str
    token_estimate: int


class QueryView(BaseModel):
    messages: list[SessionMessage] = Field(default_factory=list)
    compact_summary: str | None = None
    token_estimate: int = 0
    stages: list[QueryStage] = Field(default_factory=list)


class SystemPromptSegments(BaseModel):
    attribution_header: str
    cli_prefix: str
    static_block: str
    dynamic_block: str


class ToolSchemaSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    strict: bool = True
    defer_loading: bool = False
    cache_control: str | None = None


class PreparedModelRequest(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list)
    system: list[str] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: str | None = None
    max_tokens: int = 1200
    thinking: dict[str, Any] | None = None
    output_config: dict[str, Any] | None = None
    cache_markers: list[str] = Field(default_factory=list)


class CommandSafetyAssessment(BaseModel):
    decision: Literal["allow", "confirm", "deny"] = "allow"
    risk_level: Literal["low", "medium", "high"] = "low"
    reason: str = ""
    matched_rules: list[str] = Field(default_factory=list)
    normalized_command: list[str] = Field(default_factory=list)
    sensitive_paths: list[str] = Field(default_factory=list)


class ToolPermissionDecision(BaseModel):
    allowed: bool
    tool_name: str
    reason: str
    risk_level: Literal["low", "medium", "high"] = "low"
    requires_confirmation: bool = False
    matched_rules: list[str] = Field(default_factory=list)
    command_preview: str | None = None
    safety: CommandSafetyAssessment | None = None


class PendingApproval(BaseModel):
    kind: Literal["launch_analysis"]
    assessment: CommandSafetyAssessment
    command_preview: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionContext(BaseModel):
    executable_path: str | None = None
    target_cmd: list[str] = Field(default_factory=list)
    source_dir: str | None = None
    target_pid: int | None = None
    workload_label: str | None = None
    goal: str | None = None
    cwd: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    attachments: list[AttachmentRef] = Field(default_factory=list)


class AnalysisRunSummary(BaseModel):
    run_id: str
    status: str
    summary: str
    report_md: str | None = None
    report_html: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InteractiveSessionState(BaseModel):
    session_id: str
    context: SessionContext = Field(default_factory=SessionContext)
    history: list[SessionMessage] = Field(default_factory=list)
    compact_summary: str | None = None
    last_query_view: QueryView | None = None
    last_prepared_request: PreparedModelRequest | None = None
    runs: list[AnalysisRunSummary] = Field(default_factory=list)
    pending_approval: PendingApproval | None = None
