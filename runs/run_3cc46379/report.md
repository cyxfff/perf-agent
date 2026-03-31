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
- 热点符号: (anonymous namespace)::worker, entry_SYSCALL_64_after_hwframe, do_syscall_64, 0000000000000000, __x64_sys_futex
- 时间序列指标: cache_misses, context_switches, cycles, instructions, ipc
- 是否需要进一步区分 lock_contention 与其他候选瓶颈。

## 6. 关键观测
- obs_5498e3b0: time.user_time_sec=0.0
- obs_66b039c6: time.system_time_sec=0.05
- obs_d4bca736: time.cpu_utilization_pct=13
- obs_9607078d: time.max_rss_kb=4000
- obs_d33d43c8: time.major_faults=0
- obs_7bf5bc9b: time.voluntary_context_switches=23239
- obs_1295b5e9: time.involuntary_context_switches=2
- obs_9708ec76: time.elapsed_time_sec=0.47
- obs_90727819: perf_stat.cycles=74402995
- obs_59849fba: perf_stat.instructions=120319928
- obs_af121260: perf_stat.cache_references=376996
- obs_d9076f63: perf_stat.cache_misses=32583
- obs_f93cbb8b: perf_stat.context_switches=18341
- obs_eeb3cfa0: perf_stat.cpu_migrations=45
- obs_1f1ead65: perf_stat.page_faults=144
- obs_aa113244: mpstat.01=38:55     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_c1bdcb18: mpstat.01=38:56     all    0.30    0.00    0.05    0.15    0.00    0.00    0.00    0.00    0.00   99.50
- obs_b9756596: mpstat.average=all    0.30    0.00    0.05    0.15    0.00    0.00    0.00    0.00    0.00   99.50
- obs_25d878e8: perf_record.callgraph_samples=3876
- obs_758a9323: perf_record.hot_symbol_pct=87.52
- obs_7e787e49: perf_record.hot_symbol_pct=53.35
- obs_d09d01b1: perf_record.hot_symbol_pct=53.35
- obs_cb743468: perf_record.hot_symbol_pct=52.33
- obs_dcb216bd: perf_record.hot_symbol_pct=28.2
- obs_85b59d2f: perf_stat.cycles=23369984
- obs_00c78009: perf_stat.cycles=16410072
- obs_dd9f1a39: perf_stat.instructions=36910974
- obs_6d690843: perf_stat.instructions=23281229
- obs_c2289c7f: perf_stat.cache_misses=24175
- obs_7a1ee230: perf_stat.cache_misses=2419
- obs_a4c2507c: perf_stat.context_switches=2397
- obs_0113ad44: perf_stat.cycles=20657759
- obs_b5b651ae: perf_stat.cycles=11150608
- obs_7282434c: perf_stat.instructions=33803258
- obs_3051d46d: perf_stat.instructions=17203550
- obs_508182e0: perf_stat.cache_misses=1356
- obs_e99370f8: perf_stat.cache_misses=99
- obs_bd7920bb: perf_stat.context_switches=2411
- obs_06b61bdc: perf_stat.cycles=20821043
- obs_4604dc60: perf_stat.cycles=5138082
- obs_5affefcc: perf_stat.instructions=34076359
- obs_50a7f528: perf_stat.instructions=8085038
- obs_d0dbc1d5: perf_stat.cache_misses=672
- obs_daabca4f: perf_stat.cache_misses=12
- obs_7eb2d5aa: perf_stat.context_switches=2402
- obs_b4c01d88: perf_stat.cycles=22268242
- obs_403fcb17: perf_stat.cycles=4073430
- obs_f375c49d: perf_stat.instructions=36310986
- obs_e330db76: perf_stat.instructions=6600424
- obs_e6dd8ca1: perf_stat.cache_misses=976
- obs_f9c46ac2: perf_stat.cache_misses=58
- obs_e1e8fc43: perf_stat.context_switches=2392
- obs_eb964abf: perf_stat.cycles=3812666
- obs_8672da5f: perf_stat.cycles=8729391
- obs_ae53d0be: perf_stat.instructions=6525795
- obs_a67f7f7a: perf_stat.instructions=14767785
- obs_30b79c0d: perf_stat.cache_misses=5497
- obs_f6d1d178: perf_stat.cache_misses=348
- obs_3dab1c25: perf_stat.context_switches=836
- obs_9b6dc86f: perf_stat.ipc=1.5131
- obs_18daca6d: perf_stat.ipc=1.6036
- obs_02f45df0: perf_stat.ipc=1.6241
- obs_d6184b74: perf_stat.ipc=1.629
- obs_4e6262be: perf_stat.ipc=1.6978

