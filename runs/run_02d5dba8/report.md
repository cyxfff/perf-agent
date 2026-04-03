# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.95。

## 2. 分析目标
- 命令: examples/bin/multiprocess_fanout_demo
- 可执行文件: examples/bin/multiprocess_fanout_demo
- 源码目录: examples/cpp
- 运行信息: verification_rounds=1, actions_executed=9
- 工作目录: /home/tchen/agent/perf_agent

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
- 热点符号: _start, __libc_start_main@@GLIBC_2.34, __libc_start_call_main, main, __cos_fma
- 时间序列指标: cache_misses, context_switches, cycles, instructions
- 进程级样本拆账: multiprocess_fa pid=3620574 33.29%, multiprocess_fa pid=3620575 33.29%, multiprocess_fa pid=3620573 33.17%, multiprocess_fa pid=3620571 0.24%
- 线程级样本拆账: multiprocess_fa pid/tid=3620574/3620574 33.29%, multiprocess_fa pid/tid=3620575/3620575 33.29%, multiprocess_fa pid/tid=3620573/3620573 33.17%, multiprocess_fa pid/tid=3620571/3620571 0.24%
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在并发工作函数入口，建议结合热点和调度证据一起判断线程或子进程的贡献。
- 已采集到 top-down 前后端指标，可进一步区分 frontend / backend / bad speculation / retiring。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_feb34d5e: time.user_time_sec=0.22
- obs_c8664098: time.system_time_sec=0.0
- obs_21282e3b: time.cpu_utilization_pct=296
- obs_ded24c6e: time.max_rss_kb=4000
- obs_208c5563: time.major_faults=0
- obs_fcb649a7: time.voluntary_context_switches=6
- obs_9e1a0f9a: time.involuntary_context_switches=8
- obs_4ff3d13f: time.elapsed_time_sec=0.07
- obs_6ecfa4bb: perf_stat.cycles=1113453734
- obs_086ca75f: perf_stat.instructions=4401414830
- obs_ed5ea612: perf_stat.msec=218.3
- obs_a20a6156: perf_stat.slots=6677739780
- obs_666adebc: perf_stat.seconds=0.073546791
- obs_1d666f41: perf_stat.topdown_be_bound_pct=17667686
- obs_ba05ebc1: perf_stat.cache_references=132809
- obs_d0fae650: perf_stat.cache_misses=28916
- obs_f9607c43: perf_stat.llc_miss_count=30291
- obs_95511af1: perf_stat.l2_miss_count=142219
- obs_f6078162: perf_stat.l1_miss_count=175396
- obs_6c8818aa: perf_stat.seconds=0.073431917
- obs_55c9194e: perf_stat.slots=6678911622
- obs_e4db6c96: perf_stat.cycles=1113428526
- obs_e7bae6ce: perf_stat.instructions=4401126660
- obs_09b17088: perf_stat.seconds=0.073382999
- obs_566771a8: perf_stat.context_switches=7
- obs_99aee510: perf_stat.cpu_migrations=2
- obs_a780e5db: perf_stat.page_faults=290
- obs_0859da84: perf_stat.lock_loads=23035
- obs_cc9041eb: perf_stat.seconds=0.074237642
- obs_bdb34a16: mpstat.01=25:03     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_d918c8f2: mpstat.01=25:04     all    0.45    0.00    0.35    0.05    0.00    0.00    0.00    0.00    0.00   99.15
- obs_a11ec411: mpstat.average=all    0.45    0.00    0.35    0.05    0.00    0.00    0.00    0.00    0.00   99.15
- obs_9d8c7913: perf_record.hot_symbol_pct=99.1
- obs_19ceec47: perf_record.hot_symbol_pct=99.1
- obs_ad856bb3: perf_record.hot_symbol_pct=99.1
- obs_ea574412: perf_record.hot_symbol_pct=90.02
- obs_47fa2a53: perf_record.hot_symbol_pct=41.51
- obs_8257a020: perf_record.hot_symbol_pct=36.96
- obs_06af269d: perf_record.hot_symbol_pct=5.59
- obs_b52ba4f8: perf_record.hot_symbol_pct=2.15
- obs_77e1bf15: perf_record.callgraph_samples=847
- obs_07d54847: perf_record.process_sample_count=280
- obs_9c240828: perf_record.process_sample_pct=33.2937
- obs_d7b85708: perf_record.process_sample_count=280
- obs_16a4446f: perf_record.process_sample_pct=33.2937
- obs_be1c8613: perf_record.process_sample_count=279
- obs_e6758c7c: perf_record.process_sample_pct=33.1748
- obs_b45d5d9c: perf_record.process_sample_count=2
- obs_3cb6827d: perf_record.process_sample_pct=0.2378
- obs_36644aab: perf_record.thread_sample_count=280
- obs_97df1246: perf_record.thread_sample_pct=33.2937
- obs_d6c2bc4a: perf_record.thread_sample_count=280
- obs_33562ada: perf_record.thread_sample_pct=33.2937
- obs_f14c0b2d: perf_record.thread_sample_count=279
- obs_4213eeac: perf_record.thread_sample_pct=33.1748
- obs_7ece7392: perf_record.thread_sample_count=2
- obs_e5ba5bce: perf_record.thread_sample_pct=0.2378
- obs_e11f15dc: perf_record.hot_frame_sample_pct=1.432
- obs_47b92f61: perf_record.hot_frame_sample_pct=1.074
- obs_b864e60e: perf_record.hot_frame_sample_pct=0.9547
- obs_097d5fbe: perf_record.hot_frame_sample_pct=0.9547
- obs_474be801: perf_record.hot_frame_sample_pct=0.9547
- obs_e2b27100: perf_record.hot_frame_sample_pct=0.9547
- obs_f83f2890: perf_record.hot_frame_sample_pct=0.9547
- obs_00546e33: perf_record.hot_frame_sample_pct=0.9547
- obs_5018d86c: perf_record.hot_frame_sample_pct=0.8353
- obs_e258d19d: perf_record.hot_frame_sample_pct=0.8353
- obs_1bc5bc7e: perf_stat.cycles=1113318481
- obs_1156172b: perf_stat.instructions=4401028299
- obs_a402f9dd: perf_stat.cache_misses=31999
- obs_87fa1251: perf_stat.context_switches=10

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.95
- 支持证据: obs_21282e3b, obs_9c240828, obs_16a4446f, obs_e6758c7c, obs_3cb6827d, obs_97df1246, obs_33562ada, obs_4213eeac, obs_e5ba5bce
- 反证: 无
- 验证状态: 证据基本充分

