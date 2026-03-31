# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.76。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/multithread_cpu_demo 4 400 18000
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/multithread_cpu_demo
- 源码目录: /home/tchen/agent/perf_agent/examples/cpp
- 运行信息: verification_rounds=1, actions_executed=9
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
- 第 1 轮 [baseline] iostat / I/O 等待: 用 iostat 看设备利用率和等待延迟。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。
- 第 2 轮 [verification] perf stat / 时间序列行为: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 4 个，时间序列指标 5 个。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, callgraph_samples, hot_symbol_pct
- 热点符号: 0000000000000000, std::thread::_State_impl<std::thread::_Invoker<std::tuple<main::{lambda()#1}> > >::_M_run, __cos_fma, __sin_fma
- 时间序列指标: cache_misses, context_switches, cycles, instructions, ipc
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在工作线程入口，建议结合线程级热点与调度证据一起判断瓶颈。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_3811319b: time.user_time_sec=0.39
- obs_3d08ea65: time.system_time_sec=0.0
- obs_4c4f7b0f: time.cpu_utilization_pct=273
- obs_3c35e696: time.max_rss_kb=3840
- obs_cc3f5ff6: time.major_faults=0
- obs_7840912e: time.voluntary_context_switches=25
- obs_2cf43855: time.involuntary_context_switches=11
- obs_16d88158: time.elapsed_time_sec=0.14
- obs_042f5f44: perf_stat.cycles=1728337829
- obs_7c34f44c: perf_stat.instructions=6719416632
- obs_98faa0ac: perf_stat.cache_references=197228
- obs_c960c4fa: perf_stat.cache_misses=16132
- obs_14cb2e64: perf_stat.context_switches=37
- obs_cbfea0ef: perf_stat.cpu_migrations=6
- obs_bdca7708: perf_stat.page_faults=293
- obs_63813b65: mpstat.02=07:43     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_d575afb9: mpstat.02=07:44     all    0.50    0.00    0.30    0.10    0.00    0.00    0.00    0.00    0.00   99.10
- obs_2be2050a: mpstat.average=all    0.50    0.00    0.30    0.10    0.00    0.00    0.00    0.00    0.00   99.10
- obs_c9263a7a: perf_record.callgraph_samples=77
- obs_87feae69: perf_record.hot_symbol_pct=98.91
- obs_8a900a2a: perf_record.hot_symbol_pct=94.52
- obs_5fc7d53e: perf_record.hot_symbol_pct=48.84
- obs_7bce2544: perf_record.hot_symbol_pct=37.58
- obs_f87599fc: perf_record.hot_symbol_pct=2.38
- obs_c0eee38d: perf_stat.cycles=1800739165
- obs_559229ac: perf_stat.cycles=384083778
- obs_90b9d9c9: perf_stat.instructions=6997303759
- obs_23d82cb8: perf_stat.instructions=843738587
- obs_c7b75e38: perf_stat.cache_misses=32519
- obs_2060a642: perf_stat.cache_misses=4776
- obs_27d4e01a: perf_stat.context_switches=28
- obs_f6e86259: perf_stat.cycles=137655892
- obs_85d5ffb8: perf_stat.instructions=533431920
- obs_39df2404: perf_stat.cache_misses=9192
- obs_5c2d8fe0: perf_stat.context_switches=0
- obs_4e325452: perf_stat.ipc=3.5889
- obs_9c2ce1a1: perf_stat.ipc=3.8751

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.76
- 支持证据: obs_4c4f7b0f, obs_4e325452, obs_9c2ce1a1
- 反证: 无
- 验证状态: 需要进一步验证

## 8. 源码定位
- 线程工作函数: /home/tchen/agent/perf_agent/examples/cpp/multithread_cpu_demo.cpp:9
  依据: 检测到并发工作线程入口，CPU 消耗可能分散在多个工作单元。
  代码: double worker(std::size_t outer_loops, std::size_t inner_loops, std::size_t seed) {
- 大规模向量处理: /home/tchen/agent/perf_agent/examples/cpp/multithread_cpu_demo.cpp:10
  依据: 检测到可能参与高频数据处理的容器代码。
  代码: std::vector<double> values(inner_loops, 0.0);

## 9. 二次验证
- 已执行动作:
- act_23dd7df5: /usr/bin/time / 运行时基线 [done]
- act_38cc7624: perf stat / 指令效率 [done]
- act_4b9bb981: perf stat / 缓存与内存压力 [done]
- act_e5f3687e: perf stat / 调度上下文 [done]
- act_30d61aa7: pidstat / 调度上下文 [done]
- act_f764263d: mpstat / 调度上下文 [done]
- act_882a70e2: iostat / I/O 等待 [done]
- act_fb156268: perf record / 热点函数调用链 [done]
- act_24fc0e1e: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=273
- CPU 瓶颈: perf_stat.ipc=3.5889
- CPU 瓶颈: perf_stat.ipc=3.8751

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_729ebece/artifacts/act_23dd7df5.json
- runs/run_729ebece/artifacts/act_23dd7df5.stderr.txt
- runs/run_729ebece/artifacts/act_23dd7df5.stdout.txt
- runs/run_729ebece/artifacts/act_24fc0e1e.json
- runs/run_729ebece/artifacts/act_24fc0e1e.stderr.txt
- runs/run_729ebece/artifacts/act_24fc0e1e.stdout.txt
- runs/run_729ebece/artifacts/act_30d61aa7.json
- runs/run_729ebece/artifacts/act_30d61aa7.stdout.txt
- runs/run_729ebece/artifacts/act_38cc7624.json
- runs/run_729ebece/artifacts/act_38cc7624.stderr.txt
- runs/run_729ebece/artifacts/act_38cc7624.stdout.txt
- runs/run_729ebece/artifacts/act_4b9bb981.json
- runs/run_729ebece/artifacts/act_4b9bb981.stderr.txt
- runs/run_729ebece/artifacts/act_4b9bb981.stdout.txt
- runs/run_729ebece/artifacts/act_882a70e2.json
- runs/run_729ebece/artifacts/act_882a70e2.stdout.txt
- runs/run_729ebece/artifacts/act_e5f3687e.json
- runs/run_729ebece/artifacts/act_e5f3687e.stderr.txt
- runs/run_729ebece/artifacts/act_e5f3687e.stdout.txt
- runs/run_729ebece/artifacts/act_f764263d.json
- runs/run_729ebece/artifacts/act_f764263d.stdout.txt
- runs/run_729ebece/artifacts/act_fb156268.json
- runs/run_729ebece/artifacts/act_fb156268.perf.data
- runs/run_729ebece/artifacts/act_fb156268.record.stdout.txt
- runs/run_729ebece/artifacts/act_fb156268.stderr.txt
- runs/run_729ebece/artifacts/act_fb156268.stdout.txt
- runs/run_729ebece/environment.json
- runs/run_729ebece/source_manifest.json
- runs/run_729ebece/target.json
