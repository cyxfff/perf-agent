# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.95。

## 2. 分析目标
- 命令: examples/bin/multiprocess_fanout_demo 3 250 24000
- 可执行文件: examples/bin/multiprocess_fanout_demo
- 源码目录: examples/cpp
- 运行信息: verification_rounds=1, actions_executed=9
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
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。
- 第 2 轮 [verification] perf stat / 时间序列行为: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 9 个，时间序列指标 6 个，进程拆账 4 条，线程拆账 4 条。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, hot_symbol_pct
- 热点符号: _start, __libc_start_main@@GLIBC_2.34, __libc_start_call_main, main, __cos_fma
- 时间序列指标: cache_misses, context_switches, cycles, instructions, topdown_be_bound_pct, topdown_fe_bound_pct
- 进程级样本拆账: multiprocess_fa pid=60 35.59%, multiprocess_fa pid=58 32.38%, multiprocess_fa pid=59 31.00%, multiprocess_fa pid=56 1.03%
- 线程级样本拆账: multiprocess_fa pid/tid=60/60 35.59%, multiprocess_fa pid/tid=58/58 32.38%, multiprocess_fa pid/tid=59/59 31.00%, multiprocess_fa pid/tid=56/56 1.03%
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在并发工作函数入口，建议结合热点和调度证据一起判断线程或子进程的贡献。
- 已采集到 top-down 前后端指标，可进一步区分 frontend / backend / bad speculation / retiring。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_1e0b5ecc: time.user_time_sec=0.29
- obs_940c7d0a: time.system_time_sec=0.0
- obs_98219f34: time.cpu_utilization_pct=232
- obs_1c4d9d8a: time.max_rss_kb=3840
- obs_23fb4127: time.major_faults=0
- obs_53151cb9: time.voluntary_context_switches=7
- obs_f21ffcde: time.involuntary_context_switches=7
- obs_8350d395: time.elapsed_time_sec=0.12
- obs_492e1458: perf_stat.cycles=1293470523
- obs_dcca950c: perf_stat.instructions=5649196836
- obs_cd0e689d: perf_stat.msec=253.6
- obs_bf84e13b: perf_stat.slots=7752575700
- obs_7c39b76d: perf_stat.seconds=0.108691086
- obs_f6841d46: perf_stat.context_switches=13
- obs_08fcac83: perf_stat.cpu_migrations=3
- obs_5e8d3cd5: perf_stat.page_faults=291
- obs_9b4b06d3: perf_stat.lock_loads=23882
- obs_60a19bc2: perf_stat.seconds=0.096979332
- obs_23b20792: mpstat.03=04:31     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_33d0b6cf: mpstat.03=04:32     all    0.60    0.00    0.25    0.05    0.00    0.00    0.00    0.00    0.00   99.10
- obs_884d1963: mpstat.average=all    0.60    0.00    0.25    0.05    0.00    0.00    0.00    0.00    0.00   99.10
- obs_ca050263: perf_record.hot_symbol_pct=99.72
- obs_772d72f1: perf_record.hot_symbol_pct=99.72
- obs_7eb6b915: perf_record.hot_symbol_pct=99.72
- obs_5557907e: perf_record.hot_symbol_pct=92.94
- obs_512cbe81: perf_record.hot_symbol_pct=47.41
- obs_042f1f74: perf_record.hot_symbol_pct=36.25
- obs_aba70071: perf_record.hot_symbol_pct=2.53
- obs_81561f8f: perf_record.hot_symbol_pct=2.17
- obs_14369838: perf_record.callgraph_samples=877
- obs_75723da0: perf_record.process_sample_count=310
- obs_bb866595: perf_record.process_sample_pct=35.5913
- obs_89379a59: perf_record.process_sample_count=282
- obs_2072c29e: perf_record.process_sample_pct=32.3766
- obs_52081aae: perf_record.process_sample_count=270
- obs_8c4f173a: perf_record.process_sample_pct=30.9989
- obs_81d5ef8c: perf_record.process_sample_count=9
- obs_6d462ee6: perf_record.process_sample_pct=1.0333
- obs_9527eaee: perf_record.thread_sample_count=310
- obs_3e36a5c6: perf_record.thread_sample_pct=35.5913
- obs_b4ec2e1e: perf_record.thread_sample_count=282
- obs_3c87b5cf: perf_record.thread_sample_pct=32.3766
- obs_2b751d33: perf_record.thread_sample_count=270
- obs_b9d2e4c3: perf_record.thread_sample_pct=30.9989
- obs_428b7783: perf_record.thread_sample_count=9
- obs_1623cf8f: perf_record.thread_sample_pct=1.0333
- obs_d68e73ae: perf_record.hot_frame_sample_pct=1.1481
- obs_346512de: perf_record.hot_frame_sample_pct=1.0333
- obs_591b3404: perf_record.hot_frame_sample_pct=1.0333
- obs_1ffa7c23: perf_record.hot_frame_sample_pct=0.9185
- obs_40698f48: perf_record.hot_frame_sample_pct=0.9185
- obs_a9313453: perf_record.hot_frame_sample_pct=0.8037
- obs_066ee209: perf_record.hot_frame_sample_pct=0.8037
- obs_f73d2b99: perf_record.hot_frame_sample_pct=0.8037
- obs_9f6f195a: perf_record.hot_frame_sample_pct=0.8037
- obs_c7043a41: perf_record.hot_frame_sample_pct=0.8037
- obs_ab18ec99: perf_stat.cycles=1201889362
- obs_856629f5: perf_stat.cycles=112060511
- obs_3905a070: perf_stat.instructions=4974122474
- obs_9c840dc4: perf_stat.cache_misses=50529
- obs_bc81ef01: perf_stat.cache_misses=487
- obs_98884d02: perf_stat.context_switches=6
- obs_abc952b2: perf_stat.topdown_fe_bound_pct=76632708
- obs_2a971a12: perf_stat.topdown_be_bound_pct=184731883

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.95
- 支持证据: obs_98219f34, obs_bb866595, obs_2072c29e, obs_8c4f173a, obs_6d462ee6, obs_3e36a5c6, obs_3c87b5cf, obs_b9d2e4c3, obs_1623cf8f
- 反证: 无
- 验证状态: 证据基本充分

