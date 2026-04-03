# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.90。

## 2. 分析目标
- 命令: examples/bin/cpu_bound_demo 120 4000
- 可执行文件: examples/bin/cpu_bound_demo
- 源码目录: examples/cpp
- 运行信息: verification_rounds=1, actions_executed=9
- 工作目录: 

## 3. 运行环境
- 架构: x86_64
- 内核: 6.2.0-37-generic
- CPU: 13th Gen Intel(R) Core(TM) i5-13600K
- CPU 配置: 物理核 14 / 逻辑核 20
- 内存: 31 GB
- CPU 频率: 800 MHz - 5.10 GHz，当前缩放 54%
- Cache: L1d 544 KiB (14 instances) / L1i 704 KiB (14 instances) / L2 20 MiB (8 instances) / L3 24 MiB (1 instance)
- NUMA: 1 节点
- perf: 可用 perf version 6.2.16
- 调用栈模式: fp, dwarf, lbr
- 可用工具: perf, pidstat, mpstat, iostat, addr2line
- PMU: cpu_atom, cpu_core
- 源码映射: addr2line 可用

## 4. 实验设计与执行
- 第 1 轮 [baseline] /usr/bin/time / 运行时基线: 用 /usr/bin/time -v 建立程序运行基线。
- 第 1 轮 [baseline] perf stat / 指令效率: 判断 cycles、instructions 和 IPC 的健康度。当前使用首选事件组合。 事件为 cycles, Instructions, task-clock, cpu-clock, SLOTS。
- 第 1 轮 [baseline] perf stat / 缓存与内存压力 [1/2]: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 cache-references, cache-misses, mem_load_retired.l1_hit, mem_load_retired.l1_miss, l2_rqsts.references, L2_RQSTS.MISS, longest_lat_cache.reference, longest_lat_cache.miss, topdown-be-bound。 第 1/2 批。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 缓存与内存压力 [2/2]: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 cache-references, cache-misses, mem_load_retired.l1_hit, mem_load_retired.l1_miss, l2_rqsts.references, L2_RQSTS.MISS, longest_lat_cache.reference, longest_lat_cache.miss, topdown-be-bound。 第 2/2 批。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 前后端停顿: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 SLOTS, topdown-retiring, topdown-bad-spec, topdown-fe-bound, topdown-be-bound, cycles, Instructions。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用首选事件组合。 事件为 context-switches, cpu-migrations, page-faults, mem_inst_retired.lock_loads。
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 8 个，时间序列指标 0 个，进程拆账 1 条，线程拆账 1 条。
- 重点指标: voluntary_context_switches, cache_misses, context_switches, hot_symbol_pct
- 热点符号: main
- 进程级样本拆账: cpu_bound_demo pid=3796126 100.00%
- 线程级样本拆账: cpu_bound_demo pid/tid=3796126/3796126 100.00%
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。
- 当前还缺少时间序列证据，尚不能判断瓶颈是否阶段性出现。

