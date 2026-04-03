from __future__ import annotations

from pathlib import Path

from perf_agent.agents.environment_profiler import EnvironmentProfiler
from perf_agent.models.environment import ConnectedDevice
from perf_agent.storage.json_store import JSONArtifactStore


def test_environment_profiler_parses_android_raw_lines(tmp_path: Path) -> None:
    profiler = EnvironmentProfiler(JSONArtifactStore(tmp_path))
    text = """
List of hardware events:
  cpu-cycles

List of raw events provided by cpu pmu:
  raw-cpu-cycles (supported on cpu 0-7)        # Cycle
  raw-inst-retired (supported on cpu 0-7)      # Instruction architecturally executed
"""

    events, aliases, catalog = profiler._parse_perf_list(text)

    assert "raw-cpu-cycles" in events
    assert "raw-inst-retired" in events
    assert "raw-cpu-cycles" in aliases["cycles"]
    assert "raw-inst-retired" in aliases["instructions"]
    assert catalog["raw-cpu-cycles"].source_type == "raw"


def test_environment_profiler_ignores_hiperf_not_supported_lines(tmp_path: Path) -> None:
    profiler = EnvironmentProfiler(JSONArtifactStore(tmp_path))
    text = """
event not support hw-ref-cpu-cycles

Supported events for hardware:
\thw-cpu-cycles
\thw-instructions
"""

    events, aliases, catalog = profiler._parse_perf_list(text)

    assert "event" not in events
    assert "hw-cpu-cycles" in events
    assert "hw-cpu-cycles" in aliases["cycles"]
    assert catalog["hw-cpu-cycles"].source_type == "hardware"


def test_environment_profiler_parses_adb_devices_and_marks_remote(tmp_path: Path) -> None:
    profiler = EnvironmentProfiler(JSONArtifactStore(tmp_path))
    profiler._probe_connected_device = lambda device: device  # type: ignore[method-assign]
    text = """
List of devices attached
10.87.51.151:5555      device product:scout_cn_sys model:XT2503_3 device:scout transport_id:1
emulator-5554          offline transport_id:2
"""

    devices = profiler._discover_connected_devices(text)

    assert len(devices) == 2
    assert devices[0].serial == "10.87.51.151:5555"
    assert devices[0].is_remote is True
    assert devices[0].host == "10.87.51.151"
    assert devices[0].port == 5555
    assert devices[0].model == "XT2503_3"
    assert devices[1].status == "offline"


def test_environment_profiler_selects_best_online_device(tmp_path: Path) -> None:
    profiler = EnvironmentProfiler(JSONArtifactStore(tmp_path))
    devices = [
        ConnectedDevice(
            serial="emulator-5554",
            status="device",
            model="sdk_gphone64",
            backend_tools=["simpleperf"],
            platform_hint="android",
            selectable=True,
        ),
        ConnectedDevice(
            serial="10.87.51.151:5555",
            status="device",
            model="XT2503_3",
            backend_tools=["simpleperf"],
            platform_hint="android",
            is_remote=True,
            selectable=True,
        ),
    ]

    selected, reason = profiler._select_device(devices)

    assert selected is not None
    assert selected.serial == "10.87.51.151:5555"
    assert reason is not None
    assert "已在 2 台在线 ADB 设备中自动选择" in reason
