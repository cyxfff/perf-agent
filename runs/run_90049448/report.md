# Performance Analysis Report

## Executive Summary
Primary suspected bottleneck: lock_contention (confidence=0.73).

## Observed Facts
- lock_contention: perf_stat.lock_wait_pct=18.0
- lock_contention: mpstat.context_switches_per_sec=22000
- lock_contention: perf_record.callgraph_samples=2
- scheduler_issue: time.involuntary_context_switches=410
- scheduler_issue: mpstat.context_switches_per_sec=22000
- scheduler_issue: mpstat.run_queue=9

## Candidate Bottlenecks
- lock_contention
- scheduler_issue

## Rejected Alternatives
- scheduler_issue had weaker support than the top candidate.

## Confidence
- overall=0.73

## Recommended Next Steps
- Collect perf record stacks and look for futex or lock-owner hotspots.
- Inspect run queue pressure and context-switch behavior with mpstat or sched traces.
