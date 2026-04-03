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
- 进程级样本拆账: multiprocess_fa pid=3619168 38.27%, multiprocess_fa pid=3619167 30.75%, multiprocess_fa pid=3619169 30.75%, multiprocess_fa pid=3619165 0.22%
- 线程级样本拆账: multiprocess_fa pid/tid=3619168/3619168 38.27%, multiprocess_fa pid/tid=3619167/3619167 30.75%, multiprocess_fa pid/tid=3619169/3619169 30.75%, multiprocess_fa pid/tid=3619165/3619165 0.22%
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在并发工作函数入口，建议结合热点和调度证据一起判断线程或子进程的贡献。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_085bc617: time.user_time_sec=0.22
- obs_8d797ee8: time.system_time_sec=0.0
- obs_ccbd2050: time.cpu_utilization_pct=298
- obs_2b57372a: time.max_rss_kb=4000
- obs_34924c69: time.major_faults=0
- obs_ad0184c3: time.voluntary_context_switches=5
- obs_341bf409: time.involuntary_context_switches=1
- obs_0b156c7f: time.elapsed_time_sec=0.07
- obs_b3c60c1b: perf_stat.cycles=1142465769
- obs_13b2c939: perf_stat.instructions=4617707449
- obs_37988612: perf_stat.msec=223.98
- obs_294a3b04: perf_stat.slots=6813681627
- obs_4aa27fb9: perf_stat.seconds=0.078221521
- obs_189ebf15: perf_stat.cache_references=146335
- obs_5ce5d491: perf_stat.cache_misses=31351
- obs_811512b3: perf_stat.llc_miss_count=31351
- obs_86820a16: perf_stat.l2_miss_count=160532
- obs_cc6721e3: perf_stat.l1_miss_count=165883
- obs_983fdc6f: perf_stat.seconds=0.073555886
- obs_4562ea51: perf_stat.slots=6675968934
- obs_c8b5a7e4: perf_stat.cycles=1114100495
- obs_eb8c8ca8: perf_stat.instructions=4401066658
- obs_4fd7ff6f: perf_stat.seconds=0.073479256
- obs_0b457076: perf_stat.context_switches=7
- obs_369a8bf7: perf_stat.cpu_migrations=3
- obs_4b6184be: perf_stat.page_faults=292
- obs_49d377ad: perf_stat.lock_loads=23305
- obs_cefcd36f: perf_stat.seconds=0.07337064
- obs_9633690d: mpstat.01=22:52     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_fb897a0b: mpstat.01=22:53     all    0.10    0.00    0.15    0.10    0.00    0.00    0.00    0.00    0.00   99.65
- obs_d9579926: mpstat.average=all    0.10    0.00    0.15    0.10    0.00    0.00    0.00    0.00    0.00   99.65
- obs_e2d242b8: perf_record.hot_symbol_pct=99.61
- obs_347e9abd: perf_record.hot_symbol_pct=99.61
- obs_744bac65: perf_record.hot_symbol_pct=99.61
- obs_793db3e7: perf_record.hot_symbol_pct=93.18
- obs_3fb17a04: perf_record.hot_symbol_pct=46.19
- obs_d6ebf9d5: perf_record.hot_symbol_pct=36.39
- obs_c34afb0d: perf_record.hot_symbol_pct=3.57
- obs_c101c96a: perf_record.hot_symbol_pct=2.25
- obs_3af3773e: perf_record.callgraph_samples=910
- obs_01988e6c: perf_record.process_sample_count=346
- obs_78ddc69e: perf_record.process_sample_pct=38.2743
- obs_04ec6361: perf_record.process_sample_count=278
- obs_d29c95f2: perf_record.process_sample_pct=30.7522
- obs_9a9b2676: perf_record.process_sample_count=278
- obs_7af318bf: perf_record.process_sample_pct=30.7522
- obs_b76f6c7a: perf_record.process_sample_count=2
- obs_079ad850: perf_record.process_sample_pct=0.2212
- obs_0f5db17a: perf_record.thread_sample_count=346
- obs_19a63bd2: perf_record.thread_sample_pct=38.2743
- obs_39c8dcc5: perf_record.thread_sample_count=278
- obs_18f48428: perf_record.thread_sample_pct=30.7522
- obs_ea471215: perf_record.thread_sample_count=278
- obs_b0fc33f8: perf_record.thread_sample_pct=30.7522
- obs_17cfe87b: perf_record.thread_sample_count=2
- obs_52de3a52: perf_record.thread_sample_pct=0.2212
- obs_32d5a05b: perf_record.hot_frame_sample_pct=1.3304
- obs_0bf4c76f: perf_record.hot_frame_sample_pct=1.2195
- obs_78488ace: perf_record.hot_frame_sample_pct=1.1086
- obs_36dc5b7a: perf_record.hot_frame_sample_pct=0.9978
- obs_753c29b1: perf_record.hot_frame_sample_pct=0.8869
- obs_bf9d421a: perf_record.hot_frame_sample_pct=0.8869
- obs_4ee24a9c: perf_record.hot_frame_sample_pct=0.8869
- obs_86f233fc: perf_record.hot_frame_sample_pct=0.8869
- obs_fa76de5c: perf_record.hot_frame_sample_pct=0.7761
- obs_14e34bed: perf_record.hot_frame_sample_pct=0.7761
- obs_8ff2997d: perf_stat.cycles=1113864602
- obs_e60febd1: perf_stat.instructions=4401050777
- obs_d6007d65: perf_stat.cache_misses=34360
- obs_d56f83c4: perf_stat.context_switches=6

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.95
- 支持证据: obs_ccbd2050, obs_78ddc69e, obs_d29c95f2, obs_7af318bf, obs_079ad850, obs_19a63bd2, obs_18f48428, obs_b0fc33f8, obs_52de3a52
- 反证: 无
- 验证状态: 证据基本充分

