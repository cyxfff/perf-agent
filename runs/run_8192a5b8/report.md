# Performance Analysis Report

## 1. Executive Summary
Primary suspected bottleneck: cpu_bound (confidence=0.70).

## 2. Target
- command: python app.py --input data.txt
- runtime: verification_rounds=2, actions_executed=5
- environment: cwd=

## 3. Key Observations
- obs_bf021894: time.user_time_sec=0.04
- obs_da85f186: time.system_time_sec=0.02
- obs_49e3d53e: time.cpu_utilization_pct=101
- obs_4501d2fd: time.max_rss_kb=6400
- obs_bf5936df: time.major_faults=0
- obs_9a2f4980: time.voluntary_context_switches=103
- obs_4a9bf1e0: time.involuntary_context_switches=4
- obs_42a63451: perf_record.callgraph_samples=2000
- obs_2bb62c37: perf_record.callgraph_samples=819

## 4. Candidate Bottlenecks
### 4.1 cpu_bound
- confidence: 0.70
- supporting evidence: obs_49e3d53e
- contradicting evidence: none
- verification status: needs more evidence

## 5. Additional Verification
- actions executed:
- act_29c784a1: time [failed]
- act_00d8e808: perf_stat [failed]
- act_22c119a8: pidstat [done]
- act_25582e34: perf_record [failed]
- act_fda95acc: perf_record [failed]
- new evidence:
- cpu_bound: time.cpu_utilization_pct=101

## 6. Recommendations
- Run perf record -g to locate the hottest functions.

## 7. Artifacts
- runs/run_8192a5b8/artifacts/act_00d8e808.json
- runs/run_8192a5b8/artifacts/act_00d8e808.stderr.txt
- runs/run_8192a5b8/artifacts/act_00d8e808.stderr.txt
- runs/run_8192a5b8/artifacts/act_22c119a8.json
- runs/run_8192a5b8/artifacts/act_22c119a8.stdout.txt
- runs/run_8192a5b8/artifacts/act_22c119a8.stdout.txt
- runs/run_8192a5b8/artifacts/act_25582e34.json
- runs/run_8192a5b8/artifacts/act_25582e34.stderr.txt
- runs/run_8192a5b8/artifacts/act_25582e34.stderr.txt
- runs/run_8192a5b8/artifacts/act_25582e34.stdout.txt
- runs/run_8192a5b8/artifacts/act_25582e34.stdout.txt
- runs/run_8192a5b8/artifacts/act_29c784a1.json
- runs/run_8192a5b8/artifacts/act_29c784a1.stderr.txt
- runs/run_8192a5b8/artifacts/act_29c784a1.stderr.txt
- runs/run_8192a5b8/artifacts/act_fda95acc.json
- runs/run_8192a5b8/artifacts/act_fda95acc.stderr.txt
- runs/run_8192a5b8/artifacts/act_fda95acc.stderr.txt
- runs/run_8192a5b8/artifacts/act_fda95acc.stdout.txt
- runs/run_8192a5b8/artifacts/act_fda95acc.stdout.txt
