# Performance Analysis Report

## 1. Executive Summary
Primary suspected bottleneck: cpu_bound (confidence=0.95).

## 2. Target
- command: python demo_cpu.py
- runtime: verification_rounds=0, actions_executed=4
- environment: cwd=

## 3. Key Observations
- obs_212275ca: time.user_time_sec=3.2
- obs_ebad467b: time.system_time_sec=0.1
- obs_5237daaa: time.cpu_utilization_pct=99
- obs_ddc42db7: time.max_rss_kb=20480
- obs_521ae1bc: time.major_faults=0
- obs_8edd9f8d: time.voluntary_context_switches=12
- obs_2a6f78d2: time.involuntary_context_switches=31
- obs_c4c9f305: perf_stat.task_clock_ms=1234.56
- obs_0801f80a: perf_stat.cpu_utilization_pct=98.7
- obs_2c2504dd: perf_stat.cycles=4200000000
- obs_7e7031e3: perf_stat.instructions=2100000000
- obs_543c940e: perf_stat.ipc=0.5
- obs_9b7603ff: perf_stat.cache_misses=12500
- obs_12b97cb8: pidstat.usr_pct=94.0
- obs_a7860452: pidstat.system_pct=4.0
- obs_6b574c9a: pidstat.wait_pct=1.0
- obs_f9cd2023: pidstat.cpu_utilization_pct=98.0
- obs_0200c555: mpstat.cpu_utilization_pct=98.0
- obs_f8e68ae6: mpstat.iowait_pct=1.0
- obs_a0d95c1a: mpstat.context_switches_per_sec=1500

## 4. Candidate Bottlenecks
### 4.1 cpu_bound
- confidence: 0.95
- supporting evidence: obs_5237daaa, obs_0801f80a, obs_543c940e, obs_12b97cb8, obs_a7860452, obs_f9cd2023, obs_0200c555
- contradicting evidence: none
- verification status: sufficient

## 5. Additional Verification
- actions executed:
- act_9fe7d083: time [done]
- act_b1cf7786: perf_stat [done]
- act_b7fd0f5f: pidstat [done]
- act_8cf81d5e: mpstat [done]
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
- runs/run_0f76d5dc/artifacts/act_8cf81d5e.json
- runs/run_0f76d5dc/artifacts/act_8cf81d5e.stdout.txt
- runs/run_0f76d5dc/artifacts/act_9fe7d083.json
- runs/run_0f76d5dc/artifacts/act_9fe7d083.stdout.txt
- runs/run_0f76d5dc/artifacts/act_b1cf7786.json
- runs/run_0f76d5dc/artifacts/act_b1cf7786.stdout.txt
- runs/run_0f76d5dc/artifacts/act_b7fd0f5f.json
- runs/run_0f76d5dc/artifacts/act_b7fd0f5f.stdout.txt
