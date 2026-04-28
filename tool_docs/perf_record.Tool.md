# perf_record

Use when:
- You need function-level hotspots or callgraph attribution.

Default recipe:
```bash
perf record -g --call-graph fp -e cycles -- <target>
perf report --stdio -i <perf.data>
```

Notes:
- Best for mapping CPU pressure back to functions and stacks.
- Requires symbols or at least stable callchains to be most useful.
