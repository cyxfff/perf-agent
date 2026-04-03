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
- 进程级样本拆账: multiprocess_fa pid=3619816 33.94%, multiprocess_fa pid=3619817 33.82%, multiprocess_fa pid=3619818 32.00%, multiprocess_fa pid=3619814 0.24%
- 线程级样本拆账: multiprocess_fa pid/tid=3619816/3619816 33.94%, multiprocess_fa pid/tid=3619817/3619817 33.82%, multiprocess_fa pid/tid=3619818/3619818 32.00%, multiprocess_fa pid/tid=3619814/3619814 0.24%
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在并发工作函数入口，建议结合热点和调度证据一起判断线程或子进程的贡献。
- 已采集到 top-down 前后端指标，可进一步区分 frontend / backend / bad speculation / retiring。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_24d75e97: time.user_time_sec=0.22
- obs_70d790dd: time.system_time_sec=0.0
- obs_55b2a9ed: time.cpu_utilization_pct=296
- obs_b4c62e6c: time.max_rss_kb=4000
- obs_9ca542bc: time.major_faults=0
- obs_3208d7e8: time.voluntary_context_switches=7
- obs_1b4386f0: time.involuntary_context_switches=4
- obs_0cf6eb99: time.elapsed_time_sec=0.07
- obs_8e21ad92: perf_stat.cycles=1112930939
- obs_8fe6519d: perf_stat.instructions=4401096456
- obs_680f9795: perf_stat.msec=224.39
- obs_90b496ad: perf_stat.slots=6675912912
- obs_7524391f: perf_stat.seconds=0.075348068
- obs_11add397: perf_stat.topdown_be_bound_pct=132221171
- obs_94077341: perf_stat.cache_references=159055
- obs_8cb86e63: perf_stat.cache_misses=23242
- obs_fb9f7ed0: perf_stat.llc_miss_count=23316
- obs_f8e6782d: perf_stat.l2_miss_count=163759
- obs_433eed42: perf_stat.l1_miss_count=174529
- obs_3ef86d0e: perf_stat.seconds=0.082577676
- obs_fae023e6: perf_stat.slots=6676921734
- obs_fba08c4a: perf_stat.cycles=1113131881
- obs_1dd7df1d: perf_stat.instructions=4401102253
- obs_68f08a62: perf_stat.seconds=0.073338888
- obs_b28f8129: perf_stat.context_switches=7
- obs_121af927: perf_stat.cpu_migrations=2
- obs_265b8ac9: perf_stat.page_faults=292
- obs_86c141b9: perf_stat.lock_loads=23171
- obs_733ab546: perf_stat.seconds=0.073264864
- obs_13c60fbf: mpstat.01=24:58     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_d25f0257: mpstat.01=24:59     all    1.05    0.00    0.35    0.25    0.00    0.00    0.00    0.00    0.00   98.35
- obs_4152306f: mpstat.average=all    1.05    0.00    0.35    0.25    0.00    0.00    0.00    0.00    0.00   98.35
- obs_4fb5a6a8: perf_record.hot_symbol_pct=99.3
- obs_5a322318: perf_record.hot_symbol_pct=99.3
- obs_b4f8d10f: perf_record.hot_symbol_pct=99.3
- obs_b47ddf0e: perf_record.hot_symbol_pct=92.07
- obs_d2e721f8: perf_record.hot_symbol_pct=44.67
- obs_fdb41b36: perf_record.hot_symbol_pct=38.52
- obs_e4cece81: perf_record.hot_symbol_pct=3.2
- obs_07b1a04a: perf_record.hot_symbol_pct=2.04
- obs_e8b55860: perf_record.callgraph_samples=831
- obs_ddad12aa: perf_record.process_sample_count=280
- obs_cf878977: perf_record.process_sample_pct=33.9394
- obs_f55ed356: perf_record.process_sample_count=279
- obs_9c623595: perf_record.process_sample_pct=33.8182
- obs_3299292c: perf_record.process_sample_count=264
- obs_0d63d760: perf_record.process_sample_pct=32.0
- obs_8e3a0f36: perf_record.process_sample_count=2
- obs_6badaa70: perf_record.process_sample_pct=0.2424
- obs_e132e288: perf_record.thread_sample_count=280
- obs_80272453: perf_record.thread_sample_pct=33.9394
- obs_a6c2619c: perf_record.thread_sample_count=279
- obs_e59f7bbe: perf_record.thread_sample_pct=33.8182
- obs_6719e9b2: perf_record.thread_sample_count=264
- obs_d1663ab2: perf_record.thread_sample_pct=32.0
- obs_4b00a4e2: perf_record.thread_sample_count=2
- obs_94d4e707: perf_record.thread_sample_pct=0.2424
- obs_a22b4ec8: perf_record.hot_frame_sample_pct=1.2136
- obs_c0f5fa00: perf_record.hot_frame_sample_pct=1.0922
- obs_a8647228: perf_record.hot_frame_sample_pct=1.0922
- obs_e2bad5fb: perf_record.hot_frame_sample_pct=1.0922
- obs_5ba95d52: perf_record.hot_frame_sample_pct=0.9709
- obs_6879801a: perf_record.hot_frame_sample_pct=0.9709
- obs_d9b44a28: perf_record.hot_frame_sample_pct=0.9709
- obs_202f94a1: perf_record.hot_frame_sample_pct=0.9709
- obs_fa3d07ad: perf_record.hot_frame_sample_pct=0.9709
- obs_6faec63a: perf_record.hot_frame_sample_pct=0.9709
- obs_cc8b2b60: perf_stat.cycles=1113429588
- obs_39e7d9c5: perf_stat.instructions=4401099197
- obs_1f0da0fb: perf_stat.cache_misses=34159
- obs_4ed69343: perf_stat.context_switches=7

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.95
- 支持证据: obs_55b2a9ed, obs_cf878977, obs_9c623595, obs_0d63d760, obs_6badaa70, obs_80272453, obs_e59f7bbe, obs_d1663ab2, obs_94d4e707
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
- act_f0a1fcb5: /usr/bin/time / 运行时基线 [done]
- act_fa0b1e8a: perf stat / 指令效率 [done]
- act_6fcff3dc: perf stat / 缓存与内存压力 [done]
- act_bf1c66fb: perf stat / 前后端停顿 [done]
- act_d27fbc6c: perf stat / 调度上下文 [done]
- act_778961a0: pidstat / 调度上下文 [done]
- act_b50042f9: mpstat / 调度上下文 [done]
- act_e3b9c340: perf record / 热点函数调用链 [done]
- act_7f47f13e: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=296
- CPU 瓶颈: perf_record.process_sample_pct=33.9394
- CPU 瓶颈: perf_record.process_sample_pct=33.8182
- CPU 瓶颈: perf_record.process_sample_pct=32.0
- CPU 瓶颈: perf_record.process_sample_pct=0.2424
- CPU 瓶颈: perf_record.thread_sample_pct=33.9394
- CPU 瓶颈: perf_record.thread_sample_pct=33.8182
- CPU 瓶颈: perf_record.thread_sample_pct=32.0
- CPU 瓶颈: perf_record.thread_sample_pct=0.2424

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_16e8d5ac/artifacts/act_6fcff3dc.json
- runs/run_16e8d5ac/artifacts/act_6fcff3dc.stderr.txt
- runs/run_16e8d5ac/artifacts/act_6fcff3dc.stdout.txt
- runs/run_16e8d5ac/artifacts/act_778961a0.json
- runs/run_16e8d5ac/artifacts/act_778961a0.stdout.txt
- runs/run_16e8d5ac/artifacts/act_7f47f13e.json
- runs/run_16e8d5ac/artifacts/act_7f47f13e.stderr.txt
- runs/run_16e8d5ac/artifacts/act_7f47f13e.stdout.txt
- runs/run_16e8d5ac/artifacts/act_b50042f9.json
- runs/run_16e8d5ac/artifacts/act_b50042f9.stdout.txt
- runs/run_16e8d5ac/artifacts/act_bf1c66fb.json
- runs/run_16e8d5ac/artifacts/act_bf1c66fb.stderr.txt
- runs/run_16e8d5ac/artifacts/act_bf1c66fb.stdout.txt
- runs/run_16e8d5ac/artifacts/act_d27fbc6c.json
- runs/run_16e8d5ac/artifacts/act_d27fbc6c.stderr.txt
- runs/run_16e8d5ac/artifacts/act_d27fbc6c.stdout.txt
- runs/run_16e8d5ac/artifacts/act_e3b9c340.json
- runs/run_16e8d5ac/artifacts/act_e3b9c340.perf.data
- runs/run_16e8d5ac/artifacts/act_e3b9c340.record.stdout.txt
- runs/run_16e8d5ac/artifacts/act_e3b9c340.script.txt
- runs/run_16e8d5ac/artifacts/act_e3b9c340.stderr.txt
- runs/run_16e8d5ac/artifacts/act_e3b9c340.stdout.txt
- runs/run_16e8d5ac/artifacts/act_f0a1fcb5.json
- runs/run_16e8d5ac/artifacts/act_f0a1fcb5.stderr.txt
- runs/run_16e8d5ac/artifacts/act_f0a1fcb5.stdout.txt
- runs/run_16e8d5ac/artifacts/act_fa0b1e8a.json
- runs/run_16e8d5ac/artifacts/act_fa0b1e8a.stderr.txt
- runs/run_16e8d5ac/artifacts/act_fa0b1e8a.stdout.txt
- runs/run_16e8d5ac/artifacts/perf_list.txt
- runs/run_16e8d5ac/environment.json
- runs/run_16e8d5ac/source_manifest.json
- runs/run_16e8d5ac/target.json
