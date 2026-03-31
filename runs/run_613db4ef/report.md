# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.76。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/cpu_bound_demo 700 18000
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/cpu_bound_demo
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
- 重点指标: cache_misses, context_switches, cache_misses, context_switches, voluntary_context_switches, cache_misses, context_switches, callgraph_samples
- 热点符号: main                                      -      -, __cos_fma                                 -      -, __sin_fma                                 -      -, 0x0000555c3d43b350                        -      -, 0x00000000000011f4                        -      -
- 时间序列指标: cache_misses, context_switches, cycles, instructions, ipc
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_f68cc089: time.user_time_sec=0.14
- obs_68d68dc3: time.system_time_sec=0.0
- obs_eb576d5b: time.cpu_utilization_pct=100
- obs_11123123: time.max_rss_kb=4320
- obs_690242c9: time.major_faults=0
- obs_84ead917: time.voluntary_context_switches=1
- obs_6e8ee80d: time.involuntary_context_switches=2
- obs_a6313c5a: perf_stat.cycles=763054676
- obs_a6f08cbf: perf_stat.instructions=2941673320
- obs_ee2772d2: perf_stat.cache_references=51369
- obs_6681d225: perf_stat.cache_misses=18004
- obs_9c1acc05: perf_stat.context_switches=1
- obs_04793295: perf_stat.cpu_migrations=0
- obs_34c4534e: perf_stat.page_faults=170
- obs_b0ba073c: mpstat.01=15:42     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_0a0dba1b: mpstat.01=15:43     all    0.65    0.00    0.35    1.70    0.00    0.00    0.00    0.00    0.00   97.30
- obs_097cc33a: mpstat.average=all    0.65    0.00    0.35    1.70    0.00    0.00    0.00    0.00    0.00   97.30
- obs_a0d8be95: perf_record.callgraph_samples=119
- obs_05b5ec90: perf_record.hot_symbol_pct=94.09
- obs_fb4a657a: perf_record.hot_symbol_pct=45.59
- obs_b0d4e35a: perf_record.hot_symbol_pct=40.33
- obs_a60076ad: perf_record.hot_symbol_pct=1.99
- obs_0cdf33d8: perf_record.hot_symbol_pct=1.89
- obs_133b2ab9: perf_stat.cycles=499115196
- obs_efe1520d: perf_stat.instructions=1921333985
- obs_d4f41e67: perf_stat.cache_misses=23973
- obs_c1fabe6d: perf_stat.context_switches=5
- obs_43a56242: perf_stat.cycles=264497631
- obs_955f2da2: perf_stat.instructions=1020410904
- obs_31bc586e: perf_stat.cache_misses=4074
- obs_71b3533e: perf_stat.context_switches=0
- obs_727801e3: perf_stat.ipc=3.8495
- obs_5a1a9084: perf_stat.ipc=3.8579

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.76
- 支持证据: obs_eb576d5b, obs_727801e3, obs_5a1a9084
- 反证: 无
- 验证状态: 需要进一步验证

## 8. 源码定位
- 大规模向量处理: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:9
  依据: 检测到可能参与高频数据处理的容器代码。
  代码: std::vector<double> values(inner_loops, 0.0);
- 热点循环: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:11
  依据: 检测到疑似高频计算循环或数学函数调用。
  代码: for (std::size_t round = 0; round < outer_loops; ++round) {

## 9. 二次验证
- 已执行动作:
- act_0d95ee69: /usr/bin/time / 运行时基线 [done]
- act_670b1b8a: perf stat / 指令效率 [done]
- act_6b87501c: perf stat / 缓存与内存压力 [done]
- act_3158dd3f: perf stat / 调度上下文 [done]
- act_5ab21293: pidstat / 调度上下文 [done]
- act_5f30890e: mpstat / 调度上下文 [done]
- act_ed1060c7: perf record / 热点函数调用链 [done]
- act_03a9e13f: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=100
- CPU 瓶颈: perf_stat.ipc=3.8495
- CPU 瓶颈: perf_stat.ipc=3.8579

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_613db4ef/artifacts/act_03a9e13f.json
- runs/run_613db4ef/artifacts/act_03a9e13f.stderr.txt
- runs/run_613db4ef/artifacts/act_03a9e13f.stdout.txt
- runs/run_613db4ef/artifacts/act_0d95ee69.json
- runs/run_613db4ef/artifacts/act_0d95ee69.stderr.txt
- runs/run_613db4ef/artifacts/act_0d95ee69.stdout.txt
- runs/run_613db4ef/artifacts/act_3158dd3f.json
- runs/run_613db4ef/artifacts/act_3158dd3f.stderr.txt
- runs/run_613db4ef/artifacts/act_3158dd3f.stdout.txt
- runs/run_613db4ef/artifacts/act_5ab21293.json
- runs/run_613db4ef/artifacts/act_5ab21293.stdout.txt
- runs/run_613db4ef/artifacts/act_5f30890e.json
- runs/run_613db4ef/artifacts/act_5f30890e.stdout.txt
- runs/run_613db4ef/artifacts/act_670b1b8a.json
- runs/run_613db4ef/artifacts/act_670b1b8a.stderr.txt
- runs/run_613db4ef/artifacts/act_670b1b8a.stdout.txt
- runs/run_613db4ef/artifacts/act_6b87501c.json
- runs/run_613db4ef/artifacts/act_6b87501c.stderr.txt
- runs/run_613db4ef/artifacts/act_6b87501c.stdout.txt
- runs/run_613db4ef/artifacts/act_ed1060c7.json
- runs/run_613db4ef/artifacts/act_ed1060c7.perf.data
- runs/run_613db4ef/artifacts/act_ed1060c7.record.stdout.txt
- runs/run_613db4ef/artifacts/act_ed1060c7.stderr.txt
- runs/run_613db4ef/artifacts/act_ed1060c7.stdout.txt
- runs/run_613db4ef/environment.json
- runs/run_613db4ef/source_manifest.json
- runs/run_613db4ef/target.json
