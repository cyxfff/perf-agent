# 性能分析报告

## 1. 执行摘要
当前最可能的瓶颈方向是 未知瓶颈，置信度为 0.32。

## 2. 分析目标
- 命令: /home/tchen/agent/perf_agent/examples/bin/lock_contention_demo 6 120000
- 可执行文件: /home/tchen/agent/perf_agent/examples/bin/lock_contention_demo
- 源码目录: /home/tchen/agent/perf_agent/examples/cpp
- 运行信息: verification_rounds=2, actions_executed=7
- 工作目录: 

## 3. 关键观测
- obs_8f3a0286: time.user_time_sec=0.02
- obs_add90d61: time.system_time_sec=0.01
- obs_ab2ded3d: time.cpu_utilization_pct=7
- obs_b7105c30: time.max_rss_kb=3840
- obs_f8d16b53: time.major_faults=0
- obs_b004985b: time.voluntary_context_switches=15340
- obs_05687523: time.involuntary_context_switches=7
- obs_1dd334cb: mpstat.23=56:24     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
- obs_aa0edb51: mpstat.23=56:25     all    1.60    0.00    1.10    1.70    0.00    0.05    0.00    0.00    0.00   95.55
- obs_0cebf1d6: mpstat.average=all    1.60    0.00    1.10    1.70    0.00    0.05    0.00    0.00    0.00   95.55

## 4. 候选瓶颈
### 4.1 未知瓶颈
- 置信度: 0.32
- 支持证据: obs_8f3a0286
- 反证: 无
- 验证状态: 需要进一步验证

## 5. 源码定位
- 未发现可直接关联的源码位置。

## 6. 二次验证
- 已执行动作:
- act_c301857d: time [done]
- act_59c88de1: perf_stat [done]
- act_c84cba57: pidstat [done]
- act_65e935ee: mpstat [done]
- act_eab33183: iostat [done]
- act_6bcc69dc: perf_stat [done]
- act_9f785997: perf_stat [done]
- 新证据:
- 未知瓶颈: time.user_time_sec=0.02

## 7. 建议
- 建议补充一轮基线采样后再做结论。

## 8. 产物
- runs/run_4a75471a/artifacts/act_59c88de1.json
- runs/run_4a75471a/artifacts/act_59c88de1.stderr.txt
- runs/run_4a75471a/artifacts/act_59c88de1.stdout.txt
- runs/run_4a75471a/artifacts/act_65e935ee.json
- runs/run_4a75471a/artifacts/act_65e935ee.stdout.txt
- runs/run_4a75471a/artifacts/act_6bcc69dc.json
- runs/run_4a75471a/artifacts/act_6bcc69dc.stderr.txt
- runs/run_4a75471a/artifacts/act_6bcc69dc.stdout.txt
- runs/run_4a75471a/artifacts/act_9f785997.json
- runs/run_4a75471a/artifacts/act_9f785997.stderr.txt
- runs/run_4a75471a/artifacts/act_9f785997.stdout.txt
- runs/run_4a75471a/artifacts/act_c301857d.json
- runs/run_4a75471a/artifacts/act_c301857d.stderr.txt
- runs/run_4a75471a/artifacts/act_c301857d.stdout.txt
- runs/run_4a75471a/artifacts/act_c84cba57.json
- runs/run_4a75471a/artifacts/act_c84cba57.stdout.txt
- runs/run_4a75471a/artifacts/act_eab33183.json
- runs/run_4a75471a/artifacts/act_eab33183.stdout.txt
- runs/run_4a75471a/source_manifest.json
- runs/run_4a75471a/target.json
