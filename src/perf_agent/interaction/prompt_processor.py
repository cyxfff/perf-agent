from __future__ import annotations

import mimetypes
import os
from pathlib import Path
import re
import shlex

from perf_agent.interaction.models import (
    AttachmentRef,
    InteractiveIntentResult,
    MessageBlock,
    NormalizedUserInput,
    SessionContext,
    SessionMessage,
    SlashCommand,
)
from perf_agent.interaction.query import QueryView, estimate_message_tokens
from perf_agent.llm.client import LLMClient
from perf_agent.utils.ids import new_id


ANALYZE_HINTS = ("分析", "测试", "跑", "运行", "benchmark", "analyse", "analyze", "profile")
RUN_HINTS = ("开始", "run", "go", "执行", "继续")
STATUS_HINTS = ("状态", "show", "当前", "配置", "context")
QUIT_HINTS = ("退出", "quit", "exit")
SOURCE_HINTS = ("源码", "source", "代码")
PID_PATTERN = re.compile(r"(?:pid|进程)\s*[:=]?\s*(\d+)", re.IGNORECASE)
QUOTED_PATH_PATTERN = re.compile(r"[\"']([^\"']+)[\"']")
PATH_FRAGMENT_PATTERN = re.compile(
    r"((?:~|\.{1,2})?/[^,\s\"'<>，。；：！？、]+|(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+)"
)


