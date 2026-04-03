# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.90。

## 2. 分析目标
- 命令: examples/bin/cpu_bound_demo 10 100
- 可执行文件: examples/bin/cpu_bound_demo
- 源码目录: 未提供
- 运行信息: verification_rounds=1, actions_executed=9
- 工作目录: 

## 3. 运行环境
- 架构: x86_64
- 内核: 6.2.0-37-generic
- CPU: 13th Gen Intel(R) Core(TM) i5-13600K
- CPU 配置: 物理核 14 / 逻辑核 20
- 内存: 31 GB
- CPU 频率: 800 MHz - 5.10 GHz，当前缩放 89%
- Cache: L1d 544 KiB (14 instances) / L1i 704 KiB (14 instances) / L2 20 MiB (8 instances) / L3 24 MiB (1 instance)
- NUMA: 1 节点
- perf: 可用 perf version 6.2.16
- 调用栈模式: fp, dwarf, lbr
- 可用工具: perf, pidstat, mpstat, iostat, addr2line
- ADB: 可用，已发现 1 台设备
- 目标设备: 10.87.51.151:5555
- 设备选择: 已自动选择 ADB 设备 10.87.51.151:5555（XT2503_3，android，后端 simpleperf），因为它是当前唯一在线的可分析设备。
- PMU: cpu_atom, cpu_core
- 源码映射: addr2line 可用

## 4. 实验设计与执行
- 第 1 轮 [baseline] /usr/bin/time / 运行时基线: 用 /usr/bin/time -v 建立程序运行基线。
- 第 1 轮 [baseline] perf stat / 指令效率: 判断 cycles、instructions 和 IPC 的健康度。当前使用首选事件组合。 事件为 cycles, Instructions, task-clock, cpu-clock, SLOTS。
- 第 1 轮 [baseline] perf stat / 缓存与内存压力 [1/2]: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 cache-references, cache-misses, mem_load_retired.l1_hit, mem_load_retired.l1_miss, l2_rqsts.references, L2_RQSTS.MISS, longest_lat_cache.reference, longest_lat_cache.miss, topdown-be-bound。 第 1/2 批。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 缓存与内存压力 [2/2]: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 cache-references, cache-misses, mem_load_retired.l1_hit, mem_load_retired.l1_miss, l2_rqsts.references, L2_RQSTS.MISS, longest_lat_cache.reference, longest_lat_cache.miss, topdown-be-bound。 第 2/2 批。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 前后端停顿: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 SLOTS, topdown-retiring, topdown-bad-spec, topdown-fe-bound, topdown-be-bound, cycles, Instructions。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用首选事件组合。 事件为 context-switches, cpu-migrations, page-faults, mem_inst_retired.lock_loads。
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 cpu_bound。 重点 observation 数量 10，热点符号 6 个，时间序列指标 0 个，进程拆账 1 条，线程拆账 1 条。
- 重点指标: voluntary_context_switches, cache_misses, context_switches, hot_symbol_pct
- 热点符号: asm_exc_page_fault, _dl_start_user, _dl_init, call_init.part.0
- 进程级样本拆账: cpu_bound_demo pid=3802059 100.00%
- 线程级样本拆账: cpu_bound_demo pid/tid=3802059/3802059 100.00%
- 是否需要进一步区分 cpu_bound 与其他候选瓶颈。
- 当前还缺少时间序列证据，尚不能判断瓶颈是否阶段性出现。

