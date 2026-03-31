# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.70。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/cpu_bound_demo 700 18000
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/cpu_bound_demo
- 源码目录: /home/tchen/agent/perf_agent/examples/cpp
- 运行信息: verification_rounds=1, actions_executed=7
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
- perf_event_paranoid=-1

## 4. 实验设计与执行
- 第 1 轮 [baseline] /usr/bin/time / 运行时基线: 用 /usr/bin/time -v 建立程序运行基线。
- 第 1 轮 [baseline] perf stat / 指令效率: 判断 cycles、instructions 和 IPC 的健康度。当前使用首选事件组合。 事件为 cycles, instructions, task-clock, cpu-clock。，事件: cycles, instructions, task-clock, cpu-clock
- 第 1 轮 [baseline] perf stat / 缓存与内存压力: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 cache-references, cache-misses。，事件: cache-references, cache-misses，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用首选事件组合。 事件为 context-switches, cpu-migrations, page-faults。，事件: context-switches, cpu-migrations, page-faults
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。

## 5. 关键观测
- obs_e5df2ebb: time.user_time_sec=0.15
- obs_a46690cb: time.system_time_sec=0.0
- obs_e2f93669: time.cpu_utilization_pct=100
- obs_fcf7d7d4: time.max_rss_kb=4160
- obs_66da2970: time.major_faults=0
- obs_76d42ea0: time.voluntary_context_switches=1
- obs_cb5e5f13: time.involuntary_context_switches=2
- obs_4866e3b2: perf_stat.context_switches=3
- obs_3ad2f667: perf_stat.cpu_migrations=1
- obs_83c70d66: perf_stat.page_faults=171
- obs_27cbdfca: mpstat.00=44:26     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_abfb88e1: mpstat.00=44:27     all    0.75    0.00    0.30    1.65    0.00    0.05    0.00    0.00    0.00   97.24
- obs_80c3f90c: mpstat.average=all    0.75    0.00    0.30    1.65    0.00    0.05    0.00    0.00    0.00   97.24
- obs_0d8e2327: perf_record.callgraph_samples=283

## 6. 候选瓶颈
### 6.1 CPU 瓶颈
- 置信度: 0.70
- 支持证据: obs_e2f93669
- 反证: 无
- 验证状态: 需要进一步验证

## 7. 源码定位
- 大规模向量处理: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:9
  依据: 检测到可能参与高频数据处理的容器代码。
  代码: std::vector<double> values(inner_loops, 0.0);
- 热点循环: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:11
  依据: 检测到疑似高频计算循环或数学函数调用。
  代码: for (std::size_t round = 0; round < outer_loops; ++round) {
- 热点循环: /home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp:14
  依据: 检测到疑似高频计算循环或数学函数调用。
  代码: for (std::size_t i = 0; i < iterations; ++i) {
- 大规模向量处理: /home/tchen/agent/perf_agent/examples/cpp/lock_contention_demo.cpp:35
  依据: 检测到可能参与高频数据处理的容器代码。
  代码: std::vector<std::thread> threads;

## 8. 二次验证
- 已执行动作:
- act_2dfe94ef: /usr/bin/time / 运行时基线 [done]
- act_3039c213: perf stat / 指令效率 [done]
- act_dcd4040e: perf stat / 缓存与内存压力 [done]
- act_b55f6dc6: perf stat / 调度上下文 [done]
- act_607125fd: pidstat / 调度上下文 [done]
- act_80f4f608: mpstat / 调度上下文 [done]
- act_cf22eb14: perf record / 热点函数调用链 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=100

## 9. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 10. 产物
- runs/run_1c182e4b/artifacts/act_2dfe94ef.json
- runs/run_1c182e4b/artifacts/act_2dfe94ef.stderr.txt
- runs/run_1c182e4b/artifacts/act_2dfe94ef.stdout.txt
- runs/run_1c182e4b/artifacts/act_3039c213.json
- runs/run_1c182e4b/artifacts/act_3039c213.stderr.txt
- runs/run_1c182e4b/artifacts/act_3039c213.stdout.txt
- runs/run_1c182e4b/artifacts/act_607125fd.json
- runs/run_1c182e4b/artifacts/act_607125fd.stdout.txt
- runs/run_1c182e4b/artifacts/act_80f4f608.json
- runs/run_1c182e4b/artifacts/act_80f4f608.stdout.txt
- runs/run_1c182e4b/artifacts/act_b55f6dc6.json
- runs/run_1c182e4b/artifacts/act_b55f6dc6.stderr.txt
- runs/run_1c182e4b/artifacts/act_b55f6dc6.stdout.txt
- runs/run_1c182e4b/artifacts/act_cf22eb14.json
- runs/run_1c182e4b/artifacts/act_cf22eb14.stderr.txt
- runs/run_1c182e4b/artifacts/act_cf22eb14.stdout.txt
- runs/run_1c182e4b/artifacts/act_dcd4040e.json
- runs/run_1c182e4b/artifacts/act_dcd4040e.stderr.txt
- runs/run_1c182e4b/artifacts/act_dcd4040e.stdout.txt
- runs/run_1c182e4b/environment.json
- runs/run_1c182e4b/source_manifest.json
- runs/run_1c182e4b/target.json
