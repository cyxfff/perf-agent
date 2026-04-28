# perf_agent

`perf_agent` is a Python 3.11+ performance analysis prototype. It accepts an executable, command, or PID, profiles it with available system tools, converts raw profiler output into structured evidence, and writes Markdown/HTML reports under `runs/<run_id>/`.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

The LLM client reads OpenAI-compatible settings from `.env` in this order:

- API key: `OPENAI_API_KEY`, `LLM_API_KEY`, `DEEPSEEK_API_KEY`
- model: `PERF_AGENT_MODEL`, `LLM_MODEL_ID`, `DEEPSEEK_MODEL`
- base URL: `OPENAI_BASE_URL`, `LLM_BASE_URL`, `DEEPSEEK_BASE_URL`

Set `PERF_AGENT_DISABLE_LLM=1` to force deterministic fallbacks.
Set `PERF_AGENT_DISABLE_ADB=1` for host-only runs that should not probe ADB devices.

## Run

```bash
./examples/build_examples.sh
perf-agent analyze --task examples/tasks/cpu_bound.json
perf-agent analyze --task-note examples/tasks/cpu_bound.task.md
perf-agent analyze -- examples/bin/cpu_bound_demo
perf-agent interactive
```

`analyze` accepts three interface styles:

- `--task path.json` for structured, repeatable runs.
- `--task-note path.md` for human-editable task notes with fields such as `goal:`, `command:`, `source_dir:`, and `max_rounds:`.
- Direct CLI flags (`--cmd`, `--exe`, `--pid`, or command tokens after `--`) for quick ad-hoc runs.

Profiling actions are intentionally executed serially by default to avoid multiple target instances contaminating perf counters. Parsing can be parallelized with `PERF_AGENT_PARSE_WORKERS=<n>`.

For local development:

```bash
.venv/bin/python -m pytest
```

## Project Layout

- `src/perf_agent/`: package source
- `configs/`: tool, event, rule, safety, and prompt configuration
- `examples/`: sample workloads and C++ demo programs
- `tests/`: regression tests
- `tool_docs/`: tool capability notes used by Toolsmith
- `docs/reports/`: design/report notes
- `docs/reference/`: captured profiler event lists
- `runs/`: generated analysis artifacts, ignored by git

The older long-form design document is kept at `docs/README-Old.md`.
The current multi-agent engineering design and refactor target is `docs/engineering_design.md`.