## 7. 候选瓶颈
### 7.1 锁竞争
- 置信度: 0.95
- 支持证据: obs_7bf5bc9b, obs_f93cbb8b, obs_25d878e8, obs_a4c2507c, obs_bd7920bb, obs_7eb2d5aa, obs_e1e8fc43, obs_3dab1c25
- 反证: 无
- 验证状态: 需要进一步验证
### 7.2 调度压力
- 置信度: 0.65
- 支持证据: obs_7bf5bc9b, obs_1295b5e9
- 反证: 无
- 验证状态: 需要进一步验证

## 8. 源码定位
- 热点函数定位: /home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp:13
  依据: perf record / report 显示热点符号 worker，该源码位置与热点调用路径直接相关。
  代码: void worker(std::size_t iterations) {
- 热点函数定位: /home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp:38
  依据: perf record / report 显示热点符号 worker，该源码位置与热点调用路径直接相关。
  代码: threads.emplace_back(worker, iterations);
- 锁竞争: /home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp:10
  依据: 检测到互斥锁相关代码，可能与锁竞争有关。
  代码: std::mutex global_mutex;
- 共享临界区: /home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp:10
  依据: 检测到共享状态或临界区命名痕迹。
  代码: std::mutex global_mutex;

## 9. 二次验证
- 已执行动作:
- act_a0a68b4e: /usr/bin/time / 运行时基线 [done]
- act_3293bd75: perf stat / 指令效率 [done]
- act_38b1ed6e: perf stat / 缓存与内存压力 [done]
- act_8a0a98fb: perf stat / 调度上下文 [done]
- act_8d509dc7: pidstat / 调度上下文 [done]
- act_716a66d7: mpstat / 调度上下文 [done]
- act_ece348eb: iostat / I/O 等待 [done]
- act_0952e0cd: perf record / 热点函数调用链 [done]
- act_17afa1e7: perf stat / 时间序列行为 [done]
- 新证据:
- 锁竞争: time.voluntary_context_switches=23239
- 锁竞争: perf_stat.context_switches=18341
- 锁竞争: perf_record.callgraph_samples=3876
- 锁竞争: perf_stat.context_switches=2397
- 锁竞争: perf_stat.context_switches=2411
- 锁竞争: perf_stat.context_switches=2402
- 锁竞争: perf_stat.context_switches=2392
- 锁竞争: perf_stat.context_switches=836
- 调度压力: time.voluntary_context_switches=23239
- 调度压力: time.involuntary_context_switches=2

## 10. 建议
- 建议采集 perf record 调用栈，检查锁持有者和等待热点。
- 建议补充 mpstat 或调度跟踪，检查上下文切换和运行队列压力。

## 11. 产物
- runs/run_3cc46379/artifacts/act_0952e0cd.json
- runs/run_3cc46379/artifacts/act_0952e0cd.perf.data
- runs/run_3cc46379/artifacts/act_0952e0cd.record.stdout.txt
- runs/run_3cc46379/artifacts/act_0952e0cd.stderr.txt
- runs/run_3cc46379/artifacts/act_0952e0cd.stdout.txt
- runs/run_3cc46379/artifacts/act_17afa1e7.json
- runs/run_3cc46379/artifacts/act_17afa1e7.stderr.txt
- runs/run_3cc46379/artifacts/act_17afa1e7.stdout.txt
- runs/run_3cc46379/artifacts/act_3293bd75.json
- runs/run_3cc46379/artifacts/act_3293bd75.stderr.txt
- runs/run_3cc46379/artifacts/act_3293bd75.stdout.txt
- runs/run_3cc46379/artifacts/act_38b1ed6e.json
- runs/run_3cc46379/artifacts/act_38b1ed6e.stderr.txt
- runs/run_3cc46379/artifacts/act_38b1ed6e.stdout.txt
- runs/run_3cc46379/artifacts/act_716a66d7.json
- runs/run_3cc46379/artifacts/act_716a66d7.stdout.txt
- runs/run_3cc46379/artifacts/act_8a0a98fb.json
- runs/run_3cc46379/artifacts/act_8a0a98fb.stderr.txt
- runs/run_3cc46379/artifacts/act_8a0a98fb.stdout.txt
- runs/run_3cc46379/artifacts/act_8d509dc7.json
- runs/run_3cc46379/artifacts/act_8d509dc7.stdout.txt
- runs/run_3cc46379/artifacts/act_a0a68b4e.json
- runs/run_3cc46379/artifacts/act_a0a68b4e.stderr.txt
- runs/run_3cc46379/artifacts/act_a0a68b4e.stdout.txt
- runs/run_3cc46379/artifacts/act_ece348eb.json
- runs/run_3cc46379/artifacts/act_ece348eb.stdout.txt
- runs/run_3cc46379/environment.json
- runs/run_3cc46379/source_manifest.json
- runs/run_3cc46379/target.json
