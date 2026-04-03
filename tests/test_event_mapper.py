from __future__ import annotations

from perf_agent.models.environment import ConnectedDevice, EnvironmentCapability, EventDescriptor
from perf_agent.models.state import AnalysisState
from perf_agent.planning.event_mapper import EventMapper


def test_event_mapper_prefers_arm_raw_for_architected_cpu_events() -> None:
    state = AnalysisState(
        run_id="run_test",
        environment=EnvironmentCapability(
            arch="aarch64",
            perf_available=True,
            available_events=["hw-cpu-cycles", "raw-cpu-cycles"],
            event_aliases={
                "cycles": ["hw-cpu-cycles", "raw-cpu-cycles"],
                "cpu-cycles": ["hw-cpu-cycles", "raw-cpu-cycles"],
            },
            event_catalog={
                "hw-cpu-cycles": EventDescriptor(
                    name="hw-cpu-cycles",
                    source_type="hardware",
                    semantic_keys=["hw-cpu-cycles", "cpu-cycles", "cycles"],
                    portability_score=95,
                ),
                "raw-cpu-cycles": EventDescriptor(
                    name="raw-cpu-cycles",
                    source_type="raw",
                    semantic_keys=["raw-cpu-cycles", "cpu-cycles", "cycles"],
                    portability_score=85,
                ),
            },
        ),
    )

    mapper = EventMapper()

    assert mapper._resolve_event_name(state, "cycles") == "raw-cpu-cycles"


def test_event_mapper_prefers_software_event_for_scheduler_baseline() -> None:
    state = AnalysisState(
        run_id="run_test",
        environment=EnvironmentCapability(
            arch="aarch64",
            perf_available=True,
            available_events=["sw-context-switches", "sched:sched_switch"],
            event_aliases={
                "context-switches": ["sw-context-switches", "sched:sched_switch"],
            },
            event_catalog={
                "sw-context-switches": EventDescriptor(
                    name="sw-context-switches",
                    source_type="software",
                    semantic_keys=["sw-context-switches", "context-switches"],
                    portability_score=90,
                ),
                "sched:sched_switch": EventDescriptor(
                    name="sched:sched_switch",
                    source_type="tracepoint",
                    semantic_keys=["sched:sched_switch", "context-switches"],
                    portability_score=45,
                ),
            },
        ),
    )

    mapper = EventMapper()

    assert mapper._resolve_event_name(state, "context-switches") == "sw-context-switches"


def test_event_mapper_uses_selected_device_arch_for_raw_preference() -> None:
    state = AnalysisState(
        run_id="run_test",
        environment=EnvironmentCapability(
            arch="x86_64",
            execution_target="device",
            selected_device_serial="10.0.0.2:5555",
            connected_devices=[
                ConnectedDevice(
                    serial="10.0.0.2:5555",
                    status="device",
                    arch="arm64-v8a",
                )
            ],
            perf_available=True,
            available_events=["cpu-cycles", "raw-cpu-cycles"],
            event_aliases={"cycles": ["cpu-cycles", "raw-cpu-cycles"]},
            event_catalog={
                "cpu-cycles": EventDescriptor(
                    name="cpu-cycles",
                    source_type="hardware",
                    semantic_keys=["cpu-cycles", "cycles"],
                    portability_score=95,
                ),
                "raw-cpu-cycles": EventDescriptor(
                    name="raw-cpu-cycles",
                    source_type="raw",
                    semantic_keys=["raw-cpu-cycles", "cpu-cycles", "cycles"],
                    portability_score=85,
                ),
            },
        ),
    )

    mapper = EventMapper()

    assert mapper._resolve_event_name(state, "cycles") == "raw-cpu-cycles"
