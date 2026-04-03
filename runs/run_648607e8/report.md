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
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 9 个，时间序列指标 4 个，进程拆账 4 条，线程拆账 4 条。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, hot_symbol_pct
- 热点符号: _start, __libc_start_main@@GLIBC_2.34, __libc_start_call_main, main, __cos_fma
- 时间序列指标: cache_misses, context_switches, cycles, instructions
- 进程级样本拆账: multiprocess_fa pid=3619067 33.37%, multiprocess_fa pid=3619069 33.25%, multiprocess_fa pid=3619068 33.14%, multiprocess_fa pid=3619065 0.24%
- 线程级样本拆账: multiprocess_fa pid/tid=3619067/3619067 33.37%, multiprocess_fa pid/tid=3619069/3619069 33.25%, multiprocess_fa pid/tid=3619068/3619068 33.14%, multiprocess_fa pid/tid=3619065/3619065 0.24%
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在并发工作函数入口，建议结合热点和调度证据一起判断线程或子进程的贡献。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_4a413d64: time.user_time_sec=0.23
- obs_312a95aa: time.system_time_sec=0.0
- obs_5ac59fd0: time.cpu_utilization_pct=293
- obs_f719aaec: time.max_rss_kb=4000
- obs_7400aa67: time.major_faults=0
- obs_2818c25a: time.voluntary_context_switches=6
- obs_4a99243c: time.involuntary_context_switches=15
- obs_5b631223: time.elapsed_time_sec=0.08
- obs_497b6d8e: perf_stat.cycles=1113798369
- obs_e5c34a87: perf_stat.instructions=4401146961
- obs_2374e509: perf_stat.msec=224.42
- obs_6329443e: perf_stat.slots=6677578356
- obs_a54e845c: perf_stat.seconds=0.07543367
- obs_cd4798c9: perf_stat.cache_references=147463
- obs_d77c2d81: perf_stat.cache_misses=27135
- obs_05fbb5f2: perf_stat.llc_miss_count=27135
- obs_4637b0ae: perf_stat.l2_miss_count=156110
- obs_cf7134bc: perf_stat.l1_miss_count=161845
- obs_28423b2f: perf_stat.seconds=0.07335833
- obs_7641d98f: perf_stat.slots=6682465668
- obs_dc9959b9: perf_stat.cycles=1113878817
- obs_08dfcf8b: perf_stat.instructions=4401125833
- obs_a1649557: perf_stat.seconds=0.073411477
- obs_c9c816fb: perf_stat.context_switches=8
- obs_075e0985: perf_stat.cpu_migrations=3
- obs_47a3b456: perf_stat.page_faults=288
- obs_3dde2c91: perf_stat.lock_loads=22883
- obs_44c22fad: perf_stat.seconds=0.073301007
- obs_442b0fa3: mpstat.01=22:47     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_35d35a9c: mpstat.01=22:48     all    0.10    0.00    0.05    0.10    0.00    0.00    0.00    0.00    0.00   99.75
- obs_67b1bc5c: mpstat.average=all    0.10    0.00    0.05    0.10    0.00    0.00    0.00    0.00    0.00   99.75
- obs_1bce8f14: perf_record.hot_symbol_pct=99.3
- obs_c176cff6: perf_record.hot_symbol_pct=99.3
- obs_56842c4a: perf_record.hot_symbol_pct=99.3
- obs_2376d10b: perf_record.hot_symbol_pct=90.62
- obs_e6c59367: perf_record.hot_symbol_pct=43.79
- obs_48f1c936: perf_record.hot_symbol_pct=37.38
- obs_7c49fd80: perf_record.hot_symbol_pct=4.6
- obs_6e7be5fd: perf_record.hot_symbol_pct=2.87
- obs_8a83aa37: perf_record.callgraph_samples=848
- obs_df051f2f: perf_record.process_sample_count=281
- obs_323a1b97: perf_record.process_sample_pct=33.3729
- obs_8e28cb95: perf_record.process_sample_count=280
- obs_3e3476aa: perf_record.process_sample_pct=33.2542
- obs_ca99d975: perf_record.process_sample_count=279
- obs_137cdfc9: perf_record.process_sample_pct=33.1354
- obs_1f0528eb: perf_record.process_sample_count=2
- obs_359d10ab: perf_record.process_sample_pct=0.2375
- obs_5c1f4932: perf_record.thread_sample_count=281
- obs_43fc3d88: perf_record.thread_sample_pct=33.3729
- obs_9014ab1b: perf_record.thread_sample_count=280
- obs_b62f1b6b: perf_record.thread_sample_pct=33.2542
- obs_5467791b: perf_record.thread_sample_count=279
- obs_01cb7e56: perf_record.thread_sample_pct=33.1354
- obs_25f76bfa: perf_record.thread_sample_count=2
- obs_aad50c5b: perf_record.thread_sample_pct=0.2375
- obs_fec0cda6: perf_record.hot_frame_sample_pct=1.1891
- obs_cafd4f62: perf_record.hot_frame_sample_pct=1.1891
- obs_054f69bf: perf_record.hot_frame_sample_pct=1.1891
- obs_744a1b1c: perf_record.hot_frame_sample_pct=1.0702
- obs_944dfced: perf_record.hot_frame_sample_pct=0.9512
- obs_161b684e: perf_record.hot_frame_sample_pct=0.9512
- obs_17936f8b: perf_record.hot_frame_sample_pct=0.8323
- obs_69ae0f08: perf_record.hot_frame_sample_pct=0.8323
- obs_b8918e48: perf_record.hot_frame_sample_pct=0.8323
- obs_2390a2f0: perf_record.hot_frame_sample_pct=0.8323
- obs_b8792970: perf_stat.cycles=1113825902
- obs_eeef9905: perf_stat.instructions=4401114376
- obs_69cd7081: perf_stat.cache_misses=33013
- obs_7c450503: perf_stat.context_switches=4

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.95
- 支持证据: obs_5ac59fd0, obs_323a1b97, obs_3e3476aa, obs_137cdfc9, obs_359d10ab, obs_43fc3d88, obs_b62f1b6b, obs_01cb7e56, obs_aad50c5b
- 反证: 无
- 验证状态: 证据基本充分

