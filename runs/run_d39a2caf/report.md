# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 分支预测失误，置信度为 0.95。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/phased_cache_wave_demo 8 140 128
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/phased_cache_wave_demo
- 源码目录: /home/tchen/agent/perf_agent/examples/cpp
- 运行信息: verification_rounds=1, actions_executed=10
- 工作目录: 

## 3. 运行环境
- 架构: x86_64
- 内核: 6.2.0-37-generic
- CPU: 13th Gen Intel(R) Core(TM) i5-13600K
- CPU 配置: 物理核 14 / 逻辑核 20
- 内存: 31 GB
- CPU 频率: 800 MHz - 5.10 GHz，当前缩放 87%
- Cache: L1d 544 KiB (14 instances) / L1i 704 KiB (14 instances) / L2 20 MiB (8 instances) / L3 24 MiB (1 instance)
- NUMA: 1 节点
- perf: 可用 perf version 6.2.16
- 调用栈模式: fp, dwarf, lbr
- 可用工具: perf, pidstat, mpstat, iostat, addr2line
- PMU: cpu_atom, cpu_core
- 源码映射: addr2line 可用

## 4. 实验设计与执行
- 第 1 轮 [baseline] /usr/bin/time / 运行时基线: 用 /usr/bin/time -v 建立程序运行基线。
- 第 1 轮 [baseline] perf stat / 指令效率: 判断 cycles、instructions 和 IPC 的健康度。当前使用首选事件组合。 事件为 cycles, Instructions, task-clock, cpu-clock, SLOTS。
- 第 1 轮 [baseline] perf stat / 缓存与内存压力: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 cache-references, cache-misses, longest_lat_cache.reference, longest_lat_cache.miss, topdown-be-bound。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 前后端停顿: 判断 cache miss、内存压力以及前后端停顿。当前使用退化事件组合。 事件为 SLOTS, topdown-retiring, topdown-bad-spec, topdown-fe-bound, topdown-be-bound, cycles, Instructions。，已退化到当前机器可用方案
- 第 1 轮 [baseline] perf stat / 调度上下文: 判断调度切换、迁移与系统级 CPU 上下文。当前使用退化事件组合。 事件为 context-switches, cpu-migrations, page-faults。，已退化到当前机器可用方案
- 第 1 轮 [baseline] pidstat / 调度上下文: 补充进程级 CPU 与等待拆分。
- 第 1 轮 [baseline] mpstat / 调度上下文: 补充系统级 CPU 与调度上下文。
- 第 2 轮 [verification] perf record / 热点函数调用链: 使用 perf record 采样热点函数和调用链，调用栈模式为 fp。
- 第 2 轮 [verification] perf stat / 时间序列行为 [1/2]: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。 第 1/2 批。，已退化到当前机器可用方案
- 第 2 轮 [verification] perf stat / 时间序列行为 [2/2]: 使用 perf stat interval mode 观察 IPC、cache 和调度指标随时间的波动。 第 2/2 批。，已退化到当前机器可用方案

## 5. 证据摘要
- 第 2 轮后，当前最强规则候选为 branch_mispredict。 重点 observation 数量 10，热点符号 9 个，时间序列指标 13 个，进程拆账 1 条，线程拆账 1 条。
- 重点指标: cache_misses
- 热点符号: main
- 时间序列指标: branch_miss_rate_pct, branch_misses, branches, cache_miss_rate_pct, cache_misses, cache_references
- 进程级样本拆账: phased_cache_wa pid=3652075 100.00%
- 线程级样本拆账: phased_cache_wa pid/tid=3652075/3652075 100.00%
- 是否需要进一步区分 branch_mispredict 与其他候选瓶颈。

