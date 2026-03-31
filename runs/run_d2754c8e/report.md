# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 锁竞争，置信度为 0.95。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/lock_contention_demo 6 120000
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/lock_contention_demo
- 源码目录: /home/tchen/agent/perf_agent/examples/cpp
- 运行信息: verification_rounds=1, actions_executed=9
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
- 第 2 轮 [verification] perf stat / 时间序列行为: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 lock_contention。 重点 observation 数量 10，热点符号 5 个，时间序列指标 5 个。
- 重点指标: cache_misses, context_switches
- 热点符号: (anonymous namespace)::worker, do_syscall_64, entry_SYSCALL_64_after_hwframe, __x64_sys_futex, do_futex
- 时间序列指标: cache_misses, context_switches, cycles, instructions, ipc
- 是否需要进一步区分 lock_contention 与其他候选瓶颈。

## 6. 关键观测
- obs_f8882115: time.user_time_sec=0.03
- obs_6280e33c: time.system_time_sec=0.04
- obs_514380a6: time.cpu_utilization_pct=17
- obs_e1ddf151: time.max_rss_kb=4000
- obs_7593f805: time.major_faults=0
- obs_9839fad8: time.voluntary_context_switches=25460
- obs_b09e9302: time.involuntary_context_switches=3
- obs_8015a16e: time.elapsed_time_sec=0.48
- obs_5f0033cd: perf_stat.cycles=96858559
- obs_3ef61808: perf_stat.instructions=155118793
- obs_a3b8152e: perf_stat.cache_references=393511
- obs_dd06fe78: perf_stat.cache_misses=39862
- obs_423c3928: perf_stat.context_switches=19087
- obs_e2573320: perf_stat.cpu_migrations=71
- obs_6acb918e: perf_stat.page_faults=147
- obs_28f436e1: mpstat.01=18:39     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_dd872915: mpstat.01=18:40     all    0.65    0.00    0.10    1.20    0.00    0.05    0.00    0.00    0.00   97.99
- obs_16bc1c6f: mpstat.average=all    0.65    0.00    0.10    1.20    0.00    0.05    0.00    0.00    0.00   97.99
- obs_aec2f6cd: perf_record.callgraph_samples=3616
- obs_55d4d252: perf_record.hot_symbol_pct=81.96
- obs_63811bb0: perf_record.hot_symbol_pct=60.17
- obs_e04a2cac: perf_record.hot_symbol_pct=60.15
- obs_a0808596: perf_record.hot_symbol_pct=40.46
- obs_ae199ef8: perf_record.hot_symbol_pct=40.36
- obs_4b9ac5e5: perf_stat.cycles=21740402
- obs_20d20900: perf_stat.cycles=5834197
- obs_7d8df75a: perf_stat.instructions=34224651
- obs_df2cac8f: perf_stat.instructions=2242050
- obs_810ec428: perf_stat.cache_misses=22967
- obs_656f0879: perf_stat.cache_misses=8222
- obs_2fcd423d: perf_stat.context_switches=2257
- obs_41d858e1: perf_stat.cycles=20403213
- obs_9e196ac4: perf_stat.cycles=6439203
- obs_23f94b47: perf_stat.instructions=32877122
- obs_fe3793d7: perf_stat.instructions=8901955
- obs_a0f8849a: perf_stat.cache_misses=1457
- obs_80799103: perf_stat.cache_misses=1381
- obs_143bf7b2: perf_stat.context_switches=2311
- obs_0ce9d595: perf_stat.cycles=20726057
- obs_e0d5b9ce: perf_stat.cycles=4408858
- obs_dec8f89c: perf_stat.instructions=33821705
- obs_3506f387: perf_stat.instructions=6894835
- obs_4a881c83: perf_stat.cache_misses=473
- obs_3f7982ee: perf_stat.cache_misses=57
- obs_0afda0b3: perf_stat.context_switches=2410
- obs_3ecf499e: perf_stat.cycles=22712780
- obs_bcbe8201: perf_stat.cycles=11600841
- obs_65f42366: perf_stat.instructions=36924983
- obs_ff453093: perf_stat.instructions=19167560
- obs_62dc2d94: perf_stat.cache_misses=531
- obs_b0a363c1: perf_stat.cache_misses=102
- obs_5c6ce39c: perf_stat.context_switches=2403
- obs_a0f67046: perf_stat.cycles=10361461
- obs_816cc07f: perf_stat.cycles=2576721
- obs_3e70a566: perf_stat.instructions=18214836
- obs_b53a1336: perf_stat.instructions=4389079
- obs_0ffc72dc: perf_stat.cache_misses=4084
- obs_5fe0ac09: perf_stat.cache_misses=25
- obs_1fb23a6d: perf_stat.context_switches=977
- obs_9b7ae932: perf_stat.ipc=1.3225
- obs_ffc91d39: perf_stat.ipc=1.5565
- obs_0c253da9: perf_stat.ipc=1.6199
- obs_8dd9b5b0: perf_stat.ipc=1.6347
- obs_c478dfde: perf_stat.ipc=1.7471

