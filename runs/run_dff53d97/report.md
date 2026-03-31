# Performance Analysis Report

## 1. Executive Summary
Primary suspected bottleneck: cpu_bound (confidence=0.95).

## 2. Target
- command: python demo_cpu.py
- runtime: verification_rounds=0, actions_executed=4
- environment: cwd=

## 3. Key Observations
- obs_53e967a7: time.user_time_sec=3.2
- obs_3ab78ecf: time.system_time_sec=0.1
- obs_477d0556: time.cpu_utilization_pct=99
- obs_eeeb65f8: time.max_rss_kb=20480
- obs_63b8d373: time.major_faults=0
- obs_0a8b0970: time.voluntary_context_switches=12
- obs_54a72cce: time.involuntary_context_switches=31
- obs_2d157c45: perf_stat.task_clock_ms=1234.56
- obs_96cbba2e: perf_stat.cpu_utilization_pct=98.7
- obs_6e7d0f43: perf_stat.cycles=4200000000
- obs_148d5c1b: perf_stat.instructions=2100000000
- obs_a47361f3: perf_stat.ipc=0.5
- obs_ef910bc1: perf_stat.cache_misses=12500
- obs_cae0d476: pidstat.usr_pct=94.0
- obs_0607c63e: pidstat.system_pct=4.0
- obs_d0aeaf8f: pidstat.wait_pct=1.0
- obs_927eb3d5: pidstat.cpu_utilization_pct=98.0
- obs_1c6c27f9: mpstat.cpu_utilization_pct=98.0
- obs_56c4c501: mpstat.iowait_pct=1.0
- obs_77a5ff97: mpstat.context_switches_per_sec=1500

## 4. Candidate Bottlenecks
### 4.1 cpu_bound
- confidence: 0.95
- supporting evidence: obs_477d0556, obs_96cbba2e, obs_a47361f3, obs_cae0d476, obs_0607c63e, obs_927eb3d5, obs_1c6c27f9
- contradicting evidence: none
- verification status: sufficient

## 5. Additional Verification
- actions executed:
- act_46bf3b59: time [done]
- act_b98952e6: perf_stat [done]
- act_e203fcac: pidstat [done]
- act_d81a9c05: mpstat [done]
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
- runs/run_dff53d97/artifacts/act_46bf3b59.json
- runs/run_dff53d97/artifacts/act_46bf3b59.stdout.txt
- runs/run_dff53d97/artifacts/act_b98952e6.json
- runs/run_dff53d97/artifacts/act_b98952e6.stdout.txt
- runs/run_dff53d97/artifacts/act_d81a9c05.json
- runs/run_dff53d97/artifacts/act_d81a9c05.stdout.txt
- runs/run_dff53d97/artifacts/act_e203fcac.json
- runs/run_dff53d97/artifacts/act_e203fcac.stdout.txt
