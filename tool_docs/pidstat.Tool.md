# pidstat

Use when:
- You need per-process CPU split, wait time, or scheduler clues.

Default recipes:
```bash
pidstat -dur -h 1 1
pidstat -w -h 1 1
```

Notes:
- Useful fallback when perf counters are unavailable.
- Strong evidence source for scheduler and lock-related investigations.
