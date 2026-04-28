# perf_agent 工程设计文档

本文档定义 `perf_agent` 的目标架构、模块边界、结构化数据契约、执行流程、诊断规则、失败降级策略和 MVP 拆分任务。系统目标是面向本地程序性能分析与瓶颈定位，围绕任务解析、采样规划、指标采集、证据构建、诊断推理、动态重规划和报告生成形成可复盘闭环。

## 1. 系统架构

```text
User / CLI / Interactive Session
  |
  v
Orchestrator / Controller
  |
  +--> Runner: target normalization and source indexing
  +--> EnvironmentProfiler: host/perf/tool capability probing
  +--> MemoryManager: short-term context + curated long-term patterns
  +--> Planner Agent: evidence request planning
  +--> Toolsmith/EventMapper: request -> executable sampling actions
  +--> Executor/Collector: command execution and artifact capture
  +--> Collector/Parser: raw output -> structured observations
  +--> EvidenceBuilder: observations -> factual evidence packets
  +--> Analyst Agent: evidence-driven diagnosis
  +--> Replanner/Verifier: evidence gaps -> next-round requests
  +--> SourceAnalyzer: hotspot/symbol/source correlation
  +--> Reporter: Markdown/HTML/JSON report
```

The current implementation keeps `AnalysisState` as the single durable state object. External text output is never passed as a module contract; it is persisted as artifacts and referenced by path. Structured observations, evidence packs, hypotheses, execution plans, and reports are persisted under `runs/<run_id>/`.

## 2. Module Responsibilities

| Module | Responsibilities | Input | Output | Failure handling | Protocol |
| --- | --- | --- | --- | --- | --- |
| Orchestrator / Controller | Own lifecycle, instantiate agents, persist state after every transition, cap iterations | `AnalysisState` from `TaskSpec` | Updated `AnalysisState`, report artifacts | Set `FAILED` only for non-recoverable setup/execution errors; otherwise record audit notes and continue degraded | State transitions: `INIT -> ENV_PROBING -> PLAN_GENERATED -> RUNNING -> EVIDENCE_BUILT -> DIAGNOSING -> REPLANNING -> REPORT_READY` |
| Planner Agent | Convert task, env, memory and evidence gaps into structured evidence requests | user goal, command, `EnvProfile`, short-term memory, current evidence | `EvidenceRequest` / `SamplingPlan` candidates | If LLM fails or selects invalid request, fall back to deterministic baseline intents | Does not execute commands; emits only structured plan/request objects |
| Toolsmith / EventMapper | Convert abstract requests into concrete tools, events and commands | `EvidenceRequest`, env capabilities, tool configs | `ExecutionPlan`, `PlannedAction`, `EventMapping` | Drop unsupported tools/events and mark fallback notes; cancel request if no executable action remains | Uses tool registry and normalized event catalog |
| Executor Agent | Run environment probes and profiling commands with timeout and artifact capture | `PlannedAction`, `AnalysisState`, artifact store | `ExecutionResult` / `ToolResult` | Timeout -> exit 124; missing binary -> exit 127; nonzero exit -> structured failure, captured stderr | No raw text return; stdout/stderr paths are returned |
| Collector / Parser Agent | Parse perf stat, perf record, time, pidstat, sar, iostat and generic output | `ExecutionResult` artifact paths | `MetricSample` / current `Observation` list | Unsupported event and permission text become parser notes or missing observations; unparsed text stays as artifacts | Parser registry keyed by tool name |
| Evidence Builder | Compress each round into factual evidence; compute derived metrics and deltas | observations, actions, env, previous evidence | `EvidenceItem` / current `EvidencePack` | Low parse coverage lowers evidence confidence; missing data creates unresolved questions | Separates facts from diagnosis; no causal claims |
| Analyst Agent | Rank bottleneck hypotheses using rules and optional LLM review | evidence chain, observations, prior hypotheses | `DiagnosisResult` / current `Hypothesis` list | If evidence insufficient, emits unknown/low-confidence hypothesis with verification requests | Every nonzero confidence hypothesis must cite evidence |
| Replanner Agent | Generate next-round sampling based on missing evidence and uncertainty | diagnosis, evidence gaps, env, max-round budget | next `SamplingPlan` / evidence requests or `None` | If round budget exhausted, stop and report residual uncertainty | Optimizes for minimal discriminating measurements |
| Memory Manager | Maintain compact task memory and curated long-term patterns | `AnalysisState`, pattern catalog | `ShortTermContext`, relevant `LongTermPattern` list | If no matching pattern, returns empty long-term context | Does not dump raw logs into prompts |
| Reporter | Render structured final report and machine-readable JSON | final state, evidence chain, hypotheses, artifacts | Markdown, HTML, JSON | Missing sections are explicit, not omitted silently | Report references raw artifacts by path |

