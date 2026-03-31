# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.76。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/cpu_bound_demo 700 18000
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/cpu_bound_demo
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
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 3 个，时间序列指标 5 个。
- 重点指标: cache_misses, context_switches, voluntary_context_switches, callgraph_samples, hot_symbol_pct
- 热点符号: main, __cos_fma, __sin_fma
- 时间序列指标: cache_misses, context_switches, cycles, instructions, ipc
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。

## 6. 关键观测
- obs_10e34b8d: time.user_time_sec=0.15
- obs_55573bdf: time.system_time_sec=0.0
- obs_b1155976: time.cpu_utilization_pct=100
- obs_81c6f69e: time.max_rss_kb=4320
- obs_0d15cb31: time.major_faults=0
- obs_244fa175: time.voluntary_context_switches=1
- obs_9a881548: time.involuntary_context_switches=0
- obs_c2221f28: perf_stat.cycles=763080253
- obs_4879545d: perf_stat.instructions=2941663228
- obs_67bbf2e7: perf_stat.cache_references=56737
- obs_325ecd7c: perf_stat.cache_misses=19593
- obs_58cb2042: perf_stat.context_switches=1
- obs_4135abfb: perf_stat.cpu_migrations=0
- obs_c0d9589d: perf_stat.page_faults=169
- obs_c9553e70: mpstat.01=18:00     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_94a4728e: mpstat.01=18:01     all    0.65    0.00    0.25    0.05    0.00    0.10    0.00    0.00    0.00   98.95
- obs_9f27f1dc: mpstat.average=all    0.65    0.00    0.25    0.05    0.00    0.10    0.00    0.00    0.00   98.95
- obs_ed20757c: perf_record.callgraph_samples=161
- obs_edbe75d1: perf_record.hot_symbol_pct=95.4
- obs_de8dba90: perf_record.hot_symbol_pct=48.05
- obs_49854e95: perf_record.hot_symbol_pct=39.87
- obs_11be67de: perf_record.hot_symbol_pct=2.16
- obs_6b500b9e: perf_record.hot_symbol_pct=1.91
- obs_89928187: perf_stat.cycles=494452318
- obs_501b8a54: perf_stat.instructions=1904663765
- obs_a05bb412: perf_stat.cache_misses=24417
- obs_b5d1cd98: perf_stat.context_switches=1
- obs_62bcd051: perf_stat.cycles=268899753
- obs_6beb7dcc: perf_stat.instructions=1036972076
- obs_ae17d3a3: perf_stat.cache_misses=7662
- obs_b7020da5: perf_stat.context_switches=0
- obs_68490e86: perf_stat.ipc=3.8521
- obs_1fe11c27: perf_stat.ipc=3.8564

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.76
- 支持证据: obs_b1155976, obs_68490e86, obs_1fe11c27
- 反证: 无
- 验证状态: 需要进一步验证

## 8. 源码定位
- 热点函数定位: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:23
  依据: perf record / report 显示热点符号 main，该源码位置与热点调用路径直接相关。
  代码: int main(int argc, char** argv) {
- 大规模向量处理: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:9
  依据: 检测到可能参与高频数据处理的容器代码。
  代码: std::vector<double> values(inner_loops, 0.0);
- 热点循环: /home/tchen/agent/perf_agent/examples/cpp/cpu_bound_demo.cpp:11
  依据: 检测到疑似高频计算循环或数学函数调用。
  代码: for (std::size_t round = 0; round < outer_loops; ++round) {

## 9. 二次验证
- 已执行动作:
- act_5e7980dd: /usr/bin/time / 运行时基线 [done]
- act_74927fb1: perf stat / 指令效率 [done]
- act_dc0da6a8: perf stat / 缓存与内存压力 [done]
- act_a33cc6a7: perf stat / 调度上下文 [done]
- act_a31cd2f8: pidstat / 调度上下文 [done]
- act_61aec8d4: mpstat / 调度上下文 [done]
- act_98c39f80: perf record / 热点函数调用链 [done]
- act_c21869b5: perf stat / 时间序列行为 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=100
- CPU 瓶颈: perf_stat.ipc=3.8521
- CPU 瓶颈: perf_stat.ipc=3.8564

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 11. 产物
- runs/run_704a936d/artifacts/act_5e7980dd.json
- runs/run_704a936d/artifacts/act_5e7980dd.stderr.txt
- runs/run_704a936d/artifacts/act_5e7980dd.stdout.txt
- runs/run_704a936d/artifacts/act_61aec8d4.json
- runs/run_704a936d/artifacts/act_61aec8d4.stdout.txt
- runs/run_704a936d/artifacts/act_74927fb1.json
- runs/run_704a936d/artifacts/act_74927fb1.stderr.txt
- runs/run_704a936d/artifacts/act_74927fb1.stdout.txt
- runs/run_704a936d/artifacts/act_98c39f80.json
- runs/run_704a936d/artifacts/act_98c39f80.perf.data
- runs/run_704a936d/artifacts/act_98c39f80.record.stdout.txt
- runs/run_704a936d/artifacts/act_98c39f80.stderr.txt
- runs/run_704a936d/artifacts/act_98c39f80.stdout.txt
- runs/run_704a936d/artifacts/act_a31cd2f8.json
- runs/run_704a936d/artifacts/act_a31cd2f8.stdout.txt
- runs/run_704a936d/artifacts/act_a33cc6a7.json
- runs/run_704a936d/artifacts/act_a33cc6a7.stderr.txt
- runs/run_704a936d/artifacts/act_a33cc6a7.stdout.txt
- runs/run_704a936d/artifacts/act_c21869b5.json
- runs/run_704a936d/artifacts/act_c21869b5.stderr.txt
- runs/run_704a936d/artifacts/act_c21869b5.stdout.txt
- runs/run_704a936d/artifacts/act_dc0da6a8.json
- runs/run_704a936d/artifacts/act_dc0da6a8.stderr.txt
- runs/run_704a936d/artifacts/act_dc0da6a8.stdout.txt
- runs/run_704a936d/environment.json
- runs/run_704a936d/source_manifest.json
- runs/run_704a936d/target.json
