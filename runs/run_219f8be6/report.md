# Performance Analysis Report

## Executive Summary
Primary suspected bottleneck: io_bound (confidence=0.92).

## Observed Facts
- io_bound: time.cpu_utilization_pct=32
- io_bound: perf_stat.cpu_utilization_pct=40.0
- io_bound: pidstat.wait_pct=42.0
- io_bound: pidstat.cpu_utilization_pct=25.0
- io_bound: iostat.disk_util_pct=89.0
- io_bound: iostat.await_ms=23.5

## Candidate Bottlenecks
- io_bound

## Rejected Alternatives

## Confidence
- overall=0.92

## Recommended Next Steps
- Add iostat to validate disk latency and utilization.
