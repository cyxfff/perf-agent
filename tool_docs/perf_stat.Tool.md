# perf_stat

Use when:
- You need cycles, instructions, IPC, cache misses, or short interval trends.

Default recipe:
```bash
perf stat -e cycles,instructions,cache-misses -- <target>
```

Timeline recipe:
```bash
perf stat -I 100 -e cycles,instructions,cache-misses -- <target>
```

Notes:
- Prefer this before callgraph collection when the bottleneck class is still uncertain.
- On some hosts counters may be multiplexed; split into batches when needed.
