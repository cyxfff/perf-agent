# perf_agent

`perf_agent` 是一个以“可执行程序优先”为入口的自动性能分析原型系统。它的目标不是简单包一层 `perf` 命令，而是把环境探测、实验设计、证据提炼、热点定位和源码关联串成一个可复盘的调查流程。

## 1. 产品目标

给定一个可执行文件、启动命令或已有 PID，系统自动完成：

1. 准备运行目标和可选源码目录。
2. 探测当前机器架构、内核版本、`perf` 能力和可用事件。
3. 基于“分析意图”设计实验，而不是写死固定工具列表。
4. 运行采样实验，采集 `perf` 与系统级指标。
5. 把原始输出解析成结构化 observation。
6. 形成候选瓶颈假设，并判断证据是否充分。
7. 在必要时自动追加第二轮实验，例如调用链采样或时间序列采样。
8. 生成中文 Markdown / HTML 报告，并尽量把热点路径关联到源码位置。

如果同时提供源码目录，系统会进一步尝试回答：

- 热点函数落在哪个文件、哪个函数附近？
- 这段代码为什么可能与当前瓶颈一致？
- 当前证据是总体统计、时间序列变化，还是调用链热点？

系统只负责定位与解释，不会自动修改代码做性能优化。

## 2. 第一版设计原则

- 使用 Python 3.11+
- 所有状态、观测、假设、报告对象都使用 Pydantic v2 建模
- 第一版不依赖 LangGraph / AutoGen
- 以单一状态机作为唯一真实状态来源
- LLM 只出现在 `analyzer`、`verifier`、`reporter`
- `collector`、`parser`、`rules`、事件映射逻辑保持确定性
- 所有中间产物都落盘到 `runs/<run_id>/`
- 所有结论都必须绑定 observation 证据
- 报告和 CLI 都尽量用中文输出

## 3. 系统架构

```text
用户输入
   |
   v
Task Loader
   |
   v
Orchestrator（中心状态机）
   |
   +--> Runner
   +--> Environment Profiler
   +--> Planner（分析意图规划）
   +--> Event Mapper（意图到事件映射）
   +--> Collector
   +--> Parser / Normalizer
   +--> Rule Engine
   +--> Analyzer（LLM 辅助）
   +--> Verifier（LLM 辅助 + 自动补采样）
   +--> Source Analyzer
   +--> Reporter（LLM 辅助）
   |
   v
JSON / Markdown / HTML / Artifacts
```

这里最核心的不是固定 `planner`，而是三层能力：

- Environment Profiler：先弄清楚“这台机器是谁、支持什么”
- Planner：先决定“我想回答什么问题”
- Event Mapper：再决定“这个问题在当前机器上用哪些事件和工具实现”

## 4. 调查层次

当前版本把性能调查拆成四层证据：

1. Aggregate Profiling
   用 `time`、`perf stat`、`pidstat`、`mpstat`、`iostat` 看总体效率与系统体征。

2. Temporal Profiling
   用 `perf stat -I <ms>` 做时间序列采样，判断问题是持续存在还是阶段性爆发。

3. Hotspot / Callchain Profiling
   用 `perf record` + `perf report --stdio` 看热点函数和主要调用路径。

4. Source Correlation
   把热点函数、热点路径和源码文件、函数、可疑代码模式对齐。

## 5. 当前支持的场景

当前项目已经覆盖并验证了这些典型场景：

- 单进程 CPU 密集计算
- 多线程锁竞争
- 多线程 CPU fanout
- 多进程 fanout / 父子进程并发
- 带源码目录时的热点源码定位
- `perf record` 样本下的进程级 / 线程级开销拆账
- `addr2line` 支持下的源码行号映射与代码片段展示

注意：并发场景现在已经能给出线程级 / 进程级样本占比，但它本质上仍然是“基于采样的开销拆账”，不是严格的 wall time / CPU time 记账。

## 6. 快速开始

### 6.1 安装