## 6. 关键观测
- obs_e1d5646c: time.user_time_sec=3.02
- obs_6877815c: time.system_time_sec=0.19
- obs_dc13850e: time.cpu_utilization_pct=99
- obs_b6d372c7: time.max_rss_kb=134636
- obs_7547bf73: time.major_faults=0
- obs_4878919d: time.voluntary_context_switches=1
- obs_89cfcf6f: time.involuntary_context_switches=18
- obs_7862cedb: time.elapsed_time_sec=3.22
- obs_359c149f: perf_stat.cycles=16264987629
- obs_a33e3afa: perf_stat.instructions=25620732480
- obs_7d40940c: perf_stat.msec=3193.57
- obs_91c8b962: perf_stat.slots=97585087830
- obs_3b599975: perf_stat.seconds=3.194077926
- obs_f8b9c193: perf_stat.ipc=1.5752
- obs_ebe3928c: perf_stat.cache_references=426401167
- obs_4b983868: perf_stat.cache_misses=336087092
- obs_47bf83ba: perf_stat.llc_access_count=426401167
- obs_f3f040db: perf_stat.llc_miss_count=336087092
- obs_6e7c4326: perf_stat.seconds=3.188697679
- obs_adb20a29: perf_stat.cache_miss_rate_pct=78.8195
- obs_5579c565: perf_stat.llc_miss_rate_pct=78.8195
- obs_22e3dad8: perf_stat.slots=99113083866
- obs_be679938: perf_stat.cycles=16521025923
- obs_8f0671e7: perf_stat.instructions=25638082739
- obs_a39e4fa7: perf_stat.seconds=3.240248841
- obs_9e9db42f: perf_stat.ipc=1.5518
- obs_fefaad96: perf_stat.context_switches=39
- obs_058f60a9: perf_stat.cpu_migrations=2
- obs_0b163c19: perf_stat.page_faults=262293
- obs_f68d800a: perf_stat.seconds=3.216696543
- obs_8d994c89: mpstat.03=29:25     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_6d5db7c1: mpstat.03=29:26     all    1.05    0.00    0.30    1.60    0.00    0.10    0.00    0.00    0.00   96.95
- obs_fb8475d0: mpstat.average=all    1.05    0.00    0.30    1.60    0.00    0.10    0.00    0.00    0.00   96.95
- obs_554422da: perf_record.hot_symbol_pct=99.98
- obs_e5fb88b1: perf_record.hot_symbol_pct=99.98
- obs_9ee061bd: perf_record.hot_symbol_pct=99.98
- obs_89be227f: perf_record.hot_symbol_pct=98.48
- obs_351c52d9: perf_record.hot_symbol_pct=15.65
- obs_3489f9dd: perf_record.hot_symbol_pct=15.23
- obs_601d64e0: perf_record.hot_symbol_pct=4.69
- obs_387b8469: perf_record.hot_symbol_pct=3.93
- obs_ab0f37b3: perf_record.callgraph_samples=12789
- obs_f34a015e: perf_record.process_sample_count=12784
- obs_6b9db48a: perf_record.process_sample_pct=100.0
- obs_a1a12b79: perf_record.thread_sample_count=12784
- obs_0741c71f: perf_record.thread_sample_pct=100.0
- obs_64486f94: perf_record.hot_frame_sample_pct=51.2909
- obs_a27c343e: perf_record.hot_frame_sample_pct=6.2197
- obs_36f291f4: perf_record.hot_frame_sample_pct=2.0654
- obs_ef4290f3: perf_record.hot_frame_sample_pct=1.6742
- obs_7bf0eaa8: perf_record.hot_frame_sample_pct=1.5021
- obs_fcdbe6b4: perf_record.hot_frame_sample_pct=1.4552
- obs_dd25b293: perf_record.hot_frame_sample_pct=0.6494
- obs_56e7ef64: perf_record.hot_frame_sample_pct=0.6259
- obs_81dc5eeb: perf_record.hot_frame_sample_pct=0.6259
- obs_d4d52e1c: perf_record.hot_frame_sample_pct=0.6181
- obs_792d283c: perf_stat.cycles=492445771
- obs_4c6b8f2b: perf_stat.instructions=1785878873
- obs_7c3e2248: perf_stat.cache_references=41200
- obs_40298718: perf_stat.cache_misses=19110
- obs_ef399efd: perf_stat.cycles=510745518
- obs_453fbd6d: perf_stat.instructions=996180741
- obs_add1253e: perf_stat.cache_references=9405298
- obs_4e8f59ed: perf_stat.cache_misses=7876971
- obs_e305734a: perf_stat.cycles=510742227
- obs_1562bc68: perf_stat.instructions=157253839
- obs_efb1cfd0: perf_stat.cache_references=20714707
- obs_eacb9f94: perf_stat.cache_misses=16690760
- obs_4e1c3f44: perf_stat.cycles=510761819
- obs_b1685d57: perf_stat.instructions=180962782
- obs_bfc64e8b: perf_stat.cache_references=22450391
- obs_755529a4: perf_stat.cache_misses=17239901
- obs_e19c8936: perf_stat.cycles=510925065
- obs_6ebfff61: perf_stat.instructions=1862629167
- obs_82d44bca: perf_stat.cache_references=105384
- obs_0eb74951: perf_stat.cache_misses=50112
- obs_199a407d: perf_stat.cycles=510822555
- obs_44f6410b: perf_stat.instructions=1006756422
- obs_1f4eb140: perf_stat.cache_references=9880017
- obs_d32e4cb6: perf_stat.cache_misses=7975791
- obs_e6b52bd9: perf_stat.cycles=511035609
- obs_ec8e1bd7: perf_stat.instructions=157282609
- obs_a14b528d: perf_stat.cache_references=20357008
- obs_fe03b536: perf_stat.cache_misses=16566689
- obs_02782fcd: perf_stat.cycles=511009145
- obs_8f40b4f1: perf_stat.instructions=177230017
- obs_dad0e83a: perf_stat.cache_references=22023329
- obs_9a8ecfda: perf_stat.cache_misses=17131781
- obs_bcee17a1: perf_stat.cycles=510945295
- obs_a0fad5eb: perf_stat.instructions=1862819816
- obs_2fdd0f67: perf_stat.cache_references=119894
- obs_a4678ff5: perf_stat.cache_misses=61447
- obs_78dfabb4: perf_stat.cycles=510956499
- obs_d66b4ffc: perf_stat.instructions=1009722315
- obs_90b4417f: perf_stat.cache_references=9870966
- obs_8b7ea76c: perf_stat.cache_misses=7977323
- obs_4d57f0af: perf_stat.cycles=510813211
- obs_cae90cb4: perf_stat.instructions=147509985
- obs_84269560: perf_stat.cache_references=17455285
- obs_92336e9c: perf_stat.cache_misses=14313340
- obs_6286bf38: perf_stat.cycles=510968057
- obs_42e228bf: perf_stat.instructions=158486526
- obs_517fdfc5: perf_stat.cache_references=20432394
- obs_531a3eaa: perf_stat.cache_misses=16633504
- obs_9af81b6f: perf_stat.cycles=510885350
- obs_831141bf: perf_stat.instructions=1667146459
- obs_82a83043: perf_stat.cache_references=2352165
- obs_917ab534: perf_stat.cache_misses=1995380
- obs_d03fb41a: perf_stat.cycles=510959783
- obs_bea782b7: perf_stat.instructions=1223178002
- obs_54220cb6: perf_stat.cache_references=6822014
- obs_f7d3891d: perf_stat.cache_misses=5683553
- obs_e3d80ecc: perf_stat.cycles=511008169
- obs_54cfbc79: perf_stat.instructions=162241786
- obs_3c6e1d84: perf_stat.cache_references=22822998
- obs_c9d071cd: perf_stat.cache_misses=17543173
- obs_f41d707b: perf_stat.cycles=511251992
- obs_aa64b72b: perf_stat.instructions=160384638
- obs_c45ed803: perf_stat.cache_references=21031573
- obs_b61e06a1: perf_stat.cache_misses=16940741
- obs_01755189: perf_stat.cycles=510722108
- obs_a20b7bc3: perf_stat.instructions=1717746442
- obs_351c2fd7: perf_stat.cache_references=2159093
- obs_b0f721e6: perf_stat.cache_misses=1621071
- obs_d17effb5: perf_stat.cycles=510999907
- obs_2391f5bb: perf_stat.instructions=1175816902
- obs_fa5c0bb1: perf_stat.cache_references=7592658
- obs_5008dc1d: perf_stat.cache_misses=6234618
- obs_e3aa9710: perf_stat.cycles=510649873
- obs_4cd8b1e8: perf_stat.instructions=159325451
- obs_a6d02c0b: perf_stat.cache_references=22076388
- obs_3e0411da: perf_stat.cache_misses=17136151
- obs_cb43d9c8: perf_stat.cycles=510925614
- obs_eda5466f: perf_stat.instructions=159389975
- obs_30ae2231: perf_stat.cache_references=20835995
- obs_d1408c16: perf_stat.cache_misses=16803599
- obs_2d7b778c: perf_stat.cycles=510700704
- obs_35d43fe2: perf_stat.instructions=1734566402
- obs_994c6fa7: perf_stat.cache_references=1922102
- obs_87e589b9: perf_stat.cache_misses=1438574
- obs_8137bb0a: perf_stat.cycles=510831326
- obs_a6045385: perf_stat.instructions=1159816965
- obs_260932b3: perf_stat.cache_references=7081160
- obs_dbdbab2a: perf_stat.cache_misses=6113984
- obs_fac97604: perf_stat.cycles=511045137
- obs_302afd95: perf_stat.instructions=156792317
- obs_aa6e60a0: perf_stat.cache_references=19834288
- obs_64e90027: perf_stat.cache_misses=16388015
- obs_d52cf830: perf_stat.cycles=511202783
- obs_a405c60c: perf_stat.instructions=162714441
- obs_4f475c4b: perf_stat.cache_references=23183426
- obs_d838c955: perf_stat.cache_misses=17707345
- obs_bcbe7c61: perf_stat.cycles=510825726
- obs_1217fbe8: perf_stat.instructions=1749159293
- obs_6109fb52: perf_stat.cache_references=1729438
- obs_44173f89: perf_stat.cache_misses=1293755
- obs_fc32421e: perf_stat.cycles=510905560
- obs_63b4d075: perf_stat.instructions=1143291398
- obs_1221b28b: perf_stat.cache_references=8275431
- obs_24f153d0: perf_stat.cache_misses=6656714
- obs_46f8f39d: perf_stat.cycles=511012487
- obs_ce1368a5: perf_stat.instructions=159739424
- obs_6f176a47: perf_stat.cache_references=21405079
- obs_946d1db2: perf_stat.cache_misses=17009824
- obs_54a8f6d7: perf_stat.cycles=511155031
- obs_069ff270: perf_stat.instructions=161492502
- obs_6a1e915e: perf_stat.cache_references=22460761
- obs_4d6ca837: perf_stat.cache_misses=17410145
- obs_288c812e: perf_stat.cycles=510883695
- obs_113c9c35: perf_stat.instructions=1788233276
- obs_a599c06a: perf_stat.cache_references=1151198
- obs_32789ef9: perf_stat.cache_misses=856755
- obs_1143a0b3: perf_stat.cycles=511061528
- obs_3e9b2f15: perf_stat.instructions=1103666916
- obs_c4cced64: perf_stat.cache_references=8824978
- obs_07481749: perf_stat.cache_misses=7058685
- obs_fc2effc1: perf_stat.cycles=510994843
- obs_7b4428b7: perf_stat.instructions=161469199
- obs_dadf03db: perf_stat.cache_references=22983825
- obs_e74f339c: perf_stat.cache_misses=17520851
- obs_8a21ee0f: perf_stat.cycles=511178872
- obs_7ba96ccd: perf_stat.instructions=161099202
- obs_8c28176b: perf_stat.cache_references=21993120
- obs_95b0d4b8: perf_stat.cache_misses=17236477
- obs_8070e974: perf_stat.cycles=17949005
- obs_cd1bf31f: perf_stat.instructions=51259157
- obs_54418047: perf_stat.cache_references=311816
- obs_b5e0c02b: perf_stat.cache_misses=231758
- obs_b491887d: perf_stat.ipc=3.6265
- obs_b5777613: perf_stat.cache_miss_rate_pct=46.3835
- obs_c8996c60: perf_stat.ipc=1.9504
- obs_42efa59c: perf_stat.cache_miss_rate_pct=83.7504
- obs_854aedab: perf_stat.ipc=0.3079
- obs_1ceb14bd: perf_stat.cache_miss_rate_pct=80.5744
- obs_c53483e5: perf_stat.ipc=0.3543
- obs_21348b80: perf_stat.cache_miss_rate_pct=76.7911
- obs_1e1a9109: perf_stat.ipc=3.6456
- obs_e5f9bb72: perf_stat.cache_miss_rate_pct=47.5518
- obs_75469cf4: perf_stat.ipc=1.9709
- obs_53430532: perf_stat.cache_miss_rate_pct=80.7265
- obs_94854553: perf_stat.ipc=0.3078
- obs_a2d216cf: perf_stat.cache_miss_rate_pct=81.3808
- obs_b8066c93: perf_stat.ipc=0.3468
- obs_9156310d: perf_stat.cache_miss_rate_pct=77.7892
- obs_1297724b: perf_stat.ipc=3.6458
- obs_7dcc38da: perf_stat.cache_miss_rate_pct=51.2511
- obs_a1c01169: perf_stat.ipc=1.9761
- obs_9fcedf52: perf_stat.cache_miss_rate_pct=80.816
- obs_533ed393: perf_stat.ipc=0.2888
- obs_d808275d: perf_stat.cache_miss_rate_pct=82.0
- obs_d517421a: perf_stat.ipc=0.3102
- obs_25ed7a09: perf_stat.cache_miss_rate_pct=81.4075
- obs_00881e5d: perf_stat.ipc=3.2632
- obs_a2dbfd2a: perf_stat.cache_miss_rate_pct=84.8316
- obs_ef9648db: perf_stat.ipc=2.3939
- obs_303d1309: perf_stat.cache_miss_rate_pct=83.312
- obs_2fb2aef8: perf_stat.ipc=0.3175
- obs_e89cef36: perf_stat.cache_miss_rate_pct=76.8662
- obs_6afe3258: perf_stat.ipc=0.3137
- obs_5a307f6a: perf_stat.cache_miss_rate_pct=80.5491
- obs_87c47a1c: perf_stat.ipc=3.3634
- obs_124b839b: perf_stat.cache_miss_rate_pct=75.0811
- obs_444a2659: perf_stat.ipc=2.301
- obs_431846d7: perf_stat.cache_miss_rate_pct=82.1138
- obs_3b3943fe: perf_stat.ipc=0.312
- obs_09e9e8ac: perf_stat.cache_miss_rate_pct=77.6221
- obs_12255dbd: perf_stat.ipc=0.312
- obs_9bad2b2f: perf_stat.cache_miss_rate_pct=80.647
- obs_d9c985de: perf_stat.ipc=3.3964
- obs_59ae9281: perf_stat.cache_miss_rate_pct=74.8438
- obs_31919a46: perf_stat.ipc=2.2704
- obs_5f9caec0: perf_stat.cache_miss_rate_pct=86.3416
- obs_c33b768a: perf_stat.ipc=0.3068
- obs_dce9aa46: perf_stat.cache_miss_rate_pct=82.6247
- obs_072247f5: perf_stat.ipc=0.3183
- obs_6eaba41e: perf_stat.cache_miss_rate_pct=76.3793
- obs_91414b2a: perf_stat.ipc=3.4242
- obs_f5660a92: perf_stat.cache_miss_rate_pct=74.8078
- obs_04f321a1: perf_stat.ipc=2.2378
- obs_354d1742: perf_stat.cache_miss_rate_pct=80.4395
- obs_dca8a497: perf_stat.ipc=0.3126
- obs_15d93309: perf_stat.cache_miss_rate_pct=79.4663
- obs_854feeb3: perf_stat.ipc=0.3159
- obs_8a1130c3: perf_stat.cache_miss_rate_pct=77.5136
- obs_774de375: perf_stat.ipc=3.5003
- obs_bafb4554: perf_stat.cache_miss_rate_pct=74.4229
- obs_2ed35be3: perf_stat.ipc=2.1596
- obs_46c15845: perf_stat.cache_miss_rate_pct=79.9853
- obs_7d2baad7: perf_stat.ipc=0.316
- obs_b3f68503: perf_stat.cache_miss_rate_pct=76.2312
- obs_d35fc9dc: perf_stat.ipc=0.3152
- obs_05dc0d0f: perf_stat.cache_miss_rate_pct=78.3721
- obs_800a52dc: perf_stat.ipc=2.8558
- obs_13f63a50: perf_stat.cache_miss_rate_pct=74.3252
- obs_7047a92f: perf_stat.llc_access_count=38706
- obs_6a51e78d: perf_stat.llc_miss_count=16897
- obs_157d7a07: perf_stat.branches=247506197
- obs_e7f74cf3: perf_stat.branch_misses=1227645
- obs_71b84126: perf_stat.context_switches=2
- obs_7656a3d5: perf_stat.llc_access_count=9969370
- obs_fbfc4cc8: perf_stat.llc_miss_count=8056618
- obs_659aa642: perf_stat.branches=143884850
- obs_531e5cdb: perf_stat.branch_misses=487324
- obs_518e926e: perf_stat.context_switches=1
- obs_9af4c266: perf_stat.llc_access_count=22944944
- obs_60ea7084: perf_stat.llc_miss_count=17500370
- obs_1e3e9033: perf_stat.branches=14672828
- obs_5375762f: perf_stat.branch_misses=285
- obs_9a89d193: perf_stat.context_switches=1
- obs_5839d43d: perf_stat.llc_access_count=21795180
- obs_25bfac61: perf_stat.llc_miss_count=16755423
- obs_f663ef92: perf_stat.branches=26520439
- obs_15efb835: perf_stat.branch_misses=17035
- obs_430b3882: perf_stat.context_switches=0
- obs_5897217d: perf_stat.llc_access_count=3431
- obs_c429ddc7: perf_stat.llc_miss_count=323
- obs_23e5c3ce: perf_stat.branches=247644510
- obs_ccbb26e5: perf_stat.branch_misses=1251724
- obs_ceb9b57c: perf_stat.context_switches=0
- obs_9ff6e821: perf_stat.llc_access_count=9801014
- obs_4b4fdf29: perf_stat.llc_miss_count=8233453
- obs_59b8295a: perf_stat.branches=138531596
- obs_cc4c6b66: perf_stat.branch_misses=441864
- obs_1202724e: perf_stat.context_switches=0
- obs_0dd9c858: perf_stat.llc_access_count=22683181
- obs_84cff2bd: perf_stat.llc_miss_count=17439463
- obs_ab7776b9: perf_stat.branches=14668100
- obs_fa189cff: perf_stat.branch_misses=201
- obs_79d4805f: perf_stat.context_switches=0
- obs_f23d19f4: perf_stat.llc_access_count=21236171
- obs_c1d379fc: perf_stat.llc_miss_count=16338567
- obs_6551782a: perf_stat.branches=31260569
- obs_b0102f1b: perf_stat.branch_misses=28680
- obs_726679e6: perf_stat.context_switches=0
- obs_ca607196: perf_stat.llc_access_count=3082
- obs_3d6d2e38: perf_stat.llc_miss_count=383
- obs_4c0c997f: perf_stat.branches=247488341
- obs_6d9f4a2a: perf_stat.branch_misses=1257337
- obs_ef06e89d: perf_stat.context_switches=0
- obs_a580bbe4: perf_stat.llc_access_count=9633951
- obs_c682c614: perf_stat.llc_miss_count=8345484
- obs_762f041f: perf_stat.branches=133739592
- obs_8513d69a: perf_stat.branch_misses=423162
- obs_ce67365c: perf_stat.context_switches=0
- obs_0e2eb499: perf_stat.llc_access_count=21966852
- obs_07e978e3: perf_stat.llc_miss_count=17210278
- obs_ad13c6ef: perf_stat.branches=14576123
- obs_f2793329: perf_stat.branch_misses=357
- obs_ca8e5fc5: perf_stat.context_switches=2
- obs_d002c689: perf_stat.llc_access_count=20734005
- obs_39cbe307: perf_stat.llc_miss_count=16088299
- obs_feff4c67: perf_stat.branches=33455592
- obs_b9dbf789: perf_stat.branch_misses=35719
- obs_c12dac6d: perf_stat.context_switches=1
- obs_2bd3aebe: perf_stat.llc_access_count=4147
- obs_0bbbb8b0: perf_stat.llc_miss_count=453
- obs_292e74be: perf_stat.branches=247448517
- obs_0fa896b3: perf_stat.branch_misses=1261476
- obs_baf0ebc0: perf_stat.context_switches=1
- obs_d2f3b4d5: perf_stat.llc_access_count=11078392
- obs_702873f0: perf_stat.llc_miss_count=8926305
- obs_9c3d4f71: perf_stat.branches=131525457
- obs_edba39a2: perf_stat.branch_misses=414130
- obs_33857e9f: perf_stat.context_switches=1
- obs_ba9b59c3: perf_stat.llc_access_count=22911950
- obs_e10b5135: perf_stat.llc_miss_count=17534561
- obs_bfed95f1: perf_stat.branches=14743294
- obs_d6d0bd43: perf_stat.branch_misses=252
- obs_90f54e39: perf_stat.context_switches=0
- obs_2d564cda: perf_stat.llc_access_count=20715185
- obs_5faf8d87: perf_stat.llc_miss_count=15785609
- obs_96ac18c6: perf_stat.branches=43138831
- obs_4487581b: perf_stat.branch_misses=75361
- obs_79cce217: perf_stat.context_switches=0
- obs_3d4f15a2: perf_stat.llc_access_count=4326
- obs_83ba0d10: perf_stat.llc_miss_count=739
- obs_2aa630d0: perf_stat.branches=247431390
- obs_77782149: perf_stat.branch_misses=1267550
- obs_da824abe: perf_stat.context_switches=0
- obs_8f40e999: perf_stat.llc_access_count=12218668
- obs_6abd7098: perf_stat.llc_miss_count=9730248
- obs_99a86403: perf_stat.branches=122335654
- obs_25fa3806: perf_stat.branch_misses=369470
- obs_440bacbb: perf_stat.context_switches=0
- obs_fa9bfce5: perf_stat.llc_access_count=23146097
- obs_00e23e38: perf_stat.llc_miss_count=17699595
- obs_6f82f588: perf_stat.branches=14806552
- obs_6d73b9be: perf_stat.branch_misses=148
- obs_e9fb467f: perf_stat.context_switches=0
- obs_0c8c4970: perf_stat.llc_access_count=19614524
- obs_e19456c0: perf_stat.llc_miss_count=14975421
- obs_804ec9b1: perf_stat.branches=54088805
- obs_5f378751: perf_stat.branch_misses=122163
- obs_45404ef4: perf_stat.context_switches=0
- obs_d8c84257: perf_stat.llc_access_count=3603
- obs_0396b423: perf_stat.llc_miss_count=533
- obs_68f9a7e0: perf_stat.branches=247000222
- obs_0ff51a9e: perf_stat.branch_misses=1274444
- obs_e2d036aa: perf_stat.context_switches=1
- obs_50a32f28: perf_stat.llc_access_count=12688562
- obs_1ebc0d76: perf_stat.llc_miss_count=10279495
- obs_a27b2946: perf_stat.branches=111487883
- obs_38bb3521: perf_stat.branch_misses=317726
- obs_e441316b: perf_stat.context_switches=1
- obs_9f01ee13: perf_stat.llc_access_count=22692734
- obs_3c0e72b0: perf_stat.llc_miss_count=17491885
- obs_5e6e8123: perf_stat.branches=14736929
- obs_386bcff7: perf_stat.branch_misses=154
- obs_c25f03a1: perf_stat.context_switches=0
- obs_2f9656bd: perf_stat.llc_access_count=18324740
- obs_cddc81ef: perf_stat.llc_miss_count=14169272
- obs_40ab59d5: perf_stat.branches=62080879
- obs_db37565d: perf_stat.branch_misses=161313
- obs_c02bea38: perf_stat.context_switches=0
- obs_32e14691: perf_stat.llc_access_count=4895
- obs_f2118b25: perf_stat.llc_miss_count=816
- obs_84ed5313: perf_stat.branches=247048161
- obs_077872d4: perf_stat.branch_misses=1281906
- obs_f5a8bf69: perf_stat.context_switches=1
- obs_7eb33e46: perf_stat.llc_access_count=14291228
- obs_252484d8: perf_stat.llc_miss_count=11200224
- obs_967ffc91: perf_stat.branches=103660357
- obs_e368e81d: perf_stat.branch_misses=281555
- obs_8d1a9ac1: perf_stat.context_switches=0
- obs_8daa445b: perf_stat.llc_access_count=22753282
- obs_302b2815: perf_stat.llc_miss_count=17516897
- obs_3d1f17ba: perf_stat.branches=14784855
- obs_62594f3a: perf_stat.branch_misses=157
- obs_9ede1128: perf_stat.context_switches=0
- obs_dd93a4e2: perf_stat.llc_access_count=17723172
- obs_81e59384: perf_stat.llc_miss_count=13500651
- obs_be5669f5: perf_stat.branches=73353575
- obs_99a28e2b: perf_stat.branch_misses=229448
- obs_bc237660: perf_stat.context_switches=2
- obs_a82a061d: perf_stat.llc_access_count=2867
- obs_6a503d80: perf_stat.llc_miss_count=275
- obs_c6d8e599: perf_stat.branches=247077434
- obs_1b8afee7: perf_stat.branch_misses=1265235
- obs_216b1b49: perf_stat.context_switches=0
- obs_be8b720c: perf_stat.llc_access_count=14499479
- obs_59af547b: perf_stat.llc_miss_count=11740140
- obs_4455e355: perf_stat.branches=92294877
- obs_da516357: perf_stat.branch_misses=224048
- obs_4c4ae14a: perf_stat.context_switches=0
- obs_4890d656: perf_stat.llc_access_count=23230175
- obs_845422f1: perf_stat.llc_miss_count=17763147
- obs_c76eeca5: perf_stat.branches=14835314
- obs_681e271c: perf_stat.branch_misses=192
- obs_cb67c179: perf_stat.context_switches=0
- obs_f1adff4d: perf_stat.llc_access_count=16727550
- obs_e6fb1467: perf_stat.llc_miss_count=12774967
- obs_7b1d1264: perf_stat.branches=18289775
- obs_f5fc06b6: perf_stat.branch_misses=11193
- obs_e8e0d712: perf_stat.context_switches=1
- obs_d38412c5: perf_stat.branch_miss_rate_pct=0.496
- obs_60fc61a7: perf_stat.llc_miss_rate_pct=43.6547
- obs_000f4b6b: perf_stat.branch_miss_rate_pct=0.3387
- obs_28f10ef8: perf_stat.llc_miss_rate_pct=80.8137
- obs_bb0e65e0: perf_stat.branch_miss_rate_pct=0.0019
- obs_d669f265: perf_stat.llc_miss_rate_pct=76.2711
- obs_59ccc71e: perf_stat.branch_miss_rate_pct=0.0642
- obs_ec483e00: perf_stat.llc_miss_rate_pct=76.8767
- obs_d8bcaff9: perf_stat.branch_miss_rate_pct=0.5055
- obs_9fdbbc23: perf_stat.llc_miss_rate_pct=9.4142
- obs_5211084c: perf_stat.branch_miss_rate_pct=0.319
- obs_7ddad4ee: perf_stat.llc_miss_rate_pct=84.0061
- obs_fa7ee154: perf_stat.branch_miss_rate_pct=0.0014
- obs_3c1584ef: perf_stat.llc_miss_rate_pct=76.8828
- obs_1316e3bb: perf_stat.branch_miss_rate_pct=0.0917
- obs_8f63ca4d: perf_stat.llc_miss_rate_pct=76.9374
- obs_68af0008: perf_stat.branch_miss_rate_pct=0.508
- obs_a79fad3b: perf_stat.llc_miss_rate_pct=12.427
- obs_0d94a824: perf_stat.branch_miss_rate_pct=0.3164
- obs_c540ae44: perf_stat.llc_miss_rate_pct=86.6258
- obs_1c3ef387: perf_stat.branch_miss_rate_pct=0.0024
- obs_8e4a8667: perf_stat.llc_miss_rate_pct=78.3466
- obs_a58cfb08: perf_stat.branch_miss_rate_pct=0.1068
- obs_1706cdbd: perf_stat.llc_miss_rate_pct=77.5938
- obs_261137b9: perf_stat.branch_miss_rate_pct=0.5098
- obs_b665d237: perf_stat.llc_miss_rate_pct=10.9236
- obs_9efa0276: perf_stat.branch_miss_rate_pct=0.3149
- obs_2bc8a231: perf_stat.llc_miss_rate_pct=80.574
- obs_e4bf02c6: perf_stat.branch_miss_rate_pct=0.0017
- obs_d48b9869: perf_stat.llc_miss_rate_pct=76.5302
- obs_3ab25eb1: perf_stat.branch_miss_rate_pct=0.1747
- obs_a3364f57: perf_stat.llc_miss_rate_pct=76.2031
- obs_6d971d71: perf_stat.branch_miss_rate_pct=0.5123
- obs_6b8b6284: perf_stat.llc_miss_rate_pct=17.0828
- obs_cea779ea: perf_stat.branch_miss_rate_pct=0.302
- obs_41105500: perf_stat.llc_miss_rate_pct=79.6343
- obs_7d478986: perf_stat.branch_miss_rate_pct=0.001
- obs_fabf0e26: perf_stat.llc_miss_rate_pct=76.469
- obs_a30e51ed: perf_stat.branch_miss_rate_pct=0.2259
- obs_e555324e: perf_stat.llc_miss_rate_pct=76.3486
- obs_f68dcb55: perf_stat.branch_miss_rate_pct=0.516
- obs_7bb04ebc: perf_stat.llc_miss_rate_pct=14.7932
- obs_ab30bf72: perf_stat.branch_miss_rate_pct=0.285
- obs_9dc67961: perf_stat.llc_miss_rate_pct=81.0139
- obs_642ab0f0: perf_stat.branch_miss_rate_pct=0.001
- obs_bc285989: perf_stat.llc_miss_rate_pct=77.0814
- obs_910da866: perf_stat.branch_miss_rate_pct=0.2598
- obs_1cb993ba: perf_stat.llc_miss_rate_pct=77.3232
- obs_8b8951e1: perf_stat.branch_miss_rate_pct=0.5189
- obs_f0b9377e: perf_stat.llc_miss_rate_pct=16.6701
- obs_86f5bb27: perf_stat.branch_miss_rate_pct=0.2716
- obs_c36d5f6d: perf_stat.llc_miss_rate_pct=78.3713
- obs_ad737fbb: perf_stat.branch_miss_rate_pct=0.0011
- obs_d68d5376: perf_stat.llc_miss_rate_pct=76.9862
- obs_ccbe1e1d: perf_stat.branch_miss_rate_pct=0.3128
- obs_15a1a11a: perf_stat.llc_miss_rate_pct=76.1751
- obs_d0af1cd8: perf_stat.branch_miss_rate_pct=0.5121
- obs_aa2a177b: perf_stat.llc_miss_rate_pct=9.5919
- obs_e73aa649: perf_stat.branch_miss_rate_pct=0.2428
- obs_c32c5506: perf_stat.llc_miss_rate_pct=80.9694
- obs_3cf29442: perf_stat.branch_miss_rate_pct=0.0013
- obs_cdcd7ba7: perf_stat.llc_miss_rate_pct=76.4658
- obs_1049b03e: perf_stat.branch_miss_rate_pct=0.0612
- obs_df441bfe: perf_stat.llc_miss_rate_pct=76.3708

