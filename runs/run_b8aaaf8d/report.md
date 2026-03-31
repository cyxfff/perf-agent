# Performance Analysis Report

## Executive Summary
Primary suspected bottleneck: io_bound (confidence=0.85).

## Observed Facts
- io_bound: time.cpu_utilization_pct=32
- io_bound: perf_stat.cpu_utilization_pct=40.0
- io_bound: pidstat.wait_pct=42.0
- io_bound: pidstat.cpu_utilization_pct=25.0
- io_bound: iostat.disk_util_pct=89.0\nawait_ms=23.5\nread_mb_s=120.0\nwrite_mb_s=15.0\n

## Candidate Bottlenecks
- io_bound

## Rejected Alternatives

## Confidence
- overall=0.85

## Recommended Next Steps
- Add iostat to validate disk latency and utilization.
