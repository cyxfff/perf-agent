# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.70。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/multiprocess_fanout_demo 3 250 24000
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/multiprocess_fanout_demo
- 源码目录: /home/tchen/agent/perf_agent/examples/cpp
- 运行信息: verification_rounds=1, actions_executed=8
- 工作目录: 

## 3. 运行环境
- 架构: x86_64
- 内核: 6.2.0-37-generic
- CPU: 13th Gen Intel(R) Core(TM) i5-13600K
- 逻辑核数: 20
- perf: 可用 perf version 6.2.16
- 可用事件数: 15
- 调用栈模式: fp, dwarf, lbr
- perf_event_paranoid: -1
- 检测到 topdown 相关事件，可在后续实验中优先尝试。

## 4. 实验设计与执行
- 第 1 轮 [baseline] /usr/bin/time / 运行时基线: 用 /usr/bin/time -v 建立程序运行基线。
- 第 1 轮 [baseline] perf stat / 指令效率: 判断 cycles、instructions 和 IPC 的健康度。当前使用首选事件组合。 事件为 cycles, instructions, task-clock, cpu-clock。
- 第 1 轮 [baseline] perf stat / 缓存与内存压力: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 cache-references, cache-misses。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用首选事件组合。 事件为 context-switches, cpu-migrations, page-faults。
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。
- 第 2 轮 [verification] perf stat / 时间序列行为: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 4 个，时间序列指标 5 个。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, callgraph_samples, hot_symbol_pct
- 热点符号: main, __cos_fma, __sin_fma, __sqrt
- 时间序列指标: cache_misses, context_switches, cycles, instructions, ipc
- 观测到 CPU 利用率超过 100%，说明存在多线程或多进程并发执行。
- 源码中存在并发工作函数入口，建议结合热点和调度证据一起判断线程或子进程的贡献。
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_4d984abc: time.user_time_sec=0.21
- obs_6b50e711: time.system_time_sec=0.0
- obs_9fa5fcf7: time.cpu_utilization_pct=298
- obs_346af1dc: time.max_rss_kb=4000
- obs_467e26ef: time.major_faults=0
- obs_8ab3d06e: time.voluntary_context_switches=6
- obs_82a8be65: time.involuntary_context_switches=2
- obs_b7008bb6: time.elapsed_time_sec=0.07
- obs_3c0c6970: perf_stat.cycles=1096436975
- obs_043e4969: perf_stat.instructions=4401164908
- obs_522d588c: perf_stat.cache_references=125930
- obs_55f123c9: perf_stat.cache_misses=27538
- obs_3670dfba: perf_stat.context_switches=6
- obs_4d9d0b47: perf_stat.cpu_migrations=1
- obs_7942ae82: perf_stat.page_faults=292
- obs_d1d0c5e2: mpstat.02=08:50     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_7ab5b378: mpstat.02=08:51     all    0.75    0.00    0.25    3.16    0.00    0.05    0.00    0.00    0.00   95.78
- obs_77614c34: mpstat.average=all    0.75    0.00    0.25    3.16    0.00    0.05    0.00    0.00    0.00   95.78
- obs_dfc464fc: perf_record.callgraph_samples=59
- obs_f7ca7e6b: perf_record.hot_symbol_pct=92.4
- obs_fa528619: perf_record.hot_symbol_pct=43.94
- obs_28ecc5e1: perf_record.hot_symbol_pct=38.51
- obs_d6b321a3: perf_record.hot_symbol_pct=3.63
- obs_7a3e540f: perf_record.hot_symbol_pct=2.31
- obs_b0545811: perf_stat.cycles=1096399591
- obs_6d7fcd3d: perf_stat.instructions=4401119609
- obs_17fc4125: perf_stat.cache_misses=36279
- obs_0582925d: perf_stat.context_switches=11
- obs_b1ec2ec5: perf_stat.ipc=4.0142

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.70
- 支持证据: obs_9fa5fcf7, obs_b1ec2ec5
- 反证: 无
- 验证状态: 需要进一步验证

## 8. 源码定位
- 热点函数定位: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:26
  依据: perf record / report 显示热点符号 main，该源码位置与热点调用路径直接相关。
  代码: int main(int argc, char** argv) {
- 并发工作函数: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:13
  依据: 检测到并发工作单元入口，CPU 消耗可能分散在多个线程或子进程。
  代码: double worker(std::size_t outer_loops, std::size_t inner_loops, std::size_t seed) {
- 热点循环: /home/tchen/agent/perf_agent/examples/cpp/multiprocess_fanout_demo.cpp:15
  依据: 检测到疑似高频计算循环或数学函数调用。
  代码: for (std::size_t round = 0; round < outer_loops; ++round) {

## 9. 二次验证
- 已执行动作:
- act_0946fd4a: /usr/bin/time / 运行时基线 [done]
- act_19313e2a: perf stat / 指令效率 [done]
- act_cb6a38b6: perf stat / 缓存与内存压力 [done]
- act_bca4bddc: perf stat / 调度上下文 [done]
- act_5042b8c1: pidstat / 调度上下文 [done]
- act_987abd3e: mpstat / 调度上下文 [done]
- act_cfcdbd84: perf record / 热点函数调用链 [done]
- act_5c7bd14e: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=298
- CPU 瓶颈: perf_stat.ipc=4.0142

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_51c81f2f/artifacts/act_0946fd4a.json
- runs/run_51c81f2f/artifacts/act_0946fd4a.stderr.txt
- runs/run_51c81f2f/artifacts/act_0946fd4a.stdout.txt
- runs/run_51c81f2f/artifacts/act_19313e2a.json
- runs/run_51c81f2f/artifacts/act_19313e2a.stderr.txt
- runs/run_51c81f2f/artifacts/act_19313e2a.stdout.txt
- runs/run_51c81f2f/artifacts/act_5042b8c1.json
- runs/run_51c81f2f/artifacts/act_5042b8c1.stdout.txt
- runs/run_51c81f2f/artifacts/act_5c7bd14e.json
- runs/run_51c81f2f/artifacts/act_5c7bd14e.stderr.txt
- runs/run_51c81f2f/artifacts/act_5c7bd14e.stdout.txt
- runs/run_51c81f2f/artifacts/act_987abd3e.json
- runs/run_51c81f2f/artifacts/act_987abd3e.stdout.txt
- runs/run_51c81f2f/artifacts/act_bca4bddc.json
- runs/run_51c81f2f/artifacts/act_bca4bddc.stderr.txt
- runs/run_51c81f2f/artifacts/act_bca4bddc.stdout.txt
- runs/run_51c81f2f/artifacts/act_cb6a38b6.json
- runs/run_51c81f2f/artifacts/act_cb6a38b6.stderr.txt
- runs/run_51c81f2f/artifacts/act_cb6a38b6.stdout.txt
- runs/run_51c81f2f/artifacts/act_cfcdbd84.json
- runs/run_51c81f2f/artifacts/act_cfcdbd84.perf.data
- runs/run_51c81f2f/artifacts/act_cfcdbd84.record.stdout.txt
- runs/run_51c81f2f/artifacts/act_cfcdbd84.stderr.txt
- runs/run_51c81f2f/artifacts/act_cfcdbd84.stdout.txt
- runs/run_51c81f2f/environment.json
- runs/run_51c81f2f/source_manifest.json
- runs/run_51c81f2f/target.json