## 6. 关键观测
- obs_a19b28a4: time.user_time_sec=0.01
- obs_675d9675: time.system_time_sec=0.0
- obs_ca657a73: time.cpu_utilization_pct=100
- obs_e2a33315: time.max_rss_kb=4160
- obs_927eb34d: time.major_faults=0
- obs_79c4aced: time.voluntary_context_switches=1
- obs_c161a415: time.involuntary_context_switches=0
- obs_0c265df0: time.elapsed_time_sec=0.01
- obs_926d24ae: perf_stat.cycles=32207277
- obs_63a3b133: perf_stat.instructions=116047799
- obs_779ac8b1: perf_stat.msec=11.2
- obs_e260dab3: perf_stat.slots=193048212
- obs_f4bdb613: perf_stat.seconds=0.011371723
- obs_030ad3b2: perf_stat.ipc=3.6032
- obs_f8030c02: perf_stat.cpi=0.2775
- obs_98a17735: perf_stat.cache_references=46283
- obs_445875b8: perf_stat.cache_misses=10217
- obs_a3329b70: perf_stat.l1_hit_count=29899952
- obs_668e6ed5: perf_stat.l1_miss_count=18350
- obs_b9323355: perf_stat.l2_access_count=171830
- obs_175d33a1: perf_stat.l2_miss_count=49360
- obs_0cd1a74d: perf_stat.llc_access_count=46283
- obs_0fb2539c: perf_stat.llc_miss_count=10217
- obs_e07303ea: perf_stat.seconds=0.006409487
- obs_61c9d2dc: perf_stat.cache_miss_rate_pct=22.0751
- obs_bde21c5a: perf_stat.l1_miss_rate_pct=0.0613
- obs_20013dbc: perf_stat.l2_miss_rate_pct=28.7261
- obs_65108586: perf_stat.llc_miss_rate_pct=22.0751
- obs_7dad5ebd: perf_stat.seconds=0.006462413
- obs_be0a3e87: perf_stat.slots=191949498
- obs_1a9f6f95: perf_stat.cycles=32018810
- obs_9a7399ee: perf_stat.instructions=116035429
- obs_01740ecb: perf_stat.seconds=0.006378627
- obs_e20cc690: perf_stat.ipc=3.624
- obs_b44de41c: perf_stat.cpi=0.2759
- obs_88d60b75: perf_stat.context_switches=0
- obs_cdd3eb75: perf_stat.cpu_migrations=0
- obs_ca81b41d: perf_stat.page_faults=139
- obs_9b92c8bb: perf_stat.lock_loads=9124
- obs_0622ffef: perf_stat.seconds=0.006362323
- obs_92fc8114: mpstat.15=08:53     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_5baeccbf: mpstat.15=08:54     all    0.80    0.00    0.65    0.05    0.00    0.00    0.00    0.00    0.00   98.50
- obs_1d3daa75: mpstat.average=all    0.80    0.00    0.65    0.05    0.00    0.00    0.00    0.00    0.00   98.50
- obs_aeaf90b3: perf_record.hot_symbol_pct=77.08
- obs_4e4000d7: perf_record.hot_symbol_pct=77.08
- obs_e3e6a8a0: perf_record.hot_symbol_pct=77.08
- obs_521beb12: perf_record.hot_symbol_pct=77.08
- obs_af2d8bec: perf_record.hot_symbol_pct=39.32
- obs_9853498c: perf_record.hot_symbol_pct=29.79
- obs_e3cb6cd1: perf_record.hot_symbol_pct=14.87
- obs_12526727: perf_record.hot_symbol_pct=14.87
- obs_c4939a4f: perf_record.callgraph_samples=16
- obs_8489aeea: perf_record.process_sample_count=10
- obs_cba0768d: perf_record.process_sample_pct=100.0
- obs_7d71fa65: perf_record.thread_sample_count=10
- obs_ff51fa12: perf_record.thread_sample_pct=100.0
- obs_cfb7d52c: perf_record.hot_frame_sample_pct=11.1111
- obs_7eb07c1a: perf_record.hot_frame_sample_pct=11.1111
- obs_76c2e2a2: perf_record.hot_frame_sample_pct=11.1111
- obs_5e14569d: perf_record.hot_frame_sample_pct=11.1111
- obs_9da095e4: perf_record.hot_frame_sample_pct=11.1111
- obs_58581528: perf_record.hot_frame_sample_pct=11.1111
- obs_e88ba2b1: perf_record.hot_frame_sample_pct=11.1111
- obs_5f528c56: perf_record.hot_frame_sample_pct=11.1111
- obs_ee6b17bd: perf_record.hot_frame_sample_pct=11.1111

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.90
- 支持证据: obs_ca657a73, obs_030ad3b2, obs_e20cc690, obs_cba0768d, obs_ff51fa12
- 反证: 无
- 验证状态: 证据基本充分

## 8. 源码定位
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:14
- 依据: perf record 样本中 main 占 11.11%，地址 0x1463 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.11
```cpp
  12 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  13 |             const double x = static_cast<double>((round + 1) * (i + 3));
  14 |             values[i] = std::sin(x) * std::cos(x / 3.0) + std::sqrt(x + 11.0);
  15 |             checksum += values[i];
  16 |         }
```
### 热点函数定位: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:23
- 依据: perf record / report 显示热点符号 main，该源码位置与热点调用路径直接相关。
- 映射方式: symbol_scan
- 置信度: 0.50
```cpp
  21 | }  // namespace
  22 | 
  23 | int main(int argc, char** argv) {
  24 |     std::size_t outer_loops = 1200;
  25 |     std::size_t inner_loops = 24000;
```
### 大规模向量处理: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:9
- 依据: 检测到可能参与高频数据处理的容器代码。
- 映射方式: heuristic
- 置信度: 0.35
```cpp
   7 | 
   8 | double hot_loop(std::size_t outer_loops, std::size_t inner_loops) {
   9 |     std::vector<double> values(inner_loops, 0.0);
  10 |     double checksum = 0.0;
  11 |     for (std::size_t round = 0; round < outer_loops; ++round) {
```
### 热点循环: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:11
- 依据: 检测到疑似高频计算循环或数学函数调用。
- 映射方式: heuristic
- 置信度: 0.35
```cpp
   9 |     std::vector<double> values(inner_loops, 0.0);
  10 |     double checksum = 0.0;
  11 |     for (std::size_t round = 0; round < outer_loops; ++round) {
  12 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  13 |             const double x = static_cast<double>((round + 1) * (i + 3));
```

## 9. 二次验证
- 已执行动作:
- act_2fbd49d8: /usr/bin/time / 运行时基线 [done]
- act_d2f1a359: perf stat / 指令效率 [done]
- act_3fb58340: perf stat / 缓存与内存压力 [1/2] [done]
- act_4871d2d8: perf stat / 缓存与内存压力 [2/2] [done]
- act_f52cbaef: perf stat / 前后端停顿 [done]
- act_2d010fd6: perf stat / 调度上下文 [done]
- act_a2715e07: pidstat / 调度上下文 [done]
- act_3ef5bc6e: mpstat / 调度上下文 [done]
- act_13718534: perf record / 热点函数调用链 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=100
- CPU 瓶颈: perf_stat.ipc=3.6032
- CPU 瓶颈: perf_stat.ipc=3.624
- CPU 瓶颈: perf_record.process_sample_pct=100.0
- CPU 瓶颈: perf_record.thread_sample_pct=100.0

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。
