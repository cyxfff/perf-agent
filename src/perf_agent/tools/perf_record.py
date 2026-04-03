from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import time

from perf_agent.models.action import PlannedAction
from perf_agent.models.state import AnalysisState
from perf_agent.storage.artifact_store import ArtifactStore
from perf_agent.tools.base import BaseCommandTool, ToolResult


class PerfRecordTool(BaseCommandTool):
    name = "perf_record"

    def artifact_dir(self, action: PlannedAction) -> str:
        return f"artifacts/callgraph/{action.id}"

    def build_command(self, state: AnalysisState, action: PlannedAction) -> list[str]:
        backend = self.profiling_backend(state)
        event = action.event_names[0] if action.event_names else None

        if backend.tool_name == "simpleperf":
            remote = [backend.tool_name, "record"]
            if event:
                remote.extend(["-e", event])
            remote.extend(["--call-graph", action.call_graph_mode or "fp"])
            remote.extend(["-o", f"/data/local/tmp/{action.id}.perf.data"])
            remote.extend(self.remote_target_command(state, action))
            return self.build_device_command(backend, remote)

        if backend.tool_name == "hiperf":
            remote = [backend.tool_name, "record"]
            if event:
                remote.extend(["-e", event])
            remote.extend(["-s", action.call_graph_mode or "fp", "-o", f"/data/local/tmp/{action.id}.perf.data"])
            remote.extend(self.remote_target_command(state, action))
            return self.build_device_command(backend, remote)

        call_graph_args = ["--call-graph", action.call_graph_mode] if action.call_graph_mode else ["-g"]
        if state.target_pid is not None and not state.target_cmd:
            return ["perf", "record", *call_graph_args, "-p", str(state.target_pid), "--", "sleep", "3"]
        remote_target = self.sandbox_target_command(state, action)
        command = ["perf", "record", *call_graph_args]
        if event:
            command.extend(["-e", event])
        command.extend(["--", *remote_target])
        return command

    def run(self, state: AnalysisState, action: PlannedAction, store: ArtifactStore) -> ToolResult:
        if self.name in state.mock_outputs:
            return super().run(state, action, store)

        backend = self.profiling_backend(state)
        if backend.tool_name == "simpleperf" and backend.device_serial is not None:
            return self._run_simpleperf(state, action, store, backend.device_serial)
        if backend.tool_name == "hiperf" and backend.device_serial is not None:
            return self._run_hiperf(state, action, store, backend.device_serial)
        return self._run_host_perf(state, action, store)

    def _run_host_perf(self, state: AnalysisState, action: PlannedAction, store: ArtifactStore) -> ToolResult:
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
        completed, exit_code, success, error_message, record_stdout, record_stderr = self._run_subprocess(
            record_command,
            cwd=state.cwd,
            env=env,
            timeout=action.timeout_sec,
        )

        if record_stdout:
            path = store.save_text(self.artifact_path(action, "record.stdout.txt"), record_stdout)
            artifact_paths.append(str(path))
        if record_stderr:
            path = store.save_text(self.artifact_path(action, "record.stderr.txt"), record_stderr)
            stderr_path = str(path)
            artifact_paths.append(str(path))

        if os.path.exists(data_path):
            data_bytes = Path(data_path).read_bytes()
            if data_bytes:
                saved_data = store.save_bytes(self.artifact_path(action, "perf.data"), data_bytes)
                artifact_paths.append(str(saved_data))

        report_stdout = ""
        report_stderr = ""
        script_stdout = ""
        script_stderr = ""
        if success and os.path.exists(data_path):
            report_completed, _, _, _, report_stdout, report_stderr = self._run_subprocess(
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
                cwd=state.cwd,
                env=env,
                timeout=max(action.timeout_sec, 30),
            )
            script_completed, _, _, _, script_stdout, script_stderr = self._run_subprocess(
                [
                    "perf",
                    "script",
                    "-F",
                    "comm,pid,tid,time,ip,sym,dso",
                    "-i",
                    data_path,
                ],
                cwd=state.cwd,
                env=env,
                timeout=max(action.timeout_sec, 30),
            )
            _ = report_completed, script_completed

        if report_stdout:
            path = store.save_text(self.artifact_path(action, "report.txt"), report_stdout)
            stdout_path = str(path)
            artifact_paths.append(str(path))
        if script_stdout:
            path = store.save_text(self.artifact_path(action, "script.txt"), script_stdout)
            artifact_paths.append(str(path))
        if report_stderr:
            path = store.save_text(self.artifact_path(action, "report.stderr.txt"), report_stderr)
            artifact_paths.append(str(path))
        if script_stderr:
            path = store.save_text(self.artifact_path(action, "script.stderr.txt"), script_stderr)
            artifact_paths.append(str(path))

        meta_path = store.save_json(
            self.artifact_path(action, "action.json"),
            {
                "action_id": action.id,
                "tool": self.name,
                "backend": "perf",
                "command": record_command,
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

    def _run_simpleperf(self, state: AnalysisState, action: PlannedAction, store: ArtifactStore, serial: str) -> ToolResult:
        start = time.perf_counter()
        artifact_paths: list[str] = []
        stdout_path: str | None = None
        stderr_path: str | None = None
        remote_data = f"/data/local/tmp/{action.id}.perf.data"
        event = action.event_names[0] if action.event_names else "raw-cpu-cycles:u"
        record_command = [
            "simpleperf",
            "record",
            "-e",
            event,
            "--call-graph",
            action.call_graph_mode or "fp",
            "-o",
            remote_data,
            *self.remote_target_command(state, action),
        ]
        completed, exit_code, success, error_message, record_stdout, record_stderr = self._run_subprocess(
            self.build_device_command(self.profiling_backend(state), record_command),
            cwd=state.cwd,
            env=os.environ.copy(),
            timeout=action.timeout_sec,
        )

        if record_stdout:
            path = store.save_text(self.artifact_path(action, "record.stdout.txt"), record_stdout)
            artifact_paths.append(str(path))
        if record_stderr:
            path = store.save_text(self.artifact_path(action, "record.stderr.txt"), record_stderr)
            stderr_path = str(path)
            artifact_paths.append(str(path))

        report_stdout = ""
        report_stderr = ""
        sample_stdout = ""
        sample_stderr = ""
        if success:
            _, _, _, _, report_stdout, report_stderr = self._run_subprocess(
                ["adb", "-s", serial, "shell", "simpleperf", "report", "-i", remote_data, "--sort", "symbol", "--percent-limit", "0.5"],
                env=os.environ.copy(),
                timeout=max(action.timeout_sec, 30),
            )
            _, _, _, _, sample_stdout, sample_stderr = self._run_subprocess(
                ["adb", "-s", serial, "shell", "simpleperf", "report-sample", "-i", remote_data, "--show-callchain"],
                env=os.environ.copy(),
                timeout=max(action.timeout_sec, 30),
            )
            with tempfile.NamedTemporaryFile(prefix=f"{action.id}_", suffix=".perf.data", delete=False) as local_file:
                local_data_path = local_file.name
            _, pull_exit_code, pull_success, pull_error, _, pull_stderr = self._run_subprocess(
                ["adb", "-s", serial, "pull", remote_data, local_data_path],
                env=os.environ.copy(),
                timeout=max(action.timeout_sec, 30),
            )
            if pull_success and Path(local_data_path).exists():
                data_bytes = Path(local_data_path).read_bytes()
                if data_bytes:
                    saved_data = store.save_bytes(self.artifact_path(action, "perf.data"), data_bytes)
                    artifact_paths.append(str(saved_data))
            elif pull_stderr:
                path = store.save_text(self.artifact_path(action, "pull.stderr.txt"), pull_stderr)
                artifact_paths.append(str(path))
            if Path(local_data_path).exists():
                os.unlink(local_data_path)
            if not pull_success and error_message is None:
                error_message = pull_error or f"adb pull failed with exit code {pull_exit_code}"

        if report_stdout:
            path = store.save_text(self.artifact_path(action, "report.txt"), report_stdout)
            stdout_path = str(path)
            artifact_paths.append(str(path))
        if sample_stdout:
            path = store.save_text(self.artifact_path(action, "script.txt"), sample_stdout)
            artifact_paths.append(str(path))
        if report_stderr:
            path = store.save_text(self.artifact_path(action, "report.stderr.txt"), report_stderr)
            artifact_paths.append(str(path))
        if sample_stderr:
            path = store.save_text(self.artifact_path(action, "script.stderr.txt"), sample_stderr)
            artifact_paths.append(str(path))

        self._run_subprocess(["adb", "-s", serial, "shell", "rm", "-f", remote_data], env=os.environ.copy(), timeout=10)

        meta_path = store.save_json(
            self.artifact_path(action, "action.json"),
            {
                "action_id": action.id,
                "tool": self.name,
                "backend": "simpleperf",
                "device_serial": serial,
                "command": record_command,
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

    def _run_hiperf(self, state: AnalysisState, action: PlannedAction, store: ArtifactStore, serial: str) -> ToolResult:
        start = time.perf_counter()
        artifact_paths: list[str] = []
        stdout_path: str | None = None
        stderr_path: str | None = None
        remote_data = f"/data/local/tmp/{action.id}.perf.data"
        remote_dump = f"/data/local/tmp/{action.id}.dump.txt"
        event = action.event_names[0] if action.event_names else "hw-cpu-cycles:u"
        target = " ".join(self.remote_target_command(state, action))
        capture_script = (
            f"{target} >/dev/null 2>/dev/null & TARGET_PID=$!; "
            f"hiperf record -p $TARGET_PID -s {action.call_graph_mode or 'fp'} -f 4000 -e {event} -o {remote_data} >/dev/null 2>&1 & "
            "HIPERF_PID=$!; wait $TARGET_PID; kill -2 $HIPERF_PID >/dev/null 2>&1; wait $HIPERF_PID >/dev/null 2>&1; "
            f"hiperf dump -i {remote_data} -o {remote_dump}"
        )
        completed, exit_code, success, error_message, record_stdout, record_stderr = self._run_subprocess(
            ["adb", "-s", serial, "shell", "sh", "-c", capture_script],
            env=os.environ.copy(),
            timeout=action.timeout_sec,
        )
        if record_stdout:
            path = store.save_text(self.artifact_path(action, "record.stdout.txt"), record_stdout)
            artifact_paths.append(str(path))
        if record_stderr:
            path = store.save_text(self.artifact_path(action, "record.stderr.txt"), record_stderr)
            stderr_path = str(path)
            artifact_paths.append(str(path))

        dump_stdout = ""
        if success:
            _, _, _, _, dump_stdout, dump_stderr = self._run_subprocess(
                ["adb", "-s", serial, "shell", "cat", remote_dump],
                env=os.environ.copy(),
                timeout=max(action.timeout_sec, 30),
            )
            if dump_stdout:
                path = store.save_text(self.artifact_path(action, "script.txt"), dump_stdout)
                stdout_path = str(path)
                artifact_paths.append(str(path))
            if dump_stderr:
                path = store.save_text(self.artifact_path(action, "script.stderr.txt"), dump_stderr)
                artifact_paths.append(str(path))

        self._run_subprocess(["adb", "-s", serial, "shell", "rm", "-f", remote_data, remote_dump], env=os.environ.copy(), timeout=10)

        meta_path = store.save_json(
            self.artifact_path(action, "action.json"),
            {
                "action_id": action.id,
                "tool": self.name,
                "backend": "hiperf",
                "device_serial": serial,
                "command": capture_script,
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

    def _run_subprocess(
        self,
        command: list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int = 60,
    ) -> tuple[subprocess.CompletedProcess[str] | None, int, bool, str | None, str, str]:
        try:
            completed = subprocess.run(
                command,
                cwd=cwd or None,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            return completed, completed.returncode, completed.returncode == 0, None, completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as exc:
            error_message = f"Timed out after {timeout}s."
            return None, 124, False, error_message, exc.stdout or "", (exc.stderr or "") + f"\n{error_message}"
        except FileNotFoundError as exc:
            return None, 127, False, str(exc), "", str(exc)
