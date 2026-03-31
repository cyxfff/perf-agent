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
- 第 2 轮后，当前最强规则候选为 lock_contention。 重点 observation 数量 10，热点符号 4 个，时间序列指标 0 个。
- 重点指标: voluntary_context_switches, cache_misses, context_switches, callgraph_samples, hot_symbol_pct, cpu_utilization_pct
- 热点符号: entry_SYSCALL_64_after_hwframe, do_syscall_64, (anonymous namespace)::worker, __x64_sys_futex
- 是否需要进一步区分 lock_contention 与其他候选瓶颈。
- 当前还缺少时间序列证据，尚不能判断瓶颈是否阶段性出现。

## 6. 关键观测
- obs_0a17e36b: time.user_time_sec=0.02
- obs_82a256f6: time.system_time_sec=0.02
- obs_4bbff213: time.cpu_utilization_pct=9
- obs_d4b56887: time.max_rss_kb=3840
- obs_87930eba: time.major_faults=0
- obs_1772f419: time.voluntary_context_switches=17995
- obs_68510c2c: time.involuntary_context_switches=7
- obs_073d57ef: perf_stat.cycles=91944858
- obs_dc0d2080: perf_stat.instructions=147339963
- obs_952c5585: perf_stat.cache_references=389938
- obs_dac93b83: perf_stat.cache_misses=38422
- obs_ee714b4d: perf_stat.context_switches=18960
- obs_43a0e801: perf_stat.cpu_migrations=43
- obs_a7e29917: perf_stat.page_faults=145
- obs_13578251: mpstat.01=18:02     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_bfdeab55: mpstat.01=18:03     all    1.70    0.00    0.85    0.20    0.00    0.00    0.00    0.00    0.00   97.25
- obs_479791d8: mpstat.average=all    1.70    0.00    0.85    0.20    0.00    0.00    0.00    0.00    0.00   97.25
- obs_f8cd3ffa: perf_record.callgraph_samples=3811
- obs_0580b88b: perf_record.hot_symbol_pct=72.1
- obs_c191c457: perf_record.hot_symbol_pct=72.1
- obs_b0851e45: perf_record.hot_symbol_pct=41.43
- obs_4372a771: perf_record.hot_symbol_pct=36.58
- obs_a8bba6f3: perf_record.hot_symbol_pct=32.31

## 7. 候选瓶颈
### 7.1 锁竞争
- 置信度: 0.73
- 支持证据: obs_1772f419, obs_ee714b4d, obs_f8cd3ffa
- 反证: 无
- 验证状态: 需要进一步验证
### 7.2 调度压力
- 置信度: 0.65
- 支持证据: obs_1772f419, obs_68510c2c
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
- act_c613de9c: /usr/bin/time / 运行时基线 [done]
- act_2e4fe48a: perf stat / 指令效率 [done]
- act_0e6d59e2: perf stat / 缓存与内存压力 [done]
- act_bfb373a1: perf stat / 调度上下文 [done]
- act_da7cfb11: pidstat / 调度上下文 [done]
- act_43ed3259: mpstat / 调度上下文 [done]
- act_c622150b: iostat / I/O 等待 [done]
- act_37464a3e: perf record / 热点函数调用链 [done]
- 新证据:
- 锁竞争: time.voluntary_context_switches=17995
- 锁竞争: perf_stat.context_switches=18960
- 锁竞争: perf_record.callgraph_samples=3811
- 调度压力: time.voluntary_context_switches=17995
- 调度压力: time.involuntary_context_switches=7

## 10. 建议
- 建议采集 perf record 调用栈，检查锁持有者和等待热点。
- 建议补充 mpstat 或调度跟踪，检查上下文切换和运行队列压力。

## 11. 产物
- runs/run_185d9035/artifacts/act_0e6d59e2.json
- runs/run_185d9035/artifacts/act_0e6d59e2.stderr.txt
- runs/run_185d9035/artifacts/act_0e6d59e2.stdout.txt
- runs/run_185d9035/artifacts/act_2e4fe48a.json
- runs/run_185d9035/artifacts/act_2e4fe48a.stderr.txt
- runs/run_185d9035/artifacts/act_2e4fe48a.stdout.txt
- runs/run_185d9035/artifacts/act_37464a3e.json
- runs/run_185d9035/artifacts/act_37464a3e.perf.data
- runs/run_185d9035/artifacts/act_37464a3e.record.stdout.txt
- runs/run_185d9035/artifacts/act_37464a3e.stderr.txt
- runs/run_185d9035/artifacts/act_37464a3e.stdout.txt
- runs/run_185d9035/artifacts/act_43ed3259.json
- runs/run_185d9035/artifacts/act_43ed3259.stdout.txt
- runs/run_185d9035/artifacts/act_bfb373a1.json
- runs/run_185d9035/artifacts/act_bfb373a1.stderr.txt
- runs/run_185d9035/artifacts/act_bfb373a1.stdout.txt
- runs/run_185d9035/artifacts/act_c613de9c.json
- runs/run_185d9035/artifacts/act_c613de9c.stderr.txt
- runs/run_185d9035/artifacts/act_c613de9c.stdout.txt
- runs/run_185d9035/artifacts/act_c622150b.json
- runs/run_185d9035/artifacts/act_c622150b.stdout.txt
- runs/run_185d9035/artifacts/act_da7cfb11.json
- runs/run_185d9035/artifacts/act_da7cfb11.stdout.txt
- runs/run_185d9035/environment.json
- runs/run_185d9035/source_manifest.json
- runs/run_185d9035/target.json
