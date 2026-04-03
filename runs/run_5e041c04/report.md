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
- CPU 配置: 物理核 14 / 逻辑核 20
- 内存: 31 GB
- CPU 频率: 800 MHz - 5.10 GHz，当前缩放 83%
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
- 第 1 轮 [baseline] perf stat / 缓存与内存压力: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 topdown-be-bound, cache-references, cache-misses, longest_lat_cache.miss。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 前后端停顿: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 SLOTS, topdown-retiring, topdown-bad-spec, topdown-fe-bound, topdown-be-bound, cycles, Instructions。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用退化事件组合。 事件为 context-switches, cpu-migrations, page-faults。，已退化到当前机器可用方案
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。
- 第 2 轮 [verification] perf stat / 时间序列行为: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 7 个，时间序列指标 4 个，进程拆账 1 条，线程拆账 1 条。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, hot_symbol_pct
- 热点符号: main
- 时间序列指标: cache_misses, context_switches, cycles, instructions
- 进程级样本拆账: cpu_bound_demo pid=3643895 100.00%
- 线程级样本拆账: cpu_bound_demo pid/tid=3643895/3643895 100.00%
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_dba9819d: time.user_time_sec=0.14
- obs_f943664d: time.system_time_sec=0.0
- obs_05e2a289: time.cpu_utilization_pct=100
- obs_b6c71cae: time.max_rss_kb=4160
- obs_bece7cbe: time.major_faults=0
- obs_cbcc536f: time.voluntary_context_switches=1
- obs_27d2aeae: time.involuntary_context_switches=1
- obs_d8ade1ed: time.elapsed_time_sec=0.14
- obs_4f9200b5: perf_stat.cycles=760511253
- obs_2660ce26: perf_stat.instructions=2941644547
- obs_4a61e4d9: perf_stat.msec=149.09
- obs_b820cfb8: perf_stat.slots=4562607786
- obs_8a33d5d6: perf_stat.seconds=0.14923545
- obs_d12ff5dd: perf_stat.cache_references=53028
- obs_fced7422: perf_stat.cache_misses=14669
- obs_f3927e70: perf_stat.llc_miss_count=14669
- obs_fc4fd0cc: perf_stat.seconds=0.149136579
- obs_c72afba0: perf_stat.slots=4561188498
- obs_b4a398fe: perf_stat.cycles=760896941
- obs_ef4ba649: perf_stat.instructions=2941568449
- obs_7a5e184d: perf_stat.seconds=0.149327069
- obs_603e6a7d: perf_stat.context_switches=1
- obs_d92f82a1: perf_stat.cpu_migrations=0
- obs_592469c4: perf_stat.page_faults=170
- obs_152b303d: perf_stat.seconds=0.14930844
- obs_a801a2b7: mpstat.02=58:52     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_cae74e71: mpstat.02=58:53     all    0.55    0.00    0.10    0.05    0.00    0.00    0.00    0.00    0.00   99.30
- obs_24fa1776: mpstat.average=all    0.55    0.00    0.10    0.05    0.00    0.00    0.00    0.00    0.00   99.30
- obs_76b8eeab: perf_record.hot_symbol_pct=99.62
- obs_28ae399a: perf_record.hot_symbol_pct=99.62
- obs_3443e70d: perf_record.hot_symbol_pct=99.62
- obs_9cae02ec: perf_record.hot_symbol_pct=96.23
- obs_d0a55a16: perf_record.hot_symbol_pct=46.37
- obs_63b35079: perf_record.hot_symbol_pct=41.16
- obs_9973b83f: perf_record.hot_symbol_pct=2.0
- obs_9486678a: perf_record.hot_symbol_pct=1.33
- obs_00a34489: perf_record.callgraph_samples=585
- obs_18a9c84e: perf_record.process_sample_count=579
- obs_132c40c3: perf_record.process_sample_pct=100.0
- obs_a63eca4a: perf_record.thread_sample_count=579
- obs_caf2ab18: perf_record.thread_sample_pct=100.0
- obs_0cc0bd7a: perf_record.hot_frame_sample_pct=2.7682
- obs_233c7069: perf_record.hot_frame_sample_pct=2.4221
- obs_6dac677c: perf_record.hot_frame_sample_pct=2.2491
- obs_968ccdc5: perf_record.hot_frame_sample_pct=2.2491
- obs_e66b6a3b: perf_record.hot_frame_sample_pct=2.0761
- obs_05ddb34b: perf_record.hot_frame_sample_pct=2.0761
- obs_7f79e862: perf_record.hot_frame_sample_pct=1.9031
- obs_6bd2d367: perf_record.hot_frame_sample_pct=1.9031
- obs_01d7f2ca: perf_record.hot_frame_sample_pct=1.7301
- obs_865a5b26: perf_record.hot_frame_sample_pct=1.7301
- obs_c1f86141: perf_stat.cycles=493632658
- obs_9143234a: perf_stat.instructions=1907660887
- obs_7b6a4034: perf_stat.cache_misses=23047
- obs_ffd39637: perf_stat.context_switches=4
- obs_e6d41305: perf_stat.cycles=267195674
- obs_81556522: perf_stat.instructions=1034017523
- obs_8bf1eeb4: perf_stat.cache_misses=3584
- obs_cf340a9a: perf_stat.context_switches=0

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.76
- 支持证据: obs_05e2a289, obs_132c40c3, obs_caf2ab18
- 反证: 无
- 验证状态: 需要进一步验证

## 8. 源码定位
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:13
- 依据: perf record 样本中 main 占 2.77%，地址 0x1430 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.03
```cpp
  11 |     for (std::size_t round = 0; round < outer_loops; ++round) {
  12 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  13 |             const double x = static_cast<double>((round + 1) * (i + 3));
  14 |             values[i] = std::sin(x) * std::cos(x / 3.0) + std::sqrt(x + 11.0);
  15 |             checksum += values[i];
```
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:14
- 依据: perf record 样本中 main 占 2.42%，地址 0x144a 通过 addr2line 映射到该源码位置。
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
- act_ed140c46: /usr/bin/time / 运行时基线 [done]
- act_7a75da96: perf stat / 指令效率 [done]
- act_6c6529a8: perf stat / 缓存与内存压力 [done]
- act_05caba4e: perf stat / 前后端停顿 [done]
- act_f042b0cc: perf stat / 调度上下文 [done]
- act_a58647ba: pidstat / 调度上下文 [done]
- act_f886d777: mpstat / 调度上下文 [done]
- act_ce5f2d6b: perf record / 热点函数调用链 [done]
- act_758fcc50: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=100
- CPU 瓶颈: perf_record.process_sample_pct=100.0
- CPU 瓶颈: perf_record.thread_sample_pct=100.0

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。
