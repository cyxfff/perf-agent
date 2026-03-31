# Performance Analysis Report

## 1. Executive Summary
Primary suspected bottleneck: cpu_bound (confidence=0.95).

## 2. Target
- command: python demo_cpu.py
- executable: n/a
- source_dir: src/perf_agent
- runtime: verification_rounds=0, actions_executed=4
- environment: cwd=

## 3. Key Observations
- obs_c526c8c5: time.user_time_sec=3.2
- obs_06063c3c: time.system_time_sec=0.1
- obs_91eaa292: time.cpu_utilization_pct=99
- obs_8be5df4c: time.max_rss_kb=20480
- obs_982c491a: time.major_faults=0
- obs_f17959b9: time.voluntary_context_switches=12
- obs_f557095d: time.involuntary_context_switches=31
- obs_b537321a: perf_stat.task_clock_ms=1234.56
- obs_4283c4d4: perf_stat.cpu_utilization_pct=98.7
- obs_5beaa706: perf_stat.cycles=4200000000
- obs_a199fae7: perf_stat.instructions=2100000000
- obs_6cc835c6: perf_stat.ipc=0.5
- obs_4692681f: perf_stat.cache_misses=12500
- obs_eefb216a: pidstat.usr_pct=94.0
- obs_85af96cf: pidstat.system_pct=4.0
- obs_34d0b5ec: pidstat.wait_pct=1.0
- obs_513f341e: pidstat.cpu_utilization_pct=98.0
- obs_3ecd00ec: mpstat.cpu_utilization_pct=98.0
- obs_9289399d: mpstat.iowait_pct=1.0
- obs_56d1ed60: mpstat.context_switches_per_sec=1500

## 4. Candidate Bottlenecks
### 4.1 cpu_bound
- confidence: 0.95
- supporting evidence: obs_91eaa292, obs_4283c4d4, obs_6cc835c6, obs_eefb216a, obs_85af96cf, obs_513f341e, obs_3ecd00ec
- contradicting evidence: none
- verification status: sufficient

## 5. Additional Verification
- actions executed:
- act_d3ffe3cf: time [done]
- act_f13c38b5: perf_stat [done]
- act_f9a45963: pidstat [done]
- act_d51333a9: mpstat [done]
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
- runs/run_0a46fc06/artifacts/act_d3ffe3cf.json
- runs/run_0a46fc06/artifacts/act_d3ffe3cf.stdout.txt
- runs/run_0a46fc06/artifacts/act_d51333a9.json
- runs/run_0a46fc06/artifacts/act_d51333a9.stdout.txt
- runs/run_0a46fc06/artifacts/act_f13c38b5.json
- runs/run_0a46fc06/artifacts/act_f13c38b5.stdout.txt
- runs/run_0a46fc06/artifacts/act_f9a45963.json
- runs/run_0a46fc06/artifacts/act_f9a45963.stdout.txt
- runs/run_0a46fc06/source_manifest.json
- runs/run_0a46fc06/target.json
