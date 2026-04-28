# iostat

Use when:
- You need device-level utilization and wait latency.

Default recipe:
```bash
iostat -dx 1 1
```

Notes:
- Focus on `%util`, `r_await`, and `w_await`.
- Use together with process-side evidence when diagnosing I/O bottlenecks.
