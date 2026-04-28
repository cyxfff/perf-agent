---
goal: Diagnose why the demo workload is CPU-bound.
command: examples/bin/cpu_bound_demo
source_dir: examples/cpp
workload: cpu_bound_demo
max_rounds: 3
---

# CPU-bound demo task

Use local perf only. This file is intentionally human-editable and can be passed with:

```bash
perf-agent analyze --task-note examples/tasks/cpu_bound.task.md
```
