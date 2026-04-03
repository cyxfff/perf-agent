from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from perf_agent.models.environment import ConnectedDevice, EnvironmentCapability, EventDescriptor
from perf_agent.models.state import AnalysisState
from perf_agent.security.sandbox import SandboxManager
from perf_agent.storage.json_store import JSONArtifactStore
from perf_agent.tools.backend import should_use_device_target

ALIAS_LINE_PATTERN = re.compile(r"^\s*([A-Za-z0-9_./:-]+(?:\s+OR\s+[A-Za-z0-9_./:-]+)*)\s*(?:\[.*\])?$")
INDENTED_EVENT_PATTERN = re.compile(r"^\s{2,}([A-Za-z0-9_./:-]+)")
RAW_HEX_PATTERN = re.compile(r"^r[0-9a-f]+$", re.IGNORECASE)
KNOWN_HARDWARE_KEYS = {
    "cycles",
    "cpu-cycles",
    "instructions",
    "cache-references",
    "cache-misses",
    "branches",
    "branch-instructions",
    "branch-misses",
    "bus-cycles",
    "stalled-cycles-frontend",
    "stalled-cycles-backend",
    "slots",
}
KNOWN_SOFTWARE_KEYS = {
    "cpu-clock",
    "task-clock",
    "page-faults",
    "context-switches",
    "cpu-migrations",
    "minor-faults",
    "major-faults",
    "alignment-faults",
    "emulation-faults",
    "bpf-output",
    "dummy",
}
SEMANTIC_ALIASES = {
    "cpu-cycles": ["cycles"],
    "hw-cpu-cycles": ["cycles"],
    "raw-cpu-cycles": ["cycles"],
    "instruction-retired": ["instructions"],
    "raw-instruction-retired": ["instructions"],
    "hw-instructions": ["instructions"],
    "branch-instructions": ["branches"],
    "hw-branch-instructions": ["branches"],
    "br-mis-pred": ["branch-misses"],
    "raw-br-mis-pred": ["branch-misses"],
    "raw-br-mis-pred-retired": ["branch-misses"],
    "stalled-frontend": ["stalled-cycles-frontend"],
    "raw-stall-frontend": ["stalled-cycles-frontend"],
    "stalled-backend": ["stalled-cycles-backend"],
    "raw-stall-backend": ["stalled-cycles-backend"],
    "ll-cache": ["cache-references"],
    "raw-ll-cache": ["cache-references"],
    "ll-cache-miss": ["cache-misses"],
    "raw-ll-cache-miss": ["cache-misses"],
    "sw-context-switches": ["context-switches"],
    "sw-cpu-migrations": ["cpu-migrations"],
    "sw-task-clock": ["task-clock"],
    "sw-cpu-clock": ["cpu-clock"],
    "sw-page-faults": ["page-faults"],
    "raw-inst-retired": ["instructions"],
    "inst-retired": ["instructions"],
    "inst_retired": ["instructions"],
    "cpu_cycles": ["cycles"],
    "cnt_cycles": ["cycles"],
    "br_mis_pred": ["branch-misses"],
    "br_mis_pred_retired": ["branch-misses"],
    "br_retired": ["branches"],
    "branch-load-misses": ["branch-misses"],
    "branch-loads": ["branches"],
    "stall_backend": ["stalled-cycles-backend"],
    "stall_backend_mem": ["stalled-cycles-backend"],
    "stall_frontend": ["stalled-cycles-frontend"],
    "stall_slot_backend": ["stalled-cycles-backend"],
    "stall_slot_frontend": ["stalled-cycles-frontend"],
    "l1d_cache_refill": ["cache-misses", "l1d-cache-refill"],
    "l1d-cache-load-misses": ["cache-misses", "l1d-cache-refill"],
    "l1-dcache-load-misses": ["cache-misses", "l1d-cache-refill"],
    "l1d_cache": ["l1d-cache", "l1d-cache-access", "l1_access"],
    "l1d-cache-loads": ["l1d-cache", "l1d-cache-access", "l1_access"],
    "l1-dcache-loads": ["l1d-cache", "l1d-cache-access", "l1_access"],
    "mem_load_retired.l1_hit": ["l1d-cache-hit", "l1_hit_count"],
    "mem_load_retired.l1_miss": ["l1d-cache-refill", "l1_miss_count"],
    "l2d_cache_refill": ["cache-misses", "l2d-cache-refill"],
    "l2_rqsts.references": ["l2d-cache", "l2d-cache-access", "l2_access"],
    "l2_rqsts.miss": ["cache-misses", "l2d-cache-refill", "l2_miss_count"],
    "l2d_cache": ["l2d-cache", "l2d-cache-access", "l2_access"],
    "l3d_cache_refill": ["cache-misses", "l3d-cache-refill"],
    "l3d_cache": ["l3d-cache", "l3d-cache-access", "l3_access"],
    "ll_cache_rd": ["cache-references"],
    "ll_cache_miss_rd": ["cache-misses"],
    "llc-load-misses": ["cache-misses", "llc-miss", "llc_miss_count"],
    "llc-loads": ["cache-references", "llc-access", "llc_access_count"],
    "longest_lat_cache.reference": ["cache-references", "llc-access", "llc_access_count"],
    "longest_lat_cache.miss": ["cache-misses", "llc-miss", "llc_miss_count"],
    "mem_access": ["mem-access"],
}