## 8. 源码定位
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:18
- 依据: perf record 样本中 main 占 1.03%，地址 0x2bc5 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.01
```cpp
  16 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  17 |             const double x = static_cast<double>((round + seed + 3) * (i + 11));
  18 |             checksum += std::sin(x) * std::cos(x / 7.0) + std::sqrt(x + 29.0);
  19 |         }
  20 |     }
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
### 热点函数定位: /home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp:25
- 依据: perf record / report 显示热点符号 main，该源码位置与热点调用路径直接相关。
- 映射方式: symbol_scan
- 置信度: 0.50
```cpp
  23 | }  // namespace
  24 | 
  25 | int main(int argc, char** argv) {
  26 |     std::size_t thread_count = 6;
  27 |     std::size_t iterations = 180000;
```
### 热点函数定位: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:26
- 依据: perf record / report 显示热点符号 main，该源码位置与热点调用路径直接相关。
- 映射方式: symbol_scan
- 置信度: 0.50
```cpp
  24 | }  // namespace
  25 | 
  26 | int main(int argc, char** argv) {
  27 |     std::size_t process_count = 3;
  28 |     std::size_t outer_loops = 250;
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

## 9. 二次验证
- 已执行动作:
- act_33aaf278: /usr/bin/time / 运行时基线 [done]
- act_0d8e586d: perf stat / 指令效率 [done]
- act_ac06aeb7: perf stat / 缓存与内存压力 [failed]
- act_122013db: perf stat / 前后端停顿 [failed]
- act_cad74044: perf stat / 调度上下文 [done]
- act_1c05b2d7: pidstat / 调度上下文 [done]
- act_c1507a5a: mpstat / 调度上下文 [done]
- act_5cd0ae37: perf record / 热点函数调用链 [done]
- act_c1cf0de3: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=232
- CPU 瓶颈: perf_record.process_sample_pct=35.5913
- CPU 瓶颈: perf_record.process_sample_pct=32.3766
- CPU 瓶颈: perf_record.process_sample_pct=30.9989
- CPU 瓶颈: perf_record.process_sample_pct=1.0333
- CPU 瓶颈: perf_record.thread_sample_pct=35.5913
- CPU 瓶颈: perf_record.thread_sample_pct=32.3766
- CPU 瓶颈: perf_record.thread_sample_pct=30.9989
- CPU 瓶颈: perf_record.thread_sample_pct=1.0333

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_7112dda3/artifacts/act_0d8e586d.json
- runs/run_7112dda3/artifacts/act_0d8e586d.stderr.txt
- runs/run_7112dda3/artifacts/act_0d8e586d.stdout.txt
- runs/run_7112dda3/artifacts/act_122013db.json
- runs/run_7112dda3/artifacts/act_122013db.stderr.txt
- runs/run_7112dda3/artifacts/act_1c05b2d7.json
- runs/run_7112dda3/artifacts/act_1c05b2d7.stdout.txt
- runs/run_7112dda3/artifacts/act_33aaf278.json
- runs/run_7112dda3/artifacts/act_33aaf278.stderr.txt
- runs/run_7112dda3/artifacts/act_33aaf278.stdout.txt
- runs/run_7112dda3/artifacts/act_5cd0ae37.json
- runs/run_7112dda3/artifacts/act_5cd0ae37.perf.data
- runs/run_7112dda3/artifacts/act_5cd0ae37.record.stdout.txt
- runs/run_7112dda3/artifacts/act_5cd0ae37.script.txt
- runs/run_7112dda3/artifacts/act_5cd0ae37.stderr.txt
- runs/run_7112dda3/artifacts/act_5cd0ae37.stdout.txt
- runs/run_7112dda3/artifacts/act_ac06aeb7.json
- runs/run_7112dda3/artifacts/act_ac06aeb7.stderr.txt
- runs/run_7112dda3/artifacts/act_c1507a5a.json
- runs/run_7112dda3/artifacts/act_c1507a5a.stdout.txt
- runs/run_7112dda3/artifacts/act_c1cf0de3.json
- runs/run_7112dda3/artifacts/act_c1cf0de3.stderr.txt
- runs/run_7112dda3/artifacts/act_c1cf0de3.stdout.txt
- runs/run_7112dda3/artifacts/act_cad74044.json
- runs/run_7112dda3/artifacts/act_cad74044.stderr.txt
- runs/run_7112dda3/artifacts/act_cad74044.stdout.txt
- runs/run_7112dda3/artifacts/perf_list.txt
- runs/run_7112dda3/environment.json
- runs/run_7112dda3/source_manifest.json
- runs/run_7112dda3/target.json
