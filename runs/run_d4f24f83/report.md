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
- 第 1 轮 [baseline] perf stat / 缓存与内存压力: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 topdown-be-bound, cache-references, cache-misses, longest_lat_cache.miss, l2_rqsts.miss, mem_load_completed.l1_miss_any。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 前后端停顿: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 SLOTS, topdown-retiring, topdown-bad-spec, topdown-fe-bound, topdown-be-bound, cycles, Instructions。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用首选事件组合。 事件为 context-switches, cpu-migrations, page-faults, mem_inst_retired.lock_loads。
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。
- 第 2 轮 [verification] perf stat / 时间序列行为: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 7 个，时间序列指标 4 个，进程拆账 4 条，线程拆账 4 条。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, hot_symbol_pct
- 热点符号: __libc_start_main@@GLIBC_2.34, __libc_start_call_main, _start, main, __cos_fma
- 时间序列指标: cache_misses, context_switches, cycles, instructions
- 进程级样本拆账: multiprocess_fa pid=66 33.73%, multiprocess_fa pid=68 33.61%, multiprocess_fa pid=67 32.41%, multiprocess_fa pid=64 0.24%
- 线程级样本拆账: multiprocess_fa pid/tid=66/66 33.73%, multiprocess_fa pid/tid=68/68 33.61%, multiprocess_fa pid/tid=67/67 32.41%, multiprocess_fa pid/tid=64/64 0.24%
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在并发工作函数入口，建议结合热点和调度证据一起判断线程或子进程的贡献。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_395d03e9: time.user_time_sec=0.21
- obs_76004fbf: time.system_time_sec=0.0
- obs_35830987: time.cpu_utilization_pct=295
- obs_4ad4e79b: time.max_rss_kb=4000
- obs_be376719: time.major_faults=0
- obs_9429635b: time.voluntary_context_switches=6
- obs_377fa77c: time.involuntary_context_switches=2
- obs_13778274: time.elapsed_time_sec=0.07
- obs_1072446d: perf_stat.cycles=1114078614
- obs_434b3a6a: perf_stat.instructions=4401125463
- obs_bf6ad74e: perf_stat.msec=218.42
- obs_ae3e1b47: perf_stat.slots=6676954914
- obs_09639655: perf_stat.seconds=0.073432801
- obs_9e47207f: perf_stat.cache_references=147954
- obs_dc7f39c8: perf_stat.cache_misses=45198
- obs_5593a549: perf_stat.llc_miss_count=45198
- obs_05814b56: perf_stat.l2_miss_count=164571
- obs_c9e0f296: perf_stat.l1_miss_count=164035
- obs_099dc5fe: perf_stat.seconds=0.073476512
- obs_3eefd2c3: perf_stat.slots=6716034252
- obs_d05c0b91: perf_stat.cycles=1119559961
- obs_21357ccc: perf_stat.instructions=4401194532
- obs_ad80106c: perf_stat.seconds=0.0737292
- obs_29e0bc3b: perf_stat.context_switches=10
- obs_e8856235: perf_stat.cpu_migrations=3
- obs_73c0e31f: perf_stat.page_faults=292
- obs_5b19264b: perf_stat.lock_loads=23967
- obs_05389998: perf_stat.seconds=0.073267019
- obs_4f2fabb0: mpstat.03=07:22     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_9e4db408: mpstat.03=07:23     all    0.15    0.00    0.10    0.45    0.00    0.00    0.00    0.00    0.00   99.30
- obs_9ff79da1: mpstat.average=all    0.15    0.00    0.10    0.45    0.00    0.00    0.00    0.00    0.00   99.30
- obs_d5f2eeec: perf_record.hot_symbol_pct=99.31
- obs_570b3e89: perf_record.hot_symbol_pct=99.31
- obs_04028081: perf_record.hot_symbol_pct=88.99
- obs_9284a855: perf_record.hot_symbol_pct=81.53
- obs_5d5f9c9b: perf_record.hot_symbol_pct=40.82
- obs_99a6fc42: perf_record.hot_symbol_pct=39.39
- obs_56593056: perf_record.hot_symbol_pct=10.32
- obs_6b67ef82: perf_record.hot_symbol_pct=9.06
- obs_18db54f6: perf_record.callgraph_samples=836
- obs_5cf4876f: perf_record.process_sample_count=280
- obs_4556de69: perf_record.process_sample_pct=33.7349
- obs_620d01f6: perf_record.process_sample_count=279
- obs_d01c5a2b: perf_record.process_sample_pct=33.6145
- obs_89608c42: perf_record.process_sample_count=269
- obs_c8fa9a45: perf_record.process_sample_pct=32.4096
- obs_57f35d17: perf_record.process_sample_count=2
- obs_64fba318: perf_record.process_sample_pct=0.241
- obs_e9dd41e8: perf_record.thread_sample_count=280
- obs_2cfc02a0: perf_record.thread_sample_pct=33.7349
- obs_59ebdd74: perf_record.thread_sample_count=279
- obs_3916d703: perf_record.thread_sample_pct=33.6145
- obs_303c75e9: perf_record.thread_sample_count=269
- obs_00a90c5f: perf_record.thread_sample_pct=32.4096
- obs_5ccafd8f: perf_record.thread_sample_count=2
- obs_e005a9d0: perf_record.thread_sample_pct=0.241
- obs_86378d98: perf_record.hot_frame_sample_pct=1.3269
- obs_8c425cf0: perf_record.hot_frame_sample_pct=1.0856
- obs_1a61454b: perf_record.hot_frame_sample_pct=0.965
- obs_64147930: perf_record.hot_frame_sample_pct=0.8444
- obs_5d16c2f9: perf_record.hot_frame_sample_pct=0.8444
- obs_db72b7e6: perf_record.hot_frame_sample_pct=0.8444
- obs_ed6029b4: perf_record.hot_frame_sample_pct=0.8444
- obs_3eb0cce0: perf_record.hot_frame_sample_pct=0.8444
- obs_0adffb18: perf_record.hot_frame_sample_pct=0.8444
- obs_e46ba920: perf_record.hot_frame_sample_pct=0.8444
- obs_7eda9957: perf_stat.cycles=1120862927
- obs_b6eb54e6: perf_stat.instructions=4401136464
- obs_f545f6c3: perf_stat.cache_misses=40591
- obs_89784aad: perf_stat.context_switches=6

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.95
- 支持证据: obs_35830987, obs_4556de69, obs_d01c5a2b, obs_c8fa9a45, obs_64fba318, obs_2cfc02a0, obs_3916d703, obs_00a90c5f, obs_e005a9d0
- 反证: 无
- 验证状态: 证据基本充分