## 3. Core Data Contracts

The canonical Pydantic contract module is `src/perf_agent/models/contracts.py`.

- `TaskSpec`: normalized user task: goal, binary path, command, workload, pid, cwd, env, source dir, max rounds, timeout, safety mode.
- `EnvProfile`: OS/kernel/CPU/perf/tool capability snapshot, including `perf_event_paranoid`, available events, call graph modes and degradation notes.
- `PerfEventGroup`: coherent event set with purpose, preferred events, fallback events, interval and required flag.
- `SamplingPlan`: executable plan for one round, including tools, event groups, warmup/repeat count, timeout, CPU affinity, call graph mode and record size limit.
- `ExecutionResult`: structured executor output with command, exit code, stdout/stderr paths, artifacts, duration, timeout flag and risk-check flag.
- `MetricSample`: one parsed fact with source, scope, labels, raw artifact path and parse status.
- `DerivedMetric`: computed metric with formula, input metric ids and confidence.
- `EvidenceItem`: factual round evidence including command, environment, raw artifacts, direct metrics, derived metrics, anomalies, deltas and evidence confidence.
- `Hypothesis`: diagnosis candidate with bottleneck kind, cited evidence/metrics, confidence, reasoning, contradictions and validation suggestions.
- `DiagnosisResult`: ranked hypotheses, sufficiency flag, missing evidence, rejected causes and stability notes.
- `ReplanRequest`: structured request to collect targeted additional evidence.
- `Report`: machine-readable final report with task, environment, sampling methods, evidence chain, diagnosis, key metrics, suggestions and raw data index.

Existing runtime models map to these contracts as follows:

| Contract | Current runtime model |
| --- | --- |
| `TaskSpec` | `AnalysisTask` |
| `EnvProfile` | `EnvironmentCapability` |
| `SamplingPlan` | `EvidenceRequest` + `ExecutionPlan` + `PlannedAction` |
| `ExecutionResult` | `ToolResult` |
| `MetricSample` | `Observation` |
| `EvidenceItem` | `EvidencePack` |
| `Hypothesis` | `models.hypothesis.Hypothesis` |
| `Report` | `FinalReport` |

## 4. Execution Flow

1. Normalize user input into `TaskSpec` / `AnalysisTask`.
2. Prepare target command: validate binary path, expand command tokens, index optional source tree.
3. Probe environment: OS, kernel, CPU model, core count, `perf --version`, `perf_event_paranoid`, available tools, available events, call graph modes, symbol tooling.
4. Build initial baseline plan:
   - `time` for elapsed/user/sys/RSS.
   - `sar` or `mpstat` for system CPU pressure.
   - `perf stat` for cycles, instructions, branches, branch-misses, cache-references, cache-misses, context-switches, page-faults, task-clock.
   - Optional top-down events when available.
