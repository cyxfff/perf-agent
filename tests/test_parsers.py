from __future__ import annotations

from pathlib import Path

from perf_agent.parsers.generic_parser import parse_text as parse_generic
from perf_agent.parsers.perf_record_parser import parse_text as parse_perf_record
from perf_agent.parsers.perf_stat_parser import parse_text as parse_perf_stat
from perf_agent.parsers.pidstat_parser import parse_text as parse_pidstat


def test_perf_stat_parser_extracts_core_metrics() -> None:
    sample = Path("tests/fixtures/perf_stat_sample.txt").read_text(encoding="utf-8")
    observations = parse_perf_stat(sample, source="perf_stat", action_id="artifact_1")

    metrics = {observation.metric: observation.value for observation in observations}
    assert metrics["cpu_utilization_pct"] == 98.7
    assert metrics["ipc"] == 0.5


def test_pidstat_parser_extracts_wait_and_cpu() -> None:
    sample = Path("tests/fixtures/pidstat_sample.txt").read_text(encoding="utf-8")
    observations = parse_pidstat(sample, source="pidstat", action_id="artifact_2")

    metrics = {observation.metric: observation.value for observation in observations}
    assert metrics["usr_pct"] == 94.0
    assert metrics["wait_pct"] == 1.0


def test_generic_parser_extracts_kv_metrics() -> None:
    observations = parse_generic("disk_util=89.0\nawait_ms=23.5\n", source="iostat", action_id="artifact_3")

    metrics = {observation.metric: observation.value for observation in observations}
    assert metrics["disk_util_pct"] == 89.0
    assert metrics["await_ms"] == 23.5


def test_perf_stat_parser_extracts_timeline_metrics_on_hybrid_events() -> None:
    sample = "\n".join(
        [
            "0.100105668,23828070,,cpu_core/cycles/,5603814,91.00,,",
            "0.100105668,14567877,,cpu_atom/cycles/,527685,8.00,,",
            "0.100105668,37602097,,cpu_core/instructions/,5603814,91.00,,",
            "0.100105668,20140995,,cpu_atom/instructions/,527685,8.00,,",
            "0.200259401,21902972,,cpu_core/cycles/,4458057,78.00,,",
            "0.200259401,11602137,,cpu_atom/cycles/,1203881,25.00,,",
            "0.200259401,35387498,,cpu_core/instructions/,4458057,78.00,,",
            "0.200259401,17597063,,cpu_atom/instructions/,1203881,25.00,,",
        ]
    )
    observations = parse_perf_stat(sample, source="perf_stat", action_id="artifact_4")

    timeline_ipc = [item for item in observations if item.metric == "ipc" and item.labels.get("series_type") == "timeline"]
    timeline_cycles = [item for item in observations if item.metric == "cycles" and item.labels.get("series_type") == "timeline"]
    assert len(timeline_cycles) >= 2
    assert len(timeline_ipc) == 2


def test_perf_record_parser_extracts_hot_symbols() -> None:
    sample = "\n".join(
        [
            "Samples: 432 of event 'cycles', Event count (approx.): 123456",
            "  35.12%  cpu_bound_demo  cpu_bound_demo  [.] hot_loop",
            "  18.44%  cpu_bound_demo  cpu_bound_demo  [.] main",
        ]
    )
    observations = parse_perf_record(sample, source="perf_record", action_id="artifact_5")
    hot_symbols = [item.labels.get("symbol") for item in observations if item.metric == "hot_symbol_pct"]
    assert "hot_loop" in hot_symbols


def test_perf_stat_parser_extracts_simpleperf_interval_metrics() -> None:
    sample = "\n".join(
        [
            "Performance counter statistics,",
            "245385664,raw-cpu-cycles:u,2.454,G/sec,",
            "753542440,raw-inst-retired:u,7.534,G/sec,",
            "Total test time,0.100951,seconds,",
            "Performance counter statistics,",
            "259295132,raw-cpu-cycles:u,2.590,G/sec,",
            "802565875,raw-inst-retired:u,8.016,G/sec,",
            "Total test time,0.213901,seconds,",
        ]
    )

    observations = parse_perf_stat(sample, source="perf_stat", action_id="artifact_6")

    timeline_cycles = [item for item in observations if item.metric == "cycles" and item.labels.get("series_type") == "timeline"]
    timeline_ipc = [item for item in observations if item.metric == "ipc" and item.labels.get("series_type") == "timeline"]
    assert len(timeline_cycles) == 2
    assert len(timeline_ipc) == 2


def test_perf_record_parser_extracts_simpleperf_samples() -> None:
    sample = "\n".join(
        [
            "=== report ===",
            "Overhead  Symbol",
            "18.64%    scudo::HybridMutex::tryLock()",
            "16.26%    scudo::HybridMutex::unlock()",
            "",
            "=== script ===",
            "sample:",
            "  event_type: raw-cpu-cycles:u",
            "  time: 123216683338189",
            "  event_count: 69",
            "  thread_id: 28287",
            "  thread_name: sh",
            "  vaddr_in_file: 1644a0",
            "  file: /apex/com.android.runtime/bin/linker64",
            "  symbol: [linker]__linker_init",
            "sample:",
            "  event_type: raw-cpu-cycles:u",
            "  time: 123216683342497",
            "  event_count: 570",
            "  thread_id: 28287",
            "  thread_name: sh",
            "  vaddr_in_file: c6cae",
            "  file: /apex/com.android.runtime/bin/linker64",
            "  symbol: *linker64[+c6cae]",
        ]
    )

    observations = parse_perf_record(sample, source="perf_record", action_id="artifact_7")

    metrics = [item.metric for item in observations]
    hot_symbols = [item.labels.get("symbol") for item in observations if item.metric == "hot_symbol_pct"]
    assert "callgraph_samples" in metrics
    assert "thread_sample_pct" in metrics
    assert "hot_frame_sample_pct" in metrics
    assert "scudo::HybridMutex::tryLock()" in hot_symbols
