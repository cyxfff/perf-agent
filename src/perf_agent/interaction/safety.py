from __future__ import annotations

import os
from pathlib import Path
import re
import shutil

from perf_agent.interaction.models import CommandSafetyAssessment, SessionContext


SHELL_INTERPRETERS = {"sh", "bash", "zsh", "dash", "fish"}
INLINE_CODE_INTERPRETERS = {
    "python",
    "python3",
    "python3.11",
    "python3.12",
    "perl",
    "ruby",
    "node",
}
READ_ONLY_COMMANDS = {"cat", "grep", "rg", "sed", "head", "tail", "less", "more", "bat"}
WRITE_COMMANDS = {
    "echo",
    "printf",
    "tee",
    "touch",
    "cp",
    "mv",
    "rm",
    "sed",
    "perl",
    "python",
    "python3",
    "bash",
    "sh",
    "chmod",
    "chown",
    "ln",
}
PACKAGE_MANAGERS = {"apt", "apt-get", "yum", "dnf", "pip", "pip3", "npm", "pnpm", "yarn", "cargo"}
SENSITIVE_ABSOLUTE_PATHS = {
    "/etc/profile",
    "/etc/environment",
    "/etc/bash.bashrc",
    "/etc/zsh/zshrc",
}
SENSITIVE_SUFFIXES = {
    ".bashrc",
    ".bash_profile",
    ".bash_login",
    ".profile",
    ".zshrc",
    ".zprofile",
    ".zlogin",
    ".env",
    ".envrc",
    "config.fish",
}