## 8. 源码定位
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:18
- 依据: perf record 样本中 main 占 0.84%，地址 0x2be6 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.01
```cpp
  16 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  17 |             const double x = static_cast<double>((round + seed + 3) * (i + 11));
  18 |             checksum += std::sin(x) * std::cos(x / 7.0) + std::sqrt(x + 29.0);
  19 |         }
  20 |     }
```
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:18
- 依据: perf record 样本中 main 占 0.84%，地址 0x2b68 通过 addr2line 映射到该源码位置。
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
- act_83ff242a: /usr/bin/time / 运行时基线 [done]
- act_89ecddc7: perf stat / 指令效率 [done]
- act_6c4366fa: perf stat / 缓存与内存压力 [done]
- act_615078b5: perf stat / 前后端停顿 [done]
- act_c4fb118e: perf stat / 调度上下文 [done]
- act_bc18f595: pidstat / 调度上下文 [done]
- act_95e422ac: mpstat / 调度上下文 [done]
- act_f3702f49: perf record / 热点函数调用链 [done]
- act_ff746f44: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=296
- CPU 瓶颈: perf_record.process_sample_pct=33.2937
- CPU 瓶颈: perf_record.process_sample_pct=33.2937
- CPU 瓶颈: perf_record.process_sample_pct=33.1748
- CPU 瓶颈: perf_record.process_sample_pct=0.2378
- CPU 瓶颈: perf_record.thread_sample_pct=33.2937
- CPU 瓶颈: perf_record.thread_sample_pct=33.2937
- CPU 瓶颈: perf_record.thread_sample_pct=33.1748
- CPU 瓶颈: perf_record.thread_sample_pct=0.2378

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_02d5dba8/artifacts/act_615078b5.json
- runs/run_02d5dba8/artifacts/act_615078b5.stderr.txt
- runs/run_02d5dba8/artifacts/act_615078b5.stdout.txt
- runs/run_02d5dba8/artifacts/act_6c4366fa.json
- runs/run_02d5dba8/artifacts/act_6c4366fa.stderr.txt
- runs/run_02d5dba8/artifacts/act_6c4366fa.stdout.txt
- runs/run_02d5dba8/artifacts/act_83ff242a.json
- runs/run_02d5dba8/artifacts/act_83ff242a.stderr.txt
- runs/run_02d5dba8/artifacts/act_83ff242a.stdout.txt
- runs/run_02d5dba8/artifacts/act_89ecddc7.json
- runs/run_02d5dba8/artifacts/act_89ecddc7.stderr.txt
- runs/run_02d5dba8/artifacts/act_89ecddc7.stdout.txt
- runs/run_02d5dba8/artifacts/act_95e422ac.json
- runs/run_02d5dba8/artifacts/act_95e422ac.stdout.txt
- runs/run_02d5dba8/artifacts/act_bc18f595.json
- runs/run_02d5dba8/artifacts/act_bc18f595.stdout.txt
- runs/run_02d5dba8/artifacts/act_c4fb118e.json
- runs/run_02d5dba8/artifacts/act_c4fb118e.stderr.txt
- runs/run_02d5dba8/artifacts/act_c4fb118e.stdout.txt
- runs/run_02d5dba8/artifacts/act_f3702f49.json
- runs/run_02d5dba8/artifacts/act_f3702f49.perf.data
- runs/run_02d5dba8/artifacts/act_f3702f49.record.stdout.txt
- runs/run_02d5dba8/artifacts/act_f3702f49.script.txt
- runs/run_02d5dba8/artifacts/act_f3702f49.stderr.txt
- runs/run_02d5dba8/artifacts/act_f3702f49.stdout.txt
- runs/run_02d5dba8/artifacts/act_ff746f44.json
- runs/run_02d5dba8/artifacts/act_ff746f44.stderr.txt
- runs/run_02d5dba8/artifacts/act_ff746f44.stdout.txt
- runs/run_02d5dba8/artifacts/perf_list.txt
- runs/run_02d5dba8/environment.json
- runs/run_02d5dba8/source_manifest.json
- runs/run_02d5dba8/target.json
