# Performance Analysis Report

Summary: The strongest current signal points to a cpu bottleneck with confidence 0.84.

## Finding 1
- Phenomenon: The workload is likely CPU bound with high active CPU utilization.
- Evidence: perf_stat: CPU utilization 98.7%, IPC 0.5, cache misses 12500; pidstat: demo_cpu\n used 94.0% user CPU, 4.0% system CPU, and waited 1.0%.; mpstat: mpstat reported avg_cpu=98.0\niowait=1.0\ncswch_per_sec=1500\n
- Inference: The strongest current signal points to a cpu bottleneck with confidence 0.84.
- Recommendation: Collect call stacks with perf record to find the hottest functions.
