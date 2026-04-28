# 多智能体性能诊断系统 — 架构设计与实现报告

## 目录

1. [项目概述与目标](#1-项目概述与目标)
2. [整体架构设计](#2-整体架构设计)
3. [状态机与编排引擎](#3-状态机与编排引擎)
4. [多智能体协作机制](#4-多智能体协作机制)
5. [数据模型设计](#5-数据模型设计)
6. [证据驱动的推理链路](#6-证据驱动的推理链路)
7. [LLM 集成与降级策略](#7-llm-集成与降级策略)
8. [工具抽象与事件映射](#8-工具抽象与事件映射)
9. [规则引擎与置信度评分](#9-规则引擎与置信度评分)
10. [安全沙箱机制](#10-安全沙箱机制)
11. [持久化与可审计性](#11-持久化与可审计性)
12. [跨平台与设备适配](#12-跨平台与设备适配)
13. [关键设计决策与权衡](#13-关键设计决策与权衡)
14. [遇到的问题与解决方案](#14-遇到的问题与解决方案)
15. [面试深度问答](#15-面试深度问答)

---

## 1. 项目概述与目标

### 1.1 项目定位

perf_agent 是一个**自动化性能诊断系统**，采用多智能体（Multi-Agent）架构，能够接收一个可执行程序、启动命令或进程 PID，自动完成从环境探测、实验设计、证据采集、假设生成、验证闭环到最终报告的完整性能分析流水线。

### 1.2 核心设计理念

- **证据驱动（Evidence-Driven）**：所有诊断结论必须有可追溯的观测数据支撑，不允许凭单一指标下结论
- **迭代验证（Iterative Verification）**：通过多轮"计划→采集→分析→验证"循环逐步收敛诊断结论
- **确定性优先（Deterministic-First）**：规则引擎提供确定性基线，LLM 仅在规则不足时辅助推理
- **全链路可审计（Full Audit Trail）**：每一步决策、每一次 LLM 调用、每一条命令都有完整记录

### 1.3 解决的核心问题

传统性能分析依赖工程师手动执行 `perf stat`、`perf record`、`pidstat` 等工具，逐步缩小瓶颈范围。这个过程存在几个痛点：

1. **工具选择依赖经验**：不同瓶颈类型需要不同的工具和事件组合，新手难以选择
2. **指标解读需要专业知识**：IPC、cache MPKI、backend stall 等指标的交叉分析门槛高
3. **诊断过程不可复现**：手动分析缺乏结构化记录，难以回溯推理路径
4. **跨平台适配复杂**：x86 和 ARM 的 PMU 事件名称不同，需要手动映射

---

## 2. 整体架构设计

### 2.1 架构选型：为什么选择多智能体 + 状态机

本系统采用 **"中央状态机编排 + 专职智能体"** 的混合架构，而非纯粹的 LLM Agent 自主决策或传统的单体脚本。

**对比方案分析：**

| 方案 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| 纯 LLM Agent（如 AutoGPT） | 灵活、自主决策 | 不可控、幻觉风险高、成本高 | 开放式探索任务 |
| 传统脚本流水线 | 确定性强、可控 | 无法适应未知瓶颈、缺乏推理能力 | 已知模式的批量检测 |
| **本系统：状态机 + 多智能体** | **可控流程 + 智能推理、确定性兜底** | 架构复杂度较高 | **需要可靠性的自动化诊断** |

**选择理由：**

1. **可控性**：状态机保证流程不会跑偏，每个阶段有明确的输入输出契约
2. **可靠性**：每个 LLM 调用都有确定性 fallback，即使 LLM 不可用也能完成基本诊断
3. **可审计性**：状态机的每次转换都被记录，支持事后回溯
4. **可扩展性**：新增智能体只需实现 `run(state) -> state` 接口并注册到状态机

### 2.2 系统分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    交互层 (Interaction)                    │
│              CLI / Interactive Session                     │
├─────────────────────────────────────────────────────────┤
│                    编排层 (Orchestrator)                   │
│         Orchestrator + StateMachine + Transitions          │
├─────────────────────────────────────────────────────────┤
│                    智能体层 (Agents)                       │
│  Planner │ Toolsmith │ Collector │ Parser │ Analyzer      │
│  Verifier │ SourceAnalyzer │ Reporter │ EnvironmentProfiler│
├─────────────────────────────────────────────────────────┤
│                    推理层 (Reasoning)                      │
│     Rules/Classifier │ Evidence/Summarizer │ LLM Client    │
├─────────────────────────────────────────────────────────┤
│                    工具层 (Tools)                          │
│  time │ perf_stat │ perf_record │ pidstat │ sar │ iostat  │
│  mpstat │ flamegraph │ Parsers │ EventMapper              │
├─────────────────────────────────────────────────────────┤
│                    基础设施层 (Infrastructure)              │
│  Storage │ Security/Sandbox │ Config │ Utils               │
└─────────────────────────────────────────────────────────┘
```

### 2.3 核心数据流

```
用户输入 (executable/cmd/pid)
    │
    ▼
[Runner] ──→ 解析目标、索引源码
    │
    ▼
[EnvironmentProfiler] ──→ 探测系统能力、PMU 事件、调用栈模式
    │
    ▼
[Planner] ──→ 生成证据请求 (EvidenceRequest)
    │
    ▼
[Toolsmith] ──→ 选择工具、映射事件 → 生成 PlannedAction
    │
    ▼
[Collector] ──→ 执行命令、收集原始输出
    │
    ▼
[Parser] ──→ 解析为结构化 Observation
    │
    ▼
[Analyzer] ──→ 规则分类 + LLM 推理 → 生成 Hypothesis
    │
    ▼
[Verifier] ──→ 证据充分？──→ 否 → 回到 Toolsmith（最多 N 轮）
    │                          是
    ▼
[SourceAnalyzer] ──→ 热点映射到源码
    │
    ▼
[Reporter] ──→ 生成 Markdown + HTML 报告
```

---

## 3. 状态机与编排引擎

### 3.1 状态定义

系统定义了 13 个状态，形成一条主干流水线加一个验证回环：

```
init → running → profiling_environment → planning → tool_selecting
→ collecting → parsing → analyzing → verifying → source_analyzing
→ reporting → done
                                            │
                                    (证据不足时回环)
                              verifying → tool_selecting → collecting → ...
```

终态为 `done`（成功）或 `failed`（失败）。

### 3.2 编排引擎实现

`Orchestrator` 类是整个系统的中枢，核心逻辑非常简洁：

```python
class Orchestrator:
    def run(self, state: AnalysisState) -> AnalysisState:
        while state.status not in {"done", "failed"}:
            state = self._step(state, runner, collector, environment_profiler)
            self._persist_state(store, run_log, state)
        return state
```

**设计要点：**

- **单一状态对象**：整个系统只有一个 `AnalysisState` 实例作为唯一的真相来源（Single Source of Truth），所有智能体通过读写这个对象来协作
- **每步持久化**：每次状态转换后立即序列化到磁盘，支持断点恢复和事后审计
- **显式阶段转换**：`_step()` 方法通过 `if state.status == "xxx"` 分支显式处理每个阶段，而非隐式的事件驱动，这使得流程完全可预测

### 3.3 为什么不用事件驱动或 DAG 调度

**对比事件驱动架构（如 Celery/RabbitMQ）：**
- 性能诊断是严格顺序依赖的：必须先采集才能解析，先解析才能分析
- 事件驱动引入了不必要的异步复杂度和消息丢失风险
- 状态机的确定性转换更适合需要可审计的诊断场景

**对比 DAG 调度（如 Airflow）：**
- DAG 适合静态已知的任务图，但性能诊断的任务图是动态的（验证轮次不确定）
- 状态机天然支持条件回环（verifying → tool_selecting），DAG 需要额外的动态任务生成机制

### 3.4 验证回环机制

验证回环是系统的核心创新之一：

```python
# analyzing 阶段结束后的转换逻辑
state.status = "verifying" if self.verifier.should_verify(state) else "source_analyzing"

# verifying 阶段结束后的转换逻辑
state.status = "tool_selecting" if state.pending_evidence_requests() else "source_analyzing"
```

**回环控制：**
- `max_verification_rounds`（默认 2）限制最大验证轮次，防止无限循环
- `verification_rounds_done` 计数器跟踪已完成的验证轮次
- 每轮验证会检查是否有新的 `pending_evidence_requests`，有则回到 `tool_selecting`

---

## 4. 多智能体协作机制

### 4.1 智能体设计原则

每个智能体遵循统一的接口契约：

```python
def run(self, state: AnalysisState) -> AnalysisState
```

**设计原则：**
- **无状态**：智能体本身不持有跨调用的状态，所有信息通过 `AnalysisState` 传递
- **幂等性**：同一输入多次调用应产生相同结果（LLM 调用除外，但有 fallback 保证）
- **单一职责**：每个智能体只负责一个阶段的逻辑

### 4.2 九大智能体详解

#### 4.2.1 Runner（目标准备）

**职责**：解析用户输入，准备分析目标。

- 支持三种输入模式：可执行文件路径、完整命令行、PID 附着
- 扫描源码目录（如果提供），索引最多 500 个源文件
- 检测源码语言（C/C++/Rust/Go/Java/Python 等）
- 输出 `target.json` 和 `source_manifest.json`

**设计决策**：为什么限制 500 个源文件？
- 避免大型项目（如 Linux 内核）的源码索引耗时过长
- 后续的 SourceAnalyzer 只需要关注热点相关的少量文件
- 500 是经验值，覆盖了绝大多数单项目的源码规模

#### 4.2.2 EnvironmentProfiler（环境探测）

**职责**：全面探测当前系统的性能分析能力。

探测内容包括：
- 操作系统、内核版本、CPU 架构
- CPU 型号、核心数、缓存层级（L1d/L1i/L2/L3）、NUMA 拓扑
- `perf` 工具可用性、版本、权限（`perf_event_paranoid`）
- **PMU 事件目录**：解析 `perf list` 输出，构建事件描述符（EventDescriptor）
- 事件语义别名映射（如 `cycles` → `cpu-cycles`、`hw-cpu-cycles`）
- 调用栈模式支持（fp/dwarf/lbr）
- ADB 设备发现（Android 场景）
- 沙箱运行时可用性

**事件目录构建**是环境探测的核心创新：

```python
class EventDescriptor(BaseModel):
    name: str                    # 事件全名
    source_type: str             # hardware/software/tracepoint/raw/metric/pmu
    semantic_keys: list[str]     # 语义标签（如 "cycles", "cache-misses"）
    portability_score: int       # 可移植性评分（95=hardware, 45=tracepoint）
    stat_usable: bool            # 是否可用于 perf stat
```

这个目录使得后续的 EventMapper 能够在不同平台上自动选择等价事件。

#### 4.2.3 Planner（证据规划）

**职责**：根据目标特征和环境能力，设计首轮证据采集策略。

**基线意图生成逻辑**：

```python
def build_baseline_intents(state):
    intents = [
        baseline_runtime,          # 必选：运行时长、CPU、内存基线
        system_cpu_profile,        # 必选：系统级 CPU 利用率
        instruction_efficiency,    # 必选：IPC、cycles
        cache_memory_pressure,     # 必选：cache miss、backend stall
        frontend_backend_bound,    # 必选：top-down 前后端（如果平台支持）
        scheduler_context,         # 必选：调度、上下文切换
    ]
    # 条件意图：根据目标命令关键词动态添加
    if "branch" or "predict" in target_cmd:
        intents.append(branch_behavior)
    if "io" or "disk" in target_cmd:
        intents.append(io_wait_detail)
```

**LLM 辅助规划**：
- 如果 LLM 可用，将候选意图列表发送给 Strategist 角色
- LLM 可以根据工作负载特征调整优先级和问题描述
- 如果 LLM 不可用或返回无效结果，直接使用全部基线意图

#### 4.2.4 Toolsmith（工具选择）

**职责**：将抽象的证据请求转化为具体的工具执行计划。

**工具选择流程**：

1. **候选生成**：根据意图类型和环境可用工具，生成候选工具列表
2. **LLM 辅助选择**（可选）：将候选工具、环境信息、工具文档发送给 Toolsmith LLM
3. **启发式兜底**：按意图类型的硬编码优先级选择工具

```python
# 启发式工具选择示例
if intent == "baseline_runtime":     → time
if intent == "system_cpu_profile":   → sar > mpstat
if intent == "scheduler_context":    → pidstat > perf_stat > mpstat
if intent == "hot_function_callgraph": → perf_record
```

**去重机制**：`_action_already_seen()` 检查是否已存在相同 (tool, events, callgraph_mode, intent, phase) 的 action，避免重复执行。

#### 4.2.5 Collector（证据采集）

**职责**：执行 pending_actions 中的所有命令，收集原始输出。

- 遍历 `state.pending_actions`，逐个调用 `ToolRunner.run_action()`
- 将 stdout/stderr 保存为 artifact 文件
- 更新 action 状态（done/failed）和 request 状态
- 支持 mock 输出（用于测试）

#### 4.2.6 Parser（结果解析）

**职责**：将原始工具输出转化为结构化的 Observation 对象。

**解析器注册表**：

```python
registry = {
    "time":        time_parser,        # 解析 /usr/bin/time -v 输出
    "perf_stat":   perf_stat_parser,   # 解析 perf stat JSON/文本
    "perf_record": perf_record_parser, # 解析 perf report --stdio
    "pidstat":     pidstat_parser,     # 解析 pidstat 输出
    "sar":         sar_parser,         # 解析 sar 输出
    "mpstat":      generic_parser,     # 通用解析
    "iostat":      generic_parser,     # 通用解析
}
```

每个解析器将原始文本转化为带有 category、metric、value、scope、labels 的 Observation 对象。

#### 4.2.7 Analyzer（诊断分析）

**职责**：从观测数据中生成候选瓶颈假设。

**两阶段分析**：

1. **规则分类**（确定性）：`classify_observations()` 应用阈值规则检测已知模式
2. **LLM 推理**（辅助）：将规则候选和结构化观测发送给 Analyzer LLM，生成更精细的假设

**关键设计**：规则引擎先行，LLM 后行。这保证了即使 LLM 不可用，系统也能产出有意义的诊断结果。

#### 4.2.8 Verifier（验证闭环）

**职责**：判断当前证据是否充分，决定是否需要追加实验。

**决策逻辑**：

```python
def should_verify(self, state):
    if verification_rounds_done >= max_verification_rounds:
        return False  # 达到上限，强制结束
    if not hypotheses:
        return True   # 没有假设，需要更多证据
    return any(h.needs_verification for h in hypotheses)
```

**追加实验映射**：根据当前最强假设类型，选择针对性的追加实验：

- CPU bound → `hot_function_callgraph` + `temporal_behavior`
- Memory bound → `cache_memory_pressure` + `temporal_behavior`
- I/O bound → `io_wait_detail` + `temporal_behavior`
- Lock contention → `hot_function_callgraph` + `scheduler_context`

#### 4.2.9 Reporter（报告生成）

**职责**：生成结构化的最终诊断报告。

- 构建 `FinalReport` 对象，包含执行摘要、环境信息、实验历史、证据摘要、图表规格等
- LLM 辅助润色执行摘要和建议
- 渲染 Markdown 和 HTML 两种格式
- HTML 报告包含交互式图表（假设置信度对比、热点函数分布、时间序列等）

---

## 5. 数据模型设计

### 5.1 核心模型关系

```
AnalysisState (中央状态)
    ├── EnvironmentCapability (环境能力)
    │       └── EventDescriptor[] (事件描述符)
    ├── EvidenceRequest[] (证据请求)
    │       └── ExecutionPlan (执行计划)
    ├── PlannedAction[] (计划动作)
    ├── Observation[] (观测数据)
    ├── Hypothesis[] (候选假设)
    ├── EvidencePack[] (证据压缩包)
    ├── SourceFinding[] (源码定位)
    ├── FinalReport (最终报告)
    ├── AuditEvent[] (审计日志)
    └── LLMTrace[] (LLM 调用记录)
```

### 5.2 为什么选择 Pydantic v2

所有数据模型基于 Pydantic v2 BaseModel，原因：

1. **类型安全**：运行时类型验证，防止脏数据进入流水线
2. **序列化/反序列化**：`model_dump(mode="json")` 直接输出 JSON，无需手写序列化逻辑
3. **模型验证器**：如 Hypothesis 的 `@model_validator` 确保非零置信度必须有支撑证据
4. **LLM 结构化输出**：Pydantic schema 可直接作为 OpenAI `response_format` 的类型约束
5. **不可变拷贝**：`model_copy(update={...})` 支持安全的部分更新

### 5.3 关键模型设计细节

#### Observation（观测数据）

```python
class Observation(BaseModel):
    id: str                    # 全局唯一 ID
    source: str                # 产生工具（perf_stat, pidstat 等）
    category: Literal[...]     # cpu/memory/cache/branch/io/lock/scheduler/callgraph/system
    metric: str                # 指标名（ipc, cache_misses 等）
    value: float | int | str   # 指标值
    unit: str | None           # 单位
    normalized_value: float | None  # 归一化值（0-1 或百分比）
    scope: Literal[...]        # process/thread/system/function/callchain
    labels: dict[str, str]     # 附加元数据（symbol, pid, series_type 等）
    evidence_level: Literal["direct", "derived"]  # 直接观测 vs 派生指标
```

**设计要点**：
- `category` 枚举覆盖了性能分析的所有维度
- `labels` 字典提供了灵活的扩展能力（如 `series_type=timeline` 标记时间序列数据）
- `evidence_level` 区分直接测量值和计算派生值，影响后续的置信度评估

#### Hypothesis（候选假设）

```python
class Hypothesis(BaseModel):
    kind: Literal["cpu_bound", "memory_bound", "io_bound",
                  "lock_contention", "scheduler_issue",
                  "branch_mispredict", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_observation_ids: list[str]
    contradicting_observation_ids: list[str]
    needs_verification: bool

    @model_validator(mode="after")
    def validate_support(self):
        if self.confidence > 0 and not self.supporting_observation_ids:
            raise ValueError("Hypotheses with non-zero confidence must cite observations.")
```

**设计要点**：
- `model_validator` 强制要求非零置信度的假设必须引用支撑观测，从模型层面杜绝"无中生有"
- `contradicting_observation_ids` 记录反证，支持后续的假设排除推理
- `needs_verification` 标记是否需要追加实验

#### EvidenceRequest（证据请求）

```python
class EvidenceRequest(BaseModel):
    intent: str                # 分析意图（baseline_runtime, instruction_efficiency 等）
    question: str              # 要回答的具体问题
    phase: Literal["baseline", "verification", "source_correlation"]
    granularity: Literal["process", "system", "thread", "function", "timeline"]
    priority: int              # 优先级（数字越小越优先）
    status: Literal["planned", "tool_selected", "collecting", "completed", "failed", "cancelled"]
```

**设计要点**：
- `phase` 区分基线采集和验证追加，影响后续的去重逻辑
- `granularity` 指导工具选择（如 function 粒度需要 perf_record，system 粒度用 sar）
- `status` 状态机跟踪请求的完整生命周期

---

## 6. 证据驱动的推理链路

### 6.1 推理流程

系统的推理链路遵循 **"观测 → 规则分类 → 证据压缩 → LLM 推理 → 假设验证"** 的五步流程：

```
Observations ──→ RuleClassifier ──→ rule_candidates (Hypothesis[])
                                          │
                                          ▼
Observations + rule_candidates ──→ EvidenceSummarizer ──→ EvidencePack
                                                              │
                                                              ▼
Observations + rule_candidates + EvidencePack ──→ LLM Analyzer ──→ refined Hypotheses
                                                                        │
                                                                        ▼
                                                              Verifier 判断是否充分
```

### 6.2 证据压缩（EvidencePack）

EvidencePack 是连接规则引擎和 LLM 的关键中间层：

```python
class EvidencePack(BaseModel):
    round_index: int                    # 第几轮
    summary: str                        # 文本摘要
    top_observation_ids: list[str]      # 最重要的观测 ID
    highlighted_metrics: list[str]      # 重点指标
    hotspot_symbols: list[str]          # 热点函数
    timeline_metrics: list[str]         # 时间序列指标
    top_processes: list[str]            # 进程级拆账
    top_threads: list[str]              # 线程级拆账
    unresolved_questions: list[str]     # 未解决的问题
```

**为什么需要证据压缩？**

1. **Token 预算控制**：原始 Observation 列表可能有几十到上百条，直接发送给 LLM 会超出 token 限制
2. **信噪比提升**：EvidenceSummarizer 通过评分机制筛选最重要的观测，减少噪声
3. **上下文聚焦**：`unresolved_questions` 引导 LLM 关注当前最需要回答的问题

**观测评分逻辑**：

```python
def _top_observations(self, observations):
    preferred_metrics = {"cpu_utilization_pct", "ipc", "cache_misses",
                         "branch_misses", "context_switches", "hot_symbol_pct", ...}
    for obs in observations:
        score = 0
        if obs.metric in preferred_metrics: score += 5
        if obs.category in {"callgraph", "scheduler", "cache"}: score += 2
        if obs.labels.get("series_type") == "timeline": score += 1
    return top_10_by_score
```

### 6.3 多轮验证的收敛策略

验证轮次的追加实验不是随机的，而是根据当前最强假设类型精确选择：

| 当前最强假设 | 追加实验 | 目的 |
|-------------|---------|------|
| cpu_bound | hot_function_callgraph + temporal_behavior | 定位热点函数，确认是否阶段性 |
| memory_bound | cache_memory_pressure + temporal_behavior | 确认 cache 层级，观察时间波动 |
| io_bound | io_wait_detail + temporal_behavior | 补充设备级 I/O 证据 |
| lock_contention | hot_function_callgraph + scheduler_context | 定位锁持有者，确认调度压力 |
| branch_mispredict | hot_function_callgraph + cache_memory_pressure | 定位分支热点，排除 cache 干扰 |

**temporal_behavior 的条件触发**：只有当程序运行时间 ≥ 80ms 时才追加时间序列采样，因为太短的程序无法产生有意义的时间序列数据。

---

## 7. LLM 集成与降级策略

### 7.1 LLM 在系统中的角色定位

LLM 在本系统中是**辅助推理者**，而非**主导决策者**。这是一个关键的架构决策。

**LLM 参与的 5 个节点：**

| 节点 | LLM 角色 | 输入 | 输出 | 降级方案 |
|------|---------|------|------|---------|
| Planner | Strategist | 目标信息 + 环境能力 + 候选意图 | 筛选后的意图列表 | 使用全部基线意图 |
| Toolsmith | Toolsmith | 证据请求 + 候选工具 + 工具文档 | 工具选择 + 理由 | 启发式规则选择 |
| Analyzer | Analyzer | 观测 + 规则候选 + 证据包 | 精细化假设 | 直接使用规则候选 |
| Verifier | Verifier | 观测 + 假设 + 已执行动作 | 充分性判断 + 追加实验 | 阈值判断 + 映射表 |
| Reporter | Reporter | 观测 + 假设 + 证据包 | 润色后的摘要和建议 | 使用模板生成 |

### 7.2 为什么不用 RAG？

**面试高频问题：为什么不用 RAG（检索增强生成）来增强 LLM 的性能分析知识？**

**回答：**

1. **知识类型不匹配**：RAG 适合检索事实性知识（"perf stat 的参数是什么"），但性能诊断需要的是**推理能力**（"IPC=0.3 + backend_stall=45% 意味着什么"）。推理能力无法通过检索获得。

2. **上下文已经结构化**：我们发送给 LLM 的不是自然语言描述，而是结构化的 JSON payload（Observation 列表、规则候选、EvidencePack）。这比 RAG 检索到的非结构化文档片段更精确。

3. **领域知识已编码在规则中**：性能分析的核心知识（如"IPC < 0.8 + backend_stall > 20% = memory_bound"）已经编码在规则引擎中。LLM 只需要在规则覆盖不到的边界情况下提供补充推理。

4. **延迟和成本**：RAG 需要额外的向量检索步骤，增加延迟。性能诊断是交互式场景，每个 LLM 调用的超时设为 20 秒，加入 RAG 会进一步压缩推理时间。

5. **幻觉风险**：RAG 检索到的文档片段可能与当前平台不匹配（如 x86 的文档用于 ARM 分析），反而引入误导。我们的事件目录和环境探测已经解决了平台适配问题。

**什么场景下可能需要 RAG？**
- 如果要支持用户自定义的性能模式库（如"我们公司的 XX 服务常见的瓶颈模式"）
- 如果要支持自然语言的工具文档查询（目前通过 tool_docs 目录静态提供）

### 7.3 降级策略的三层保障

```
Layer 1: LLM 可用且返回有效结果 → 使用 LLM 输出
Layer 2: LLM 可用但返回无效结果 → 记录 fallback trace，使用确定性逻辑
Layer 3: LLM 不可用（无 API key / 禁用） → 完全使用确定性逻辑
```

**每个 LLM 调用的降级模式**：

```python
def generate_hypotheses(self, observations, rule_candidates, ...):
    if self.enabled:
        try:
            parsed = self._parse_structured_output(AnalyzerOutput, ...)
            validated = self._validate_hypotheses(parsed.hypotheses, observations)
            if validated:
                return validated  # Layer 1: LLM 成功
            self.last_error = "No usable hypotheses"  # Layer 2: LLM 返回无效
        except Exception as exc:
            self.last_error = f"LLM call failed: {exc}"  # Layer 2: LLM 异常
    # Layer 3: 使用规则候选作为最终结果
    return [Hypothesis(...) for candidate in rule_candidates]
```

### 7.4 LLM 调用的结构化输出

系统使用 OpenAI 的 Structured Output 功能，确保 LLM 返回的 JSON 严格符合 Pydantic schema：

```python
def _parse_structured_output(self, schema, system_prompt, user_payload, ...):
    try:
        # 优先使用 responses.parse API（更新的接口）
        response = self.client.responses.parse(
            model=self.model, input=messages,
            text_format=schema, temperature=0
        )
        return response.output_parsed
    except:
        # 降级到 chat.completions.parse API
        completion = self.client.beta.chat.completions.parse(
            model=self.model, messages=messages,
            response_format=schema, temperature=0
        )
        return completion.choices[0].message.parsed
```

**双 API 降级**：先尝试 `responses.parse`（新 API），失败则降级到 `chat.completions.parse`（旧 API），确保兼容不同版本的 OpenAI SDK。

### 7.5 LLM Trace 审计

每次 LLM 调用都会记录 trace：

```python
class LLMTrace(BaseModel):
    agent: str          # 哪个智能体调用的
    prompt_kind: str    # 什么类型的 prompt
    status: Literal["used", "fallback", "error"]  # 调用结果
    note: str           # 详细说明
    model: str | None   # 使用的模型
    transport: str | None  # 使用的 API（responses.parse / chat.completions.parse）
```

这使得事后可以精确分析：哪些诊断结论依赖了 LLM，哪些是纯规则产出的。

---

## 8. 工具抽象与事件映射

### 8.1 工具注册表

系统通过 `ToolRunner` 管理所有性能分析工具：

```python
registry = {
    "time":        TimeTool,       # /usr/bin/time -v
    "perf_stat":   PerfStatTool,   # perf stat -e events
    "perf_record": PerfRecordTool, # perf record -g
    "pidstat":     PidstatTool,    # pidstat -u -w -t
    "mpstat":      MpstatTool,     # mpstat -P ALL
    "iostat":      IostatTool,     # iostat -x
    "sar":         SarTool,        # sar -u -P ALL
    "flamegraph":  FlamegraphTool, # FlameGraph 生成
}
```

每个工具实现统一接口：

```python
class Tool(Protocol):
    def build_command(self, state, action) -> list[str]
    def run(self, state, action, store) -> ToolResult
```

### 8.2 EventMapper：意图到事件的智能映射

EventMapper 是工具层最复杂的组件，负责将抽象的分析意图转化为具体的 perf 事件组合。

**核心挑战**：不同平台的 PMU 事件名称不同。例如：
- x86: `cache-misses`, `mem_load_retired.l1_miss`
- ARM: `l1d-cache-refill`, `armv8_pmuv3/l1d_cache_refill/`

**解决方案：语义别名 + 多级降级**

```
用户意图: cache_memory_pressure
    │
    ▼
首选事件: [cache-references, cache-misses, mem_load_retired.l1_hit, ...]
    │
    ▼ _resolve_event_name()
在事件目录中查找语义别名
    │
    ├── 找到 → 使用平台特定事件名
    └── 未找到 → 尝试 fallback 事件列表
              │
              ├── 找到 → 使用 fallback 事件
              └── 全部未找到 → 使用通用 fallback
```

**事件批次拆分**：

当事件数量超过平台的 PMU 计数器预算时，EventMapper 会自动拆分为多批执行：

```python
def _event_batches(self, state, events, sample_interval_ms=None):
    budget = state.environment.interval_event_budget if sample_interval_ms else state.environment.stat_event_budget
    # 按语义分组（efficiency, branch, cache, scheduler 等）
    # 保持 access/miss 成对指标在同一批
    # 每批不超过 budget 个事件
```

**为什么要保持成对指标？** 因为 `cache-references` 和 `cache-misses` 必须在同一次运行中采集，才能计算准确的 miss rate。如果分到不同批次，由于程序行为的非确定性，计算出的比率可能不准确。

### 8.3 事件优先级选择算法

当同一个语义别名对应多个候选事件时，`_prefer_event_variant()` 通过多维评分选择最优事件：

```python
def score(candidate):
    exact = 0 if exact_match else 1           # 精确匹配优先
    source_rank = source_type_priority(...)    # hardware > pmu > raw > software
    portability = -descriptor.portability_score # 高可移植性优先
    generic = 0 if no_slash_colon else 1       # 通用名优先
    depth = len(name.split("/.:_-"))           # 短名优先
    return (exact, source_rank, portability, generic, depth)
```

**架构特定的优先级调整**：
- ARM 平台：`raw > hardware > pmu`（因为 ARM 的 raw 事件通常更可靠）
- x86 平台：`hardware > pmu > raw`（标准优先级）
- Top-down 指标：`metric > hardware > pmu`（metric 类型的 top-down 更准确）

---

## 9. 规则引擎与置信度评分

### 9.1 规则引擎架构

规则引擎采用**阈值检测 + 置信度评分**的两阶段设计：

```
Observations → latest_numeric_metrics() → metrics dict
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
            detect_memory_bound()    detect_cpu_bound()    detect_lock_contention()
                    │                         │                         │
                    ▼                         ▼                         ▼
            _build_hypothesis()      _build_hypothesis()      _build_hypothesis()
                    │                         │                         │
                    └─────────────────────────┼─────────────────────────┘
                                              ▼
                                    score_from_observations()
                                              │
                                              ▼
                                    Hypothesis[] (按 confidence 排序)
```

### 9.2 六类瓶颈检测规则

| 瓶颈类型 | 检测条件 | 设计依据 |
|----------|---------|---------|
| memory_bound | IPC ≤ 0.8 AND backend_stall ≥ 20% AND cache_misses ≥ 10000 | 低 IPC + 高后端停顿 + 高 cache miss 是内存瓶颈的经典三角验证 |
| io_bound | CPU_util ≤ 50% AND (iowait ≥ 10% OR wait ≥ 15%) | CPU 空闲但等待时间高，说明瓶颈在 I/O |
| lock_contention | (lock_wait ≥ 10% AND ctx_sw/s ≥ 5000) OR (vol_ctx_sw ≥ 5000 AND CPU_util ≤ 30%) OR tma_lock_latency ≥ 8% | 多条件 OR 组合，覆盖不同平台的锁竞争表现 |
| scheduler_issue | ctx_sw/s ≥ 10000 OR run_queue ≥ 8 OR vol_ctx_sw ≥ 12000 | 高频上下文切换或运行队列过长 |
| branch_mispredict | branch_misses ≥ 10000 OR bad_spec ≥ 12% OR tma_branch_mispredicts ≥ 8% | 绝对数量或 top-down 占比超阈值 |
| cpu_bound | CPU_util ≥ 80% OR (IPC ≥ 1.0 AND retiring ≥ 25%) | 高利用率或高效退休（说明 CPU 确实在做有用功） |

**为什么 memory_bound 需要三个条件同时满足？**

单独的低 IPC 可能是分支预测失误导致的；单独的高 cache miss 可能是正常的工作集大小；只有三者同时出现才能高置信度地判断为内存瓶颈。这体现了 Target.md 中"不依赖单一指标"的核心原则。

### 9.3 置信度评分机制

```python
def score_from_observations(observations, base=0.4, strength=0.0):
    score = base + 0.07 * len(observations) + strength
    return round(max(0.0, min(score, 0.95)), 2)
```

**评分公式解读**：
- `base = 0.4`：基础置信度，表示"有一些证据但不确定"
- `0.07 * len(observations)`：每多一条支撑观测增加 7% 置信度
- `strength`：规则特定的强度调整（如 cpu_bound 的 strength=0.15，unknown 的 strength=-0.15）
- 上限 0.95：永远不会达到 100% 置信度，保持谦逊

**为什么上限是 0.95 而不是 1.0？**

性能诊断本质上是概率性的。即使所有指标都指向同一个瓶颈，也可能存在未观测到的因素。0.95 的上限提醒用户和系统：诊断结论始终需要人工确认。

### 9.4 规则与 LLM 的协作模式

```
规则引擎输出 rule_candidates (确定性)
         │
         ▼
LLM Analyzer 接收 rule_candidates + observations + evidence_pack
         │
         ├── LLM 可能：提升某个候选的置信度（补充推理依据）
         ├── LLM 可能：降低某个候选的置信度（发现矛盾证据）
         ├── LLM 可能：合并多个候选（如 cpu_bound + memory_bound → "CPU 密集但受 cache 限制"）
         └── LLM 可能：添加新的候选（规则未覆盖的模式）
         │
         ▼
最终 Hypotheses（经过 _validate_hypotheses 验证）
```

`_validate_hypotheses()` 确保 LLM 输出的假设：
- `kind` 必须是合法的枚举值
- `confidence` 被裁剪到 [0.0, 1.0]
- `supporting_observation_ids` 必须引用真实存在的观测 ID

---

## 10. 安全沙箱机制

### 10.1 设计动机

性能分析需要执行用户提供的可执行文件，这带来安全风险。沙箱机制提供可选的隔离执行环境。

### 10.2 沙箱架构

```python
class SandboxManager:
    def resolve_runtime(self, state) -> SandboxResolution
    def wrap_target_command(self, command, state) -> (wrapped_command, resolution)
```

**运行时选择流程**：

```
配置的 default_runtime
    │
    ▼
环境变量覆盖 (PERF_AGENT_SANDBOX_RUNTIME)
    │
    ▼
按 preferred_runtimes 顺序尝试
    │
    ├── bubblewrap 可用？ → 使用 bubblewrap
    ├── docker 可用？ → 使用 docker
    ├── podman 可用？ → 使用 podman
    └── 全部不可用 → fallback_to_none？ → 直接执行 / 报错
```

### 10.3 Bubblewrap 沙箱实现

```python
def _build_bubblewrap_prefix(self, runtime_name, runtime, state):
    prefix = [executable, *extra_args]
    for path in read_only_paths:
        prefix.extend(["--ro-bind", path, path])  # 只读挂载
    for path in writable_paths:
        prefix.extend(["--bind", path, path])      # 可写挂载
    if not network_access:
        prefix.append("--unshare-net")              # 网络隔离
    prefix.append("--")
    return prefix
```

**路径模板变量**：支持 `{cwd}`、`{home}`、`{executable_dir}`、`{source_dir}` 等占位符，自动解析为实际路径。

### 10.4 安全与性能的权衡

沙箱会影响性能分析的准确性：
- 容器化沙箱（Docker/Podman）引入额外的系统调用开销
- 网络隔离可能影响网络密集型程序的行为
- 文件系统隔离可能改变 I/O 特征

因此沙箱默认关闭（`sandbox_enabled: false`），仅在分析不可信程序时启用。

---

## 11. 持久化与可审计性

### 11.1 Artifact 存储结构

```
runs/<run_id>/
├── state.json                    # 完整分析状态快照
├── observations.json             # 所有观测数据
├── hypotheses.json               # 所有候选假设
├── evidence_packs.json           # 证据压缩包
├── evidence_requests.json        # 证据请求
├── execution_plans.json          # 执行计划
├── actions_taken.json            # 已完成动作
├── pending_actions.json          # 待执行动作
├── llm_traces.json               # LLM 调用记录
├── audit.jsonl                   # 审计日志（行分隔 JSON）
├── target.json                   # 目标元数据
├── source_manifest.json          # 源码文件清单
├── report.json / report.md / report.html  # 最终报告
└── artifacts/raw/commands/<action_id>/
    ├── stdout.txt                # 命令标准输出
    └── stderr.txt                # 命令标准错误
```

### 11.2 每步持久化策略

```python
def _persist_state(self, store, run_log, state):
    store.save_json("state.json", state.model_dump(mode="json"))
    store.save_json("observations.json", [item.model_dump(...) for item in state.observations])
    # ... 所有子集合分别持久化
    for event in state.audit_log:
        if not event.persisted:
            run_log.append(event)
            event.persisted = True
```

**为什么每步都持久化？**

1. **断点恢复**：如果进程崩溃，可以从最后一个 state.json 恢复
2. **实时可观测**：外部工具可以实时读取 JSON 文件监控分析进度
3. **事后审计**：每个阶段的中间状态都有快照，支持完整的决策回溯

### 11.3 审计日志设计

```python
class AuditEvent(BaseModel):
    timestamp: datetime
    node: str       # 哪个智能体
    message: str    # 做了什么
    details: dict   # 详细参数
```

审计日志使用 JSONL（行分隔 JSON）格式，支持增量追加，避免每次重写整个文件。

---

## 12. 跨平台与设备适配

### 12.1 多平台支持

系统通过 `EnvironmentCapability` 和 `EventMapper` 的组合实现跨平台适配：

| 平台 | 采样后端 | 事件映射策略 |
|------|---------|------------|
| x86 Linux | perf | 标准 hardware 事件优先 |
| ARM Linux | perf | raw 事件优先（ARM PMU 特性） |
| Android | simpleperf/hiperf (via ADB) | 设备端执行，主机端分析 |
| 无 perf 环境 | pidstat/sar/mpstat | 降级到系统级工具 |

### 12.2 Android 设备支持

```python
class ConnectedDevice(BaseModel):
    serial: str
    status: str
    model: str | None
    arch: str | None
    os_release: str | None
    sdk: str | None
    backend_tools: list[str]  # simpleperf, hiperf 等
```

**设备选择算法**：
- 按状态（device > recovery > offline）、后端工具数量、架构匹配度、是否模拟器等多维评分
- 自动选择最优设备，或在多设备时提示用户选择

### 12.3 事件可移植性评分

```python
class EventDescriptor(BaseModel):
    portability_score: int  # 95=hardware, 90=software, 45=tracepoint, 30=raw
```

高可移植性事件（如 `cycles`、`instructions`）在所有平台上都可用；低可移植性事件（如 `mem_load_retired.l1_miss`）仅在特定 CPU 微架构上可用。EventMapper 优先选择高可移植性事件，仅在需要更精细分析时才使用低可移植性事件。

---

## 13. 关键设计决策与权衡

### 13.1 单一状态对象 vs 消息传递

**决策**：选择单一 `AnalysisState` 对象作为所有智能体的共享状态。

**替代方案**：智能体之间通过消息队列传递数据（如 Actor 模型）。

**权衡分析**：

| 维度 | 单一状态对象 | 消息传递 |
|------|------------|---------|
| 实现复杂度 | 低 | 高（需要消息序列化、路由、确认） |
| 调试难度 | 低（一个 JSON 包含所有状态） | 高（需要追踪消息流） |
| 并发支持 | 差（单线程顺序执行） | 好（天然支持并行） |
| 状态一致性 | 强一致（单一来源） | 最终一致（需要同步机制） |

**选择理由**：性能诊断是严格顺序的流水线，不需要并发执行。单一状态对象的简单性和可调试性远比并发能力重要。

### 13.2 确定性规则优先 vs LLM 优先

**决策**：规则引擎先行，LLM 仅作为辅助。

**替代方案**：完全依赖 LLM 进行诊断推理。

**权衡分析**：

| 维度 | 规则优先 | LLM 优先 |
|------|---------|---------|
| 可靠性 | 高（确定性输出） | 低（幻觉风险） |
| 可解释性 | 高（规则可追溯） | 低（黑盒推理） |
| 灵活性 | 低（需要手动添加规则） | 高（自动适应新模式） |
| 成本 | 低（无 API 调用） | 高（每次分析多次 API 调用） |
| 离线可用 | 是 | 否 |

**选择理由**：性能诊断的核心模式（CPU bound、memory bound 等）是有限且已知的，规则引擎完全可以覆盖。LLM 的价值在于处理边界情况和生成人类可读的报告，而非核心推理。

### 13.3 Pydantic 结构化输出 vs 自由文本解析

**决策**：所有 LLM 输出都通过 Pydantic schema 约束为结构化 JSON。

**替代方案**：让 LLM 输出自由文本，然后用正则或 NLP 解析。

**选择理由**：
- 结构化输出消除了解析失败的风险
- Pydantic schema 同时作为 LLM 的输出约束和代码的类型定义，一处定义两处使用
- OpenAI 的 `response_format` 原生支持 Pydantic schema

### 13.4 YAML 配置 vs 硬编码

**决策**：工具配置、事件映射、提示词模板全部外置为 YAML 文件。

```
configs/
├── events.yaml    # 意图 → 事件映射
├── tools.yaml     # 工具超时和解析器
├── prompts.yaml   # LLM 提示词
└── safety.yaml    # 沙箱配置
```

**选择理由**：
- 事件映射需要频繁调整（新增 CPU 微架构时）
- 提示词需要迭代优化
- YAML 比 JSON 更适合人类编辑（支持注释、多行字符串）
- 配置加载通过 `load_xxx_configs()` 函数统一管理，支持路径覆盖

### 13.5 每步持久化 vs 最终持久化

**决策**：每次状态转换后立即持久化所有中间状态。

**替代方案**：仅在分析完成后持久化最终结果。

**权衡**：
- 每步持久化增加了 I/O 开销（每步写入 ~10 个 JSON 文件）
- 但性能分析本身的工具执行时间远大于 JSON 序列化时间
- 换来的是完整的断点恢复和实时可观测能力

---

## 14. 遇到的问题与解决方案

### 14.1 PMU 事件跨平台不兼容

**问题**：同一个语义概念（如"L1 cache miss"）在不同平台上的事件名称完全不同：
- Intel: `mem_load_retired.l1_miss`
- AMD: `l1-dcache-load-misses`
- ARM: `l1d-cache-refill` 或 `armv8_pmuv3/l1d_cache_refill/`

**解决方案**：构建**语义别名系统**。

1. EnvironmentProfiler 解析 `perf list` 输出，为每个事件分配语义标签
2. EventMapper 通过语义别名查找，而非硬编码事件名
3. `_prefer_event_variant()` 在多个候选中选择最优事件

```python
# 别名查找链
requested: "cache-misses"
    → aliases["cache-misses"] → ["cache-misses", "l1d-cache-refill", ...]
    → _prefer_event_variant() → 选择 portability_score 最高的
```

### 14.2 perf stat 事件数量超出 PMU 计数器

**问题**：现代 CPU 通常只有 4-8 个通用 PMU 计数器，但一次分析可能需要 15+ 个事件。perf 会使用 multiplexing（时分复用），但这会降低计数精度。

**解决方案**：EventMapper 的**智能批次拆分**。

1. 按语义分组（efficiency、branch、cache、scheduler 等）
2. 保持 access/miss 成对指标在同一批
3. 每批不超过平台的 `stat_event_budget`
4. 多批次顺序执行，每批都是完整的程序运行

### 14.3 LLM 返回无效或不一致的结果

**问题**：LLM 可能返回不存在的 observation ID、超出范围的 confidence 值、或不合法的 hypothesis kind。

**解决方案**：`_validate_hypotheses()` 进行严格的后验证。

```python
def _validate_hypotheses(self, hypotheses, observations):
    valid_ids = {item.id for item in observations}
    for draft in hypotheses:
        confidence = max(0.0, min(float(draft.confidence), 1.0))  # 裁剪范围
        kind = draft.kind if draft.kind in VALID_KINDS else "unknown"  # 合法性检查
        support = [id for id in draft.supporting_observation_ids if id in valid_ids]  # ID 验证
        if confidence > 0 and not support and observations:
            support = [observations[0].id]  # 兜底：至少引用一条观测
```

### 14.4 短生命周期程序的采样困难

**问题**：运行时间 < 100ms 的程序，perf stat 的 interval mode 无法产生有意义的时间序列数据。

**解决方案**：`_runtime_seconds()` 检查已观测到的运行时长，仅在 ≥ 80ms 时才追加 `temporal_behavior` 意图。

```python
def build_follow_up_intents(state, hypotheses):
    runtime_seconds = _runtime_seconds(state)
    if runtime_seconds >= 0.08:
        follow_up.append(AnalysisIntent(name="temporal_behavior", ...))
```

### 14.5 多进程/多线程程序的归因困难

**问题**：多进程程序（如 fork-join 模式）的 perf 数据混合了父子进程的样本，难以区分各进程的贡献。

**解决方案**：
1. pidstat 提供进程级和线程级的 CPU 拆账
2. perf record 的 `--per-thread` 模式分离线程样本
3. EvidenceSummarizer 生成 `top_processes` 和 `top_threads` 拆账
4. SourceAnalyzer 检测源码中的并发模式（fork、pthread_create 等）

### 14.6 规则引擎的假阳性

**问题**：简单的阈值规则可能产生假阳性。例如，一个程序的 CPU 利用率 85% 但实际瓶颈是 cache miss。

**解决方案**：
1. **多条件组合**：memory_bound 需要 IPC + backend_stall + cache_misses 三个条件同时满足
2. **矛盾证据记录**：Hypothesis 的 `contradicting_observation_ids` 记录反证
3. **验证闭环**：Verifier 在证据不充分时追加实验，而非直接下结论
4. **LLM 交叉验证**：LLM Analyzer 可以综合考虑规则引擎可能忽略的指标组合

---

## 15. 面试深度问答

### Q1: 为什么选择多智能体架构而不是单体 LLM Agent？

**回答**：

单体 LLM Agent（如 AutoGPT 模式）的核心问题是**不可控性**和**不可靠性**：

1. **流程不可控**：LLM 可能跳过关键步骤（如环境探测），或在不必要的方向上浪费 token
2. **幻觉风险**：LLM 可能"发明"不存在的 perf 事件或编造观测数据
3. **成本不可预测**：自主决策的 Agent 可能产生大量无效的 LLM 调用
4. **调试困难**：出错时难以定位是哪个环节的推理出了问题

多智能体 + 状态机的架构将**流程控制**和**智能推理**分离：
- 状态机保证流程的确定性和可控性
- 每个智能体只在自己的职责范围内使用 LLM
- 每个 LLM 调用都有确定性 fallback
- 出错时可以精确定位到具体的智能体和 LLM 调用

### Q2: 这个架构有什么优势？

**回答**：

1. **渐进式降级**：从"LLM 全辅助"到"纯规则引擎"的平滑降级，不存在单点故障
2. **可审计性**：每一步决策都有 AuditEvent 和 LLMTrace 记录，支持完整的推理链回溯
3. **可扩展性**：新增瓶颈类型只需添加规则 + 意图 + 事件映射，不需要修改核心流程
4. **跨平台适配**：语义别名系统使得同一套分析逻辑可以在 x86/ARM/Android 上运行
5. **证据驱动**：所有结论都可追溯到具体的观测数据和命令输出，不存在"黑盒诊断"

### Q3: 为什么不用 RAG？内存/记忆机制是怎么设计的？

**回答**：

**不用 RAG 的原因**（详见 7.2 节）：
- 性能诊断需要的是推理能力而非事实检索
- 上下文已经是结构化的 JSON，比 RAG 检索的文档片段更精确
- 核心领域知识已编码在规则引擎中

**系统的"记忆"机制**：

本系统不需要传统意义上的长期记忆（如向量数据库），因为：

1. **单次分析是自包含的**：每次分析从环境探测开始，不依赖历史分析结果
2. **短期记忆 = AnalysisState**：当前分析的所有中间状态都在 AnalysisState 中，这就是"工作记忆"
3. **跨轮记忆 = EvidencePack**：每轮分析的关键发现被压缩为 EvidencePack，传递给下一轮的 LLM 调用
4. **持久化记忆 = runs/ 目录**：每次分析的完整状态都持久化到磁盘，支持事后回溯

**如果要支持跨分析的记忆**（如"上次分析发现这个程序是 memory bound"），可以：
- 在 runs/ 目录中检索历史分析结果
- 将历史假设作为 Planner 的先验知识
- 但这会引入"确认偏误"风险，需要谨慎设计

### Q4: 置信度评分为什么这样设计？有什么局限性？

**回答**：

**当前设计**：`score = base(0.4) + 0.07 * observation_count + strength`

**优势**：
- 简单可解释：每多一条支撑证据增加 7% 置信度
- 可配置：`min_confidence` 通过 rules.yaml 外置
- 有上限（0.95）：保持诊断的谦逊性

**局限性**：
- **线性假设**：实际上，第 2 条支撑证据的价值可能远大于第 10 条（边际递减）
- **不考虑证据质量**：一条 perf stat 的 IPC 观测和一条 pidstat 的 CPU% 观测被同等对待
- **不考虑证据相关性**：两条来自同一工具的观测可能高度相关，不应该双倍计分

**改进方向**：
- 引入证据权重（direct > derived，perf_stat > generic_parser）
- 使用对数评分（`base + k * log(1 + count)`）模拟边际递减
- 考虑证据来源的多样性（来自不同工具的证据更有价值）

### Q5: 如何保证诊断结论的可靠性？

**回答**：

系统通过**五层保障**确保可靠性：

1. **模型层验证**：Pydantic `model_validator` 确保数据完整性（如非零置信度必须有支撑证据）
2. **规则层验证**：多条件组合检测，避免单一指标误判
3. **LLM 输出验证**：`_validate_hypotheses()` 过滤无效的 LLM 输出
4. **验证闭环**：Verifier 在证据不充分时追加实验，而非强行下结论
5. **人类可审计**：完整的 audit log 和 LLM trace 支持人工复核

### Q6: 状态机的 13 个状态是否过多？能否简化？

**回答**：

13 个状态看似多，但每个状态都有明确的职责边界：

- `init` → `running`：初始化
- `running`：目标准备
- `profiling_environment`：环境探测
- `planning`：证据规划
- `tool_selecting`：工具选择
- `collecting`：命令执行
- `parsing`：结果解析
- `analyzing`：假设生成
- `verifying`：验证闭环
- `source_analyzing`：源码关联
- `reporting`：报告生成
- `done` / `failed`：终态

**能否合并？**

- `planning` + `tool_selecting` 可以合并，但分开后 Planner 和 Toolsmith 的职责更清晰
- `collecting` + `parsing` 可以合并，但分开后支持"采集成功但解析失败"的精确错误定位
- `analyzing` + `verifying` 不能合并，因为验证回环需要独立的状态转换点

**结论**：状态数量是职责清晰度和实现复杂度的权衡。当前的 13 个状态在可维护性和可调试性之间取得了较好的平衡。

### Q7: 如何处理 perf 权限不足的情况？

**回答**：

EnvironmentProfiler 在探测阶段就检测 perf 的可用性：

1. 检查 `perf` 命令是否存在（`shutil.which("perf")`）
2. 检查 `/proc/sys/kernel/perf_event_paranoid` 的值
3. 尝试执行 `perf list` 获取可用事件

如果 perf 不可用，系统自动降级：
- `instruction_efficiency` → 跳过（无替代）
- `cache_memory_pressure` → 跳过（无替代）
- `scheduler_context` → 降级到 `pidstat` + `mpstat`
- `system_cpu_profile` → 降级到 `sar` + `mpstat`
- `hot_function_callgraph` → 跳过（无替代）

降级信息会记录在 EventMapping 的 `fallback_used` 和 `availability_notes` 中，最终体现在报告里。

### Q8: 系统的可扩展性如何？如何添加新的瓶颈类型？

**回答**：

添加一个新的瓶颈类型（如 `numa_imbalance`）需要修改以下位置：

1. **models/hypothesis.py**：在 `kind` 的 Literal 中添加 `"numa_imbalance"`
2. **rules/heuristics.py**：添加 `detect_numa_imbalance()` 检测函数
3. **rules/classifier.py**：在 `classify_observations()` 中调用新的检测函数
4. **planning/intents.py**：在 `build_follow_up_intents()` 中添加对应的追加实验
5. **configs/events.yaml**：添加新意图的事件映射
6. **agents/reporter.py**：在 `_kind_label()` 中添加中文标签

不需要修改：Orchestrator、状态机、LLM Client、Parser、Collector 等核心组件。这体现了**开闭原则**：对扩展开放，对修改封闭。

### Q9: 如何处理分析过程中的错误和异常？

**回答**：

错误处理分为三个层次：

1. **工具执行失败**：
   - `PlannedAction.retryable` 标记是否可重试
   - 不可重试的失败设置 `state.error_message`，状态转为 `failed`
   - 可重试的失败记录日志但不中断流水线

2. **LLM 调用失败**：
   - 每个 LLM 调用都有 try-except 包裹
   - 失败时记录 `LLMTrace(status="fallback")`
   - 降级到确定性逻辑继续执行

3. **数据验证失败**：
   - Pydantic 模型验证在数据入口处拦截非法数据
   - `_validate_hypotheses()` 过滤 LLM 返回的无效假设
   - 空结果不会导致崩溃（各处都有空列表/None 的处理）

### Q10: 与现有的性能分析工具（如 Intel VTune、AMD uProf）相比，这个系统的定位是什么？

**回答**：

| 维度 | VTune/uProf | perf_agent |
|------|------------|------------|
| 定位 | 专业级 GUI 工具 | 自动化诊断系统 |
| 用户 | 性能工程师 | 普通开发者 |
| 交互方式 | 手动操作 GUI | 全自动流水线 |
| 平台 | 特定厂商 CPU | 跨平台（x86/ARM/Android） |
| 输出 | 原始数据 + 可视化 | 结构化诊断报告 + 推理链 |
| 智能程度 | 无（纯工具） | 规则 + LLM 辅助推理 |
| 可编程性 | 有限 | 完全可编程（Python） |

perf_agent 不是要替代 VTune，而是要**降低性能分析的门槛**：让不熟悉 perf 的开发者也能获得结构化的性能诊断结论。对于需要深入分析的场景，perf_agent 的报告可以作为 VTune 分析的起点。

