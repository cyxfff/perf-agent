# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.70。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/cpu_bound_demo 700 18000
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/cpu_bound_demo
- 源码目录: /home/tchen/agent/perf_agent/examples/cpp
- 运行信息: verification_rounds=1, actions_executed=7
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

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 5 个，时间序列指标 0 个。
- 重点指标: voluntary_context_switches, cache_misses, context_switches, callgraph_samples, hot_symbol_pct, hot_symbol_pct, hot_symbol_pct, hot_symbol_pct
- 热点符号: main                            -      -, __cos_fma                       -      -, __sin_fma                       -      -, 0x0000557611fb0350              -      -, 0x0000000000001354              -      -
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。
- 当前还缺少时间序列证据，尚不能判断瓶颈是否阶段性出现。

## 6. 关键观测
- obs_1fe6dc8c: time.user_time_sec=0.14
- obs_ef2a6f7a: time.system_time_sec=0.0
- obs_85e6ceb1: time.cpu_utilization_pct=100
- obs_5863a43e: time.max_rss_kb=4320
- obs_443f6c5d: time.major_faults=0
- obs_d3e2ca4a: time.voluntary_context_switches=1
- obs_beedd685: time.involuntary_context_switches=2
- obs_c6467ae0: perf_stat.cycles=762927715
- obs_0e530ecf: perf_stat.instructions=2941633403
- obs_de50e800: perf_stat.cache_references=53623
- obs_e0713e04: perf_stat.cache_misses=13363
- obs_acbd7a86: perf_stat.context_switches=2
- obs_a6eb8137: perf_stat.cpu_migrations=1
- obs_c35f6343: perf_stat.page_faults=169
- obs_3376379b: mpstat.01=14:17     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_1cc6a50d: mpstat.01=14:18     all    0.40    0.00    0.05    0.10    0.00    0.00    0.00    0.00    0.00   99.45
- obs_0192e78d: mpstat.average=all    0.40    0.00    0.05    0.10    0.00    0.00    0.00    0.00    0.00   99.45
- obs_52b19c4f: perf_record.callgraph_samples=96
- obs_8a6efb34: perf_record.hot_symbol_pct=94.35
- obs_597a79e0: perf_record.hot_symbol_pct=48.15
- obs_795d3f45: perf_record.hot_symbol_pct=38.79
- obs_dacd4a0f: perf_record.hot_symbol_pct=1.66
- obs_5f8ecb4e: perf_record.hot_symbol_pct=1.5

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.70
- 支持证据: obs_85e6ceb1
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
- act_d48c5d49: /usr/bin/time / 运行时基线 [done]
- act_210d3560: perf stat / 指令效率 [done]
- act_5acf40a5: perf stat / 缓存与内存压力 [done]
- act_51f59768: perf stat / 调度上下文 [done]
- act_7af47a39: pidstat / 调度上下文 [done]
- act_92d110a7: mpstat / 调度上下文 [done]
- act_f8a3d1c1: perf record / 热点函数调用链 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=100

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_bd6d36fb/artifacts/act_210d3560.json
- runs/run_bd6d36fb/artifacts/act_210d3560.stderr.txt
- runs/run_bd6d36fb/artifacts/act_210d3560.stdout.txt
- runs/run_bd6d36fb/artifacts/act_51f59768.json
- runs/run_bd6d36fb/artifacts/act_51f59768.stderr.txt
- runs/run_bd6d36fb/artifacts/act_51f59768.stdout.txt
- runs/run_bd6d36fb/artifacts/act_5acf40a5.json
- runs/run_bd6d36fb/artifacts/act_5acf40a5.stderr.txt
- runs/run_bd6d36fb/artifacts/act_5acf40a5.stdout.txt
- runs/run_bd6d36fb/artifacts/act_7af47a39.json
- runs/run_bd6d36fb/artifacts/act_7af47a39.stdout.txt
- runs/run_bd6d36fb/artifacts/act_92d110a7.json
- runs/run_bd6d36fb/artifacts/act_92d110a7.stdout.txt
- runs/run_bd6d36fb/artifacts/act_d48c5d49.json
- runs/run_bd6d36fb/artifacts/act_d48c5d49.stderr.txt
- runs/run_bd6d36fb/artifacts/act_d48c5d49.stdout.txt
- runs/run_bd6d36fb/artifacts/act_f8a3d1c1.json
- runs/run_bd6d36fb/artifacts/act_f8a3d1c1.perf.data
- runs/run_bd6d36fb/artifacts/act_f8a3d1c1.record.stdout.txt
- runs/run_bd6d36fb/artifacts/act_f8a3d1c1.stderr.txt
- runs/run_bd6d36fb/artifacts/act_f8a3d1c1.stdout.txt
- runs/run_bd6d36fb/environment.json
- runs/run_bd6d36fb/source_manifest.json
- runs/run_bd6d36fb/target.json
