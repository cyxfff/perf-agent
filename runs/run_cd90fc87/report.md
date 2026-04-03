# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.76。

## 2. 分析目标
- 命令: examples/bin/cpu_bound_demo 700 18000
- 可执行文件: examples/bin/cpu_bound_demo
- 源码目录: examples/cpp
- 运行信息: verification_rounds=1, actions_executed=9
- 工作目录: 

## 3. 运行环境
- 架构: x86_64
- 内核: 6.2.0-37-generic
- CPU: 13th Gen Intel(R) Core(TM) i5-13600K
- 逻辑核数: 20
- perf: 可用 perf version 6.2.16
- 可用事件数: 1070
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
- 第 1 轮 [baseline] perf stat / 缓存与内存压力: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 topdown-be-bound, cache-references, cache-misses, longest_lat_cache.miss。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 前后端停顿: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 SLOTS, topdown-retiring, topdown-bad-spec, topdown-fe-bound, topdown-be-bound, cycles, Instructions。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用退化事件组合。 事件为 context-switches, cpu-migrations, page-faults。，已退化到当前机器可用方案
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。
- 第 2 轮 [verification] perf stat / 时间序列行为: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 6 个，时间序列指标 4 个，进程拆账 1 条，线程拆账 1 条。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, hot_symbol_pct
- 热点符号: _start, __libc_start_main@@GLIBC_2.34, __libc_start_call_main, main, __cos_fma
- 时间序列指标: cache_misses, context_switches, cycles, instructions
- 进程级样本拆账: cpu_bound_demo pid=3640271 100.00%
- 线程级样本拆账: cpu_bound_demo pid/tid=3640271/3640271 100.00%
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_e313ba7a: time.user_time_sec=0.14
- obs_be8a2b5b: time.system_time_sec=0.0
- obs_49504c36: time.cpu_utilization_pct=100
- obs_0dbb1716: time.max_rss_kb=4320
- obs_a0a8487d: time.major_faults=0
- obs_a6a919ac: time.voluntary_context_switches=1
- obs_de562425: time.involuntary_context_switches=1
- obs_530f294e: time.elapsed_time_sec=0.14
- obs_c35df8b4: perf_stat.cycles=761357877
- obs_8c38b8c0: perf_stat.instructions=2941583336
- obs_cba4807d: perf_stat.msec=149.26
- obs_058b45ca: perf_stat.slots=4563678792
- obs_a1c77496: perf_stat.seconds=0.149395163
- obs_e981ca39: perf_stat.cache_references=66988
- obs_da6442c1: perf_stat.cache_misses=17703
- obs_c66512f7: perf_stat.llc_miss_count=17703
- obs_8edf19ae: perf_stat.seconds=0.149325154
- obs_e3d3cfd8: perf_stat.slots=4561312680
- obs_ca40c103: perf_stat.cycles=760253894
- obs_0e90c56e: perf_stat.instructions=2941628912
- obs_cca4f6ce: perf_stat.seconds=0.149220278
- obs_fab7ec15: perf_stat.context_switches=3
- obs_f3ffbe46: perf_stat.cpu_migrations=0
- obs_b4bd3d75: perf_stat.page_faults=168
- obs_7c11ffa6: perf_stat.seconds=0.156515634
- obs_c2277ad9: mpstat.02=45:29     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_87a91437: mpstat.02=45:30     all    0.95    0.00    0.20    0.95    0.00    0.00    0.00    0.00    0.00   97.89
- obs_cdb9afcc: mpstat.average=all    0.95    0.00    0.20    0.95    0.00    0.00    0.00    0.00    0.00   97.89
- obs_d30931d1: perf_record.hot_symbol_pct=98.84
- obs_726f0e6f: perf_record.hot_symbol_pct=98.84
- obs_41f9b675: perf_record.hot_symbol_pct=98.84
- obs_a470f6f4: perf_record.hot_symbol_pct=92.8
- obs_800aa665: perf_record.hot_symbol_pct=45.58
- obs_6984e26f: perf_record.hot_symbol_pct=40.19
- obs_7c073938: perf_record.hot_symbol_pct=1.51
- obs_e53f2bf0: perf_record.hot_symbol_pct=1.5
- obs_fa0911f0: perf_record.callgraph_samples=586
- obs_0160b5ec: perf_record.process_sample_count=580
- obs_33b147b9: perf_record.process_sample_pct=100.0
- obs_1f1347e3: perf_record.thread_sample_count=580
- obs_95106edb: perf_record.thread_sample_pct=100.0
- obs_cb4eb5aa: perf_record.hot_frame_sample_pct=3.4602
- obs_7918166a: perf_record.hot_frame_sample_pct=2.2491
- obs_e50a4660: perf_record.hot_frame_sample_pct=2.0761
- obs_a4f84a61: perf_record.hot_frame_sample_pct=2.0761
- obs_1a70a613: perf_record.hot_frame_sample_pct=2.0761
- obs_d96aecdc: perf_record.hot_frame_sample_pct=1.9031
- obs_73dbd44c: perf_record.hot_frame_sample_pct=1.9031
- obs_97bbb83e: perf_record.hot_frame_sample_pct=1.9031
- obs_c913821b: perf_record.hot_frame_sample_pct=1.9031
- obs_d0823236: perf_record.hot_frame_sample_pct=1.9031
- obs_6138da16: perf_stat.cycles=510162067
- obs_60a9458f: perf_stat.instructions=1971243423
- obs_398915c6: perf_stat.cache_misses=23419
- obs_0d519ccf: perf_stat.context_switches=1
- obs_94b53cc9: perf_stat.cycles=250829476
- obs_8a8ea0cb: perf_stat.instructions=970396857
- obs_dcbaab5c: perf_stat.cache_misses=6776
- obs_c5de540c: perf_stat.context_switches=0

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.76
- 支持证据: obs_49504c36, obs_33b147b9, obs_95106edb
- 反证: 无
- 验证状态: 需要进一步验证

