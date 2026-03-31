# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.70。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/multiprocess_fanout_demo 3 250 24000
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/multiprocess_fanout_demo
- 源码目录: /home/tchen/agent/perf_agent/examples/cpp
- 运行信息: verification_rounds=1, actions_executed=8
- 工作目录: 

## 3. 运行环境
- 架构: x86_64
- 内核: 6.2.0-37-generic
- CPU: 13th Gen Intel(R) Core(TM) i5-13600K
- 逻辑核数: 20
- perf: 可用 perf version 6.2.16
- 可用事件数: 15
- 调用栈模式: fp, dwarf, lbr
- perf_event_paranoid: -1
- 检测到 topdown 相关事件，可在后续实验中优先尝试。

## 4. 实验设计与执行
- 第 1 轮 [baseline] /usr/bin/time / 运行时基线: 用 /usr/bin/time -v 建立程序运行基线。
- 第 1 轮 [baseline] perf stat / 指令效率: 判断 cycles、instructions 和 IPC 的健康度。当前使用首选事件组合。 事件为 cycles, instructions, task-clock, cpu-clock。
- 第 1 轮 [baseline] perf stat / 缓存与内存压力: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 cache-references, cache-misses。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用首选事件组合。 事件为 context-switches, cpu-migrations, page-faults。
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。
- 第 2 轮 [verification] perf stat / 时间序列行为: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 5 个，时间序列指标 5 个。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, callgraph_samples, hot_symbol_pct
- 热点符号: main, __cos_fma, __sin_fma, __sqrt, __sqrt_finite@GLIBC_2.15
- 时间序列指标: cache_misses, context_switches, cycles, instructions, ipc
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在工作线程入口，建议结合线程级热点与调度证据一起判断瓶颈。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_8188e587: time.user_time_sec=0.21
- obs_42f4e1d1: time.system_time_sec=0.0
- obs_cc86f2b7: time.cpu_utilization_pct=298
- obs_2e4fde5c: time.max_rss_kb=4000
- obs_464927a1: time.major_faults=0
- obs_c61ef4b7: time.voluntary_context_switches=9
- obs_90da753a: time.involuntary_context_switches=8
- obs_2fba4bed: time.elapsed_time_sec=0.07
- obs_aa4c4df0: perf_stat.cycles=1096610726
- obs_06b8d1f4: perf_stat.instructions=4401166080
- obs_2019827d: perf_stat.cache_references=167470
- obs_9cf16020: perf_stat.cache_misses=23592
- obs_9dec6cc6: perf_stat.context_switches=10
- obs_40f5b80f: perf_stat.cpu_migrations=1
- obs_cba948b1: perf_stat.page_faults=289
- obs_44ab628b: mpstat.02=07:43     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_674ac0de: mpstat.02=07:44     all    0.45    0.00    0.20    0.10    0.00    0.00    0.00    0.00    0.00   99.25
- obs_a9cbb1fb: mpstat.average=all    0.45    0.00    0.20    0.10    0.00    0.00    0.00    0.00    0.00   99.25
- obs_d6977507: perf_record.callgraph_samples=89
- obs_29981079: perf_record.hot_symbol_pct=90.4
- obs_82f94f99: perf_record.hot_symbol_pct=42.45
- obs_650f4be6: perf_record.hot_symbol_pct=36.68
- obs_12ccf36e: perf_record.hot_symbol_pct=4.14
- obs_cf35e02a: perf_record.hot_symbol_pct=3.03
- obs_6e265bf1: perf_stat.cycles=1097363742
- obs_6f89420e: perf_stat.instructions=4401271485
- obs_9b742a87: perf_stat.cache_misses=34943
- obs_2230962a: perf_stat.context_switches=10
- obs_cf047d71: perf_stat.ipc=4.0108

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.70
- 支持证据: obs_cc86f2b7, obs_cf047d71
- 反证: 无
- 验证状态: 需要进一步验证

## 8. 源码定位
- 热点函数定位: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:26
  依据: perf record / report 显示热点符号 main，该源码位置与热点调用路径直接相关。
  代码: int main(int argc, char** argv) {
- 线程工作函数: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:13
  依据: 检测到并发工作线程入口，CPU 消耗可能分散在多个工作单元。
  代码: double worker(std::size_t outer_loops, std::size_t inner_loops, std::size_t seed) {
- 热点循环: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:15
  依据: 检测到疑似高频计算循环或数学函数调用。
  代码: for (std::size_t round = 0; round < outer_loops; ++round) {

## 9. 二次验证
- 已执行动作:
- act_669bb570: /usr/bin/time / 运行时基线 [done]
- act_93567ede: perf stat / 指令效率 [done]
- act_4841564d: perf stat / 缓存与内存压力 [done]
- act_8f510239: perf stat / 调度上下文 [done]
- act_4ad6ea1b: pidstat / 调度上下文 [done]
- act_c1432018: mpstat / 调度上下文 [done]
- act_fc5a6881: perf record / 热点函数调用链 [done]
- act_d9c20162: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=298
- CPU 瓶颈: perf_stat.ipc=4.0108

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_eb6a7d1f/artifacts/act_4841564d.json
- runs/run_eb6a7d1f/artifacts/act_4841564d.stderr.txt
- runs/run_eb6a7d1f/artifacts/act_4841564d.stdout.txt
- runs/run_eb6a7d1f/artifacts/act_4ad6ea1b.json
- runs/run_eb6a7d1f/artifacts/act_4ad6ea1b.stdout.txt
- runs/run_eb6a7d1f/artifacts/act_669bb570.json
- runs/run_eb6a7d1f/artifacts/act_669bb570.stderr.txt
- runs/run_eb6a7d1f/artifacts/act_669bb570.stdout.txt
- runs/run_eb6a7d1f/artifacts/act_8f510239.json
- runs/run_eb6a7d1f/artifacts/act_8f510239.stderr.txt
- runs/run_eb6a7d1f/artifacts/act_8f510239.stdout.txt
- runs/run_eb6a7d1f/artifacts/act_93567ede.json
- runs/run_eb6a7d1f/artifacts/act_93567ede.stderr.txt
- runs/run_eb6a7d1f/artifacts/act_93567ede.stdout.txt
- runs/run_eb6a7d1f/artifacts/act_c1432018.json
- runs/run_eb6a7d1f/artifacts/act_c1432018.stdout.txt
- runs/run_eb6a7d1f/artifacts/act_d9c20162.json
- runs/run_eb6a7d1f/artifacts/act_d9c20162.stderr.txt
- runs/run_eb6a7d1f/artifacts/act_d9c20162.stdout.txt
- runs/run_eb6a7d1f/artifacts/act_fc5a6881.json
- runs/run_eb6a7d1f/artifacts/act_fc5a6881.perf.data
- runs/run_eb6a7d1f/artifacts/act_fc5a6881.record.stdout.txt
- runs/run_eb6a7d1f/artifacts/act_fc5a6881.stderr.txt
- runs/run_eb6a7d1f/artifacts/act_fc5a6881.stdout.txt
- runs/run_eb6a7d1f/environment.json
- runs/run_eb6a7d1f/source_manifest.json
- runs/run_eb6a7d1f/target.json
