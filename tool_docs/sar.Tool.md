# sar

Use when:
- You need system-wide CPU utilization, iowait, and busiest-core evidence while the workload runs.

Default recipe:
```bash
sar -P ALL 1 1
```

Notes:
- Strong host-level complement to process counters.
- Prefer `Average: all` and the busiest core over raw per-core dumps.