class CommandSafetyClassifier:
    def assess_context(self, session_context: SessionContext) -> CommandSafetyAssessment:
        if session_context.target_pid is not None and not session_context.target_cmd:
            return CommandSafetyAssessment(
                decision="allow",
                risk_level="low",
                reason="当前目标是已有 PID，系统只会执行 perf 附着和存活探测。",
            )

        command = list(session_context.target_cmd)
        if not command and session_context.executable_path:
            command = [session_context.executable_path]
        return self.assess_command(command)

    def assess_command(self, command: list[str]) -> CommandSafetyAssessment:
        normalized = [token for token in command if token]
        if not normalized:
            return CommandSafetyAssessment(decision="deny", risk_level="high", reason="当前没有可执行目标命令。")

        lowered = [token.lower() for token in normalized]
        head = Path(normalized[0]).name.lower()
        joined = " ".join(normalized)
        joined_lower = joined.lower()
        sensitive_paths = self._collect_sensitive_paths(normalized, joined_lower)

        inline_body = self._extract_inline_body(normalized)
        inline_lower = inline_body.lower() if inline_body else ""

        dangerous_rules: list[str] = []
        medium_rules: list[str] = []

        if self._matches_rm_rf(head, lowered, joined_lower) or self._matches_rm_rf("", [], inline_lower):
            dangerous_rules.append("destructive_rm_rf")
        if self._matches_device_destructive(head, lowered, joined_lower) or self._matches_device_destructive("", [], inline_lower):
            dangerous_rules.append("device_or_filesystem_destructive")
        if self._matches_network_exec(joined_lower) or self._matches_network_exec(inline_lower):
            dangerous_rules.append("network_pipe_exec")
        if self._writes_sensitive_paths(head, lowered, joined_lower, sensitive_paths) or self._writes_sensitive_paths(
            "", [], inline_lower, sensitive_paths
        ):
            dangerous_rules.append("persistent_shell_profile_write")

        if dangerous_rules:
            return CommandSafetyAssessment(
                decision="deny",
                risk_level="high",
                reason="检测到高危命令模式，系统不会直接执行这类目标。",
                matched_rules=dangerous_rules,
                normalized_command=normalized,
                sensitive_paths=sensitive_paths,
            )

        if sensitive_paths:
            medium_rules.append("sensitive_env_file_access")

        if self._uses_shell_wrapper(normalized):
            medium_rules.append("shell_wrapper_execution")
        elif self._uses_inline_code(head, lowered):
            medium_rules.append("inline_code_execution")

        if head in PACKAGE_MANAGERS and any(token in {"install", "remove", "uninstall"} for token in lowered[1:]):
            medium_rules.append("package_manager_mutation")

        if medium_rules:
            return CommandSafetyAssessment(
                decision="confirm",
                risk_level="medium",
                reason="检测到可能带来副作用或难以直接审计的命令模式，需要先获得你的确认。",
                matched_rules=list(dict.fromkeys(medium_rules)),
                normalized_command=normalized,
                sensitive_paths=sensitive_paths,
            )

        return CommandSafetyAssessment(
            decision="allow",
            risk_level="low",
            reason="未检测到明显的高危或需确认模式，可以进入分析流程。",
            normalized_command=normalized,
            sensitive_paths=sensitive_paths,
        )

    def command_exists(self, command: list[str], cwd: str | None = None) -> tuple[bool, str]:
        if not command:
            return False, "当前没有分析目标。"
        candidate = command[0]
        path = Path(candidate).expanduser()
        if path.exists():
            return True, "已提供可执行目标或命令。"
        if shutil.which(candidate, path=self._build_path_env(cwd)):
            return True, "已提供 PATH 中可解析的命令。"
        return False, f"目标不存在或不可解析: {candidate}"

    def _build_path_env(self, cwd: str | None) -> str:
        path_value = os.environ.get("PATH", "")
        if cwd:
            return f"{cwd}:{path_value}" if path_value else cwd
        return path_value

    def _collect_sensitive_paths(self, command: list[str], joined_lower: str) -> list[str]:
        matches: list[str] = []
        for token in command:
            candidate = token.strip("\"'")
            if self._is_sensitive_path(candidate):
                matches.append(candidate)
        for suffix in SENSITIVE_SUFFIXES:
            if suffix.lower() in joined_lower and suffix not in matches:
                matches.append(suffix)
        for sensitive in SENSITIVE_ABSOLUTE_PATHS:
            if sensitive in joined_lower and sensitive not in matches:
                matches.append(sensitive)
        return matches

    def _is_sensitive_path(self, path_text: str) -> bool:
        expanded = path_text.replace("~", str(Path.home()))
        normalized = Path(expanded).name
        return path_text in SENSITIVE_ABSOLUTE_PATHS or normalized in SENSITIVE_SUFFIXES

    def _extract_inline_body(self, command: list[str]) -> str | None:
        head = Path(command[0]).name.lower()
        for index, token in enumerate(command[:-1]):
            lowered = token.lower()
            if head in SHELL_INTERPRETERS and lowered in {"-c", "-lc", "-xc"}:
                return command[index + 1]
            if head in INLINE_CODE_INTERPRETERS and lowered in {"-c", "-e"}:
                return command[index + 1]
        return None

    def _uses_shell_wrapper(self, command: list[str]) -> bool:
        if not command:
            return False
        head = Path(command[0]).name.lower()
        return bool(self._extract_inline_body(command)) and head in SHELL_INTERPRETERS

    def _uses_inline_code(self, head: str, lowered: list[str]) -> bool:
        return head in INLINE_CODE_INTERPRETERS and any(flag in {"-c", "-e"} for flag in lowered[1:])

    def _matches_rm_rf(self, head: str, lowered: list[str], joined_lower: str) -> bool:
        if "rm -rf" in joined_lower or "rm -fr" in joined_lower:
            return True
        if head != "rm":
            return False
        has_recursive = any(token in {"-r", "-rf", "-fr", "-r", "--recursive"} or ("r" in token and token.startswith("-")) for token in lowered[1:])
        has_force = any(token in {"-f", "-rf", "-fr", "--force"} or ("f" in token and token.startswith("-")) for token in lowered[1:])
        return has_recursive and has_force

    def _matches_device_destructive(self, head: str, lowered: list[str], joined_lower: str) -> bool:
        destructive_heads = {"mkfs", "wipefs", "fdisk", "parted", "shred"}
        if head in destructive_heads:
            return True
        if head == "dd" and "of=/dev/" in joined_lower:
            return True
        if "find " in joined_lower and " -delete" in joined_lower:
            return True
        return False

    def _matches_network_exec(self, joined_lower: str) -> bool:
        return bool(re.search(r"(curl|wget)[^|\\n]*\\|\\s*(sh|bash|zsh)", joined_lower))

    def _writes_sensitive_paths(self, head: str, lowered: list[str], joined_lower: str, sensitive_paths: list[str]) -> bool:
        if not sensitive_paths:
            return False
        if re.search(r"(>|>>|tee\\b)", joined_lower):
            return True
        if " -i" in joined_lower and head in {"sed", "perl"}:
            return True
        return head in WRITE_COMMANDS and head not in READ_ONLY_COMMANDS