## 7. 候选瓶颈
### 7.1 锁竞争
- 置信度: 0.95
- 支持证据: obs_9839fad8, obs_423c3928, obs_aec2f6cd, obs_2fcd423d, obs_143bf7b2, obs_0afda0b3, obs_5c6ce39c, obs_1fb23a6d
- 反证: 无
- 验证状态: 需要进一步验证
### 7.2 调度压力
- 置信度: 0.65
- 支持证据: obs_9839fad8, obs_b09e9302
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
- act_f05ff85d: /usr/bin/time / 运行时基线 [done]
- act_827d5bb6: perf stat / 指令效率 [done]
- act_75438a32: perf stat / 缓存与内存压力 [done]
- act_581a66e5: perf stat / 调度上下文 [done]
- act_bac3ed79: pidstat / 调度上下文 [done]
- act_a12e0b52: mpstat / 调度上下文 [done]
- act_5094d254: iostat / I/O 等待 [done]
- act_0a261334: perf record / 热点函数调用链 [done]
- act_84cc0413: perf stat / 时间序列行为 [done]
- 新证据:
- 锁竞争: time.voluntary_context_switches=25460
- 锁竞争: perf_stat.context_switches=19087
- 锁竞争: perf_record.callgraph_samples=3616
- 锁竞争: perf_stat.context_switches=2257
- 锁竞争: perf_stat.context_switches=2311
- 锁竞争: perf_stat.context_switches=2410
- 锁竞争: perf_stat.context_switches=2403
- 锁竞争: perf_stat.context_switches=977
- 调度压力: time.voluntary_context_switches=25460
- 调度压力: time.involuntary_context_switches=3

## 10. 建议
- 建议采集 perf record 调用栈，检查锁持有者和等待热点。
- 建议补充 mpstat 或调度跟踪，检查上下文切换和运行队列压力。

## 11. 产物
- runs/run_d2754c8e/artifacts/act_0a261334.json
- runs/run_d2754c8e/artifacts/act_0a261334.perf.data
- runs/run_d2754c8e/artifacts/act_0a261334.record.stdout.txt
- runs/run_d2754c8e/artifacts/act_0a261334.stderr.txt
- runs/run_d2754c8e/artifacts/act_0a261334.stdout.txt
- runs/run_d2754c8e/artifacts/act_5094d254.json
- runs/run_d2754c8e/artifacts/act_5094d254.stdout.txt
- runs/run_d2754c8e/artifacts/act_581a66e5.json
- runs/run_d2754c8e/artifacts/act_581a66e5.stderr.txt
- runs/run_d2754c8e/artifacts/act_581a66e5.stdout.txt
- runs/run_d2754c8e/artifacts/act_75438a32.json
- runs/run_d2754c8e/artifacts/act_75438a32.stderr.txt
- runs/run_d2754c8e/artifacts/act_75438a32.stdout.txt
- runs/run_d2754c8e/artifacts/act_827d5bb6.json
- runs/run_d2754c8e/artifacts/act_827d5bb6.stderr.txt
- runs/run_d2754c8e/artifacts/act_827d5bb6.stdout.txt
- runs/run_d2754c8e/artifacts/act_84cc0413.json
- runs/run_d2754c8e/artifacts/act_84cc0413.stderr.txt
- runs/run_d2754c8e/artifacts/act_84cc0413.stdout.txt
- runs/run_d2754c8e/artifacts/act_a12e0b52.json
- runs/run_d2754c8e/artifacts/act_a12e0b52.stdout.txt
- runs/run_d2754c8e/artifacts/act_bac3ed79.json
- runs/run_d2754c8e/artifacts/act_bac3ed79.stdout.txt
- runs/run_d2754c8e/artifacts/act_f05ff85d.json
- runs/run_d2754c8e/artifacts/act_f05ff85d.stderr.txt
- runs/run_d2754c8e/artifacts/act_f05ff85d.stdout.txt
- runs/run_d2754c8e/environment.json
- runs/run_d2754c8e/source_manifest.json
- runs/run_d2754c8e/target.json
