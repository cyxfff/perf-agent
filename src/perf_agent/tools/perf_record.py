from __future__ import annotations

import os
import subprocess
import tempfile
import time

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.storage.artifact_store import ArtifactStore
from perf_agent.tools.base import BaseCommandTool, ToolResult


class PerfRecordTool(BaseCommandTool):
    name = "perf_record"

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        call_graph_args = ["--call-graph", action.call_graph_mode] if action.call_graph_mode else ["-g"]
        if state.target_pid is not None and not state.target_cmd:
            return ["perf", "record", *call_graph_args, "-p", str(state.target_pid), "--", "sleep", "3"]
        return ["perf", "record", *call_graph_args, "--", *state.target_cmd]

    def run(self, state: AnalysisState, action: PlannedAction, store: ArtifactStore) -> ToolResult:
        if self.name in state.mock_outputs:
            return super().run(state, action, store)

        env = os.environ.copy()
        env.update(state.env)
        start = time.perf_counter()
        artifact_paths: list[str] = []
        stdout_path: str | None = None
        stderr_path: str | None = None
        command = self.build_command(state, action)

        with tempfile.NamedTemporaryFile(prefix=f"{action.id}_", suffix=".perf.data", delete=False) as handle:
            data_path = handle.name

        record_command = [*command[:2], "-o", data_path, *command[2:]]
        try:
            completed = subprocess.run(
                record_command,
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
            record_stdout = completed.stdout
            record_stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            success = False
            error_message = f"Timed out after {action.timeout_sec}s."
            record_stdout = exc.stdout or ""
            record_stderr = (exc.stderr or "") + f"\n{error_message}"
        except FileNotFoundError as exc:
            exit_code = 127
            success = False
            error_message = str(exc)
            record_stdout = ""
            record_stderr = str(exc)

        if record_stdout:
            path = store.save_text(f"artifacts/{action.id}.record.stdout.txt", record_stdout)
            artifact_paths.append(str(path))
        if record_stderr:
            path = store.save_text(f"artifacts/{action.id}.stderr.txt", record_stderr)
            stderr_path = str(path)
            artifact_paths.append(str(path))

        if os.path.exists(data_path):
            data_bytes = open(data_path, "rb").read()
            if data_bytes:
                saved_data = store.save_bytes(f"artifacts/{action.id}.perf.data", data_bytes)
                artifact_paths.append(str(saved_data))

        report_stdout = ""
        report_stderr = ""
        script_stdout = ""
        script_stderr = ""
        if success and os.path.exists(data_path):
            report_completed = subprocess.run(
                [
                    "perf",
                    "report",
                    "--stdio",
                    "--sort",
                    "symbol",
                    "--percent-limit",
                    "0.5",
                    "-i",
                    data_path,
                ],
                cwd=state.cwd or None,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(action.timeout_sec, 30),
                check=False,
            )
            report_stdout = report_completed.stdout
            report_stderr = report_completed.stderr
            script_completed = subprocess.run(
                [
                    "perf",
                    "script",
                    "-F",
                    "comm,pid,tid,time,ip,sym,dso",
                    "-i",
                    data_path,
                ],
                cwd=state.cwd or None,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(action.timeout_sec, 30),
                check=False,
            )
            script_stdout = script_completed.stdout
            script_stderr = script_completed.stderr

        if report_stdout:
            path = store.save_text(f"artifacts/{action.id}.stdout.txt", report_stdout)
            stdout_path = str(path)
            artifact_paths.append(str(path))
        if script_stdout:
            path = store.save_text(f"artifacts/{action.id}.script.txt", script_stdout)
            artifact_paths.append(str(path))
        if report_stderr:
            path = store.save_text(f"artifacts/{action.id}.report.stderr.txt", report_stderr)
            artifact_paths.append(str(path))
        if script_stderr:
            path = store.save_text(f"artifacts/{action.id}.script.stderr.txt", script_stderr)
            artifact_paths.append(str(path))

        meta_path = store.save_json(
            f"artifacts/{action.id}.json",
            {
                "action_id": action.id,
                "tool": self.name,
                "command": record_command,
                "report_command": [
                    "perf",
                    "report",
                    "--stdio",
                    "--sort",
                    "symbol",
                    "--percent-limit",
                    "0.5",
                    "-i",
                    data_path,
                ],
                "script_command": [
                    "perf",
                    "script",
                    "-F",
                    "comm,pid,tid,time,ip,sym,dso",
                    "-i",
                    data_path,
                ],
                "exit_code": exit_code,
                "success": success,
                "duration_sec": round(time.perf_counter() - start, 4),
                "error_message": error_message,
            },
        )
        artifact_paths.append(str(meta_path))

        if os.path.exists(data_path):
            os.unlink(data_path)

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
