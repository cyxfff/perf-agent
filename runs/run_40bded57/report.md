# Performance Analysis Report

## 1. Executive Summary
Primary suspected bottleneck: cpu_bound (confidence=0.95).

## 2. Target
- command: python demo_cpu.py
- runtime: verification_rounds=0, actions_executed=4
- environment: cwd=

## 3. Key Observations
- obs_690e360a: time.user_time_sec=3.2
- obs_ca8c2fb1: time.system_time_sec=0.1
- obs_4d95e86b: time.cpu_utilization_pct=99
- obs_b60571ba: time.max_rss_kb=20480
- obs_1f8b6c53: time.major_faults=0
- obs_c2e1e7d2: time.voluntary_context_switches=12
- obs_cf30309d: time.involuntary_context_switches=31
- obs_3ecb99d0: perf_stat.task_clock_ms=1234.56
- obs_ae1ee624: perf_stat.cpu_utilization_pct=98.7
- obs_e42f5ecc: perf_stat.cycles=4200000000
- obs_ce430217: perf_stat.instructions=2100000000
- obs_802a950c: perf_stat.ipc=0.5
- obs_80b5324a: perf_stat.cache_misses=12500
- obs_b5ac68cb: pidstat.usr_pct=94.0
- obs_33b11f17: pidstat.system_pct=4.0
- obs_7c63d854: pidstat.wait_pct=1.0
- obs_25a5bbb6: pidstat.cpu_utilization_pct=98.0
- obs_8fda297d: mpstat.cpu_utilization_pct=98.0
- obs_8477b287: mpstat.iowait_pct=1.0
- obs_cbb699a9: mpstat.context_switches_per_sec=1500

## 4. Candidate Bottlenecks
### 4.1 cpu_bound
- confidence: 0.95
- supporting evidence: obs_4d95e86b, obs_ae1ee624, obs_802a950c, obs_b5ac68cb, obs_33b11f17, obs_25a5bbb6, obs_8fda297d
- contradicting evidence: none
- verification status: sufficient

## 5. Additional Verification
- actions executed:
- act_3e25e802: time [done]
- act_5931036b: perf_stat [done]
- act_78904c8b: pidstat [done]
- act_4e8aab67: mpstat [done]
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
- runs/run_40bded57/artifacts/act_3e25e802.json
- runs/run_40bded57/artifacts/act_3e25e802.stdout.txt
- runs/run_40bded57/artifacts/act_4e8aab67.json
- runs/run_40bded57/artifacts/act_4e8aab67.stdout.txt
- runs/run_40bded57/artifacts/act_5931036b.json
- runs/run_40bded57/artifacts/act_5931036b.stdout.txt
- runs/run_40bded57/artifacts/act_78904c8b.json
- runs/run_40bded57/artifacts/act_78904c8b.stdout.txt