class PromptProcessor:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def process_user_input_base(
        self,
        raw_text: str,
        session_context: SessionContext,
    ) -> NormalizedUserInput:
        cleaned = self._normalize_text(raw_text)
        slash = self._parse_slash_command(cleaned)
        if slash is not None:
            return NormalizedUserInput(raw_text=raw_text, cleaned_text=cleaned, slash_command=slash, should_query=False)

        attachments = self._infer_attachments(cleaned)
        messages, should_query = self.process_text_prompt(cleaned, attachments)
        inferred = self._infer_fields(cleaned, attachments, session_context)
        return NormalizedUserInput(
            raw_text=raw_text,
            cleaned_text=cleaned,
            attachments=attachments,
            inferred_fields=inferred,
            messages=messages,
            should_query=should_query,
        )

    def process_text_prompt(
        self,
        cleaned_text: str,
        attachments: list[AttachmentRef],
    ) -> tuple[list[SessionMessage], bool]:
        blocks: list[MessageBlock] = []
        if cleaned_text:
            blocks.append(MessageBlock(type="text", text=cleaned_text))
        for attachment in attachments:
            blocks.append(MessageBlock(type="attachment", attachment=attachment))
        if not blocks:
            return [], False
        message = SessionMessage(
            id=new_id("msg"),
            role="user",
            blocks=blocks,
            tags=["interactive_input"],
        )
        message.token_estimate = estimate_message_tokens([message])
        return [message], True

    def interpret(
        self,
        normalized: NormalizedUserInput,
        session_context: SessionContext,
        query_view: QueryView,
    ) -> InteractiveIntentResult:
        heuristic = self._heuristic_interpret(normalized, session_context)
        if self._should_try_llm(heuristic, normalized) and self.llm_client is not None:
            llm_result = self.llm_client.interpret_interactive_input(
                normalized_input=normalized.model_dump(mode="json"),
                session_context=session_context.model_dump(mode="json"),
                query_view=query_view.model_dump(mode="json"),
            )
            if llm_result is not None:
                return self._merge_intent(heuristic, llm_result)
        return heuristic

    def _should_try_llm(self, heuristic: InteractiveIntentResult, normalized: NormalizedUserInput) -> bool:
        if self.llm_client is None or not self.llm_client.enabled:
            return False
        if not normalized.cleaned_text:
            return False
        return heuristic.intent in {"clarify", "unknown"} or (not heuristic.executable_path and not heuristic.target_cmd and heuristic.target_pid is None)

    def _merge_intent(self, heuristic: InteractiveIntentResult, llm_result: InteractiveIntentResult) -> InteractiveIntentResult:
        payload = heuristic.model_dump(mode="python")
        for key, value in llm_result.model_dump(mode="python").items():
            if value in (None, "", [], {}):
                continue
            payload[key] = value
        return InteractiveIntentResult.model_validate(payload)

    def _heuristic_interpret(
        self,
        normalized: NormalizedUserInput,
        session_context: SessionContext,
    ) -> InteractiveIntentResult:
        text = normalized.cleaned_text
        lower = text.lower()
        inferred = normalized.inferred_fields
        result = InteractiveIntentResult(summary="已完成输入归一化。")

        if any(hint in lower for hint in QUIT_HINTS):
            result.intent = "quit"
            result.summary = "收到退出请求。"
            return result

        if any(hint in lower for hint in STATUS_HINTS):
            result.intent = "show_status"
            result.summary = "用户想查看当前会话上下文。"
            return result

        if inferred.get("executable_path") or inferred.get("source_dir") or inferred.get("target_cmd") or inferred.get("target_pid"):
            result.intent = "set_context"

        if inferred.get("goal"):
            result.goal = str(inferred["goal"])

        if "executable_path" in inferred:
            result.executable_path = str(inferred["executable_path"])
        if "source_dir" in inferred:
            result.source_dir = str(inferred["source_dir"])
        if "target_cmd" in inferred:
            result.target_cmd = list(inferred["target_cmd"])
        if "target_pid" in inferred and inferred["target_pid"] is not None:
            result.target_pid = int(inferred["target_pid"])

        existing_target = bool(session_context.executable_path or session_context.target_cmd or session_context.target_pid)
        wants_analysis = any(hint in lower for hint in ANALYZE_HINTS) or any(hint in lower for hint in RUN_HINTS)

        if wants_analysis and (result.executable_path or result.target_cmd or result.target_pid or existing_target):
            result.intent = "analyze"
            result.should_run_analysis = True
            result.summary = "用户已经给出了足够的目标上下文，可以直接启动分析。"

        if result.intent == "set_context" and wants_analysis and (result.executable_path or result.target_cmd or result.target_pid or existing_target):
            result.intent = "analyze"
            result.should_run_analysis = True

        if result.intent == "unknown" and text:
            if inferred:
                result.intent = "set_context"
                result.summary = "识别到用户在补充分析目标上下文。"
            elif existing_target and wants_analysis:
                result.intent = "analyze"
                result.should_run_analysis = True
                result.summary = "用户希望在当前上下文基础上开始分析。"
            else:
                result.intent = "clarify"
                result.missing_fields = self._missing_fields(session_context, result)
                result.clarification_question = self._clarification_question(result.missing_fields)
                result.summary = "输入还不够明确，需要先补目标。"
        else:
            result.missing_fields = self._missing_fields(session_context, result)
            if result.intent == "analyze" and result.missing_fields:
                result.intent = "clarify"
                result.should_run_analysis = False
                result.clarification_question = self._clarification_question(result.missing_fields)

        if result.intent == "set_context" and SOURCE_HINTS and any(hint in lower for hint in SOURCE_HINTS) and not (result.executable_path or result.target_cmd or result.target_pid):
            result.summary = "已识别到源码目录补充请求。"

        return result

    def _missing_fields(self, session_context: SessionContext, intent: InteractiveIntentResult) -> list[str]:
        if intent.target_pid is not None:
            return []
        has_target = bool(intent.executable_path or intent.target_cmd or session_context.executable_path or session_context.target_cmd or session_context.target_pid)
        missing: list[str] = []
        if not has_target:
            missing.append("target")
        return missing

    def _clarification_question(self, missing_fields: list[str]) -> str:
        if "target" in missing_fields:
            return "我还不知道要分析哪个程序。你可以直接输入可执行文件路径，或者说“分析 ./bin/demo，源码在 ./src”。"
        return "我还需要一点补充信息后才能继续。"

    def _normalize_text(self, raw_text: str) -> str:
        return " ".join(raw_text.strip().split())

    def _parse_slash_command(self, cleaned_text: str) -> SlashCommand | None:
        if not cleaned_text.startswith("/"):
            return None
        try:
            tokens = shlex.split(cleaned_text)
        except ValueError:
            tokens = cleaned_text.split()
        if not tokens:
            return None
        return SlashCommand(name=tokens[0][1:], args=tokens[1:], raw=cleaned_text)

    def _infer_attachments(self, cleaned_text: str) -> list[AttachmentRef]:
        candidates = []
        for match in QUOTED_PATH_PATTERN.findall(cleaned_text):
            candidates.append(match)
        for match in PATH_FRAGMENT_PATTERN.findall(cleaned_text):
            candidates.append(match)
        for token in cleaned_text.split():
            stripped = token.strip(" ,.;:()[]{}<>\"'，。；：！？、")
            if os.path.exists(stripped):
                candidates.append(stripped)
        attachments: list[AttachmentRef] = []
        seen: set[str] = set()
        for candidate in candidates:
            path = str(Path(candidate).expanduser())
            if path in seen or not os.path.exists(path):
                continue
            seen.add(path)
            attachment = self._build_attachment(path)
            if attachment is not None:
                attachments.append(attachment)
        return attachments

    def _build_attachment(self, path: str) -> AttachmentRef | None:
        resolved = Path(path)
        if not resolved.exists():
            return None
        if resolved.is_dir():
            return AttachmentRef(id=new_id("att"), kind="directory", path=str(resolved), exists=True, summary=f"目录 {resolved.name}")
        mime, _ = mimetypes.guess_type(str(resolved))
        if mime and mime.startswith("image/"):
            return AttachmentRef(id=new_id("att"), kind="local_image", path=str(resolved), exists=True, media_type=mime, summary=f"图片 {resolved.name}")
        return AttachmentRef(id=new_id("att"), kind="file", path=str(resolved), exists=True, media_type=mime, summary=f"文件 {resolved.name}")

    def _infer_fields(
        self,
        cleaned_text: str,
        attachments: list[AttachmentRef],
        session_context: SessionContext,
    ) -> dict[str, object]:
        inferred: dict[str, object] = {}
        lower = cleaned_text.lower()
        pid_match = PID_PATTERN.search(cleaned_text)
        if pid_match:
            inferred["target_pid"] = int(pid_match.group(1))

        path_candidates = [attachment.path for attachment in attachments if attachment.exists]
        for path in path_candidates:
            resolved = Path(path)
            if resolved.is_dir() and self._looks_like_source_dir(resolved):
                inferred.setdefault("source_dir", str(resolved))
                continue
            if resolved.is_file():
                if resolved.suffix == ".json":
                    inferred.setdefault("task_file", str(resolved))
                elif os.access(resolved, os.X_OK):
                    inferred.setdefault("executable_path", str(resolved))
                elif resolved.suffix == ".py":
                    inferred.setdefault("target_cmd", ["python3", str(resolved)])
                    inferred.setdefault("script_path", str(resolved))
                elif resolved.suffix in {".cpp", ".cc", ".c", ".hpp", ".h", ".py", ".rs", ".go"}:
                    inferred.setdefault("source_dir", str(resolved.parent))

        if "命令" in cleaned_text or "cmd" in lower or "command" in lower:
            command = self._extract_quoted_command(cleaned_text)
            if command:
                inferred["target_cmd"] = shlex.split(command)

        if "可执行" in cleaned_text or "程序" in cleaned_text or "binary" in lower or "executable" in lower:
            quoted = self._extract_quoted_command(cleaned_text)
            if quoted and os.path.exists(quoted.split()[0]):
                tokens = shlex.split(quoted)
                candidate_path = Path(tokens[0]).expanduser()
                if candidate_path.exists() and os.access(candidate_path, os.X_OK):
                    inferred["executable_path"] = str(candidate_path)
                    if len(tokens) > 1:
                        inferred["target_cmd"] = [str(candidate_path), *tokens[1:]]

        if not inferred.get("target_cmd") and "executable_path" in inferred:
            executable_path = str(inferred["executable_path"])
            if session_context.target_cmd and session_context.target_cmd[0] == session_context.executable_path:
                inferred["target_cmd"] = [executable_path, *session_context.target_cmd[1:]]
            else:
                inferred["target_cmd"] = [executable_path]

        if any(hint in lower for hint in ANALYZE_HINTS):
            inferred["goal"] = cleaned_text
        return inferred

    def _extract_quoted_command(self, cleaned_text: str) -> str | None:
        matches = QUOTED_PATH_PATTERN.findall(cleaned_text)
        if matches:
            return matches[0]
        return None

    def _looks_like_source_dir(self, path: Path) -> bool:
        try:
            entries = list(path.iterdir())
        except OSError:
            return False
        source_suffixes = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".py", ".rs", ".go", ".java"}
        return any(item.is_file() and item.suffix.lower() in source_suffixes for item in entries)