## 7. 候选瓶颈
### 7.1 分支预测失误
- 置信度: 0.95
- 支持证据: obs_e7f74cf3, obs_531e5cdb, obs_5375762f, obs_15efb835, obs_ccbb26e5, obs_cc4c6b66, obs_fa189cff, obs_b0102f1b, obs_6d9f4a2a, obs_8513d69a, obs_f2793329, obs_b9dbf789, obs_0fa896b3, obs_edba39a2, obs_d6d0bd43, obs_4487581b, obs_77782149, obs_25fa3806, obs_6d73b9be, obs_5f378751, obs_0ff51a9e, obs_38bb3521, obs_386bcff7, obs_db37565d, obs_077872d4, obs_e368e81d, obs_62594f3a, obs_99a28e2b, obs_1b8afee7, obs_da516357, obs_681e271c, obs_f5fc06b6
- 反证: 无
- 验证状态: 需要进一步验证
### 7.2 CPU 瓶颈
- 置信度: 0.95
- 支持证据: obs_dc13850e, obs_f8b9c193, obs_9e9db42f, obs_6b9db48a, obs_0741c71f, obs_b491887d, obs_c8996c60, obs_854aedab, obs_c53483e5, obs_1e1a9109, obs_75469cf4, obs_94854553, obs_b8066c93, obs_1297724b, obs_a1c01169, obs_533ed393, obs_d517421a, obs_00881e5d, obs_ef9648db, obs_2fb2aef8, obs_6afe3258, obs_87c47a1c, obs_444a2659, obs_3b3943fe, obs_12255dbd, obs_d9c985de, obs_31919a46, obs_c33b768a, obs_072247f5, obs_91414b2a, obs_04f321a1, obs_dca8a497, obs_854feeb3, obs_774de375, obs_2ed35be3, obs_7d2baad7, obs_d35fc9dc, obs_800a52dc
- 反证: 无
- 验证状态: 证据基本充分

