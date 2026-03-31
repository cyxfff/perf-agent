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

## 4. 实验设计与执行
- 第 1 轮 [baseline] /usr/bin/time / 运行时基线: 用 /usr/bin/time -v 建立程序运行基线。
- 第 1 轮 [baseline] perf stat / 指令效率: 判断 cycles、instructions 和 IPC 的健康度。当前使用首选事件组合。 事件为 cycles, instructions, task-clock, cpu-clock。
- 第 1 轮 [baseline] perf stat / 缓存与内存压力: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 cache-references, cache-misses。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用首选事件组合。 事件为 context-switches, cpu-migrations, page-faults。
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。

## 5. 关键观测
- obs_ca154a6a: time.user_time_sec=0.15
- obs_34287bba: time.system_time_sec=0.0
- obs_124dd3bb: time.cpu_utilization_pct=100
- obs_7a10907a: time.max_rss_kb=4320
- obs_dcea3d5e: time.major_faults=0
- obs_892d688a: time.voluntary_context_switches=1
- obs_2c4fa155: time.involuntary_context_switches=1
- obs_31706f43: perf_stat.context_switches=2
- obs_a10164ec: perf_stat.cpu_migrations=0
- obs_6411eb16: perf_stat.page_faults=171
- obs_744e0330: mpstat.00=47:09     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_ff8835c3: mpstat.00=47:10     all    0.85    0.00    0.35    0.10    0.00    0.00    0.00    0.00    0.00   98.70
- obs_16190694: mpstat.average=all    0.85    0.00    0.35    0.10    0.00    0.00    0.00    0.00    0.00   98.70
- obs_4904b3df: perf_record.callgraph_samples=184

## 6. 候选瓶颈
### 6.1 CPU 瓶颈
- 置信度: 0.70
- 支持证据: obs_124dd3bb
- 反证: 无
- 验证状态: 需要进一步验证

## 7. 源码定位
- 大规模向量处理: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:9
  依据: 检测到可能参与高频数据处理的容器代码。
  代码: std::vector<double> values(inner_loops, 0.0);
- 热点循环: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:11
  依据: 检测到疑似高频计算循环或数学函数调用。
  代码: for (std::size_t round = 0; round < outer_loops; ++round) {

## 8. 二次验证
- 已执行动作:
- act_aebeaf7b: /usr/bin/time / 运行时基线 [done]
- act_b9f0d876: perf stat / 指令效率 [done]
- act_76f819e0: perf stat / 缓存与内存压力 [done]
- act_0bdf32ae: perf stat / 调度上下文 [done]
- act_7a0a1f89: pidstat / 调度上下文 [done]
- act_d04e7da4: mpstat / 调度上下文 [done]
- act_3b066dfb: perf record / 热点函数调用链 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=100

## 9. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 10. 产物
- runs/run_3930a1a1/artifacts/act_0bdf32ae.json
- runs/run_3930a1a1/artifacts/act_0bdf32ae.stderr.txt
- runs/run_3930a1a1/artifacts/act_0bdf32ae.stdout.txt
- runs/run_3930a1a1/artifacts/act_3b066dfb.json
- runs/run_3930a1a1/artifacts/act_3b066dfb.stderr.txt
- runs/run_3930a1a1/artifacts/act_3b066dfb.stdout.txt
- runs/run_3930a1a1/artifacts/act_76f819e0.json
- runs/run_3930a1a1/artifacts/act_76f819e0.stderr.txt
- runs/run_3930a1a1/artifacts/act_76f819e0.stdout.txt
- runs/run_3930a1a1/artifacts/act_7a0a1f89.json
- runs/run_3930a1a1/artifacts/act_7a0a1f89.stdout.txt
- runs/run_3930a1a1/artifacts/act_aebeaf7b.json
- runs/run_3930a1a1/artifacts/act_aebeaf7b.stderr.txt
- runs/run_3930a1a1/artifacts/act_aebeaf7b.stdout.txt
- runs/run_3930a1a1/artifacts/act_b9f0d876.json
- runs/run_3930a1a1/artifacts/act_b9f0d876.stderr.txt
- runs/run_3930a1a1/artifacts/act_b9f0d876.stdout.txt
- runs/run_3930a1a1/artifacts/act_d04e7da4.json
- runs/run_3930a1a1/artifacts/act_d04e7da4.stdout.txt
- runs/run_3930a1a1/environment.json
- runs/run_3930a1a1/source_manifest.json
- runs/run_3930a1a1/target.json