5. Execute first round with `Executor/Collector`; capture stdout/stderr/artifacts.
6. Parse artifacts into structured observations and derived metrics.
7. Build evidence packet for the round. Evidence contains facts, artifacts and open questions only.
8. Run Analyst rules and optional LLM review. Hypotheses must cite observation/evidence ids.
9. If evidence is insufficient and round budget remains, Replanner chooses discriminating measurements:
   - High branch miss: branch events + `perf record -g`.
   - High cache miss: L1/L2/LLC/TLB event groups.
   - Low IPC with unclear branch/cache: frontend stall, TLB, scheduler and call graph.
   - High context switch: pidstat/mpstat/scheduler-related sampling.
   - Unknown hotspot: `perf record -g`, `perf report`/`script` parsing.
10. Repeat until sufficient evidence or max rounds.
11. Render JSON, Markdown and HTML reports with raw data index.

## 4.1 User Interfaces

The runtime interface should avoid long command lines for repeatable investigations:

- `perf-agent analyze --task task.json`: strict JSON for CI and reproducible analysis.
- `perf-agent analyze --task-note task.md`: human-editable task note. The loader accepts YAML front matter and simple `key: value` lines such as `goal:`, `command:`, `source_dir:`, `cwd:`, `env:`, and `max_rounds:`.
- `perf-agent analyze -- ...`: short ad-hoc command invocation.
- `perf-agent interactive`: session-level agent interaction for iterative task clarification.

The task note path is intentionally similar to a skill file: it is readable by humans, then normalized into `AnalysisTask` before orchestration. The orchestrator never consumes free-form text directly after normalization.

## 4.2 Agent Interaction and Concurrency

Agent interaction is mediated by structured state, not by passing chat transcripts between agents:

- Planner emits `EvidenceRequest`.
- Toolsmith converts requests to `ExecutionPlan` and `PlannedAction`.
- Executor/Collector emits structured `ExecutionResult` and artifacts.
- Parser emits `Observation`.
- Evidence Builder emits `EvidencePack`.
- Analyst emits `Hypothesis`.
- Verifier/Replanner appends new `EvidenceRequest`.

Concurrency policy:

- Sampling actions are serial by default. Running multiple profilers concurrently would usually launch multiple target instances and corrupt measurements.
- Parsing and post-processing may run in parallel. `PERF_AGENT_PARSE_WORKERS=<n>` enables parser thread-pool execution for independent action artifacts.
- Future safe concurrency can be added for environment probes and pure post-processing tasks, but target-running profiler actions should remain exclusive unless a plan explicitly proves they share the same target execution window.

## 5. Initial Diagnosis Rules

Rules are deterministic and can run without an LLM. The LLM may refine phrasing or planning, but it may not introduce unsupported conclusions.

Derived metrics:

```text
IPC = instructions / cycles
branch_miss_rate = branch_misses / branches
cache_miss_rate = cache_misses / cache_references
MPKI = misses * 1000 / instructions
```

Baseline rules:

- Low IPC + high cache miss rate or high MPKI -> candidate `memory_hierarchy` / `cache_miss`.
- Low IPC + high branch miss rate -> candidate `branch_mispredict`.
- Low IPC with normal branch/cache -> request frontend stall, TLB, scheduler and call graph evidence.
- High context switches or high page faults -> candidate scheduler/syscall/I/O/mmap pressure.
- High hotspot concentration in call graph -> report top hot functions and cite sample percentages.
- High variance across repeated runs -> lower confidence and request repeat sampling before final diagnosis.

Every hypothesis stores:

- cited evidence ids or observation ids;
- confidence in `[0, 1]`;
- reasoning steps tied to metrics;
- contradicting evidence when present;
- next validation action when confidence is below the reporting threshold.

## 6. Key Pseudocode

