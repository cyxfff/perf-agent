# mpstat

Use when:
- You need a coarse host-wide CPU pressure view.

Default recipe:
```bash
mpstat 1 1
```

Notes:
- Good host fallback when sar is missing.
- Weaker than per-process evidence, so treat it as supporting context.
