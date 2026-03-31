# Performance Analysis Report

## Executive Summary
Primary suspected bottleneck: cpu_bound (confidence=0.95).

## Observed Facts
- cpu_bound: time.cpu_utilization_pct=99
- cpu_bound: perf_stat.cpu_utilization_pct=98.7
- cpu_bound: perf_stat.ipc=0.5
- cpu_bound: pidstat.usr_pct=94.0
- cpu_bound: pidstat.system_pct=4.0
- cpu_bound: pidstat.cpu_utilization_pct=98.0
- cpu_bound: mpstat.cpu_utilization_pct=98.0\niowait=1.0\ncswch_per_sec=1500\n

## Candidate Bottlenecks
- cpu_bound

## Rejected Alternatives

## Confidence
- overall=0.95

## Recommended Next Steps
- Run perf record -g to locate the hottest functions.
