from __future__ import annotations

import os
from pathlib import Path
import shutil
from typing import Any

from pydantic import BaseModel, Field

from perf_agent.config import SafetyConfig, SandboxRuntimeConfig, load_safety_config
from perf_agent.models.state import AnalysisState


class SandboxResolution(BaseModel):
    runtime_name: str = "none"              # 选择的运行时名称
    enabled: bool = False                   # 沙箱是否启用
    available: bool = True                  # 运行时是否可用
    applied: bool = False                   # 是否实际应用了沙箱
    fallback_used: bool = False             # 是否使用了回退方案
    reason: str = ""                        # 决策原因（中文）
    command_prefix: list[str] = Field(default_factory=list)  # 前缀命令


class SandboxManager:
    def __init__(self, config_path: str | None = None) -> None:
        self.config_path = config_path
        self.config: SafetyConfig = load_safety_config(config_path)
        self._availability_cache: dict[str, bool] = {}

    def available_runtime_names(self) -> list[str]:
        names: list[str] = []
        for name, runtime in self.config.runtimes.items():
            if runtime.enabled and self._is_runtime_available(name, runtime):
                names.append(name)
        if "none" not in names and "none" in self.config.runtimes:
            names.append("none")
        return names

    def resolve_runtime(self, state: AnalysisState) -> SandboxResolution:
        override_enabled = os.getenv("PERF_AGENT_SANDBOX_ENABLED")
        sandbox_enabled = self.config.sandbox_enabled
        if override_enabled:
            sandbox_enabled = override_enabled.lower() in {"1", "true", "yes", "on"}

        requested = os.getenv("PERF_AGENT_SANDBOX_RUNTIME") or self.config.default_runtime
        if not sandbox_enabled:
            return SandboxResolution(
                runtime_name="none",
                enabled=False,
                available=True,
                applied=False,
                reason="当前安全配置未启用内核/运行时沙箱，保持直接执行。",
            )

        selection_order = self._selection_order(requested)
        for index, runtime_name in enumerate(selection_order):
            runtime = self.config.runtimes.get(runtime_name)
            if runtime is None or not runtime.enabled:
                continue
            available = self._is_runtime_available(runtime_name, runtime)
            if not available:
                continue
            if runtime_name == "none" or runtime.kind == "none":
                return SandboxResolution(
                    runtime_name=runtime_name,
                    enabled=True,
                    available=True,
                    applied=False,
                    fallback_used=index > 0,
                    reason="已选择 none 运行时，目标命令不会再额外包裹沙箱。",
                )
            prefix = self._build_prefix(runtime_name, runtime, state)
            return SandboxResolution(
                runtime_name=runtime_name,
                enabled=True,
                available=True,
                applied=bool(prefix),
                fallback_used=index > 0,
                reason=f"已选择 {runtime_name} 作为目标命令的隔离运行时。",
                command_prefix=prefix,
            )

        if self.config.fallback_to_none:
            return SandboxResolution(
                runtime_name="none",
                enabled=True,
                available=True,
                applied=False,
                fallback_used=True,
                reason="没有找到可用的沙箱运行时，已自动退回 none。",
            )
        return SandboxResolution(
            runtime_name="unavailable",
            enabled=True,
            available=False,
            applied=False,
            reason="沙箱已启用，但当前平台上没有可用的运行时且不允许回退。",
        )

    def wrap_target_command(self, command: list[str], state: AnalysisState) -> tuple[list[str], SandboxResolution]:
        if not command:
            return command, SandboxResolution(reason="当前没有目标命令，无需包裹。")
        resolution = self.resolve_runtime(state)
        if not resolution.applied:
            return command, resolution
        return [*resolution.command_prefix, *command], resolution

    def _selection_order(self, requested: str) -> list[str]:
        if requested and requested not in {"", "auto"}:
            names = [requested]
            if requested != "none" and self.config.fallback_to_none:
                names.append("none")
            return names
        names = list(self.config.preferred_runtimes)
        if self.config.fallback_to_none and "none" not in names:
            names.append("none")
        return names

    def _is_runtime_available(self, name: str, runtime: SandboxRuntimeConfig) -> bool:
        if name in self._availability_cache:
            return self._availability_cache[name]
        if runtime.kind == "none" or runtime.detection == "always":
            available = True
        else:
            executable = runtime.executable or (runtime.template[0] if runtime.template else None)
            available = bool(executable and shutil.which(executable))
        self._availability_cache[name] = available
        return available

    def _build_prefix(self, runtime_name: str, runtime: SandboxRuntimeConfig, state: AnalysisState) -> list[str]:
        if runtime.kind == "bubblewrap":
            return self._build_bubblewrap_prefix(runtime_name, runtime, state)
        if runtime.kind == "template":
            return self._build_template_prefix(runtime, state)
        return []

    def _build_bubblewrap_prefix(
        self,
        runtime_name: str,
        runtime: SandboxRuntimeConfig,
        state: AnalysisState,
    ) -> list[str]:
        executable = runtime.executable or runtime_name
        context = self._placeholder_context(state, runtime)
        prefix: list[str] = [executable, *runtime.extra_args]
        readonly = self._render_existing_paths(runtime.read_only_paths, context)
        writable = self._render_existing_paths(runtime.writable_paths, context)

        for path in readonly:
            prefix.extend(["--ro-bind", path, path])
        for path in writable:
            prefix.extend(["--bind", path, path])

        if not runtime.network_access:
            prefix.append("--unshare-net")
        workdir = self._render_token(runtime.workdir or "", context)
        if workdir and Path(workdir).exists():
            prefix.extend(["--chdir", workdir])
        prefix.append("--")
        return prefix

    def _build_template_prefix(self, runtime: SandboxRuntimeConfig, state: AnalysisState) -> list[str]:
        context = self._placeholder_context(state, runtime)
        tokens: list[str] = []
        for token in runtime.template:
            if token == "{command}":
                break
            rendered = self._render_token(token, context)
            if rendered:
                tokens.append(rendered)
        if not tokens and runtime.executable:
            tokens.append(runtime.executable)
        return tokens

    def _render_existing_paths(self, patterns: list[str], context: dict[str, str]) -> list[str]:
        resolved: list[str] = []
        seen: set[str] = set()
        for pattern in patterns:
            candidate = self._render_token(pattern, context)
            if not candidate:
                continue
            path = Path(candidate).expanduser()
            if not path.exists():
                continue
            as_text = str(path)
            if as_text in seen:
                continue
            seen.add(as_text)
            resolved.append(as_text)
        return resolved

    def _render_token(self, token: str, context: dict[str, str]) -> str:
        if not token:
            return ""
        return token.format_map(_SafeFormatDict(context))

    def _placeholder_context(self, state: AnalysisState, runtime: SandboxRuntimeConfig) -> dict[str, str]:
        cwd = str(Path(state.cwd or os.getcwd()).expanduser().resolve())
        executable_path = ""
        if state.executable_path:
            executable_path = str(Path(state.executable_path).expanduser())
        elif state.target_cmd:
            executable_path = state.target_cmd[0]
        executable_dir = cwd
        if executable_path:
            executable_dir = str(Path(executable_path).expanduser().resolve().parent)
        source_dir = str(Path(state.source_dir).expanduser().resolve()) if state.source_dir else cwd
        context: dict[str, str] = {
            "cwd": cwd,
            "home": str(Path.home()),
            "tmpdir": "/tmp",
            "executable_path": executable_path,
            "executable_dir": executable_dir,
            "source_dir": source_dir,
            "arch": state.environment.arch or "",
        }
        for key, value in runtime.variables.items():
            context[key] = self._render_token(value, context)
        return context


class _SafeFormatDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return ""
