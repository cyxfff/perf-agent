# 性能分析报告

## 1. 执行摘要
当前证据还不足以形成高置信度瓶颈结论。

## 2. 分析目标
- 命令: sh -c n=0; while [ $n -lt 800000 ]; do n=$((n+1)); done
- 可执行文件: 未提供
- 源码目录: 未提供
- 运行信息: verification_rounds=0, actions_executed=5
- 工作目录: 

## 3. 运行环境
- 架构: x86_64
- 内核: 6.2.0-37-generic
- CPU: 13th Gen Intel(R) Core(TM) i5-13600K
- CPU 配置: 物理核 14 / 逻辑核 20
- 内存: 31 GB
- CPU 频率: 800 MHz - 5.10 GHz，当前缩放 86%
- Cache: L1d 544 KiB (14 instances) / L1i 704 KiB (14 instances) / L2 20 MiB (8 instances) / L3 24 MiB (1 instance)
- NUMA: 1 节点
- perf: 可用 simpleperf I command.cpp:262] Simpleperf version 1.build.2e79f5-9147f0
- 调用栈模式: fp, dwarf
- 可用工具: perf, pidstat, mpstat, iostat, addr2line
- 目标执行位置: 设备端
- 目标设备: 10.87.51.151:5555 / XT2503_3
- 设备架构: [Build.BRAND]: [MTK]
- 设备系统: Android [aaudio.mmap_exclusive_policy]: [2] (SDK [aaudio.mmap_policy]: [2])
- 设备后端能力: simpleperf
- 采样后端: android_simpleperf
- 后端选择: 当前目标被识别为设备端命令，使用 10.87.51.151:5555 上的 simpleperf 采样。
- ADB: 可用，已发现 1 台设备
- 目标设备: 10.87.51.151:5555
- 设备选择: 已自动选择 ADB 设备 10.87.51.151:5555（XT2503_3，android，后端 simpleperf），因为它是当前唯一在线的可分析设备。
- 源码映射: addr2line 可用

## 4. 实验设计与执行
- 第 1 轮 [baseline] simpleperf stat / 指令效率: 判断 cycles、instructions 和 IPC 的健康度。当前使用退化事件组合。 事件为 cpu-cycles, instructions, task-clock, cpu-clock。，已退化到当前机器可用方案
- 第 1 轮 [baseline] simpleperf stat / 缓存与内存压力 [1/2]: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 cache-references, cache-misses, L1-dcache-loads, L1-dcache-load-misses, raw-l2d-cache, raw-l2d-cache-refill, stalled-cycles-backend, stalled-cycles-frontend。 第 1/2 批。，已退化到当前机器可用方案
- 第 1 轮 [baseline] simpleperf stat / 缓存与内存压力 [2/2]: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 cache-references, cache-misses, L1-dcache-loads, L1-dcache-load-misses, raw-l2d-cache, raw-l2d-cache-refill, stalled-cycles-backend, stalled-cycles-frontend。 第 2/2 批。，已退化到当前机器可用方案
- 第 1 轮 [baseline] simpleperf stat / 前后端停顿: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 stalled-cycles-frontend, stalled-cycles-backend, cpu-cycles, instructions。，已退化到当前机器可用方案
- 第 1 轮 [baseline] simpleperf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用退化事件组合。 事件为 context-switches, cpu-migrations, page-faults。，已退化到当前机器可用方案

## 5. 证据摘要
- 第 1 轮后，当前最强规则候选为 unknown。 重点 observation 数量 0，热点符号 0 个，时间序列指标 0 个，进程拆账 0 条，线程拆账 0 条。
- 是否需要进一步区分 unknown 与其他候选瓶颈。
- 当前还缺少时间序列证据，尚不能判断瓶颈是否阶段性出现。
- 当前还缺少热点函数级证据，尚不能稳定映射到调用路径。

## 6. 关键观测

## 7. 候选瓶颈

## 8. 源码定位
- 未发现可直接关联的源码位置。

## 9. 二次验证
- 已执行动作:
- act_f2a4b7ee: simpleperf stat / 指令效率 [failed]
- act_19a6f909: simpleperf stat / 缓存与内存压力 [1/2] [failed]
- act_b3184432: simpleperf stat / 缓存与内存压力 [2/2] [failed]
- act_4446a10d: simpleperf stat / 前后端停顿 [failed]
- act_6406776f: simpleperf stat / 调度上下文 [failed]
- 新证据:

## 10. 建议
