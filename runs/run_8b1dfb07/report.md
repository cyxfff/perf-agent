# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 CPU 瓶颈，置信度为 0.70。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/cpu_bound_demo 700 18000
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/cpu_bound_demo
- 源码目录: /home/tchen/agent/perf_agent/examples/cpp
- 运行信息: verification_rounds=2, actions_executed=6
- 工作目录: 

## 3. 关键观测
- obs_81e6ec84: time.user_time_sec=0.14
- obs_63851688: time.system_time_sec=0.0
- obs_5382edc7: time.cpu_utilization_pct=100
- obs_bf59dd48: time.max_rss_kb=4320
- obs_cecf50c9: time.major_faults=0
- obs_d76974dd: time.voluntary_context_switches=1
- obs_c86a7c57: time.involuntary_context_switches=2
- obs_158965fb: mpstat.23=56:24     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_60af5472: mpstat.23=56:25     all    0.70    0.00    0.35    2.61    0.00    0.00    0.00    0.00    0.00   96.34
- obs_df963407: mpstat.average=all    0.70    0.00    0.35    2.61    0.00    0.00    0.00    0.00    0.00   96.34
- obs_481a2fb5: perf_record.callgraph_samples=1170
- obs_0f7fbc8d: perf_record.callgraph_samples=816

## 4. 候选瓶颈
### 4.1 CPU 瓶颈
- 置信度: 0.70
- 支持证据: obs_5382edc7
- 反证: 无
- 验证状态: 需要进一步验证

## 5. 源码定位
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

## 6. 二次验证
- 已执行动作:
- act_687ff7bb: time [done]
- act_cd6a1190: perf_stat [done]
- act_5590f2e4: pidstat [done]
- act_317dc5f8: mpstat [done]
- act_40748d8a: perf_record [done]
- act_99e920bc: perf_record [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=100

## 7. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 8. 产物
- runs/run_8b1dfb07/artifacts/act_317dc5f8.json
- runs/run_8b1dfb07/artifacts/act_317dc5f8.stdout.txt
- runs/run_8b1dfb07/artifacts/act_40748d8a.json
- runs/run_8b1dfb07/artifacts/act_40748d8a.stderr.txt
- runs/run_8b1dfb07/artifacts/act_40748d8a.stdout.txt
- runs/run_8b1dfb07/artifacts/act_5590f2e4.json
- runs/run_8b1dfb07/artifacts/act_5590f2e4.stdout.txt
- runs/run_8b1dfb07/artifacts/act_687ff7bb.json
- runs/run_8b1dfb07/artifacts/act_687ff7bb.stderr.txt
- runs/run_8b1dfb07/artifacts/act_687ff7bb.stdout.txt
- runs/run_8b1dfb07/artifacts/act_99e920bc.json
- runs/run_8b1dfb07/artifacts/act_99e920bc.stderr.txt
- runs/run_8b1dfb07/artifacts/act_99e920bc.stdout.txt
- runs/run_8b1dfb07/artifacts/act_cd6a1190.json
- runs/run_8b1dfb07/artifacts/act_cd6a1190.stderr.txt
- runs/run_8b1dfb07/artifacts/act_cd6a1190.stdout.txt
- runs/run_8b1dfb07/source_manifest.json
- runs/run_8b1dfb07/target.json
