from __future__ import annotations

from pathlib import Path

from perf_agent.config import load_tool_configs
from perf_agent.agents.analyzer import Analyzer
from perf_agent.agents.collector import Collector
from perf_agent.agents.environment_profiler import EnvironmentProfiler
from perf_agent.agents.parser import ParserNode
from perf_agent.agents.planner import Planner
from perf_agent.agents.reporter import Reporter
from perf_agent.agents.runner import Runner
from perf_agent.agents.source_analyzer import SourceAnalyzer
from perf_agent.agents.verifier import Verifier
from perf_agent.llm.client import LLMClient
from perf_agent.models.state import AnalysisState
from perf_agent.security.sandbox import SandboxManager
from perf_agent.storage.json_store import JSONArtifactStore
from perf_agent.storage.run_log import RunLog
from perf_agent.tools.runner import ToolRunner
from perf_agent.utils.progress import ConsoleProgress


class Orchestrator:
    def __init__(
        self,
        output_root: str | Path = "runs",
        tool_config_path: str | None = None,
        safety_config_path: str | None = None,
        rule_config_path: str | None = None,
        prompt_config_path: str | None = None,
        event_config_path: str | None = None,
        show_progress: bool = True,
    ) -> None:
        self.output_root = Path(output_root)
        self.sandbox_manager = SandboxManager(config_path=safety_config_path)
        self.runner = ToolRunner(sandbox_manager=self.sandbox_manager)
        self.tool_configs = load_tool_configs(tool_config_path)
        self.progress = ConsoleProgress(enabled=show_progress)
        self.planner = Planner(
            tool_runner=self.runner,
            tool_config_path=tool_config_path,
            event_config_path=event_config_path,
        )
        self.parser = ParserNode()
        llm_client = LLMClient(prompt_config_path=prompt_config_path)
        self.analyzer = Analyzer(llm_client=llm_client, rule_config_path=rule_config_path)
        self.verifier = Verifier(
            llm_client=llm_client,
            tool_runner=self.runner,
            tool_config_path=tool_config_path,
            event_config_path=event_config_path,
        )
        self.source_analyzer = SourceAnalyzer()
        self.reporter = Reporter(llm_client=llm_client)

    def run(self, state: AnalysisState) -> AnalysisState:
        store = JSONArtifactStore(state.output_dir(self.output_root))
        collector = Collector(self.runner, store, progress=self.progress)
        runner = Runner(store)
        environment_profiler = EnvironmentProfiler(store, sandbox_manager=self.sandbox_manager)
        run_log = RunLog(state.output_dir(self.output_root) / "audit.jsonl")

        while state.status not in {"done", "failed"}:
            state = self._step(state, runner, collector, environment_profiler)
            self._persist_state(store, run_log, state)
        return state

    def _step(
        self,
        state: AnalysisState,
        runner: Runner,
        collector: Collector,
        environment_profiler: EnvironmentProfiler,
    ) -> AnalysisState:
        if state.status == "init":
            self.progress.stage("准备", "开始建立分析任务。")
            state.status = "running"
            state.add_audit("orchestrator", "transitioned to running")
            return state

        if state.status == "running":
            self.progress.stage("目标准备", "解析可执行文件、命令和源码目录。")
            state = runner.run(state)
            self.progress.info(f"目标命令: {' '.join(state.target_cmd) if state.target_cmd else 'PID 附着模式'}")
            if state.source_dir:
                self.progress.info(f"已索引源码文件 {len(state.source_files)} 个。")
            state.status = "profiling_environment"
            return state

        if state.status == "profiling_environment":
            self.progress.stage("环境探测", "识别当前机器架构、perf 能力和可用事件。")
            state = environment_profiler.run(state)
            env = state.environment
            self.progress.info(
                f"架构 {env.arch or '未知'}，CPU {env.cpu_model or '未知'}，采样后端 {'可用' if env.perf_available else '不可用'}。"
            )
            self.progress.info(
                f"可用事件 {len(env.available_events)} 个，调用栈模式: {', '.join(env.callgraph_modes) or '未探测到'}。"
            )
            if env.profiling_backend_summary:
                self.progress.info(env.profiling_backend_summary)
            if env.adb_available:
                self.progress.info(f"ADB 设备: 已发现 {len(env.connected_devices)} 台。")
                if env.selected_device_summary:
                    self.progress.info(env.selected_device_summary)
            if env.sandbox_enabled:
                self.progress.info(
                    f"隔离运行时: 已配置 {env.configured_sandbox_runtime or 'auto'}，当前选择 {env.selected_sandbox_runtime or 'none'}。"
                )
                if env.available_sandbox_runtimes:
                    self.progress.info(f"可用隔离运行时: {', '.join(env.available_sandbox_runtimes)}")
            state.status = "planning"
            return state

        if state.status == "planning":
            self.progress.stage("实验规划", "根据环境能力和工作负载特征生成首轮实验计划。")
            state = self.planner.run(state)
            for mapping in state.event_mappings[-len(state.pending_actions):]:
                self.progress.info(
                    f"{mapping.display_name or mapping.tool}: {mapping.rationale}"
                )
            state.status = "collecting"
            return state

        if state.status == "collecting":
            self.progress.stage("实验执行", "开始按计划采样。")
            state = collector.run(state)
            state.status = "failed" if state.error_message else "parsing"
            return state

        if state.status == "parsing":
            self.progress.stage("结果解析", "将原始输出转成统一 observation。")
            state = self.parser.run(state)
            self.progress.info(f"当前累计 observation 数量: {len(state.observations)}")
            state.status = "analyzing"
            return state

        if state.status == "analyzing":
            self.progress.stage("诊断分析", "结合规则和 LLM 生成候选瓶颈。")
            state = self.analyzer.run(state)
            if state.hypotheses:
                top = max(state.hypotheses, key=lambda item: item.confidence)
                self.progress.info(f"当前首要候选: {top.kind}，置信度 {top.confidence:.2f}")
            state.status = "verifying" if self.verifier.should_verify(state) else "source_analyzing"
            return state

        if state.status == "verifying":
            self.progress.stage("验证闭环", "判断是否需要追加实验以补齐证据。")
            state = self.verifier.run(state)
            if state.pending_actions:
                self.progress.info(f"已追加 {len(state.pending_actions)} 个动作，准备进入下一轮采样。")
            else:
                self.progress.info("当前证据已经足够，进入源码定位和报告阶段。")
            state.status = "collecting" if state.pending_actions else "source_analyzing"
            return state

        if state.status == "source_analyzing":
            self.progress.stage("源码关联", "把热点证据与源码文件、行号和可疑模式对齐。")
            state = self.source_analyzer.run(state)
            state.status = "reporting"
            return state

        if state.status == "reporting":
            self.progress.stage("生成报告", "正在输出中文 Markdown 和 HTML 报告。")
            state = self.reporter.run(state)
            if state.final_report is not None:
                report_json = state.final_report.model_dump(mode="json")
                report_path = collector.store.save_json("report.json", report_json)
                markdown_path = collector.store.save_text("report.md", self.reporter.render_markdown(state))
                html_path = collector.store.save_text("report.html", self.reporter.render_html(state))
                state.artifacts["report.json"] = str(report_path)
                state.artifacts["report.md"] = str(markdown_path)
                state.artifacts["report.html"] = str(html_path)
                self.progress.info(f"Markdown 报告: {markdown_path}")
                self.progress.info(f"HTML 报告: {html_path}")
            state.status = "done"
            return state

        return state

    def _persist_state(self, store: JSONArtifactStore, run_log: RunLog, state: AnalysisState) -> None:
        store.save_json("state.json", state.model_dump(mode="json"))
        store.save_json("observations.json", [item.model_dump(mode="json") for item in state.observations])
        store.save_json("hypotheses.json", [item.model_dump(mode="json") for item in state.hypotheses])
        store.save_json("evidence_packs.json", [item.model_dump(mode="json") for item in state.evidence_packs])
        store.save_json("actions_taken.json", [item.model_dump(mode="json") for item in state.actions_taken])
        store.save_json("pending_actions.json", [item.model_dump(mode="json") for item in state.pending_actions])
        for event in state.audit_log:
            if not event.persisted:
                run_log.append(event)
                event.persisted = True