## 8. 源码定位
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:17
- 依据: perf record 样本中 main 占 0.96%，地址 0x2b5b 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.01
```cpp
  15 |     for (std::size_t round = 0; round < outer_loops; ++round) {
  16 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  17 |             const double x = static_cast<double>((round + seed + 3) * (i + 11));
  18 |             checksum += std::sin(x) * std::cos(x / 7.0) + std::sqrt(x + 29.0);
  19 |         }
```
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:18
- 依据: perf record 样本中 main 占 0.84%，地址 0x2bc5 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.01
```cpp
  16 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  17 |             const double x = static_cast<double>((round + seed + 3) * (i + 11));
  18 |             checksum += std::sin(x) * std::cos(x / 7.0) + std::sqrt(x + 29.0);
  19 |         }
  20 |     }
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

## 9. 二次验证
- 已执行动作:
- act_df0c9c9c: /usr/bin/time / 运行时基线 [done]
- act_2e262c5f: perf stat / 指令效率 [done]
- act_d44ff0f7: perf stat / 缓存与内存压力 [done]
- act_3b180023: perf stat / 前后端停顿 [done]
- act_27709503: perf stat / 调度上下文 [done]
- act_91b0782c: pidstat / 调度上下文 [done]
- act_b16e4d71: mpstat / 调度上下文 [done]
- act_45d95e07: perf record / 热点函数调用链 [done]
- act_9c8298c3: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=295
- CPU 瓶颈: perf_record.process_sample_pct=33.7349
- CPU 瓶颈: perf_record.process_sample_pct=33.6145
- CPU 瓶颈: perf_record.process_sample_pct=32.4096
- CPU 瓶颈: perf_record.process_sample_pct=0.241
- CPU 瓶颈: perf_record.thread_sample_pct=33.7349
- CPU 瓶颈: perf_record.thread_sample_pct=33.6145
- CPU 瓶颈: perf_record.thread_sample_pct=32.4096
- CPU 瓶颈: perf_record.thread_sample_pct=0.241

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_d4f24f83/artifacts/act_27709503.json
- runs/run_d4f24f83/artifacts/act_27709503.stderr.txt
- runs/run_d4f24f83/artifacts/act_27709503.stdout.txt
- runs/run_d4f24f83/artifacts/act_2e262c5f.json
- runs/run_d4f24f83/artifacts/act_2e262c5f.stderr.txt
- runs/run_d4f24f83/artifacts/act_2e262c5f.stdout.txt
- runs/run_d4f24f83/artifacts/act_3b180023.json
- runs/run_d4f24f83/artifacts/act_3b180023.stderr.txt
- runs/run_d4f24f83/artifacts/act_3b180023.stdout.txt
- runs/run_d4f24f83/artifacts/act_45d95e07.json
- runs/run_d4f24f83/artifacts/act_45d95e07.perf.data
- runs/run_d4f24f83/artifacts/act_45d95e07.record.stdout.txt
- runs/run_d4f24f83/artifacts/act_45d95e07.script.txt
- runs/run_d4f24f83/artifacts/act_45d95e07.stderr.txt
- runs/run_d4f24f83/artifacts/act_45d95e07.stdout.txt
- runs/run_d4f24f83/artifacts/act_91b0782c.json
- runs/run_d4f24f83/artifacts/act_91b0782c.stdout.txt
- runs/run_d4f24f83/artifacts/act_9c8298c3.json
- runs/run_d4f24f83/artifacts/act_9c8298c3.stderr.txt
- runs/run_d4f24f83/artifacts/act_9c8298c3.stdout.txt
- runs/run_d4f24f83/artifacts/act_b16e4d71.json
- runs/run_d4f24f83/artifacts/act_b16e4d71.stdout.txt
- runs/run_d4f24f83/artifacts/act_d44ff0f7.json
- runs/run_d4f24f83/artifacts/act_d44ff0f7.stderr.txt
- runs/run_d4f24f83/artifacts/act_d44ff0f7.stdout.txt
- runs/run_d4f24f83/artifacts/act_df0c9c9c.json
- runs/run_d4f24f83/artifacts/act_df0c9c9c.stderr.txt
- runs/run_d4f24f83/artifacts/act_df0c9c9c.stdout.txt
- runs/run_d4f24f83/artifacts/perf_list.txt
- runs/run_d4f24f83/environment.json
- runs/run_d4f24f83/source_manifest.json
- runs/run_d4f24f83/target.json