```bash
cd /home/tchen/agent/perf_agent
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 6.2 运行真实样例

建议把待测程序编译成带调试信息的版本，这样 `addr2line` 才能更稳定地映射到源码行号。对 C/C++ 程序，推荐至少带上：

```bash
-g -fno-omit-frame-pointer
```

CPU 密集型样例：

```bash
perf-agent analyze --exe examples/bin/cpu_bound_demo --source-dir examples/cpp -- 700 18000
```

锁竞争样例：

```bash
perf-agent analyze --exe examples/bin/lock_contention_demo --source-dir examples/cpp -- 6 120000
```

多线程 CPU fanout 样例：

```bash
perf-agent analyze --exe examples/bin/multithread_cpu_demo --source-dir examples/cpp -- 4 400 18000
```

多进程 fanout 样例：

```bash
perf-agent analyze --exe examples/bin/multiprocess_fanout_demo --source-dir examples/cpp -- 3 250 24000
```

如果只想看最终结果，不想看中间过程：

```bash
perf-agent analyze --quiet --exe examples/bin/cpu_bound_demo --source-dir examples/cpp -- 700 18000
```

## 7. CLI 使用方式

当前支持这些命令形式：

```bash
perf-agent analyze --exe ./my_binary -- --input case.txt
perf-agent analyze --exe ./my_binary --source-dir ./src
perf-agent analyze --quiet --exe ./my_binary -- --input case.txt
perf-agent analyze -- python app.py
perf-agent analyze --cmd "python app.py --input data.txt"
perf-agent analyze --pid 12345
perf-agent analyze --config configs/tools.yaml -- python bench.py
```

运行过程中，CLI 会直接告诉你：

- 当前在哪个阶段
- 探测到了什么架构和 `perf` 能力
- 当前选择了哪些分析意图
- 当前用的是 `perf stat` 还是 `perf record`
- 采了哪些事件，是否发生了 fallback
- 报告输出路径在哪里

## 8. 输入任务格式

当前 JSON 任务格式支持这些字段：

- `goal`：自然语言分析目标
- `executable_path`：可执行文件路径
- `target_args`：可执行文件参数列表
- `target_cmd`：完整命令数组
- `target_pid`：已有进程 PID
- `source_dir`：源码目录
- `workload_label`：工作负载标签
- `max_verification_rounds`：最多补采样轮数
- `mock_outputs`：用于测试或复盘的模拟输出
- `cwd`：运行目录
- `env`：附加环境变量

示例：

```json
{
  "goal": "分析一个 CPU 密集型并发程序",
  "executable_path": "examples/bin/multithread_cpu_demo",
  "target_args": ["4", "400", "18000"],
  "source_dir": "examples/cpp",
  "workload_label": "thread_cpu_demo",
  "max_verification_rounds": 2
}
```

## 9. 状态流转

当前状态机流程如下：

```text
init
 -> running
 -> profiling_environment
 -> planning
 -> collecting
 -> parsing
 -> analyzing
 -> verifying?（若需要）
 -> collecting（补采样）
 -> parsing
 -> analyzing
 -> source_analyzing
 -> reporting
 -> done
```

## 10. 实验设计逻辑

系统不是固定写死“先跑哪个工具”，而是：

1. 先探测环境能力
   - `uname -m`
   - `lscpu`
   - `perf --version`
   - `perf list`
   - `/sys/bus/event_source/devices`
   - 调用栈支持模式

2. 再生成分析意图
   例如：
   - baseline runtime
   - instruction efficiency
   - cache / memory pressure
   - scheduler context
   - temporal behavior
   - hot function callgraph

3. 然后映射到机器可执行事件
   - 优先使用当前机器可用的首选事件
   - 如果缺失，则退化到通用事件
   - 把 fallback 原因写进审计和报告

## 11. Evidence Pack

每一轮分析结束后，系统会生成一个 `evidence pack`，内容包括：

- 当前最重要的 observation
- 当前最值得关注的指标
- 当前最热的函数符号
- 当前已经拿到的时间序列指标
- 当前还没解决的不确定性

这部分会落盘到：

```text
runs/<run_id>/evidence_packs.json
```

同时会出现在最终报告的“证据摘要”部分。

## 12. 报告与可视化

HTML 报告不是自由画图，而是根据证据类型选图：

- 候选瓶颈置信度：条形图
- IPC / cache misses / context switches 等时间序列：折线图
- 热点函数分布：条形图
- 线程级 / 进程级样本拆账：条形图
- Top-Down / 前后端拆分：条形图
- 源码定位结果：源码卡片 + 代码片段

也就是说，图表是证据展示的一部分，不是单纯美化页面。

## 13. 输出产物

每次运行都会写出这些文件：

- `state.json`
- `target.json`
- `source_manifest.json`
- `environment.json`
- `observations.json`
- `hypotheses.json`
- `evidence_packs.json`
- `actions_taken.json`
- `pending_actions.json`
- `report.json`
- `report.md`
- `report.html`
- `artifacts/*`

## 14. 真实样例源码

当前仓库自带这些 C++ 样例：

- [cpu_bound_demo.cpp](/home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp)
- [lock_contention_demo.cpp](/home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp)
- [multithread_cpu_demo.cpp](/home/tchen/agent/perf_agent/examples/cpp/multithread_cpu_demo.cpp)
- [multiprocess_fanout_demo.cpp](/home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp)

对应可执行文件位于：

- `examples/bin/cpu_bound_demo`
- `examples/bin/lock_contention_demo`
- `examples/bin/multithread_cpu_demo`
- `examples/bin/multiprocess_fanout_demo`

## 15. 当前边界

这个项目现在已经能做：

- 自动环境探测
- 多轮实验设计
- 总体指标 + 时间序列 + 调用链热点联合分析
- 动态读取 `perf list` 并按当前机器能力解析事件别名
- 在 `perf record` 基础上做线程级 / 多进程样本拆账
- 用 `addr2line` 把热点地址映射到源码行号
- 在 Markdown / HTML 报告中展示源码片段
- 中文 Markdown / HTML 报告
- 针对长符号、模板函数、超长路径的 HTML 智能裁剪

但还没有完全做好的部分包括：

- 更稳定的 Top-Down / TMA 自动实验设计
- 多进程父子关系的严格识别与更精细归因
- 共享库热点跨仓源码映射
- 完整 flamegraph 生成链

## 16. 未来可继续增强的方向

比较值得继续做的增强项有：

- 对多线程和多进程做更明确的归因模型
- 支持多次运行对比分析
- 支持不同输入规模、不同参数配置的实验对比
- 加强调度、锁、I/O 的时间序列联合视图
- 在支持的平台上补齐 `-M TopdownL1/TopdownL2` 等更高层级 top-down 视图

如果你要继续沿这个方向推进，下一步最值钱的升级通常会是：

1. 更稳的 Top-Down / PMU 策略选择
2. 多线程 / 多进程更细的归因模型
3. 跨运行对比与回归分析
