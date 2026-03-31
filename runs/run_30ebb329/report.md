# Performance Analysis Report

## 1. Executive Summary
Primary suspected bottleneck: cpu_bound (confidence=0.95).

## 2. Target
- command: python demo_cpu.py
- runtime: verification_rounds=0, actions_executed=4
- environment: cwd=

## 3. Key Observations
- obs_54d0448d: time.user_time_sec=3.2
- obs_3ea4eae7: time.system_time_sec=0.1
- obs_8b168408: time.cpu_utilization_pct=99
- obs_a18edc5a: time.max_rss_kb=20480
- obs_343bcdd0: time.major_faults=0
- obs_55634a94: time.voluntary_context_switches=12
- obs_d1f00aa9: time.involuntary_context_switches=31
- obs_68a8a581: perf_stat.task_clock_ms=1234.56
- obs_6ce554b0: perf_stat.cpu_utilization_pct=98.7
- obs_b4e2eec9: perf_stat.cycles=4200000000
- obs_18c47bcb: perf_stat.instructions=2100000000
- obs_cb8ca69a: perf_stat.ipc=0.5
- obs_b9686459: perf_stat.cache_misses=12500
- obs_c134a647: pidstat.usr_pct=94.0
- obs_f20bfa47: pidstat.system_pct=4.0
- obs_73e55092: pidstat.wait_pct=1.0
- obs_a10145d7: pidstat.cpu_utilization_pct=98.0
- obs_8f010a8a: mpstat.cpu_utilization_pct=98.0
- obs_85c7564d: mpstat.iowait_pct=1.0
- obs_9455874e: mpstat.context_switches_per_sec=1500

## 4. Candidate Bottlenecks
### 4.1 cpu_bound
- confidence: 0.95
- supporting evidence: obs_8b168408, obs_6ce554b0, obs_cb8ca69a, obs_c134a647, obs_f20bfa47, obs_a10145d7, obs_8f010a8a
- contradicting evidence: none
- verification status: sufficient

## 5. Additional Verification
- actions executed:
- act_fe085b30: time [done]
- act_a1f4bd1a: perf_stat [done]
- act_8eea0bfb: pidstat [done]
- act_8bfd6737: mpstat [done]
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
- runs/run_30ebb329/artifacts/act_8bfd6737.json
- runs/run_30ebb329/artifacts/act_8bfd6737.stdout.txt
- runs/run_30ebb329/artifacts/act_8eea0bfb.json
- runs/run_30ebb329/artifacts/act_8eea0bfb.stdout.txt
- runs/run_30ebb329/artifacts/act_a1f4bd1a.json
- runs/run_30ebb329/artifacts/act_a1f4bd1a.stdout.txt
- runs/run_30ebb329/artifacts/act_fe085b30.json
- runs/run_30ebb329/artifacts/act_fe085b30.stdout.txt
