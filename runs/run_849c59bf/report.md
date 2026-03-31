# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.95。

## 2. 分析目标
- 命令: examples/bin/multithread_cpu_demo 4 400 18000
- 可执行文件: examples/bin/multithread_cpu_demo
- 源码目录: examples/cpp
- 运行信息: verification_rounds=1, actions_executed=10
- 工作目录: 

## 3. 运行环境
- 架构: x86_64
- 内核: 6.2.0-37-generic
- CPU: 13th Gen Intel(R) Core(TM) i5-13600K
- 逻辑核数: 20
- perf: 可用 perf version 6.2.16
- 可用事件数: 856
- 调用栈模式: fp, dwarf, lbr
- hybrid PMU: cpu_atom, cpu_core
- Top-Down/TMA: topdown 事件 50 个，TMA 指标 125 个
- addr2line: 可用
- perf_event_paranoid: -1
- 检测到 top-down / TMA 相关事件，后续实验会优先尝试更细粒度的前后端拆分。
- 检测到 hybrid PMU: cpu_atom, cpu_core。事件映射会优先选择通用别名，不足时再退化到具体 PMU。
- 检测到 addr2line，可在符号和地址可用时尝试映射到源码行号。

## 4. 实验设计与执行
- 第 1 轮 [baseline] /usr/bin/time / 运行时基线: 用 /usr/bin/time -v 建立程序运行基线。
- 第 1 轮 [baseline] perf stat / 指令效率: 判断 cycles、instructions 和 IPC 的健康度。当前使用首选事件组合。 事件为 cycles, Instructions, task-clock, cpu-clock, SLOTS。
- 第 1 轮 [baseline] perf stat / 缓存与内存压力: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 topdown-be-bound, tma_memory_bound, cache-references, cache-misses, longest_lat_cache.miss, l2_rqsts.miss, mem_load_completed.l1_miss_any。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 前后端停顿: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 SLOTS, topdown-retiring, topdown-bad-spec, topdown-fe-bound, topdown-be-bound, tma_fetch_latency, tma_fetch_bandwidth, tma_memory_bound, tma_branch_mispredicts, cycles, Instructions。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用首选事件组合。 事件为 context-switches, cpu-migrations, page-faults, mem_inst_retired.lock_loads。
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 1 轮 [baseline] iostat / I/O 等待: 用 iostat 看设备利用率和等待延迟。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。
- 第 2 轮 [verification] perf stat / 时间序列行为: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 5 个，时间序列指标 6 个，进程拆账 1 条，线程拆账 5 条。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, hot_symbol_pct
- 热点符号: clone3, start_thread, std::thread::_State_impl<std::thread::_Invoker<std::tuple<main::{lambda()#1}> > >::_M_run, __cos_fma, __sin_fma
- 时间序列指标: cache_misses, context_switches, cycles, instructions, topdown_be_bound_pct, topdown_fe_bound_pct
- 进程级样本拆账: multithread_cpu pid=60 100.00%
- 线程级样本拆账: multithread_cpu pid/tid=60/65 25.26%, multithread_cpu pid/tid=60/63 24.96%, multithread_cpu pid/tid=60/62 24.89%, multithread_cpu pid/tid=60/64 24.14%
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在并发工作函数入口，建议结合热点和调度证据一起判断线程或子进程的贡献。
- 已采集到 top-down 前后端指标，可进一步区分 frontend / backend / bad speculation / retiring。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_eecde8d5: time.user_time_sec=0.38
- obs_2c7b1bb9: time.system_time_sec=0.0
- obs_b2021c15: time.cpu_utilization_pct=398
- obs_865e0328: time.max_rss_kb=4000
- obs_289ff72d: time.major_faults=1
- obs_bf77a9fe: time.voluntary_context_switches=18
- obs_0f9cedb4: time.involuntary_context_switches=6
- obs_879f3573: time.elapsed_time_sec=0.09
- obs_9ff2669b: perf_stat.cycles=1757925147
- obs_ff974a95: perf_stat.instructions=6719473551
- obs_69e8c446: perf_stat.msec=344.64
- obs_673602c4: perf_stat.slots=10508143524
- obs_ee7486fa: perf_stat.seconds=0.087411717
- obs_5e3685ac: perf_stat.context_switches=24
- obs_79b19b5d: perf_stat.cpu_migrations=4
- obs_7e89c116: perf_stat.page_faults=294
- obs_3e142415: perf_stat.lock_loads=14652
- obs_cd1a6439: perf_stat.seconds=0.086710118
- obs_bab06181: mpstat.03=04:31     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_2fef9b42: mpstat.03=04:32     all    0.30    0.00    0.20    0.05    0.00    0.00    0.00    0.00    0.00   99.45
- obs_cab6de7c: mpstat.average=all    0.30    0.00    0.20    0.05    0.00    0.00    0.00    0.00    0.00   99.45
- obs_46a0c137: perf_record.hot_symbol_pct=99.44
- obs_903bd9b8: perf_record.hot_symbol_pct=99.39
- obs_ca09affe: perf_record.hot_symbol_pct=94.02
- obs_4463fbba: perf_record.hot_symbol_pct=82.23
- obs_aa81b7d5: perf_record.hot_symbol_pct=46.72
- obs_7243f1df: perf_record.hot_symbol_pct=40.24
- obs_8c7e9742: perf_record.hot_symbol_pct=17.16
- obs_ff699d29: perf_record.hot_symbol_pct=2.11
- obs_3adf6b92: perf_record.callgraph_samples=1339
- obs_5e511478: perf_record.process_sample_count=1334
- obs_da821f67: perf_record.process_sample_pct=100.0
- obs_a0073fc8: perf_record.thread_sample_count=337
- obs_7ddd561f: perf_record.thread_sample_pct=25.2624
- obs_90fc854e: perf_record.thread_sample_count=333
- obs_131ed8a3: perf_record.thread_sample_pct=24.9625
- obs_b55c59f9: perf_record.thread_sample_count=332
- obs_7c6d3119: perf_record.thread_sample_pct=24.8876
- obs_6af84c8c: perf_record.thread_sample_count=322
- obs_35ddba63: perf_record.thread_sample_pct=24.1379
- obs_eabf6f6e: perf_record.thread_sample_count=10
- obs_5f76d7bf: perf_record.thread_sample_pct=0.7496
- obs_47ea746d: perf_record.hot_frame_sample_pct=1.1253
- obs_1579913c: perf_record.hot_frame_sample_pct=0.9002
- obs_3f1a4c65: perf_record.hot_frame_sample_pct=0.9002
- obs_f20e5a0f: perf_record.hot_frame_sample_pct=0.8252
- obs_16518a2c: perf_record.hot_frame_sample_pct=0.8252
- obs_06d65fa9: perf_record.hot_frame_sample_pct=0.8252
- obs_6496b58c: perf_record.hot_frame_sample_pct=0.7502
- obs_8bc82aea: perf_record.hot_frame_sample_pct=0.6752
- obs_85026c7e: perf_record.hot_frame_sample_pct=0.6752
- obs_b5cb704c: perf_record.hot_frame_sample_pct=0.6752
- obs_bfba194b: perf_stat.cycles=1754545804
- obs_93092a64: perf_stat.cycles=2626585
- obs_b609ea23: perf_stat.instructions=6725612549
- obs_54914402: perf_stat.cache_misses=45007
- obs_2987e854: perf_stat.cache_misses=10061
- obs_988792d2: perf_stat.context_switches=29
- obs_b078cf4f: perf_stat.topdown_fe_bound_pct=2751014
- obs_7e911229: perf_stat.topdown_be_bound_pct=4854845

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.95
- 支持证据: obs_b2021c15, obs_da821f67, obs_7ddd561f, obs_131ed8a3, obs_7c6d3119, obs_35ddba63, obs_5f76d7bf
- 反证: 无
- 验证状态: 证据基本充分

## 8. 源码定位
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/multithread_cpu_demo.cpp:15
- 依据: perf record 样本中 std::thread::_State_impl<std::thread::_Invoker<std::tuple<main::{lambda()#1}> > >::_M_run 占 0.90%，地址 0x2e3c 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.01
```cpp
  13 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  14 |             const double x = static_cast<double>((round + seed + 1) * (i + 7));
  15 |             values[i] = std::sin(x) + std::cos(x / 5.0) + std::sqrt(x + 17.0);
  16 |             checksum += values[i];
  17 |         }
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
### 并发工作函数: /home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp:13
- 依据: 检测到并发工作单元入口，CPU 消耗可能分散在多个线程或子进程。
- 映射方式: heuristic
- 置信度: 0.35
```cpp
  11 | std::uint64_t shared_counter = 0;
  12 | 
  13 | void worker(std::size_t iterations) {
  14 |     for (std::size_t i = 0; i < iterations; ++i) {
  15 |         std::lock_guard<std::mutex> guard(global_mutex);
```
### 热点循环: /home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp:14
- 依据: 检测到疑似高频计算循环或数学函数调用。
- 映射方式: heuristic
- 置信度: 0.35
```cpp
  12 | 
  13 | void worker(std::size_t iterations) {
  14 |     for (std::size_t i = 0; i < iterations; ++i) {
  15 |         std::lock_guard<std::mutex> guard(global_mutex);
  16 |         shared_counter += static_cast<std::uint64_t>(i % 7);
```
### 并发工作函数: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:13
- 依据: 检测到并发工作单元入口，CPU 消耗可能分散在多个线程或子进程。
- 映射方式: heuristic
- 置信度: 0.35
```cpp
  11 | namespace {
  12 | 
  13 | double worker(std::size_t outer_loops, std::size_t inner_loops, std::size_t seed) {
  14 |     double checksum = 0.0;
  15 |     for (std::size_t round = 0; round < outer_loops; ++round) {
```
### 热点循环: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:15
- 依据: 检测到疑似高频计算循环或数学函数调用。
- 映射方式: heuristic
- 置信度: 0.35
```cpp
  13 | double worker(std::size_t outer_loops, std::size_t inner_loops, std::size_t seed) {
  14 |     double checksum = 0.0;
  15 |     for (std::size_t round = 0; round < outer_loops; ++round) {
  16 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  17 |             const double x = static_cast<double>((round + seed + 3) * (i + 11));
```
### 并发工作函数: /home/tchen/agent/perf_agent/examples/cpp/multithread_cpu_demo.cpp:9
- 依据: 检测到并发工作单元入口，CPU 消耗可能分散在多个线程或子进程。
- 映射方式: heuristic
- 置信度: 0.35
```cpp
   7 | namespace {
   8 | 
   9 | double worker(std::size_t outer_loops, std::size_t inner_loops, std::size_t seed) {
  10 |     std::vector<double> values(inner_loops, 0.0);
  11 |     double checksum = 0.0;
```

## 9. 二次验证
- 已执行动作:
- act_78ca3689: /usr/bin/time / 运行时基线 [done]
- act_4b9fde28: perf stat / 指令效率 [done]
- act_426a62b2: perf stat / 缓存与内存压力 [failed]
- act_18496f2a: perf stat / 前后端停顿 [failed]
- act_837ea662: perf stat / 调度上下文 [done]
- act_a7ed43d9: pidstat / 调度上下文 [done]
- act_85ec1954: mpstat / 调度上下文 [done]
- act_15504f09: iostat / I/O 等待 [done]
- act_750eba4c: perf record / 热点函数调用链 [done]
- act_241435d2: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=398
- CPU 瓶颈: perf_record.process_sample_pct=100.0
- CPU 瓶颈: perf_record.thread_sample_pct=25.2624
- CPU 瓶颈: perf_record.thread_sample_pct=24.9625
- CPU 瓶颈: perf_record.thread_sample_pct=24.8876
- CPU 瓶颈: perf_record.thread_sample_pct=24.1379
- CPU 瓶颈: perf_record.thread_sample_pct=0.7496

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_849c59bf/artifacts/act_15504f09.json
- runs/run_849c59bf/artifacts/act_15504f09.stdout.txt
- runs/run_849c59bf/artifacts/act_18496f2a.json
- runs/run_849c59bf/artifacts/act_18496f2a.stderr.txt
- runs/run_849c59bf/artifacts/act_241435d2.json
- runs/run_849c59bf/artifacts/act_241435d2.stderr.txt
- runs/run_849c59bf/artifacts/act_241435d2.stdout.txt
- runs/run_849c59bf/artifacts/act_426a62b2.json
- runs/run_849c59bf/artifacts/act_426a62b2.stderr.txt
- runs/run_849c59bf/artifacts/act_4b9fde28.json
- runs/run_849c59bf/artifacts/act_4b9fde28.stderr.txt
- runs/run_849c59bf/artifacts/act_4b9fde28.stdout.txt
- runs/run_849c59bf/artifacts/act_750eba4c.json
- runs/run_849c59bf/artifacts/act_750eba4c.perf.data
- runs/run_849c59bf/artifacts/act_750eba4c.record.stdout.txt
- runs/run_849c59bf/artifacts/act_750eba4c.script.txt
- runs/run_849c59bf/artifacts/act_750eba4c.stderr.txt
- runs/run_849c59bf/artifacts/act_750eba4c.stdout.txt
- runs/run_849c59bf/artifacts/act_78ca3689.json
- runs/run_849c59bf/artifacts/act_78ca3689.stderr.txt
- runs/run_849c59bf/artifacts/act_78ca3689.stdout.txt
- runs/run_849c59bf/artifacts/act_837ea662.json
- runs/run_849c59bf/artifacts/act_837ea662.stderr.txt
- runs/run_849c59bf/artifacts/act_837ea662.stdout.txt
- runs/run_849c59bf/artifacts/act_85ec1954.json
- runs/run_849c59bf/artifacts/act_85ec1954.stdout.txt
- runs/run_849c59bf/artifacts/act_a7ed43d9.json
- runs/run_849c59bf/artifacts/act_a7ed43d9.stdout.txt
- runs/run_849c59bf/artifacts/perf_list.txt
- runs/run_849c59bf/environment.json
- runs/run_849c59bf/source_manifest.json
- runs/run_849c59bf/target.json