```python
class Orchestrator:
    def run(self, task: TaskSpec) -> Report:
        state = self.init_state(task)
        while state.status not in {"REPORT_READY", "FAILED"}:
            if state.status == "INIT":
                state = self.runner.prepare(state)
                state.status = "ENV_PROBING"
            elif state.status == "ENV_PROBING":
                state.env = self.env_profiler.probe(state)
                state.status = "PLAN_GENERATED"
            elif state.status == "PLAN_GENERATED":
                plan = self.planner.plan(self.memory.context(state))
                state.add_plan(plan)
                state.status = "RUNNING"
            elif state.status == "RUNNING":
                result = self.executor.run(state.current_plan)
                samples = self.collector.parse(result)
                evidence = self.evidence_builder.build(samples, state)
                state.add_evidence(evidence)
                state.status = "DIAGNOSING"
            elif state.status == "DIAGNOSING":
                diagnosis = self.analyst.diagnose(state.evidence_chain)
                state.diagnosis = diagnosis
                state.status = "REPORT_READY" if diagnosis.evidence_sufficient else "REPLANNING"
            elif state.status == "REPLANNING":
                plan = self.replanner.replan(state.diagnosis, state)
                state.status = "REPORT_READY" if plan is None else "RUNNING"
        return self.reporter.build(state)
```

```python
class Planner:
    def plan(self, context) -> SamplingPlan:
        if not context.evidence_chain:
            return baseline_perf_stat_plan(context)
        return targeted_plan_from_missing_evidence(context)
```

```python
class Executor:
    def run(self, plan: SamplingPlan) -> ExecutionResult:
        command = build_command(plan)
        check_risk(command)
        completed = subprocess.run(command, timeout=plan.timeout_sec, capture_output=True)
        return ExecutionResult(
            action_id=plan.id,
            command=command,
            exit_code=completed.returncode,
            stdout_path=save(completed.stdout),
            stderr_path=save(completed.stderr),
            success=completed.returncode == 0,
            duration_sec=elapsed,
        )
```

```python
class Collector:
    def parse(self, result: ExecutionResult) -> list[MetricSample]:
        payload_paths = [result.stdout_path, result.stderr_path]
        parser = registry[result.tool]
        return parser.parse_paths(payload_paths)
```

```python
class EvidenceBuilder:
    def build(self, samples, context) -> EvidenceItem:
        derived = compute_derived_metrics(samples)
        anomalies = detect_factual_anomalies(samples, derived)
        diff = diff_against_previous(context.last_evidence, samples, derived)
        return EvidenceItem(metrics=samples, derived_metrics=derived, anomalies=anomalies, diff_from_previous=diff)
```

```python
class Analyst:
    def diagnose(self, evidence_chain) -> DiagnosisResult:
        hypotheses = []
        metrics = flatten_metrics(evidence_chain)
        hypotheses += rule_engine(metrics)
        return rank_and_mark_sufficiency(hypotheses)
```

```python
class Replanner:
    def replan(self, diagnosis, context) -> SamplingPlan | None:
        if context.round_index >= context.max_rounds or diagnosis.evidence_sufficient:
            return None
        return minimal_plan_for(diagnosis.missing_evidence, context.env)
```

```python
class Reporter:
    def render(self, report: Report) -> str:
        return render_markdown(report)
```

## 7. Failure Handling Strategy

| Failure | Detection | Degradation |
| --- | --- | --- |
| `perf` missing | `which perf` or `perf --version` fails | Use `/usr/bin/time`, pidstat/mpstat/iostat when available; report no PMU evidence |
| perf permission denied | stderr contains permission/paranoid text or no counters | Record permission note, avoid privileged events, suggest `perf_event_paranoid`/sudo, continue with software counters |
| unsupported PMU event | perf stat stderr says event not supported | Drop event, use fallback group, mark `fallback_used` in event mapping |
| target program failed | target exit code nonzero | Preserve stdout/stderr, parse any available metrics, mark run degraded; fail only if no evidence can be produced |
| output parse failure | parser returns no observations | Keep raw artifact index, add parser audit note, lower evidence confidence |
| noisy sampling | high variance across repeat runs | Request repeat sampling or report low stability confidence |
| command timeout | subprocess timeout -> exit 124 | Persist partial output, mark action failed, reduce timeout-sensitive follow-up scope |
| perf record too large | perf.data exceeds plan cap | Stop using deep record in next round, prefer stat/time-series or lower frequency/duration |
| no hot symbols | perf report has addresses only | Report stripped/debug-symbol gap, use addr2line if possible, suggest symbols |
| debug symbol missing | `file`/addr2line cannot map | Continue function/address-level report, mark source correlation degraded |
| conflicting rounds | hypotheses cite contradictory metrics | Lower confidence, report conflict explicitly, request one discriminating round if budget remains |

