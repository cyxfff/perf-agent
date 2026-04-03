from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex

from perf_agent.models.environment import ConnectedDevice
from perf_agent.models.state import AnalysisState

REMOTE_PATH_PREFIXES = ("/data/", "/system/", "/vendor/", "/product/", "/apex/", "/mnt/", "/storage/")
REMOTE_COMMAND_PREFIXES = {
    "am",
    "app_process",
    "cmd",
    "dumpsys",
    "hiperf",
    "logcat",
    "pm",
    "run-as",
    "setprop",
    "sh",
    "simpleperf",
    "toybox",
}


@dataclass(frozen=True)
class BackendSpec:
    name: str
    execution_target: str
    tool_name: str
    device_serial: str | None = None
    device: ConnectedDevice | None = None
    summary: str | None = None

    @property
    def is_device(self) -> bool:
        return self.execution_target == "device"


def select_backend(state: AnalysisState) -> BackendSpec:
    environment = state.environment
    selected_serial = environment.selected_device_serial
    selected_device = next((device for device in environment.connected_devices if device.serial == selected_serial), None)

    if environment.execution_target == "device" and selected_device is not None:
        if environment.profiling_backend_name == "android_simpleperf":
            return BackendSpec(
                name="android_simpleperf",
                execution_target="device",
                tool_name="simpleperf",
                device_serial=selected_device.serial,
                device=selected_device,
                summary=environment.profiling_backend_summary,
            )
        if environment.profiling_backend_name == "harmony_hiperf":
            return BackendSpec(
                name="harmony_hiperf",
                execution_target="device",
                tool_name="hiperf",
                device_serial=selected_device.serial,
                device=selected_device,
                summary=environment.profiling_backend_summary,
            )

    if state.target_pid is not None and not state.target_cmd:
        return BackendSpec(
            name="host_perf_attach",
            execution_target="pid_attach",
            tool_name="perf",
            summary=environment.profiling_backend_summary,
        )

    return BackendSpec(
        name="host_perf",
        execution_target="host",
        tool_name="perf",
        summary=environment.profiling_backend_summary,
    )


def should_use_device_target(state: AnalysisState, device: ConnectedDevice | None) -> bool:
    if device is None or state.target_pid is not None:
        return False
    target = list(state.target_cmd or [])
    if not target and state.executable_path:
        target = [state.executable_path, *state.target_args]
    if not target:
        return False
    executable = target[0]
    if executable.startswith(REMOTE_PATH_PREFIXES):
        return True
    if executable in REMOTE_COMMAND_PREFIXES:
        return True
    candidate = Path(executable).expanduser()
    if candidate.exists():
        return False
    if "/" in executable:
        return True
    return False


def build_device_shell_command(device_serial: str, command: list[str]) -> list[str]:
    return ["adb", "-s", device_serial, "shell", shlex.join(command)]


def tool_display_label(tool_name: str, backend: BackendSpec) -> str:
    if tool_name == "perf_stat":
        if backend.tool_name == "simpleperf":
            return "simpleperf stat"
        if backend.tool_name == "hiperf":
            return "hiperf stat"
        return "perf stat"
    if tool_name == "perf_record":
        if backend.tool_name == "simpleperf":
            return "simpleperf record"
        if backend.tool_name == "hiperf":
            return "hiperf record"
        return "perf record"
    if tool_name == "time":
        return "/usr/bin/time"
    return tool_name
