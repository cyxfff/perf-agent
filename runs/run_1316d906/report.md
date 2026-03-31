# Performance Analysis Report

## 1. Executive Summary
Primary suspected bottleneck: lock_contention (confidence=0.80).

## 2. Target
- command: python demo_lock.py
- runtime: verification_rounds=2, actions_executed=7
- environment: cwd=

## 3. Key Observations
- obs_d3df8969: time.user_time_sec=1.8
- obs_4cb259ad: time.system_time_sec=0.7
- obs_6fd7b176: time.cpu_utilization_pct=58
- obs_014adc2a: time.max_rss_kb=25000
- obs_98abd269: time.major_faults=0
- obs_c225a849: time.voluntary_context_switches=900
- obs_a3c87c59: time.involuntary_context_switches=410
- obs_0ddd230d: perf_stat.task_clock_ms=900.0
- obs_9b2cb9aa: perf_stat.cpu_utilization_pct=65.0
- obs_b1b2994a: perf_stat.cycles=900000000
- obs_5cfe6a8f: perf_stat.instructions=500000000
- obs_f30f986d: perf_stat.ipc=0.56
- obs_ebfb2028: perf_stat.lock_wait_pct=18.0
- obs_3a46dcb1: pidstat.usr_pct=40.0
- obs_94515a24: pidstat.system_pct=15.0
- obs_c156f782: pidstat.wait_pct=20.0
- obs_a09acaed: pidstat.cpu_utilization_pct=55.0
- obs_b6941dcb: mpstat.cpu_utilization_pct=55.0
- obs_39229abb: mpstat.iowait_pct=5.0
- obs_3f41f60f: mpstat.context_switches_per_sec=22000
- obs_9e37f109: mpstat.run_queue=9
- obs_d753a346: perf_record.callgraph_samples=2
- obs_0c3b33d1: perf_record.callgraph_samples=2

## 4. Candidate Bottlenecks
### 4.1 lock_contention
- confidence: 0.80
- supporting evidence: obs_ebfb2028, obs_3f41f60f, obs_d753a346, obs_0c3b33d1
- contradicting evidence: none
- verification status: needs more evidence
### 4.2 scheduler_issue
- confidence: 0.69
- supporting evidence: obs_a3c87c59, obs_3f41f60f, obs_9e37f109
- contradicting evidence: none
- verification status: needs more evidence

## 5. Additional Verification
- actions executed:
- act_eca04929: time [done]
- act_480f75b2: perf_stat [done]
- act_826e4a17: pidstat [done]
- act_a0f3b7ba: mpstat [done]
- act_490bc051: iostat [done]
- act_e32b8d81: perf_record [done]
- act_83da41e7: perf_record [done]
- new evidence:
- lock_contention: perf_stat.lock_wait_pct=18.0
- lock_contention: mpstat.context_switches_per_sec=22000
- lock_contention: perf_record.callgraph_samples=2
- lock_contention: perf_record.callgraph_samples=2
- scheduler_issue: time.involuntary_context_switches=410
- scheduler_issue: mpstat.context_switches_per_sec=22000
- scheduler_issue: mpstat.run_queue=9

## 6. Recommendations
- Collect perf record stacks and look for futex or lock-owner hotspots.
- Inspect run queue pressure and context-switch behavior with mpstat or sched traces.

## 7. Artifacts
- runs/run_1316d906/artifacts/act_480f75b2.json
- runs/run_1316d906/artifacts/act_480f75b2.stdout.txt
- runs/run_1316d906/artifacts/act_480f75b2.stdout.txt
- runs/run_1316d906/artifacts/act_490bc051.json
- runs/run_1316d906/artifacts/act_490bc051.stdout.txt
- runs/run_1316d906/artifacts/act_490bc051.stdout.txt
- runs/run_1316d906/artifacts/act_826e4a17.json
- runs/run_1316d906/artifacts/act_826e4a17.stdout.txt
- runs/run_1316d906/artifacts/act_826e4a17.stdout.txt
- runs/run_1316d906/artifacts/act_83da41e7.json
- runs/run_1316d906/artifacts/act_83da41e7.stdout.txt
- runs/run_1316d906/artifacts/act_83da41e7.stdout.txt
- runs/run_1316d906/artifacts/act_a0f3b7ba.json
- runs/run_1316d906/artifacts/act_a0f3b7ba.stdout.txt
- runs/run_1316d906/artifacts/act_a0f3b7ba.stdout.txt
- runs/run_1316d906/artifacts/act_e32b8d81.json
- runs/run_1316d906/artifacts/act_e32b8d81.stdout.txt
- runs/run_1316d906/artifacts/act_e32b8d81.stdout.txt
- runs/run_1316d906/artifacts/act_eca04929.json
- runs/run_1316d906/artifacts/act_eca04929.stdout.txt
- runs/run_1316d906/artifacts/act_eca04929.stdout.txt