## 6. 关键观测
- obs_0a0bac2f: time.user_time_sec=0.0
- obs_521f0b81: time.system_time_sec=0.0
- obs_1ebd3ddf: time.cpu_utilization_pct=95
- obs_25059de9: time.max_rss_kb=4160
- obs_61c38382: time.major_faults=0
- obs_7dde8bdb: time.voluntary_context_switches=1
- obs_4ec9302c: time.involuntary_context_switches=0
- obs_a589a255: time.elapsed_time_sec=0.0
- obs_7ebc1c78: perf_stat.cycles=2474794
- obs_91de3290: perf_stat.instructions=4333444
- obs_15582db8: perf_stat.msec=0.49
- obs_e6324b5b: perf_stat.slots=14848764
- obs_99d4f36d: perf_stat.seconds=0.000599078
- obs_7fca56b4: perf_stat.ipc=1.751
- obs_01a9fb4e: perf_stat.cpi=0.5711
- obs_f04bcfca: perf_stat.cache_references=46470
- obs_3c77151c: perf_stat.cache_misses=9454
- obs_2d293fe4: perf_stat.l1_hit_count=1050516
- obs_babea6ae: perf_stat.l1_miss_count=17820
- obs_ac41074e: perf_stat.l2_access_count=158222
- obs_f01c43cd: perf_stat.l2_miss_count=49749
- obs_19b4d566: perf_stat.llc_access_count=46470
- obs_6645df32: perf_stat.llc_miss_count=9454
- obs_a58daf74: perf_stat.seconds=0.000595376
- obs_e295469a: perf_stat.cache_miss_rate_pct=20.3443
- obs_c73b9483: perf_stat.l1_miss_rate_pct=1.668
- obs_dec7641f: perf_stat.l2_miss_rate_pct=31.4425
- obs_20f06b11: perf_stat.llc_miss_rate_pct=20.3443
- obs_5a4b2391: perf_stat.seconds=0.000597158
- obs_5f67548c: perf_stat.slots=14158230
- obs_dac0af1c: perf_stat.cycles=2359705
- obs_1d157c45: perf_stat.instructions=4363930
- obs_040f12ba: perf_stat.seconds=0.000550988
- obs_49e175f8: perf_stat.ipc=1.8494
- obs_f441130e: perf_stat.cpi=0.5407
- obs_88b2d8f2: perf_stat.context_switches=0
- obs_1abe1ebc: perf_stat.cpu_migrations=0
- obs_0c278515: perf_stat.page_faults=132
- obs_25f77e6a: perf_stat.lock_loads=9001
- obs_24d67c6f: perf_stat.seconds=0.000601796
- obs_5a70e6c1: mpstat.15=27:30     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_38729b5e: mpstat.15=27:31     all    1.00    0.00    0.80    0.15    0.00    0.00    0.00    0.00    0.00   98.05
- obs_2d9e7971: mpstat.average=all    1.00    0.00    0.80    0.15    0.00    0.00    0.00    0.00    0.00   98.05
- obs_7eaea12d: perf_record.hot_symbol_pct=97.93
- obs_60904443: perf_record.hot_symbol_pct=64.98
- obs_794a04e0: perf_record.hot_symbol_pct=64.98
- obs_afd7928c: perf_record.hot_symbol_pct=64.98
- obs_8770efe6: perf_record.hot_symbol_pct=64.98
- obs_722d9a39: perf_record.hot_symbol_pct=64.98
- obs_954218aa: perf_record.hot_symbol_pct=64.98
- obs_e55ce26d: perf_record.hot_symbol_pct=35.02
- obs_c644a0da: perf_record.callgraph_samples=8
- obs_1bcb6478: perf_record.process_sample_count=2
- obs_ca78de7e: perf_record.process_sample_pct=100.0
- obs_a7b83e66: perf_record.thread_sample_count=2
- obs_3d53443b: perf_record.thread_sample_pct=100.0
- obs_d5d329d1: perf_record.hot_frame_sample_pct=100.0

## 7. 候选瓶颈
### 7.1 CPU 瓶颈
- 置信度: 0.90
- 支持证据: obs_1ebd3ddf, obs_7fca56b4, obs_49e175f8, obs_ca78de7e, obs_3d53443b
- 反证: 无
- 验证状态: 证据基本充分

## 8. 源码定位
- 未发现可直接关联的源码位置。

## 9. 二次验证
- 已执行动作:
- act_8903a15a: /usr/bin/time / 运行时基线 [done]
- act_277daadc: perf stat / 指令效率 [done]
- act_147cd838: perf stat / 缓存与内存压力 [1/2] [done]
- act_f2ab2b6b: perf stat / 缓存与内存压力 [2/2] [done]
- act_380bed26: perf stat / 前后端停顿 [done]
- act_c56034d7: perf stat / 调度上下文 [done]
- act_221ce3bb: pidstat / 调度上下文 [done]
- act_d990dd2d: mpstat / 调度上下文 [done]
- act_936eaa44: perf record / 热点函数调用链 [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=95
- CPU 瓶颈: perf_stat.ipc=1.751
- CPU 瓶颈: perf_stat.ipc=1.8494
- CPU 瓶颈: perf_record.process_sample_pct=100.0
- CPU 瓶颈: perf_record.thread_sample_pct=100.0

## 10. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。