## 8. 源码定位
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:14
- 依据: perf record 样本中 main 占 2.08%，地址 0x143d 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.02
```cpp
  12 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  13 |             const double x = static_cast<double>((round + 1) * (i + 3));
  14 |             values[i] = std::sin(x) * std::cos(x / 3.0) + std::sqrt(x + 11.0);
  15 |             checksum += values[i];
  16 |         }
```
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:13
- 依据: perf record 样本中 main 占 1.90%，地址 0x1430 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.02
```cpp
  11 |     for (std::size_t round = 0; round < outer_loops; ++round) {
  12 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  13 |             const double x = static_cast<double>((round + 1) * (i + 3));
  14 |             values[i] = std::sin(x) * std::cos(x / 3.0) + std::sqrt(x + 11.0);
  15 |             checksum += values[i];
```
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:14
- 依据: perf record 样本中 main 占 1.90%，地址 0x1463 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.02
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
- act_76612cdc: /usr/bin/time / 运行时基线 [done]
- act_29e9da50: perf stat / 指令效率 [done]
- act_797b3f84: perf stat / 缓存与内存压力 [done]
- act_26fd339b: perf stat / 前后端停顿 [done]
- act_9cb4db4f: perf stat / 调度上下文 [done]
- act_f18a4123: pidstat / 调度上下文 [done]
- act_16a552ab: mpstat / 调度上下文 [done]
- act_e931cfe2: perf record / 热点函数调用链 [done]
- act_eec314c8: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=100
- CPU 瓶颈: perf_record.process_sample_pct=100.0
- CPU 瓶颈: perf_record.thread_sample_pct=100.0

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_cd90fc87/artifacts/act_16a552ab.json
- runs/run_cd90fc87/artifacts/act_16a552ab.stdout.txt
- runs/run_cd90fc87/artifacts/act_26fd339b.json
- runs/run_cd90fc87/artifacts/act_26fd339b.stderr.txt
- runs/run_cd90fc87/artifacts/act_26fd339b.stdout.txt
- runs/run_cd90fc87/artifacts/act_29e9da50.json
- runs/run_cd90fc87/artifacts/act_29e9da50.stderr.txt
- runs/run_cd90fc87/artifacts/act_29e9da50.stdout.txt
- runs/run_cd90fc87/artifacts/act_76612cdc.json
- runs/run_cd90fc87/artifacts/act_76612cdc.stderr.txt
- runs/run_cd90fc87/artifacts/act_76612cdc.stdout.txt
- runs/run_cd90fc87/artifacts/act_797b3f84.json
- runs/run_cd90fc87/artifacts/act_797b3f84.stderr.txt
- runs/run_cd90fc87/artifacts/act_797b3f84.stdout.txt
- runs/run_cd90fc87/artifacts/act_9cb4db4f.json
- runs/run_cd90fc87/artifacts/act_9cb4db4f.stderr.txt
- runs/run_cd90fc87/artifacts/act_9cb4db4f.stdout.txt
- runs/run_cd90fc87/artifacts/act_e931cfe2.json
- runs/run_cd90fc87/artifacts/act_e931cfe2.perf.data
- runs/run_cd90fc87/artifacts/act_e931cfe2.record.stdout.txt
- runs/run_cd90fc87/artifacts/act_e931cfe2.script.txt
- runs/run_cd90fc87/artifacts/act_e931cfe2.stderr.txt
- runs/run_cd90fc87/artifacts/act_e931cfe2.stdout.txt
- runs/run_cd90fc87/artifacts/act_eec314c8.json
- runs/run_cd90fc87/artifacts/act_eec314c8.stderr.txt
- runs/run_cd90fc87/artifacts/act_eec314c8.stdout.txt
- runs/run_cd90fc87/artifacts/act_f18a4123.json
- runs/run_cd90fc87/artifacts/act_f18a4123.stdout.txt
- runs/run_cd90fc87/artifacts/perf_list.txt
- runs/run_cd90fc87/environment.json
- runs/run_cd90fc87/source_manifest.json
- runs/run_cd90fc87/target.json
