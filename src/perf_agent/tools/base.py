from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.security.sandbox import SandboxManager
from perf_agent.storage.artifact_store import ArtifactStore
from perf_agent.tools.backend import BackendSpec, build_device_shell_command, select_backend


class ToolResult(BaseModel):
    action_id: str
    exit_code: int
    stdout_path: str | None = None
    stderr_path: str | None = None
    artifact_paths: list[str] = Field(default_factory=list)
    duration_sec: float
    success: bool
    error_message: str | None = None


class Tool(Protocol):
    name: str

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        ...

    def run(self, state: AnalysisState, action: PlannedAction, store: ArtifactStore) -> ToolResult:
        ...


class BaseCommandTool:
    name: str

    def __init__(self, sandbox_manager: SandboxManager | None = None) -> None:
        self.sandbox_manager = sandbox_manager

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        return action.command

    def profiling_backend(self, state: AnalysisState) -> BackendSpec:
        return select_backend(state)

    def artifact_dir(self, action: PlannedAction) -> str:
        return f"artifacts/raw/commands/{action.id}"

    def artifact_path(self, action: PlannedAction, filename: str) -> str:
        return f"{self.artifact_dir(action)}/{filename}"

    def sandbox_target_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        if not state.target_cmd or self.sandbox_manager is None:
            return state.target_cmd
        wrapped, resolution = self.sandbox_manager.wrap_target_command(state.target_cmd, state)
        action.sandbox_runtime = resolution.runtime_name if resolution.applied else None
        action.sandbox_summary = resolution.reason if resolution.reason and resolution.runtime_name != "none" else None
        return wrapped

    def remote_target_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        return list(state.target_cmd or [])

    def build_device_command(self, backend: BackendSpec, command: list[str]) -> list[str]:
        if backend.device_serial is None:
            raise ValueError("Device backend selected but device serial is missing.")
        return build_device_shell_command(backend.device_serial, command)

    def run(self, state: AnalysisState, action: PlannedAction, store: ArtifactStore) -> ToolResult:
        if self.name in state.mock_outputs:
            stdout_path = store.save_text(self.artifact_path(action, "stdout.txt"), state.mock_outputs[self.name])
            meta_path = store.save_json(
                self.artifact_path(action, "action.json"),
                {
                    "action_id": action.id,
                    "tool": self.name,
                    "command": self.build_command(state, action),
                    "exit_code": 0,
                    "success": True,
                    "duration_sec": 0.0,
                    "error_message": None,
                },
            )
            return ToolResult(
                action_id=action.id,
                exit_code=0,
                stdout_path=str(stdout_path),
                artifact_paths=[str(stdout_path), str(meta_path)],
                duration_sec=0.0,
                success=True,
            )

        command = self.build_command(state, action)
        env = os.environ.copy()
        env.update(state.env)
        start = time.perf_counter()
        stdout_path: str | None = None
        stderr_path: str | None = None
        artifact_paths: list[str] = []

        try:
            completed = subprocess.run(
                command,
                cwd=state.cwd or None,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=action.timeout_sec,
                check=False,
            )
            exit_code = completed.returncode
            success = exit_code == 0
            error_message = None
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            success = False
            error_message = f"Timed out after {action.timeout_sec}s."
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + f"\n{error_message}"
        except FileNotFoundError as exc:
            exit_code = 127
            success = False
            error_message = str(exc)
            stdout = ""
            stderr = str(exc)

        if stdout:
            path = store.save_text(self.artifact_path(action, "stdout.txt"), stdout)
            stdout_path = str(path)
            artifact_paths.append(str(path))
        if stderr:
            path = store.save_text(self.artifact_path(action, "stderr.txt"), stderr)
            stderr_path = str(path)
            artifact_paths.append(str(path))

        meta_path = store.save_json(
            self.artifact_path(action, "action.json"),
            {
                "action_id": action.id,
                "tool": self.name,
                "command": command,
                "exit_code": exit_code,
                "success": success,
                "duration_sec": round(time.perf_counter() - start, 4),
                "error_message": error_message,
            },
        )
        artifact_paths.append(str(meta_path))

        return ToolResult(
            action_id=action.id,
            exit_code=exit_code,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            artifact_paths=artifact_paths,
            duration_sec=round(time.perf_counter() - start, 4),
            success=success,
            error_message=error_message,
        )