class EnvironmentProfiler:
    def __init__(self, store: JSONArtifactStore, sandbox_manager: SandboxManager | None = None) -> None:
        self.store = store
        self.sandbox_manager = sandbox_manager

    def run(self, state: AnalysisState) -> AnalysisState:
        capability = EnvironmentCapability()
        capability.os_name = self._run_command(["uname", "-s"]).strip() or None
        capability.kernel_release = self._run_command(["uname", "-r"]).strip() or None
        capability.arch = self._run_command(["uname", "-m"]).strip() or None

        lscpu_text = self._run_command(["lscpu"])
        capability.cpu_model = self._extract_lscpu_value(lscpu_text, "Model name") or self._extract_lscpu_value(lscpu_text, "CPU part")
        capability.cpu_max_mhz = self._extract_lscpu_value(lscpu_text, "CPU max MHz")
        capability.cpu_min_mhz = self._extract_lscpu_value(lscpu_text, "CPU min MHz")
        capability.cpu_scaling_mhz = self._extract_lscpu_value(lscpu_text, "CPU(s) scaling MHz") or self._extract_lscpu_value(
            lscpu_text, "CPU MHz"
        )
        capability.logical_cores = self._extract_int(lscpu_text, "CPU(s)")
        cores_per_socket = self._extract_int(lscpu_text, "Core(s) per socket")
        sockets = self._extract_int(lscpu_text, "Socket(s)")
        if cores_per_socket and sockets:
            capability.physical_cores = cores_per_socket * sockets
        capability.l1d_cache = self._extract_lscpu_value(lscpu_text, "L1d cache")
        capability.l1i_cache = self._extract_lscpu_value(lscpu_text, "L1i cache")
        capability.l2_cache = self._extract_lscpu_value(lscpu_text, "L2 cache")
        capability.l3_cache = self._extract_lscpu_value(lscpu_text, "L3 cache")
        capability.numa_nodes = self._extract_int(lscpu_text, "NUMA node(s)")

        perf_version = self._run_command(["perf", "--version"])
        capability.adb_available = shutil.which("adb") is not None
        if capability.adb_available:
            adb_devices_text = self._run_command(["adb", "devices", "-l"])
            capability.connected_devices = self._discover_connected_devices(adb_devices_text)
            if adb_devices_text.strip():
                adb_devices_path = self.store.save_text("artifacts/environment/adb_devices.txt", adb_devices_text)
                state.artifacts["environment.adb_devices"] = str(adb_devices_path)
            selected_device, selected_reason = self._select_device(capability.connected_devices)
            if selected_device is not None:
                capability.selected_device_serial = selected_device.serial
                capability.selected_device_summary = selected_reason
                capability.notes.append(selected_reason)
            elif capability.connected_devices:
                capability.notes.append("检测到 adb 设备，但当前没有处于 device 状态且可直接分析的目标。")

        selected_device = next(
            (device for device in capability.connected_devices if device.serial == capability.selected_device_serial),
            None,
        )
        capability.execution_target = "device" if should_use_device_target(state, selected_device) else ("pid_attach" if state.target_pid is not None else "host")

        backend_info = self._resolve_active_backend(state, capability, selected_device, perf_version)
        capability.perf_available = backend_info["available"]
        capability.perf_version = backend_info["version"]
        capability.profiling_backend_name = backend_info["name"]
        capability.profiling_backend_tool = backend_info["tool"]
        capability.profiling_backend_summary = backend_info["summary"]
        perf_list_text = backend_info["event_list"]
        parsed_events, aliases, catalog = self._parse_perf_list(perf_list_text)
        capability.available_events = parsed_events
        capability.event_aliases = aliases
        capability.event_catalog = catalog
        capability.topdown_events = [event for event in parsed_events if "topdown" in event]
        capability.tma_metrics = [event for event in parsed_events if event.startswith("tma_")]
        capability.hybrid_pmus = sorted({event.split("/", 1)[0] for event in parsed_events if "/" in event and event.startswith("cpu_")})
        capability.topdown_supported = bool(capability.topdown_events or capability.tma_metrics)
        capability.event_sources = self._event_sources(selected_device)
        capability.callgraph_modes = self._detect_callgraph_modes(selected_device)
        capability.perf_permissions = self._read_perf_paranoid()
        capability.supports_addr2line = shutil.which("addr2line") is not None
        capability.platform_profile, capability.stat_event_budget, capability.interval_event_budget = self._detect_counter_profile(
            capability.arch,
            selected_device=selected_device,
            backend_name=capability.profiling_backend_name,
        )
        if self.sandbox_manager is not None:
            sandbox_resolution = self.sandbox_manager.resolve_runtime(state)
            capability.sandbox_enabled = sandbox_resolution.enabled
            capability.available_sandbox_runtimes = self.sandbox_manager.available_runtime_names()
            capability.configured_sandbox_runtime = (
                os.getenv("PERF_AGENT_SANDBOX_RUNTIME") or self.sandbox_manager.config.default_runtime
            )
            capability.selected_sandbox_runtime = sandbox_resolution.runtime_name
            if capability.sandbox_enabled:
                capability.notes.append(sandbox_resolution.reason)
                if capability.available_sandbox_runtimes:
                    capability.notes.append(
                        f"可用隔离运行时: {', '.join(capability.available_sandbox_runtimes)}。"
                    )
                else:
                    capability.notes.append("当前未探测到可用的隔离运行时。")

        executable_path = state.executable_path or (state.target_cmd[0] if state.target_cmd else None)
        if executable_path:
            capability.executable_kind, capability.executable_stripped = self._inspect_executable(executable_path)
            capability.executable_has_symbols = self._has_symbols(executable_path)

        if perf_list_text.strip():
            perf_list_path = self.store.save_text(f"artifacts/environment/{backend_info['list_filename']}", perf_list_text)
            state.artifacts["environment.perf_list"] = str(perf_list_path)

        if capability.topdown_supported:
            capability.notes.append("检测到 top-down / TMA 相关事件，后续实验会优先尝试更细粒度的前后端拆分。")
        else:
            capability.notes.append("未检测到 top-down / TMA 相关事件，后续会自动退化到通用计数器。")
        capability.notes.append(
            f"当前平台画像为 {capability.platform_profile or 'generic'}，perf stat 计划按最多 {capability.stat_event_budget} 个事件分组，interval 计划按最多 {capability.interval_event_budget} 个事件分组。"
        )
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
            execution_target=capability.execution_target,
            profiling_backend=capability.profiling_backend_name,
            event_count=len(capability.available_events),
            callgraph_modes=capability.callgraph_modes,
        )
        return state

    def _discover_connected_devices(self, adb_devices_text: str) -> list[ConnectedDevice]:
        devices: list[ConnectedDevice] = []
        for raw_line in adb_devices_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("List of devices attached"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial = parts[0]
            status = parts[1]
            metadata: dict[str, str] = {}
            for token in parts[2:]:
                if ":" not in token:
                    continue
                key, value = token.split(":", 1)
                metadata[key] = value
            device = ConnectedDevice(
                serial=serial,
                status=status,
                transport_id=metadata.get("transport_id"),
                product=metadata.get("product"),
                model=metadata.get("model"),
                device_name=metadata.get("device"),
                is_remote=self._is_remote_serial(serial),
                host=self._serial_host(serial),
                port=self._serial_port(serial),
            )
            if status == "device":
                device = self._probe_connected_device(device)
            devices.append(device)
        return devices

    def _probe_connected_device(self, device: ConnectedDevice) -> ConnectedDevice:
        probe = self._run_command(
            [
                "adb",
                "-s",
                device.serial,
                "shell",
                "sh",
                "-c",
                "getprop ro.product.cpu.abi; "
                "getprop ro.build.version.release; "
                "getprop ro.build.version.sdk; "
                "command -v simpleperf 2>/dev/null || true; "
                "command -v hiperf 2>/dev/null || true",
            ],
            timeout=6,
        )
        lines = [line.strip() for line in probe.replace("\r", "\n").splitlines()]
        values = [line for line in lines if line]
        if values:
            device.arch = values[0] if len(values) > 0 else None
            device.os_release = values[1] if len(values) > 1 else None
            device.sdk = values[2] if len(values) > 2 else None
            backend_candidates = values[3:]
            backends: list[str] = []
            for item in backend_candidates:
                lowered = item.lower()
                if "simpleperf" in lowered:
                    backends.append("simpleperf")
                if "hiperf" in lowered:
                    backends.append("hiperf")
            device.backend_tools = sorted(set(backends))
        if "hiperf" in device.backend_tools:
            device.platform_hint = "harmony"
        elif "simpleperf" in device.backend_tools:
            device.platform_hint = "android"
        else:
            device.platform_hint = "adb"
        return device

    def _select_device(self, devices: list[ConnectedDevice]) -> tuple[ConnectedDevice | None, str | None]:
        selectable: list[ConnectedDevice] = []
        for device in devices:
            scored = device.model_copy(deep=True)
            scored.selectable = scored.status == "device"
            scored.selection_score = self._score_device(scored)
            if scored.selectable:
                selectable.append(scored)
        if not selectable:
            return None, None
        ranked = sorted(selectable, key=lambda item: (-item.selection_score, item.serial))
        selected = ranked[0]
        if len(selectable) == 1:
            reason = (
                f"已自动选择 ADB 设备 {selected.serial}"
                f"{self._format_device_suffix(selected)}，因为它是当前唯一在线的可分析设备。"
            )
        else:
            reason = (
                f"已在 {len(selectable)} 台在线 ADB 设备中自动选择 {selected.serial}"
                f"{self._format_device_suffix(selected)}，因为它的分析后端能力与可用性评分最高。"
            )
        return selected, reason

    def _score_device(self, device: ConnectedDevice) -> int:
        if device.status != "device":
            return -100
        score = 100
        if device.backend_tools:
            score += 30 + (10 * len(device.backend_tools))
        if device.platform_hint in {"android", "harmony"}:
            score += 10
        lowered_model = (device.model or "").lower()
        lowered_serial = device.serial.lower()
        if any(keyword in lowered_model or keyword in lowered_serial for keyword in ("emulator", "sdk", "generic")):
            score -= 15
        else:
            score += 10
        if device.arch and any(token in device.arch.lower() for token in ("arm", "aarch64")):
            score += 5
        if device.is_remote:
            score += 2
        return score

    def _format_device_suffix(self, device: ConnectedDevice) -> str:
        parts: list[str] = []
        if device.model:
            parts.append(device.model)
        if device.platform_hint and device.platform_hint != "adb":
            parts.append(device.platform_hint)
        if device.backend_tools:
            parts.append(f"后端 {', '.join(device.backend_tools)}")
        return f"（{'，'.join(parts)}）" if parts else ""

    def _is_remote_serial(self, serial: str) -> bool:
        return bool(self._serial_host(serial))

    def _serial_host(self, serial: str) -> str | None:
        if ":" not in serial:
            return None
        host, _, tail = serial.rpartition(":")
        if not host or not tail.isdigit():
            return None
        return host

    def _serial_port(self, serial: str) -> int | None:
        if ":" not in serial:
            return None
        _, _, tail = serial.rpartition(":")
        if not tail.isdigit():
            return None
        return int(tail)

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

    def _event_sources(self, selected_device: ConnectedDevice | None = None) -> list[str]:
        if selected_device is not None:
            sources = ["adb"]
            sources.extend(selected_device.backend_tools)
            return sources
        root = Path("/sys/bus/event_source/devices")
        if not root.exists():
            return []
        return sorted(item.name for item in root.iterdir() if item.is_dir())

    def _detect_callgraph_modes(self, selected_device: ConnectedDevice | None = None) -> list[str]:
        if selected_device is not None:
            if "simpleperf" in selected_device.backend_tools:
                return ["fp", "dwarf"]
            if "hiperf" in selected_device.backend_tools:
                return ["fp"]
            return []
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

    def _detect_counter_profile(
        self,
        arch: str | None,
        *,
        selected_device: ConnectedDevice | None = None,
        backend_name: str | None = None,
    ) -> tuple[str, int, int]:
        if backend_name == "android_simpleperf":
            return ("android", 4, 4)
        if backend_name == "harmony_hiperf":
            return ("harmony", 6, 6)
        lowered_arch = (arch or "").lower()
        if selected_device is not None and selected_device.arch:
            lowered_arch = selected_device.arch.lower()
        if lowered_arch in {"arm64", "aarch64", "arm"}:
            return ("arm-linux", 13, 6)
        if lowered_arch in {"x86_64", "amd64"}:
            return ("x86-linux", 8, 5)
        return ("generic-linux", 6, 4)

    def _resolve_active_backend(
        self,
        state: AnalysisState,
        capability: EnvironmentCapability,
        selected_device: ConnectedDevice | None,
        host_perf_version: str,
    ) -> dict[str, str | bool]:
        if capability.execution_target == "device" and selected_device is not None:
            if "hiperf" in selected_device.backend_tools:
                version = self._run_command(["adb", "-s", selected_device.serial, "shell", "hiperf", "--help"], timeout=8)
                events = self._run_command(["adb", "-s", selected_device.serial, "shell", "hiperf", "list"], timeout=12)
                return {
                    "available": bool(events.strip()),
                    "version": "hiperf (device)" if version else "hiperf (device)",
                    "name": "harmony_hiperf",
                    "tool": "hiperf",
                    "summary": f"当前目标被识别为设备端命令，使用 {selected_device.serial} 上的 hiperf 采样。",
                    "event_list": events,
                    "list_filename": "hiperf_list.txt",
                }
            if "simpleperf" in selected_device.backend_tools:
                version = self._run_command(["adb", "-s", selected_device.serial, "shell", "simpleperf", "--version"], timeout=8).strip()
                events = self._run_command(["adb", "-s", selected_device.serial, "shell", "simpleperf", "list"], timeout=12)
                return {
                    "available": bool(events.strip()),
                    "version": version or "simpleperf (device)",
                    "name": "android_simpleperf",
                    "tool": "simpleperf",
                    "summary": f"当前目标被识别为设备端命令，使用 {selected_device.serial} 上的 simpleperf 采样。",
                    "event_list": events,
                    "list_filename": "simpleperf_list.txt",
                }

        return {
            "available": bool(host_perf_version.strip()),
            "version": host_perf_version.strip() or None,
            "name": "host_perf_attach" if state.target_pid is not None and not state.target_cmd else "host_perf",
            "tool": "perf",
            "summary": "当前目标被识别为宿主机程序，使用本机 perf 工具链采样。",
            "event_list": self._run_command(["perf", "list"]),
            "list_filename": "perf_list.txt",
        }

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

    def _parse_perf_list(self, text: str) -> tuple[list[str], dict[str, list[str]], dict[str, EventDescriptor]]:
        events: set[str] = set()
        aliases: dict[str, set[str]] = {}
        catalog: dict[str, EventDescriptor] = {}

        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped or stripped.endswith(":"):
                continue
            if stripped.startswith("#") or stripped.lower().startswith("list of "):
                continue
            if stripped.lower().startswith("supported events for "):
                continue
            if stripped.lower().startswith("event not support"):
                continue
            parsed = self._parse_event_names(line)
            if not parsed:
                continue
            for event in parsed:
                events.add(event)
                descriptor = self._describe_event(event)
                catalog[event] = descriptor
                for alias_key in descriptor.semantic_keys:
                    aliases.setdefault(alias_key, set()).add(event)
                aliases.setdefault(event.lower(), set()).add(event)

        normalized_aliases = {key: sorted(values) for key, values in aliases.items()}
        return sorted(events), normalized_aliases, catalog

    def _parse_event_names(self, line: str) -> list[str]:
        alias_match = ALIAS_LINE_PATTERN.match(line)
        if alias_match:
            return [item.strip() for item in alias_match.group(1).split(" OR ") if item.strip()]

        metric_match = INDENTED_EVENT_PATTERN.match(line)
        if metric_match:
            candidate = metric_match.group(1).strip()
            if candidate and not candidate.endswith(":"):
                return [candidate]
        return []

    def _describe_event(self, event_name: str) -> EventDescriptor:
        lowered = event_name.lower().strip().strip("/")
        semantic_keys = sorted(self._semantic_keys_for_event(lowered))
        source_type = self._event_source_type(lowered)
        descriptor = EventDescriptor(
            name=event_name,
            source_type=source_type,
            semantic_keys=semantic_keys,
            stat_usable=source_type not in {"unknown"} and not lowered.startswith("tma_"),
            record_usable=source_type not in {"metric"},
            interval_usable=source_type in {"hardware", "software", "metric", "raw", "pmu"},
            portability_score=self._portability_score(source_type, semantic_keys, lowered),
        )
        if source_type == "metric":
            descriptor.notes.append("更适合 perf stat / interval 解释，不适合直接作为 perf record 采样事件。")
        if source_type == "raw":
            descriptor.notes.append("属于 raw/PMU 编码层事件，适合架构清楚时做更底层的对齐。")
        if source_type == "tracepoint":
            descriptor.notes.append("属于 tracepoint，适合调度、IO、锁和系统行为观测。")
        return descriptor

    def _event_source_type(self, lowered: str):
        if lowered.startswith("topdown-") or lowered.startswith("tma_"):
            return "metric"
        if ":" in lowered:
            return "tracepoint"
        if lowered.startswith("raw-") or RAW_HEX_PATTERN.match(lowered) or "event=0x" in lowered or "config=0x" in lowered:
            return "raw"
        if lowered.startswith("sw-") or lowered in KNOWN_SOFTWARE_KEYS:
            return "software"
        if lowered.startswith("hw-") or lowered in KNOWN_HARDWARE_KEYS:
            return "hardware"
        if "." in lowered and any(
            lowered.startswith(prefix)
            for prefix in (
                "l1",
                "l2",
                "l3",
                "ll",
                "mem_",
                "longest_lat_cache",
                "offcore",
                "cycle_activity",
                "frontend_retired",
                "memory_activity",
                "ocr.",
            )
        ):
            return "pmu"
        if "/" in lowered:
            return "pmu"
        return "hardware" if any(key in lowered for key in ("cycles", "instructions", "cache", "branch", "slots")) else "unknown"

    def _semantic_keys_for_event(self, lowered: str) -> set[str]:
        keys = {lowered}
        stripped = lowered.strip("/")
        keys.add(stripped)
        dashed = stripped.replace("_", "-")
        underscored = stripped.replace("-", "_")
        keys.add(dashed)
        keys.add(underscored)
        base = stripped
        for prefix in ("hw-", "sw-", "raw-"):
            if base.startswith(prefix):
                base = base.removeprefix(prefix)
                keys.add(base)
                keys.add(base.replace("_", "-"))
                keys.add(base.replace("-", "_"))
        if "/" in base:
            core = base.split("/")[-1]
            keys.add(core)
            keys.add(core.replace("_", "-"))
            keys.add(core.replace("-", "_"))
            if core.startswith("event="):
                keys.add(core.removeprefix("event="))
        if base.startswith("cpu-"):
            keys.add(base.removeprefix("cpu-"))
        if base.startswith("branch-") and "instructions" in base:
            keys.add("branches")
        for source_key, aliases in SEMANTIC_ALIASES.items():
            if base == source_key or stripped == source_key:
                keys.update(aliases)
        return {key for key in keys if key}

    def _portability_score(self, source_type: str, semantic_keys: list[str], lowered: str) -> int:
        if source_type == "hardware":
            return 95
        if source_type == "software":
            return 90
        if source_type == "metric":
            return 70
        if source_type == "tracepoint":
            return 45
        if source_type == "raw":
            if any(key in semantic_keys for key in {"cycles", "instructions", "cache-misses", "cache-references", "branches", "branch-misses"}):
                return 85
            return 40
        if source_type == "pmu":
            if "cpu" in lowered or "armv8" in lowered:
                return 75
            return 35
        return 20
