# Performance Analysis Report

## 1. Executive Summary
Primary suspected bottleneck: cpu_bound (confidence=0.95).

## 2. Target
- command: python demo_cpu.py
- runtime: verification_rounds=0, actions_executed=4
- environment: cwd=

## 3. Key Observations
- obs_856b22f7: time.user_time_sec=3.2
- obs_f841e55f: time.system_time_sec=0.1
- obs_f9d43c50: time.cpu_utilization_pct=99
- obs_2778ae18: time.max_rss_kb=20480
- obs_0321fcb6: time.major_faults=0
- obs_d6cfddb3: time.voluntary_context_switches=12
- obs_cf05708b: time.involuntary_context_switches=31
- obs_f05156f2: perf_stat.task_clock_ms=1234.56
- obs_ee35679a: perf_stat.cpu_utilization_pct=98.7
- obs_0776b13a: perf_stat.cycles=4200000000
- obs_9801c436: perf_stat.instructions=2100000000
- obs_a00248a1: perf_stat.ipc=0.5
- obs_32900e5b: perf_stat.cache_misses=12500
- obs_90312350: pidstat.usr_pct=94.0
- obs_4c6cb6bd: pidstat.system_pct=4.0
- obs_fc182fe4: pidstat.wait_pct=1.0
- obs_83d748ac: pidstat.cpu_utilization_pct=98.0
- obs_83bf2f84: mpstat.cpu_utilization_pct=98.0
- obs_cbe07b57: mpstat.iowait_pct=1.0
- obs_ad19d1cc: mpstat.context_switches_per_sec=1500

## 4. Candidate Bottlenecks
### 4.1 cpu_bound
- confidence: 0.95
- supporting evidence: obs_f9d43c50, obs_ee35679a, obs_a00248a1, obs_90312350, obs_4c6cb6bd, obs_83d748ac, obs_83bf2f84
- contradicting evidence: none
- verification status: sufficient

## 5. Additional Verification
- actions executed:
- act_3e5dcf22: time [done]
- act_01facd29: perf_stat [done]
- act_e5d8ef7a: pidstat [done]
- act_100571b4: mpstat [done]
- new evidence:
- cpu_bound: time.cpu_utilization_pct=99
- cpu_bound: perf_stat.cpu_utilization_pct=98.7
- cpu_bound: perf_stat.ipc=0.5
- cpu_bound: pidstat.usr_pct=94.0
- cpu_bound: pidstat.system_pct=4.0
- cpu_bound: pidstat.cpu_utilization_pct=98.0
- cpu_bound: mpstat.cpu_utilization_pct=98.0

## 6. Recommendations

## 7. Artifacts
- runs/run_379e129f/artifacts/act_01facd29.json
- runs/run_379e129f/artifacts/act_01facd29.stdout.txt
- runs/run_379e129f/artifacts/act_100571b4.json
- runs/run_379e129f/artifacts/act_100571b4.stdout.txt
- runs/run_379e129f/artifacts/act_3e5dcf22.json
- runs/run_379e129f/artifacts/act_3e5dcf22.stdout.txt
- runs/run_379e129f/artifacts/act_e5d8ef7a.json
- runs/run_379e129f/artifacts/act_e5d8ef7a.stdout.txt