## 8. MVP Development Plan

1. Stabilize contracts and persistence:
   - add `models/contracts.py`;
   - persist report JSON and raw artifact index;
   - add model validation tests.
2. Local-only baseline path:
   - environment probing without ADB by default for host targets;
   - baseline `time + perf stat + sar/mpstat` plan;
   - deterministic parser coverage for common perf stat formats.
3. Evidence and rule engine:
   - compute IPC, miss rates, MPKI and stability metrics;
   - enforce hypothesis evidence references;
   - add contradiction tracking.
4. Targeted replanning:
   - branch, cache/TLB, scheduler, call graph recipes;
   - max-round cap and no-repeat request filtering.
5. Reporting:
   - Markdown/JSON parity;
   - key metric table, hypothesis ranking, evidence chain, raw data index.
6. Hardening:
   - timeout/permission/unsupported-event tests;
   - record-size guard;
   - debug symbol degradation.

## 9. Test Case Design

- Model validation: required contract fields, invalid confidence, invalid max rounds.
- Environment probing: perf missing, perf permission denied, ADB disabled host-only mode.
- Event mapping: unsupported event fallback, batch splitting, call graph mode selection.
- Executor: timeout, missing command, nonzero exit, stdout/stderr artifact persistence.
- Parser: perf stat comma/locale variants, unsupported event text, permission text, interval mode, perf record report/script.
- Evidence builder: derived IPC/miss-rate/MPKI, previous-round diff, low parse confidence.
- Rules: low IPC + cache miss, low IPC + branch miss, high context switch, high page faults, no evidence -> unknown.
- Replanner: branch/cache/scheduler/hotspot-specific follow-up, max-round stop, duplicate request suppression.
- Reporter: JSON/Markdown sections, raw data index, no-source and no-symbol degradation.
- End-to-end: CPU-bound demo, lock-contention demo, synthetic parser fixtures.

## 10. Example Report Shape

```markdown
# 性能分析报告

## 1. 任务背景
- 目标命令: ./demo --workload x
- 用户目标: 程序 IPC 很低，请分析原因

## 2. 运行环境
- Kernel / CPU / core count / perf version / perf_event_paranoid
- 可用事件与调用栈模式

## 3. 采样方法
- Round 1: perf stat baseline events
- Round 2: perf record -g because branch/cache evidence was insufficient

## 4. 关键指标
| metric | value | unit | source | evidence |

## 5. 异常现象
- IPC low, cache MPKI high, branch miss rate normal

## 6. 候选瓶颈排序
| rank | kind | confidence | supporting evidence |

## 7. 证据链与推理过程
- Evidence E1 fact...
- Rule R1 because...

## 8. 已验证/未验证假设
- Verified: memory hierarchy pressure
- Unverified: exact LLC/TLB split

## 9. 优化建议
- Source/file/symbol-level suggestions when evidence supports them

## 10. 原始数据索引
- perf stat stderr: runs/.../stderr.txt
- perf report: runs/.../report.txt
```

## 11. Risks and Boundaries

- PMU availability and event names vary by CPU, kernel and permission policy; plans must be adaptive.
- Short workloads may produce unstable counters; repeat sampling or workload extension is required for high confidence.
- `perf record` can distort workload or generate large files; frequency/duration caps are mandatory.
- Without symbols, source-level recommendations are limited to addresses or coarse function names.
- LLM output is advisory and must remain constrained by structured schemas and evidence references.
- The system diagnoses and explains; it should not automatically rewrite target source code.
