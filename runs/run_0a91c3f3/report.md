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
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 8 个，时间序列指标 4 个，进程拆账 4 条，线程拆账 4 条。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, hot_symbol_pct
- 热点符号: _start, __libc_start_main@@GLIBC_2.34, __libc_start_call_main, main, __cos_fma
- 时间序列指标: cache_misses, context_switches, cycles, instructions
- 进程级样本拆账: multiprocess_fa pid=3619344 33.33%, multiprocess_fa pid=3619343 33.21%, multiprocess_fa pid=3619345 33.21%, multiprocess_fa pid=3619341 0.24%
- 线程级样本拆账: multiprocess_fa pid/tid=3619344/3619344 33.33%, multiprocess_fa pid/tid=3619343/3619343 33.21%, multiprocess_fa pid/tid=3619345/3619345 33.21%, multiprocess_fa pid/tid=3619341/3619341 0.24%
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在并发工作函数入口，建议结合热点和调度证据一起判断线程或子进程的贡献。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_7be6582f: time.user_time_sec=0.22
- obs_73a4e4e7: time.system_time_sec=0.0
- obs_7068adcc: time.cpu_utilization_pct=298
- obs_f49534ec: time.max_rss_kb=4000
- obs_0b550937: time.major_faults=0
- obs_12eaeb83: time.voluntary_context_switches=6
- obs_f93983e4: time.involuntary_context_switches=4
- obs_9394bbb9: time.elapsed_time_sec=0.07
- obs_0980e945: perf_stat.cycles=1113080987
- obs_560122b4: perf_stat.instructions=4401037763
- obs_67399354: perf_stat.msec=218.21
- obs_f86a7d64: perf_stat.slots=6676540212
- obs_32f2ba31: perf_stat.seconds=0.073274895
- obs_19c74ce2: perf_stat.cache_references=128080
- obs_660818f3: perf_stat.cache_misses=25218
- obs_0fc1420e: perf_stat.llc_miss_count=25218
- obs_82bcacb9: perf_stat.l2_miss_count=134900
- obs_13a67a72: perf_stat.l1_miss_count=170862
- obs_2c7674d6: perf_stat.seconds=0.073348276
- obs_89a10198: perf_stat.slots=6674840652
- obs_5f8013dc: perf_stat.cycles=1113096897
- obs_0fde8fc3: perf_stat.instructions=4401145491
- obs_498349b0: perf_stat.seconds=0.073399077
- obs_fc29e82b: perf_stat.context_switches=6
- obs_95deab32: perf_stat.cpu_migrations=4
- obs_923198e7: perf_stat.page_faults=292
- obs_d5cb4656: perf_stat.lock_loads=23281
- obs_8a2272e3: perf_stat.seconds=0.073253259
- obs_aaeb1a20: mpstat.01=20:48     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_7a4011b1: mpstat.01=20:49     all    0.15    0.00    0.00    0.10    0.00    0.00    0.00    0.00    0.00   99.75
- obs_5d28b400: mpstat.average=all    0.15    0.00    0.00    0.10    0.00    0.00    0.00    0.00    0.00   99.75
- obs_274bb414: perf_record.hot_symbol_pct=99.3
- obs_fc28832f: perf_record.hot_symbol_pct=99.3
- obs_36a9e7d2: perf_record.hot_symbol_pct=99.3
- obs_ff094989: perf_record.hot_symbol_pct=91.29
- obs_74cfeb99: perf_record.hot_symbol_pct=42.89
- obs_181d91e3: perf_record.hot_symbol_pct=38.95
- obs_00b702e2: perf_record.hot_symbol_pct=4.37
- obs_ec55b650: perf_record.hot_symbol_pct=3.06
- obs_cf8364d1: perf_record.callgraph_samples=849
- obs_e320e695: perf_record.process_sample_count=281
- obs_b4f0f695: perf_record.process_sample_pct=33.3333
- obs_e97d1d88: perf_record.process_sample_count=280
- obs_c1e92f02: perf_record.process_sample_pct=33.2147
- obs_c3ddca2d: perf_record.process_sample_count=280
- obs_6941e8ad: perf_record.process_sample_pct=33.2147
- obs_a9568e69: perf_record.process_sample_count=2
- obs_94044e23: perf_record.process_sample_pct=0.2372
- obs_8949acbf: perf_record.thread_sample_count=281
- obs_98cba160: perf_record.thread_sample_pct=33.3333
- obs_c4a25108: perf_record.thread_sample_count=280
- obs_9f115ccf: perf_record.thread_sample_pct=33.2147
- obs_05882b46: perf_record.thread_sample_count=280
- obs_10187876: perf_record.thread_sample_pct=33.2147
- obs_f77d3d31: perf_record.thread_sample_count=2
- obs_dcf9977e: perf_record.thread_sample_pct=0.2372
- obs_5d540f9e: perf_record.hot_frame_sample_pct=1.1876
- obs_fdbb536e: perf_record.hot_frame_sample_pct=1.1876
- obs_de447424: perf_record.hot_frame_sample_pct=1.0689
- obs_e2af7a8e: perf_record.hot_frame_sample_pct=1.0689
- obs_4aed1878: perf_record.hot_frame_sample_pct=0.9501
- obs_d880f7fb: perf_record.hot_frame_sample_pct=0.8314
- obs_73a8330a: perf_record.hot_frame_sample_pct=0.8314
- obs_312e1a75: perf_record.hot_frame_sample_pct=0.8314
- obs_37a05f93: perf_record.hot_frame_sample_pct=0.8314
- obs_28b06b2d: perf_record.hot_frame_sample_pct=0.8314
- obs_719cc27c: perf_stat.cycles=1113662675
- obs_925748e9: perf_stat.instructions=4401087862
- obs_480749fb: perf_stat.cache_misses=34624
- obs_e1d10f16: perf_stat.context_switches=6

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.95
- 支持证据: obs_7068adcc, obs_b4f0f695, obs_c1e92f02, obs_6941e8ad, obs_94044e23, obs_98cba160, obs_9f115ccf, obs_10187876, obs_dcf9977e
- 反证: 无
- 验证状态: 证据基本充分

