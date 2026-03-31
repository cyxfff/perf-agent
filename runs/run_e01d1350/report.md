# Performance Analysis Report

## 1. Executive Summary
Primary suspected bottleneck: cpu_bound (confidence=0.95).

## 2. Target
- command: python demo_cpu.py
- runtime: verification_rounds=0, actions_executed=4
- environment: cwd=

## 3. Key Observations
- obs_de4e8f5c: time.user_time_sec=3.2
- obs_8d2bbc25: time.system_time_sec=0.1
- obs_5dca6af8: time.cpu_utilization_pct=99
- obs_9f1ccb4f: time.max_rss_kb=20480
- obs_fd266d02: time.major_faults=0
- obs_4aa779fe: time.voluntary_context_switches=12
- obs_fa6a162c: time.involuntary_context_switches=31
- obs_663d93a1: perf_stat.task_clock_ms=1234.56
- obs_b67d40a7: perf_stat.cpu_utilization_pct=98.7
- obs_6b090771: perf_stat.cycles=4200000000
- obs_193034e6: perf_stat.instructions=2100000000
- obs_e8c0a909: perf_stat.ipc=0.5
- obs_94990fab: perf_stat.cache_misses=12500
- obs_a21f9372: pidstat.usr_pct=94.0
- obs_95153b16: pidstat.system_pct=4.0
- obs_44342bfc: pidstat.wait_pct=1.0
- obs_ef9248cb: pidstat.cpu_utilization_pct=98.0
- obs_dae40365: mpstat.cpu_utilization_pct=98.0
- obs_27ae27a3: mpstat.iowait_pct=1.0
- obs_404b15df: mpstat.context_switches_per_sec=1500

## 4. Candidate Bottlenecks
### 4.1 cpu_bound
- confidence: 0.95
- supporting evidence: obs_5dca6af8, obs_b67d40a7, obs_e8c0a909, obs_a21f9372, obs_95153b16, obs_ef9248cb, obs_dae40365
- contradicting evidence: none
- verification status: sufficient

## 5. Additional Verification
- actions executed:
- act_50312563: time [done]
- act_288c09ed: perf_stat [done]
- act_a97f9542: pidstat [done]
- act_da653e99: mpstat [done]
- new evidence:
- cpu_bound: time.cpu_utilization_pct=99
- cpu_bound: perf_stat.cpu_utilization_pct=98.7
- cpu_bound: perf_stat.ipc=0.5
- cpu_bound: pidstat.usr_pct=94.0
- cpu_bound: pidstat.system_pct=4.0
- cpu_bound: pidstat.cpu_utilization_pct=98.0
- cpu_bound: mpstat.cpu_utilization_pct=98.0

## 6. Recommendations
- Run perf record -g to locate the hottest functions.

## 7. Artifacts
- runs/run_e01d1350/artifacts/act_288c09ed.json
- runs/run_e01d1350/artifacts/act_288c09ed.stdout.txt
- runs/run_e01d1350/artifacts/act_288c09ed.stdout.txt
- runs/run_e01d1350/artifacts/act_50312563.json
- runs/run_e01d1350/artifacts/act_50312563.stdout.txt
- runs/run_e01d1350/artifacts/act_50312563.stdout.txt
- runs/run_e01d1350/artifacts/act_a97f9542.json
- runs/run_e01d1350/artifacts/act_a97f9542.stdout.txt
- runs/run_e01d1350/artifacts/act_a97f9542.stdout.txt
- runs/run_e01d1350/artifacts/act_da653e99.json
- runs/run_e01d1350/artifacts/act_da653e99.stdout.txt
- runs/run_e01d1350/artifacts/act_da653e99.stdout.txt
