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
- obs_0e16e4f6: time.user_time_sec=0.14
- obs_87199dc6: time.system_time_sec=0.0
- obs_7e63c215: time.cpu_utilization_pct=100
- obs_d3c661ce: time.max_rss_kb=4160
- obs_4e3161f0: time.major_faults=0
- obs_c52954cb: time.voluntary_context_switches=1
- obs_9f0ae7af: time.involuntary_context_switches=0
- obs_dbac4053: mpstat.average=all    0.35    0.00    0.10    0.05    0.00    0.10    0.00    0.00    0.00   99.40
- obs_291eaaa7: perf_record.callgraph_samples=176
- obs_4c4f1dbf: perf_record.callgraph_samples=157

## 4. 候选瓶颈
### 4.1 CPU 瓶颈
- 置信度: 0.70
- 支持证据: obs_7e63c215
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
- act_d31ac54e: time [done]
- act_a11ce8dd: perf_stat [done]
- act_0284b5ac: pidstat [done]
- act_cd08eec1: mpstat [done]
- act_95ce0738: perf_record [done]
- act_4b1abaf1: perf_record [done]
- 新证据:
- CPU 瓶颈: time.cpu_utilization_pct=100

## 7. 建议
- 建议追加 perf record -g，定位最热函数和调用栈。

## 8. 产物
- runs/run_087c5a27/artifacts/act_0284b5ac.json
- runs/run_087c5a27/artifacts/act_0284b5ac.stdout.txt
- runs/run_087c5a27/artifacts/act_4b1abaf1.json
- runs/run_087c5a27/artifacts/act_4b1abaf1.stderr.txt
- runs/run_087c5a27/artifacts/act_4b1abaf1.stdout.txt
- runs/run_087c5a27/artifacts/act_95ce0738.json
- runs/run_087c5a27/artifacts/act_95ce0738.stderr.txt
- runs/run_087c5a27/artifacts/act_95ce0738.stdout.txt
- runs/run_087c5a27/artifacts/act_a11ce8dd.json
- runs/run_087c5a27/artifacts/act_a11ce8dd.stderr.txt
- runs/run_087c5a27/artifacts/act_a11ce8dd.stdout.txt
- runs/run_087c5a27/artifacts/act_cd08eec1.json
- runs/run_087c5a27/artifacts/act_cd08eec1.stdout.txt
- runs/run_087c5a27/artifacts/act_d31ac54e.json
- runs/run_087c5a27/artifacts/act_d31ac54e.stderr.txt
- runs/run_087c5a27/artifacts/act_d31ac54e.stdout.txt
- runs/run_087c5a27/source_manifest.json
- runs/run_087c5a27/target.json
