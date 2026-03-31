# Performance Analysis Report

## 1. Executive Summary
Primary suspected bottleneck: cpu_bound (confidence=0.70).

## 2. Target
- command: python bench.py
- runtime: verification_rounds=2, actions_executed=5
- environment: cwd=

## 3. Key Observations
- obs_2cba5e7f: time.user_time_sec=0.04
- obs_6a94f3a5: time.system_time_sec=0.03
- obs_a7b2db73: time.cpu_utilization_pct=101
- obs_fcf75f9d: time.max_rss_kb=6400
- obs_2e320cf1: time.major_faults=0
- obs_14700b9a: time.voluntary_context_switches=101
- obs_cee71625: time.involuntary_context_switches=2
- obs_d29bbbb6: perf_record.callgraph_samples=4785
- obs_9ff82459: perf_record.callgraph_samples=1233

## 4. Candidate Bottlenecks
### 4.1 cpu_bound
- confidence: 0.70
- supporting evidence: obs_a7b2db73
- contradicting evidence: none
- verification status: needs more evidence

## 5. Additional Verification
- actions executed:
- act_bff40177: time [failed]
- act_2c6ba90a: perf_stat [failed]
- act_dac10ca6: pidstat [done]
- act_618cf153: perf_record [failed]
- act_f12190e2: perf_record [failed]
- new evidence:
- cpu_bound: time.cpu_utilization_pct=101

## 6. Recommendations
- Run perf record -g to locate the hottest functions.

## 7. Artifacts
- runs/run_be76cbdf/artifacts/act_2c6ba90a.json
- runs/run_be76cbdf/artifacts/act_2c6ba90a.stderr.txt
- runs/run_be76cbdf/artifacts/act_2c6ba90a.stderr.txt
- runs/run_be76cbdf/artifacts/act_618cf153.json
- runs/run_be76cbdf/artifacts/act_618cf153.stderr.txt
- runs/run_be76cbdf/artifacts/act_618cf153.stderr.txt
- runs/run_be76cbdf/artifacts/act_618cf153.stdout.txt
- runs/run_be76cbdf/artifacts/act_618cf153.stdout.txt
- runs/run_be76cbdf/artifacts/act_bff40177.json
- runs/run_be76cbdf/artifacts/act_bff40177.stderr.txt
- runs/run_be76cbdf/artifacts/act_bff40177.stderr.txt
- runs/run_be76cbdf/artifacts/act_dac10ca6.json
- runs/run_be76cbdf/artifacts/act_dac10ca6.stdout.txt
- runs/run_be76cbdf/artifacts/act_dac10ca6.stdout.txt
- runs/run_be76cbdf/artifacts/act_f12190e2.json
- runs/run_be76cbdf/artifacts/act_f12190e2.stderr.txt
- runs/run_be76cbdf/artifacts/act_f12190e2.stderr.txt
- runs/run_be76cbdf/artifacts/act_f12190e2.stdout.txt
- runs/run_be76cbdf/artifacts/act_f12190e2.stdout.txt
