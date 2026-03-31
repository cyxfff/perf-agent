from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from perf_agent.models.environment import EnvironmentCapability
from perf_agent.models.state import AnalysisState
from perf_agent.storage.json_store import JSONArtifactStore

ALIAS_LINE_PATTERN = re.compile(r"^\s*([A-Za-z0-9_./:-]+(?:\s+OR\s+[A-Za-z0-9_./:-]+)*)\s*(?:\[.*\])?$")
METRIC_LINE_PATTERN = re.compile(r"^\s{2,}([A-Za-z0-9_./:-]+)\s*$")


class EnvironmentProfiler:
    def __init__(self, store: JSONArtifactStore) -> None:
        self.store = store

    def run(self, state: AnalysisState) -> AnalysisState:
        capability = EnvironmentCapability()
        capability.os_name = self._run_command(["uname", "-s"]).strip() or None
        capability.kernel_release = self._run_command(["uname", "-r"]).strip() or None
        capability.arch = self._run_command(["uname", "-m"]).strip() or None

        lscpu_text = self._run_command(["lscpu"])
        capability.cpu_model = self._extract_lscpu_value(lscpu_text, "Model name") or self._extract_lscpu_value(lscpu_text, "CPU part")
        capability.logical_cores = self._extract_int(lscpu_text, "CPU(s)")
        cores_per_socket = self._extract_int(lscpu_text, "Core(s) per socket")
        sockets = self._extract_int(lscpu_text, "Socket(s)")
        if cores_per_socket and sockets:
            capability.physical_cores = cores_per_socket * sockets

        perf_version = self._run_command(["perf", "--version"])
        capability.perf_available = bool(perf_version.strip())
        capability.perf_version = perf_version.strip() or None
        perf_list_text = self._run_command(["perf", "list"])
        parsed_events, aliases = self._parse_perf_list(perf_list_text)
        capability.available_events = parsed_events
        capability.event_aliases = aliases
        capability.topdown_events = [event for event in parsed_events if "topdown" in event]
        capability.tma_metrics = [event for event in parsed_events if event.startswith("tma_")]
        capability.hybrid_pmus = sorted({event.split("/", 1)[0] for event in parsed_events if "/" in event and event.startswith("cpu_")})
        capability.topdown_supported = bool(capability.topdown_events or capability.tma_metrics)
        capability.event_sources = self._event_sources()
        capability.callgraph_modes = self._detect_callgraph_modes()
        capability.perf_permissions = self._read_perf_paranoid()
        capability.supports_addr2line = shutil.which("addr2line") is not None

        executable_path = state.executable_path or (state.target_cmd[0] if state.target_cmd else None)
        if executable_path:
            capability.executable_kind, capability.executable_stripped = self._inspect_executable(executable_path)
            capability.executable_has_symbols = self._has_symbols(executable_path)

        if perf_list_text.strip():
            perf_list_path = self.store.save_text("artifacts/perf_list.txt", perf_list_text)
            state.artifacts["environment.perf_list"] = str(perf_list_path)

        if capability.topdown_supported:
            capability.notes.append("检测到 top-down / TMA 相关事件，后续实验会优先尝试更细粒度的前后端拆分。")
        else:
            capability.notes.append("未检测到 top-down / TMA 相关事件，后续会自动退化到通用计数器。")
        if capability.hybrid_pmus:
            capability.notes.append(f"检测到 hybrid PMU: {', '.join(capability.hybrid_pmus)}。事件映射会优先选择通用别名，不足时再退化到具体 PMU。")
        if capability.supports_addr2line:
            capability.notes.append("检测到 addr2line，可在符号和地址可用时尝试映射到源码行号。")
        else:
            capability.notes.append("未检测到 addr2line，源码行号映射能力将受限。")

        state.environment = capability
        environment_path = self.store.save_json("environment.json", capability.model_dump(mode="json"))
        state.artifacts["environment.json"] = str(environment_path)
        state.add_audit(
            "environment_profiler",
            "profiled environment capability",
            arch=capability.arch,
            cpu_model=capability.cpu_model,
            perf_available=capability.perf_available,
            event_count=len(capability.available_events),
            callgraph_modes=capability.callgraph_modes,
        )
        return state

    def _run_command(self, command: list[str], timeout: int = 10) -> str:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            return "\n".join(part for part in [completed.stdout, completed.stderr] if part)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    def _extract_lscpu_value(self, text: str, key: str) -> str | None:
        prefix = f"{key}:"
        for line in text.splitlines():
            if line.startswith(prefix):
                return line.split(":", 1)[1].strip()
        return None

    def _extract_int(self, text: str, key: str) -> int | None:
        raw = self._extract_lscpu_value(text, key)
        if raw is None:
            return None
        digits = "".join(ch for ch in raw if ch.isdigit())
        return int(digits) if digits else None

    def _event_sources(self) -> list[str]:
        root = Path("/sys/bus/event_source/devices")
        if not root.exists():
            return []
        return sorted(item.name for item in root.iterdir() if item.is_dir())

    def _detect_callgraph_modes(self) -> list[str]:
        help_text = self._run_command(["perf", "record", "-h"])
        modes: list[str] = []
        for mode in ("fp", "dwarf", "lbr"):
            if mode in help_text:
                modes.append(mode)
        return modes

    def _read_perf_paranoid(self) -> str | None:
        path = Path("/proc/sys/kernel/perf_event_paranoid")
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip()

    def _inspect_executable(self, executable_path: str) -> tuple[str | None, bool | None]:
        expanded = Path(os.path.expanduser(executable_path))
        if not expanded.exists():
            return None, None
        text = self._run_command(["file", str(expanded)])
        stripped: bool | None = None
        if "not stripped" in text:
            stripped = False
        elif "stripped" in text:
            stripped = True
        return text.strip() or None, stripped

    def _has_symbols(self, executable_path: str) -> bool | None:
        expanded = Path(os.path.expanduser(executable_path))
        if not expanded.exists():
            return None
        output = self._run_command(["nm", "-an", str(expanded)], timeout=12)
        return bool(output.strip())

    def _parse_perf_list(self, text: str) -> tuple[list[str], dict[str, list[str]]]:
        events: set[str] = set()
        aliases: dict[str, set[str]] = {}

        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if not line or line.endswith(":"):
                continue
            parsed = self._parse_event_names(line)
            if not parsed:
                continue
            for event in parsed:
                events.add(event)
                for alias_key in self._alias_keys(event):
                    aliases.setdefault(alias_key, set()).add(event)

        normalized_aliases = {key: sorted(values) for key, values in aliases.items()}
        return sorted(events), normalized_aliases

    def _parse_event_names(self, line: str) -> list[str]:
        alias_match = ALIAS_LINE_PATTERN.match(line)
        if alias_match:
            return [item.strip() for item in alias_match.group(1).split(" OR ") if item.strip()]

        metric_match = METRIC_LINE_PATTERN.match(line)
        if metric_match:
            candidate = metric_match.group(1).strip()
            if candidate and not candidate.endswith(":"):
                return [candidate]
        return []

    def _alias_keys(self, event_name: str) -> set[str]:
        keys = {event_name.lower()}
        stripped = event_name.strip().strip("/").lower()
        keys.add(stripped)
        if "/" in stripped:
            core = stripped.split("/")[-1]
            keys.add(core)
        if stripped.startswith("cpu-"):
            keys.add(stripped.removeprefix("cpu-"))
        if stripped.startswith("branch-") and "instructions" in stripped:
            keys.add("branches")
        return {key for key in keys if key}
