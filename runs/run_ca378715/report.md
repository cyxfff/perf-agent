# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 锁竞争，置信度为 0.73。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/lock_contention_demo 6 120000
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/lock_contention_demo
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
- 第 1 轮 [baseline] iostat / I/O 等待: 用 iostat 看设备利用率和等待延迟。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 lock_contention。 重点 observation 数量 10，热点符号 5 个，时间序列指标 0 个。
- 重点指标: voluntary_context_switches, cache_misses, context_switches, callgraph_samples, hot_symbol_pct, hot_symbol_pct, hot_symbol_pct, hot_symbol_pct
- 热点符号: (anonymous namespace)::worker              -      -, 0000000000000000                           -      -, entry_SYSCALL_64_after_hwframe             -      -, do_syscall_64                              -      -, pthread_mutex_lock@@GLIBC_2.2.5            -      -
- 是否需要进一步区分 lock_contention 与其他候选瓶颈。
- 当前还缺少时间序列证据，尚不能判断瓶颈是否阶段性出现。

## 6. 关键观测
- obs_a1336d4e: time.user_time_sec=0.02
- obs_6e25dbc2: time.system_time_sec=0.03
- obs_0182a5a9: time.cpu_utilization_pct=12
- obs_663d58fc: time.max_rss_kb=3840
- obs_22cdc908: time.major_faults=0
- obs_44d6464f: time.voluntary_context_switches=24131
- obs_60962e76: time.involuntary_context_switches=3
- obs_5d6647d0: perf_stat.cycles=101038635
- obs_6117378c: perf_stat.instructions=164804149
- obs_2682e24a: perf_stat.cache_references=386415
- obs_4ff064c0: perf_stat.cache_misses=47112
- obs_a919adca: perf_stat.context_switches=19390
- obs_6af20cea: perf_stat.cpu_migrations=57
- obs_1c75886d: perf_stat.page_faults=146
- obs_ae333767: mpstat.01=14:18     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_c855ae89: mpstat.01=14:19     all    1.51    0.00    0.75    1.76    0.00    0.00    0.00    0.00    0.00   95.98
- obs_65968bc2: mpstat.average=all    1.51    0.00    0.75    1.76    0.00    0.00    0.00    0.00    0.00   95.98
- obs_940568fa: perf_record.callgraph_samples=3094
- obs_5bc1d203: perf_record.hot_symbol_pct=79.64
- obs_1cb226dc: perf_record.hot_symbol_pct=54.54
- obs_20ff572f: perf_record.hot_symbol_pct=30.48
- obs_c6de086e: perf_record.hot_symbol_pct=30.45
- obs_307532ed: perf_record.hot_symbol_pct=30.21

## 7. 候选瓶颈
### 7.1 锁竞争
- 置信度: 0.73
- 支持证据: obs_44d6464f, obs_a919adca, obs_940568fa
- 反证: 无
- 验证状态: 需要进一步验证
### 7.2 调度压力
- 置信度: 0.65
- 支持证据: obs_44d6464f, obs_60962e76
- 反证: 无
- 验证状态: 需要进一步验证

## 8. 源码定位
- 锁竞争: /home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp:10
  依据: 检测到互斥锁相关代码，可能与锁竞争有关。
  代码: std::mutex global_mutex;
- 共享临界区: /home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp:10
  依据: 检测到共享状态或临界区命名痕迹。
  代码: std::mutex global_mutex;

## 9. 二次验证
- 已执行动作:
- act_04fa9c0b: /usr/bin/time / 运行时基线 [done]
- act_1d1a9e53: perf stat / 指令效率 [done]
- act_d8c85b6e: perf stat / 缓存与内存压力 [done]
- act_b71a53d1: perf stat / 调度上下文 [done]
- act_bfb0cd31: pidstat / 调度上下文 [done]
- act_c8751452: mpstat / 调度上下文 [done]
- act_8b1179fc: iostat / I/O 等待 [done]
- act_031114c3: perf record / 热点函数调用链 [done]
- 新证据:
- 锁竞争: time.voluntary_context_switches=24131
- 锁竞争: perf_stat.context_switches=19390
- 锁竞争: perf_record.callgraph_samples=3094
- 调度压力: time.voluntary_context_switches=24131
- 调度压力: time.involuntary_context_switches=3

## 10. 建议
- 建议采集 perf record 调用栈，检查锁持有者和等待热点。
- 建议补充 mpstat 或调度跟踪，检查上下文切换和运行队列压力。

## 11. 产物
- runs/run_ca378715/artifacts/act_031114c3.json
- runs/run_ca378715/artifacts/act_031114c3.perf.data
- runs/run_ca378715/artifacts/act_031114c3.record.stdout.txt
- runs/run_ca378715/artifacts/act_031114c3.stderr.txt
- runs/run_ca378715/artifacts/act_031114c3.stdout.txt
- runs/run_ca378715/artifacts/act_04fa9c0b.json
- runs/run_ca378715/artifacts/act_04fa9c0b.stderr.txt
- runs/run_ca378715/artifacts/act_04fa9c0b.stdout.txt
- runs/run_ca378715/artifacts/act_1d1a9e53.json
- runs/run_ca378715/artifacts/act_1d1a9e53.stderr.txt
- runs/run_ca378715/artifacts/act_1d1a9e53.stdout.txt
- runs/run_ca378715/artifacts/act_8b1179fc.json
- runs/run_ca378715/artifacts/act_8b1179fc.stdout.txt
- runs/run_ca378715/artifacts/act_b71a53d1.json
- runs/run_ca378715/artifacts/act_b71a53d1.stderr.txt
- runs/run_ca378715/artifacts/act_b71a53d1.stdout.txt
- runs/run_ca378715/artifacts/act_bfb0cd31.json
- runs/run_ca378715/artifacts/act_bfb0cd31.stdout.txt
- runs/run_ca378715/artifacts/act_c8751452.json
- runs/run_ca378715/artifacts/act_c8751452.stdout.txt
- runs/run_ca378715/artifacts/act_d8c85b6e.json
- runs/run_ca378715/artifacts/act_d8c85b6e.stderr.txt
- runs/run_ca378715/artifacts/act_d8c85b6e.stdout.txt
- runs/run_ca378715/environment.json
- runs/run_ca378715/source_manifest.json
- runs/run_ca378715/target.json
