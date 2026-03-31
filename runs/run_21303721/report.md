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
- 第 1 轮 [baseline] perf stat / 缓存与内存压力: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 topdown-be-bound, cache-references, cache-misses, longest_lat_cache.miss, l2_rqsts.miss, mem_load_completed.l1_miss_any。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 前后端停顿: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 SLOTS, topdown-retiring, topdown-bad-spec, topdown-fe-bound, topdown-be-bound, cycles, Instructions。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用首选事件组合。 事件为 context-switches, cpu-migrations, page-faults, mem_inst_retired.lock_loads。
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 1 轮 [baseline] iostat / I/O 等待: 用 iostat 看设备利用率和等待延迟。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。
- 第 2 轮 [verification] perf stat / 时间序列行为: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 6 个，时间序列指标 4 个，进程拆账 1 条，线程拆账 5 条。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, hot_symbol_pct
- 热点符号: clone3, start_thread, std::thread::_State_impl<std::thread::_Invoker<std::tuple<main::{lambda()#1}> > >::_M_run, __cos_fma, __sin_fma
- 时间序列指标: cache_misses, context_switches, cycles, instructions
- 进程级样本拆账: multithread_cpu pid=70 100.00%
- 线程级样本拆账: multithread_cpu pid/tid=70/74 25.11%, multithread_cpu pid/tid=70/75 25.11%, multithread_cpu pid/tid=70/72 24.89%, multithread_cpu pid/tid=70/73 24.74%
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在并发工作函数入口，建议结合热点和调度证据一起判断线程或子进程的贡献。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_adbe2cae: time.user_time_sec=0.34
- obs_7ebb188d: time.system_time_sec=0.0
- obs_259e2359: time.cpu_utilization_pct=398
- obs_ce3b1d13: time.max_rss_kb=4000
- obs_705f4c02: time.major_faults=0
- obs_18f60477: time.voluntary_context_switches=22
- obs_f242797c: time.involuntary_context_switches=5
- obs_f33b2b15: time.elapsed_time_sec=0.08
- obs_70f4f519: perf_stat.cycles=1755336932
- obs_b197a651: perf_stat.instructions=6719383605
- obs_a040bfd6: perf_stat.msec=344.13
- obs_5236ab9f: perf_stat.slots=10499414778
- obs_f1917b9d: perf_stat.seconds=0.086765805
- obs_eba59020: perf_stat.cache_references=145565
- obs_0875413e: perf_stat.cache_misses=38116
- obs_b1cbb456: perf_stat.llc_miss_count=38116
- obs_b848fb95: perf_stat.l2_miss_count=166389
- obs_6cf80e38: perf_stat.l1_miss_count=150048
- obs_66976ec3: perf_stat.seconds=0.087026678
- obs_f40d751c: perf_stat.slots=10504369062
- obs_fe46d904: perf_stat.cycles=1751854488
- obs_65379fc0: perf_stat.instructions=6719473577
- obs_f503ca86: perf_stat.seconds=0.086564924
- obs_0639e85b: perf_stat.context_switches=35
- obs_617ce98d: perf_stat.cpu_migrations=4
- obs_a88b8baa: perf_stat.page_faults=293
- obs_d8f951de: perf_stat.lock_loads=14419
- obs_0b57f815: perf_stat.seconds=0.087044899
- obs_689207ca: mpstat.03=06:34     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_619fa8d6: mpstat.03=06:35     all    0.30    0.00    0.35    0.10    0.00    0.05    0.00    0.00    0.00   99.20
- obs_b81f2aee: mpstat.average=all    0.30    0.00    0.35    0.10    0.00    0.05    0.00    0.00    0.00   99.20
- obs_766349b3: perf_record.hot_symbol_pct=99.55
- obs_d0f7a019: perf_record.hot_symbol_pct=99.42
- obs_352bcc80: perf_record.hot_symbol_pct=99.42
- obs_9867af9c: perf_record.hot_symbol_pct=94.97
- obs_f81f5157: perf_record.hot_symbol_pct=48.68
- obs_030f5105: perf_record.hot_symbol_pct=36.47
- obs_0a4bec24: perf_record.hot_symbol_pct=1.94
- obs_498c4b59: perf_record.hot_symbol_pct=1.62
- obs_55bec6f8: perf_record.callgraph_samples=1344
- obs_21e9113e: perf_record.process_sample_count=1338
- obs_d1f64327: perf_record.process_sample_pct=100.0
- obs_96c7bd77: perf_record.thread_sample_count=336
- obs_cd34e333: perf_record.thread_sample_pct=25.1121
- obs_68ec1862: perf_record.thread_sample_count=336
- obs_5fe041e2: perf_record.thread_sample_pct=25.1121
- obs_d079e1a3: perf_record.thread_sample_count=333
- obs_25a950ee: perf_record.thread_sample_pct=24.8879
- obs_3f18ba96: perf_record.thread_sample_count=331
- obs_3f304e85: perf_record.thread_sample_pct=24.7384
- obs_36b5e73e: perf_record.thread_sample_count=2
- obs_59397aa1: perf_record.thread_sample_pct=0.1495
- obs_1db7cd55: perf_record.hot_frame_sample_pct=3.8893
- obs_21e871bf: perf_record.hot_frame_sample_pct=0.8975
- obs_e5f1b1e0: perf_record.hot_frame_sample_pct=0.7479
- obs_344c1061: perf_record.hot_frame_sample_pct=0.7479
- obs_4af0a324: perf_record.hot_frame_sample_pct=0.6731
- obs_05b5224a: perf_record.hot_frame_sample_pct=0.6731
- obs_4793831e: perf_record.hot_frame_sample_pct=0.6731
- obs_acd877d6: perf_record.hot_frame_sample_pct=0.6731
- obs_7f2cb153: perf_record.hot_frame_sample_pct=0.5984
- obs_b1782406: perf_record.hot_frame_sample_pct=0.5984
- obs_b5786387: perf_stat.cycles=1757613838
- obs_a7674544: perf_stat.instructions=6719381984
- obs_6c56528c: perf_stat.cache_misses=42384
- obs_3c860b64: perf_stat.context_switches=27

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.95
- 支持证据: obs_259e2359, obs_d1f64327, obs_cd34e333, obs_5fe041e2, obs_25a950ee, obs_3f304e85, obs_59397aa1
- 反证: 无
- 验证状态: 证据基本充分

## 8. 源码定位
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/multithread_cpu_demo.cpp:14
- 依据: perf record 样本中 std::thread::_State_impl<std::thread::_Invoker<std::tuple<main::{lambda()#1}> > >::_M_run 占 0.75%，地址 0x2e72 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.01
```cpp
  12 |     for (std::size_t round = 0; round < outer_loops; ++round) {
  13 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  14 |             const double x = static_cast<double>((round + seed + 1) * (i + 7));
  15 |             values[i] = std::sin(x) + std::cos(x / 5.0) + std::sqrt(x + 17.0);
  16 |             checksum += values[i];
```
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/multithread_cpu_demo.cpp:15
- 依据: perf record 样本中 std::thread::_State_impl<std::thread::_Invoker<std::tuple<main::{lambda()#1}> > >::_M_run 占 0.67%，地址 0x2e1d 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.01
```cpp
  13 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  14 |             const double x = static_cast<double>((round + seed + 1) * (i + 7));
  15 |             values[i] = std::sin(x) + std::cos(x / 5.0) + std::sqrt(x + 17.0);
  16 |             checksum += values[i];
  17 |         }
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
### 大规模向量处理: /home/tchen/agent/perf_agent/examples/cpp/multithread_cpu_demo.cpp:10
- 依据: 检测到可能参与高频数据处理的容器代码。
- 映射方式: heuristic
- 置信度: 0.35
```cpp
   8 | 
   9 | double worker(std::size_t outer_loops, std::size_t inner_loops, std::size_t seed) {
  10 |     std::vector<double> values(inner_loops, 0.0);
  11 |     double checksum = 0.0;
  12 |     for (std::size_t round = 0; round < outer_loops; ++round) {
```

## 9. 二次验证
- 已执行动作:
- act_9e998ca6: /usr/bin/time / 运行时基线 [done]
- act_a12b5cb6: perf stat / 指令效率 [done]
- act_40f9fb4c: perf stat / 缓存与内存压力 [done]
- act_7530acd8: perf stat / 前后端停顿 [done]
- act_19efdd71: perf stat / 调度上下文 [done]
- act_7dbee3a1: pidstat / 调度上下文 [done]
- act_9e9ae6ae: mpstat / 调度上下文 [done]
- act_590b7d7a: iostat / I/O 等待 [done]
- act_f11bbe94: perf record / 热点函数调用链 [done]
- act_a9b2a591: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=398
- CPU 瓶颈: perf_record.process_sample_pct=100.0
- CPU 瓶颈: perf_record.thread_sample_pct=25.1121
- CPU 瓶颈: perf_record.thread_sample_pct=25.1121
- CPU 瓶颈: perf_record.thread_sample_pct=24.8879
- CPU 瓶颈: perf_record.thread_sample_pct=24.7384
- CPU 瓶颈: perf_record.thread_sample_pct=0.1495

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_21303721/artifacts/act_19efdd71.json
- runs/run_21303721/artifacts/act_19efdd71.stderr.txt
- runs/run_21303721/artifacts/act_19efdd71.stdout.txt
- runs/run_21303721/artifacts/act_40f9fb4c.json
- runs/run_21303721/artifacts/act_40f9fb4c.stderr.txt
- runs/run_21303721/artifacts/act_40f9fb4c.stdout.txt
- runs/run_21303721/artifacts/act_590b7d7a.json
- runs/run_21303721/artifacts/act_590b7d7a.stdout.txt
- runs/run_21303721/artifacts/act_7530acd8.json
- runs/run_21303721/artifacts/act_7530acd8.stderr.txt
- runs/run_21303721/artifacts/act_7530acd8.stdout.txt
- runs/run_21303721/artifacts/act_7dbee3a1.json
- runs/run_21303721/artifacts/act_7dbee3a1.stdout.txt
- runs/run_21303721/artifacts/act_9e998ca6.json
- runs/run_21303721/artifacts/act_9e998ca6.stderr.txt
- runs/run_21303721/artifacts/act_9e998ca6.stdout.txt
- runs/run_21303721/artifacts/act_9e9ae6ae.json
- runs/run_21303721/artifacts/act_9e9ae6ae.stdout.txt
- runs/run_21303721/artifacts/act_a12b5cb6.json
- runs/run_21303721/artifacts/act_a12b5cb6.stderr.txt
- runs/run_21303721/artifacts/act_a12b5cb6.stdout.txt
- runs/run_21303721/artifacts/act_a9b2a591.json
- runs/run_21303721/artifacts/act_a9b2a591.stderr.txt
- runs/run_21303721/artifacts/act_a9b2a591.stdout.txt
- runs/run_21303721/artifacts/act_f11bbe94.json
- runs/run_21303721/artifacts/act_f11bbe94.perf.data
- runs/run_21303721/artifacts/act_f11bbe94.record.stdout.txt
- runs/run_21303721/artifacts/act_f11bbe94.script.txt
- runs/run_21303721/artifacts/act_f11bbe94.stderr.txt
- runs/run_21303721/artifacts/act_f11bbe94.stdout.txt
- runs/run_21303721/artifacts/perf_list.txt
- runs/run_21303721/environment.json
- runs/run_21303721/source_manifest.json
- runs/run_21303721/target.json
