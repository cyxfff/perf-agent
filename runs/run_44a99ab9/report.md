# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.70。

## 2. 分析目标
- 命令: examples/bin/cpu_bound_demo 700 18000
- 可执行文件: examples/bin/cpu_bound_demo
- 源码目录: examples/cpp
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
- obs_c8cf70ce: time.user_time_sec=0.14
- obs_3ba012dc: time.system_time_sec=0.0
- obs_df89bf27: time.cpu_utilization_pct=100
- obs_f6727a37: time.max_rss_kb=4160
- obs_ad12d0c4: time.major_faults=0
- obs_19664f86: time.voluntary_context_switches=1
- obs_0161f5ed: time.involuntary_context_switches=1
- obs_cdebf973: perf_stat.context_switches=1
- obs_a76f76b2: perf_stat.cpu_migrations=1
- obs_7d131be7: perf_stat.page_faults=171
- obs_9567d825: mpstat.average=all    0.60    0.00    0.30    0.05    0.00    0.05    0.00    0.00    0.00   99.00
- obs_b57d3668: perf_record.callgraph_samples=402

## 6. 候选瓶颈
### 6.1 CPU 瓶颈
- 置信度: 0.70
- 支持证据: obs_df89bf27
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
- act_a72bd095: /usr/bin/time / 运行时基线 [done]
- act_a2fa4cca: perf stat / 指令效率 [done]
- act_8d73be11: perf stat / 缓存与内存压力 [done]
- act_73b033e0: perf stat / 调度上下文 [done]
- act_a36fc886: pidstat / 调度上下文 [done]
- act_d68a7271: mpstat / 调度上下文 [done]
- act_8f96d6f1: perf record / 热点函数调用链 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=100

## 9. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 10. 产物
- runs/run_44a99ab9/artifacts/act_73b033e0.json
- runs/run_44a99ab9/artifacts/act_73b033e0.stderr.txt
- runs/run_44a99ab9/artifacts/act_73b033e0.stdout.txt
- runs/run_44a99ab9/artifacts/act_8d73be11.json
- runs/run_44a99ab9/artifacts/act_8d73be11.stderr.txt
- runs/run_44a99ab9/artifacts/act_8d73be11.stdout.txt
- runs/run_44a99ab9/artifacts/act_8f96d6f1.json
- runs/run_44a99ab9/artifacts/act_8f96d6f1.stderr.txt
- runs/run_44a99ab9/artifacts/act_8f96d6f1.stdout.txt
- runs/run_44a99ab9/artifacts/act_a2fa4cca.json
- runs/run_44a99ab9/artifacts/act_a2fa4cca.stderr.txt
- runs/run_44a99ab9/artifacts/act_a2fa4cca.stdout.txt
- runs/run_44a99ab9/artifacts/act_a36fc886.json
- runs/run_44a99ab9/artifacts/act_a36fc886.stdout.txt
- runs/run_44a99ab9/artifacts/act_a72bd095.json
- runs/run_44a99ab9/artifacts/act_a72bd095.stderr.txt
- runs/run_44a99ab9/artifacts/act_a72bd095.stdout.txt
- runs/run_44a99ab9/artifacts/act_d68a7271.json
- runs/run_44a99ab9/artifacts/act_d68a7271.stdout.txt
- runs/run_44a99ab9/environment.json
- runs/run_44a99ab9/source_manifest.json
- runs/run_44a99ab9/target.json
