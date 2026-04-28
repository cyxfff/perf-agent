# time

Use when:
- You need wall time, RSS, and coarse context-switch evidence before deeper profiling.

Default recipe:
```bash
/usr/bin/time -v <target>
```

Notes:
- Cheap first-pass evidence.
- Structured metrics are usually written to stderr.