## 8. 源码定位
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
- act_06f5c2cb: /usr/bin/time / 运行时基线 [done]
- act_780318dc: perf stat / 指令效率 [done]
- act_31ae27f8: perf stat / 缓存与内存压力 [done]
- act_f46742b2: perf stat / 前后端停顿 [done]
- act_7872a13e: perf stat / 调度上下文 [done]
- act_a874b793: pidstat / 调度上下文 [done]
- act_cf1d1047: mpstat / 调度上下文 [done]
- act_a2352031: perf record / 热点函数调用链 [done]
- act_9020dc93: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=298
- CPU 瓶颈: perf_record.process_sample_pct=33.3333
- CPU 瓶颈: perf_record.process_sample_pct=33.2147
- CPU 瓶颈: perf_record.process_sample_pct=33.2147
- CPU 瓶颈: perf_record.process_sample_pct=0.2372
- CPU 瓶颈: perf_record.thread_sample_pct=33.3333
- CPU 瓶颈: perf_record.thread_sample_pct=33.2147
- CPU 瓶颈: perf_record.thread_sample_pct=33.2147
- CPU 瓶颈: perf_record.thread_sample_pct=0.2372

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_0a91c3f3/artifacts/act_06f5c2cb.json
- runs/run_0a91c3f3/artifacts/act_06f5c2cb.stderr.txt
- runs/run_0a91c3f3/artifacts/act_06f5c2cb.stdout.txt
- runs/run_0a91c3f3/artifacts/act_31ae27f8.json
- runs/run_0a91c3f3/artifacts/act_31ae27f8.stderr.txt
- runs/run_0a91c3f3/artifacts/act_31ae27f8.stdout.txt
- runs/run_0a91c3f3/artifacts/act_780318dc.json
- runs/run_0a91c3f3/artifacts/act_780318dc.stderr.txt
- runs/run_0a91c3f3/artifacts/act_780318dc.stdout.txt
- runs/run_0a91c3f3/artifacts/act_7872a13e.json
- runs/run_0a91c3f3/artifacts/act_7872a13e.stderr.txt
- runs/run_0a91c3f3/artifacts/act_7872a13e.stdout.txt
- runs/run_0a91c3f3/artifacts/act_9020dc93.json
- runs/run_0a91c3f3/artifacts/act_9020dc93.stderr.txt
- runs/run_0a91c3f3/artifacts/act_9020dc93.stdout.txt
- runs/run_0a91c3f3/artifacts/act_a2352031.json
- runs/run_0a91c3f3/artifacts/act_a2352031.perf.data
- runs/run_0a91c3f3/artifacts/act_a2352031.record.stdout.txt
- runs/run_0a91c3f3/artifacts/act_a2352031.script.txt
- runs/run_0a91c3f3/artifacts/act_a2352031.stderr.txt
- runs/run_0a91c3f3/artifacts/act_a2352031.stdout.txt
- runs/run_0a91c3f3/artifacts/act_a874b793.json
- runs/run_0a91c3f3/artifacts/act_a874b793.stdout.txt
- runs/run_0a91c3f3/artifacts/act_cf1d1047.json
- runs/run_0a91c3f3/artifacts/act_cf1d1047.stdout.txt
- runs/run_0a91c3f3/artifacts/act_f46742b2.json
- runs/run_0a91c3f3/artifacts/act_f46742b2.stderr.txt
- runs/run_0a91c3f3/artifacts/act_f46742b2.stdout.txt
- runs/run_0a91c3f3/artifacts/perf_list.txt
- runs/run_0a91c3f3/environment.json
- runs/run_0a91c3f3/source_manifest.json
- runs/run_0a91c3f3/target.json