## 8. 源码定位
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:18
- 依据: perf record 样本中 main 占 0.95%，地址 0x2ba9 通过 addr2line 映射到该源码位置。
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
- act_6f305002: /usr/bin/time / 运行时基线 [done]
- act_0d5545cb: perf stat / 指令效率 [done]
- act_f291eb45: perf stat / 缓存与内存压力 [done]
- act_285c3b1f: perf stat / 前后端停顿 [done]
- act_ccea54e4: perf stat / 调度上下文 [done]
- act_77d3ea50: pidstat / 调度上下文 [done]
- act_1af8dc39: mpstat / 调度上下文 [done]
- act_5decabe9: perf record / 热点函数调用链 [done]
- act_28d52ef4: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=293
- CPU 瓶颈: perf_record.process_sample_pct=33.3729
- CPU 瓶颈: perf_record.process_sample_pct=33.2542
- CPU 瓶颈: perf_record.process_sample_pct=33.1354
- CPU 瓶颈: perf_record.process_sample_pct=0.2375
- CPU 瓶颈: perf_record.thread_sample_pct=33.3729
- CPU 瓶颈: perf_record.thread_sample_pct=33.2542
- CPU 瓶颈: perf_record.thread_sample_pct=33.1354
- CPU 瓶颈: perf_record.thread_sample_pct=0.2375

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_648607e8/artifacts/act_0d5545cb.json
- runs/run_648607e8/artifacts/act_0d5545cb.stderr.txt
- runs/run_648607e8/artifacts/act_0d5545cb.stdout.txt
- runs/run_648607e8/artifacts/act_1af8dc39.json
- runs/run_648607e8/artifacts/act_1af8dc39.stdout.txt
- runs/run_648607e8/artifacts/act_285c3b1f.json
- runs/run_648607e8/artifacts/act_285c3b1f.stderr.txt
- runs/run_648607e8/artifacts/act_285c3b1f.stdout.txt
- runs/run_648607e8/artifacts/act_28d52ef4.json
- runs/run_648607e8/artifacts/act_28d52ef4.stderr.txt
- runs/run_648607e8/artifacts/act_28d52ef4.stdout.txt
- runs/run_648607e8/artifacts/act_5decabe9.json
- runs/run_648607e8/artifacts/act_5decabe9.perf.data
- runs/run_648607e8/artifacts/act_5decabe9.record.stdout.txt
- runs/run_648607e8/artifacts/act_5decabe9.script.txt
- runs/run_648607e8/artifacts/act_5decabe9.stderr.txt
- runs/run_648607e8/artifacts/act_5decabe9.stdout.txt
- runs/run_648607e8/artifacts/act_6f305002.json
- runs/run_648607e8/artifacts/act_6f305002.stderr.txt
- runs/run_648607e8/artifacts/act_6f305002.stdout.txt
- runs/run_648607e8/artifacts/act_77d3ea50.json
- runs/run_648607e8/artifacts/act_77d3ea50.stdout.txt
- runs/run_648607e8/artifacts/act_ccea54e4.json
- runs/run_648607e8/artifacts/act_ccea54e4.stderr.txt
- runs/run_648607e8/artifacts/act_ccea54e4.stdout.txt
- runs/run_648607e8/artifacts/act_f291eb45.json
- runs/run_648607e8/artifacts/act_f291eb45.stderr.txt
- runs/run_648607e8/artifacts/act_f291eb45.stdout.txt
- runs/run_648607e8/artifacts/perf_list.txt
- runs/run_648607e8/environment.json
- runs/run_648607e8/source_manifest.json
- runs/run_648607e8/target.json
