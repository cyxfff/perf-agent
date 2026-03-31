from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.storage.artifact_store import ArtifactStore


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

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        return action.command

    def run(self, state: AnalysisState, action: PlannedAction, store: ArtifactStore) -> ToolResult:
        if self.name in state.mock_outputs:
            stdout_path = store.save_text(f"artifacts/{action.id}.stdout.txt", state.mock_outputs[self.name])
            meta_path = store.save_json(
                f"artifacts/{action.id}.json",
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
            path = store.save_text(f"artifacts/{action.id}.stdout.txt", stdout)
            stdout_path = str(path)
            artifact_paths.append(str(path))
        if stderr:
            path = store.save_text(f"artifacts/{action.id}.stderr.txt", stderr)
            stderr_path = str(path)
            artifact_paths.append(str(path))

        meta_path = store.save_json(
            f"artifacts/{action.id}.json",
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