## 8. 源码定位
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/phased_cache_wave_demo.cpp:35
- 依据: perf record 样本中 main 占 51.29%，地址 0x2603 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.51
```cpp
  33 |         for (std::size_t step = 0; step < values.size(); ++step) {
  34 |             index = (index + 4099) % values.size();
  35 |             values[index] ^= static_cast<std::uint64_t>(step + checksum);
  36 |             checksum += values[index];
  37 |         }
```
### addr2line 热点定位: /usr/include/c++/11/bits/stl_algobase.h:924
- 依据: perf record 样本中 main 占 6.22%，地址 0x25a0 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.06
```cpp
 922 |       const _Tp __tmp = __value;
 923 |       for (; __first != __last; ++__first)
 924 | 	*__first = __tmp;
 925 |     }
 926 | 
```
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/phased_cache_wave_demo.cpp:36
- 依据: perf record 样本中 main 占 2.07%，地址 0x2606 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.02
```cpp
  34 |             index = (index + 4099) % values.size();
  35 |             values[index] ^= static_cast<std::uint64_t>(step + checksum);
  36 |             checksum += values[index];
  37 |         }
  38 |     }
```
### addr2line 热点定位: /home/tchen/agent/perf_agent/examples/cpp/phased_cache_wave_demo.cpp:34
- 依据: perf record 样本中 main 占 1.67%，地址 0x25e8 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.02
```cpp
  32 |     while (Clock::now() < deadline) {
  33 |         for (std::size_t step = 0; step < values.size(); ++step) {
  34 |             index = (index + 4099) % values.size();
  35 |             values[index] ^= static_cast<std::uint64_t>(step + checksum);
  36 |             checksum += values[index];
```
### addr2line 热点定位: /usr/include/c++/11/bits/stl_vector.h:1046
- 依据: perf record 样本中 main 占 1.46%，地址 0x25fc 通过 addr2line 映射到该源码位置。
- 映射方式: addr2line
- 置信度: 0.01
```cpp
1044 |       {
1045 | 	__glibcxx_requires_subscript(__n);
1046 | 	return *(this->_M_impl._M_start + __n);
1047 |       }
1048 | 
```
### 热点函数定位: /home/tchen/agent/perf_agent/examples/cpp/phased_cache_wave_demo.cpp:44
- 依据: perf record / report 显示热点符号 main，该源码位置与热点调用路径直接相关。
- 映射方式: symbol_scan
- 置信度: 0.50
```cpp
  42 | }  // namespace
  43 | 
  44 | int main(int argc, char** argv) {
  45 |     std::size_t rounds = 10;
  46 |     std::size_t phase_ms = 180;
```
### 分支预测风险: /home/tchen/agent/perf_agent/examples/cpp/phased_cache_wave_demo.cpp:50
- 依据: 检测到高频分支判断代码。
- 映射方式: heuristic
- 置信度: 0.35
```cpp
  48 |     std::size_t large_mb = 96;
  49 | 
  50 |     if (argc > 1) {
  51 |         rounds = static_cast<std::size_t>(std::stoull(argv[1]));
  52 |     }
```
### 分支预测风险: /home/tchen/agent/perf_agent/examples/cpp/phased_cache_wave_demo.cpp:53
- 依据: 检测到高频分支判断代码。
- 映射方式: heuristic
- 置信度: 0.35
```cpp
  51 |         rounds = static_cast<std::size_t>(std::stoull(argv[1]));
  52 |     }
  53 |     if (argc > 2) {
  54 |         phase_ms = static_cast<std::size_t>(std::stoull(argv[2]));
  55 |     }
```