## 8. 源码定位
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:18
- 依据: perf record 样本中 main 占 1.33%，地址 0x2bde 通过 addr2line 映射到该源码位置。
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
- 依据: perf record 样本中 main 占 1.00%，地址 0x2bea 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.01
```cpp
  16 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  17 |             const double x = static_cast<double>((round + seed + 3) * (i + 11));
  18 |             checksum += std::sin(x) * std::cos(x / 7.0) + std::sqrt(x + 29.0);
  19 |         }
  20 |     }
```
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:17
- 依据: perf record 样本中 main 占 0.89%，地址 0x2b5b 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.01
```cpp
  15 |     for (std::size_t round = 0; round < outer_loops; ++round) {
  16 |         for (std::size_t i = 0; i < inner_loops; ++i) {
  17 |             const double x = static_cast<double>((round + seed + 3) * (i + 11));
  18 |             checksum += std::sin(x) * std::cos(x / 7.0) + std::sqrt(x + 29.0);
  19 |         }
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
- act_fa7bddd4: /usr/bin/time / 运行时基线 [done]
- act_f233af9b: perf stat / 指令效率 [done]
- act_947ddbaf: perf stat / 缓存与内存压力 [done]
- act_fdf978d0: perf stat / 前后端停顿 [done]
- act_bbbf29c7: perf stat / 调度上下文 [done]
- act_50ce35cf: pidstat / 调度上下文 [done]
- act_b9a4014c: mpstat / 调度上下文 [done]
- act_2216dc36: perf record / 热点函数调用链 [done]
- act_a72de5cb: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=298
- CPU 瓶颈: perf_record.process_sample_pct=38.2743
- CPU 瓶颈: perf_record.process_sample_pct=30.7522
- CPU 瓶颈: perf_record.process_sample_pct=30.7522
- CPU 瓶颈: perf_record.process_sample_pct=0.2212
- CPU 瓶颈: perf_record.thread_sample_pct=38.2743
- CPU 瓶颈: perf_record.thread_sample_pct=30.7522
- CPU 瓶颈: perf_record.thread_sample_pct=30.7522
- CPU 瓶颈: perf_record.thread_sample_pct=0.2212

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_8424d717/artifacts/act_2216dc36.json
- runs/run_8424d717/artifacts/act_2216dc36.perf.data
- runs/run_8424d717/artifacts/act_2216dc36.record.stdout.txt
- runs/run_8424d717/artifacts/act_2216dc36.script.txt
- runs/run_8424d717/artifacts/act_2216dc36.stderr.txt
- runs/run_8424d717/artifacts/act_2216dc36.stdout.txt
- runs/run_8424d717/artifacts/act_50ce35cf.json
- runs/run_8424d717/artifacts/act_50ce35cf.stdout.txt
- runs/run_8424d717/artifacts/act_947ddbaf.json
- runs/run_8424d717/artifacts/act_947ddbaf.stderr.txt
- runs/run_8424d717/artifacts/act_947ddbaf.stdout.txt
- runs/run_8424d717/artifacts/act_a72de5cb.json
- runs/run_8424d717/artifacts/act_a72de5cb.stderr.txt
- runs/run_8424d717/artifacts/act_a72de5cb.stdout.txt
- runs/run_8424d717/artifacts/act_b9a4014c.json
- runs/run_8424d717/artifacts/act_b9a4014c.stdout.txt
- runs/run_8424d717/artifacts/act_bbbf29c7.json
- runs/run_8424d717/artifacts/act_bbbf29c7.stderr.txt
- runs/run_8424d717/artifacts/act_bbbf29c7.stdout.txt
- runs/run_8424d717/artifacts/act_f233af9b.json
- runs/run_8424d717/artifacts/act_f233af9b.stderr.txt
- runs/run_8424d717/artifacts/act_f233af9b.stdout.txt
- runs/run_8424d717/artifacts/act_fa7bddd4.json
- runs/run_8424d717/artifacts/act_fa7bddd4.stderr.txt
- runs/run_8424d717/artifacts/act_fa7bddd4.stdout.txt
- runs/run_8424d717/artifacts/act_fdf978d0.json
- runs/run_8424d717/artifacts/act_fdf978d0.stderr.txt
- runs/run_8424d717/artifacts/act_fdf978d0.stdout.txt
- runs/run_8424d717/artifacts/perf_list.txt
- runs/run_8424d717/environment.json
- runs/run_8424d717/source_manifest.json
- runs/run_8424d717/target.json