## 9. 二次验证
- 已执行动作:
- act_75af2dd9: /usr/bin/time / 运行时基线 [done]
- act_e4d49a7e: perf stat / 指令效率 [done]
- act_61da6e15: perf stat / 缓存与内存压力 [done]
- act_cdf32edd: perf stat / 前后端停顿 [done]
- act_91a244d0: perf stat / 调度上下文 [done]
- act_f23c1980: pidstat / 调度上下文 [done]
- act_948566bc: mpstat / 调度上下文 [done]
- act_b777d2ab: perf record / 热点函数调用链 [done]
- act_bb8e8068: perf stat / 时间序列行为 [1/2] [done]
- act_877c9827: perf stat / 时间序列行为 [2/2] [done]
- 新证据:
- 分支预测失误: perf_stat.branch_misses=1227645
- 分支预测失误: perf_stat.branch_misses=487324
- 分支预测失误: perf_stat.branch_misses=285
- 分支预测失误: perf_stat.branch_misses=17035
- 分支预测失误: perf_stat.branch_misses=1251724
- 分支预测失误: perf_stat.branch_misses=441864
- 分支预测失误: perf_stat.branch_misses=201
- 分支预测失误: perf_stat.branch_misses=28680
- 分支预测失误: perf_stat.branch_misses=1257337
- 分支预测失误: perf_stat.branch_misses=423162
- 分支预测失误: perf_stat.branch_misses=357
- 分支预测失误: perf_stat.branch_misses=35719
- 分支预测失误: perf_stat.branch_misses=1261476
- 分支预测失误: perf_stat.branch_misses=414130
- 分支预测失误: perf_stat.branch_misses=252
- 分支预测失误: perf_stat.branch_misses=75361
- 分支预测失误: perf_stat.branch_misses=1267550
- 分支预测失误: perf_stat.branch_misses=369470
- 分支预测失误: perf_stat.branch_misses=148
- 分支预测失误: perf_stat.branch_misses=122163
- 分支预测失误: perf_stat.branch_misses=1274444
- 分支预测失误: perf_stat.branch_misses=317726
- 分支预测失误: perf_stat.branch_misses=154
- 分支预测失误: perf_stat.branch_misses=161313
- 分支预测失误: perf_stat.branch_misses=1281906
- 分支预测失误: perf_stat.branch_misses=281555
- 分支预测失误: perf_stat.branch_misses=157
- 分支预测失误: perf_stat.branch_misses=229448
- 分支预测失误: perf_stat.branch_misses=1265235
- 分支预测失误: perf_stat.branch_misses=224048
- 分支预测失误: perf_stat.branch_misses=192
- 分支预测失误: perf_stat.branch_misses=11193
- CPU 瓶颈: time.cpu_utilization_pct=99
- CPU 瓶颈: perf_stat.ipc=1.5752
- CPU 瓶颈: perf_stat.ipc=1.5518
- CPU 瓶颈: perf_record.process_sample_pct=100.0
- CPU 瓶颈: perf_record.thread_sample_pct=100.0
- CPU 瓶颈: perf_stat.ipc=3.6265
- CPU 瓶颈: perf_stat.ipc=1.9504
- CPU 瓶颈: perf_stat.ipc=0.3079
- CPU 瓶颈: perf_stat.ipc=0.3543
- CPU 瓶颈: perf_stat.ipc=3.6456
- CPU 瓶颈: perf_stat.ipc=1.9709
- CPU 瓶颈: perf_stat.ipc=0.3078
- CPU 瓶颈: perf_stat.ipc=0.3468
- CPU 瓶颈: perf_stat.ipc=3.6458
- CPU 瓶颈: perf_stat.ipc=1.9761
- CPU 瓶颈: perf_stat.ipc=0.2888
- CPU 瓶颈: perf_stat.ipc=0.3102
- CPU 瓶颈: perf_stat.ipc=3.2632
- CPU 瓶颈: perf_stat.ipc=2.3939
- CPU 瓶颈: perf_stat.ipc=0.3175
- CPU 瓶颈: perf_stat.ipc=0.3137
- CPU 瓶颈: perf_stat.ipc=3.3634
- CPU 瓶颈: perf_stat.ipc=2.301
- CPU 瓶颈: perf_stat.ipc=0.312
- CPU 瓶颈: perf_stat.ipc=0.312
- CPU 瓶颈: perf_stat.ipc=3.3964
- CPU 瓶颈: perf_stat.ipc=2.2704
- CPU 瓶颈: perf_stat.ipc=0.3068
- CPU 瓶颈: perf_stat.ipc=0.3183
- CPU 瓶颈: perf_stat.ipc=3.4242
- CPU 瓶颈: perf_stat.ipc=2.2378
- CPU 瓶颈: perf_stat.ipc=0.3126
- CPU 瓶颈: perf_stat.ipc=0.3159
- CPU 瓶颈: perf_stat.ipc=3.5003
- CPU 瓶颈: perf_stat.ipc=2.1596
- CPU 瓶颈: perf_stat.ipc=0.316
- CPU 瓶颈: perf_stat.ipc=0.3152
- CPU 瓶颈: perf_stat.ipc=2.8558

## 10. 建议
- 建议检查高频分支代码并结合调用栈定位热点分支。
- 建议追加 perf record -g，定位最热函数和调用栈。
