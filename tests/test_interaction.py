from __future__ import annotations

from pathlib import Path

from perf_agent.interaction.prompt_processor import PromptProcessor
from perf_agent.interaction.query import QueryAssembler
from perf_agent.interaction.session import InteractivePerfSession
from perf_agent.interaction.models import MessageBlock, SessionContext, SessionMessage
from perf_agent.interaction.tool_policy import ToolPolicy


def test_prompt_processor_intercepts_slash_command() -> None:
    processor = PromptProcessor(llm_client=None)
    normalized = processor.process_user_input_base("/run", SessionContext())

    assert normalized.slash_command is not None
    assert normalized.slash_command.name == "run"
    assert normalized.should_query is False


def test_prompt_processor_extracts_executable_and_source_dir_from_chinese_text() -> None:
    processor = PromptProcessor(llm_client=None)
    context = SessionContext()
    text = "帮我分析 /home/tchen/agent/perf_agent/examples/bin/multiprocess_fanout_demo，源码在 /home/tchen/agent/perf_agent/examples/cpp。"
    normalized = processor.process_user_input_base(text, context)
    interpreted = processor.interpret(normalized, context, QueryAssembler().build([], normalized.messages))

    assert interpreted.should_run_analysis is True
    assert interpreted.executable_path is not None
    assert interpreted.executable_path.endswith("multiprocess_fanout_demo")
    assert interpreted.source_dir is not None
    assert interpreted.source_dir.endswith("examples/cpp")


def test_query_assembler_compacts_large_tool_results() -> None:
    assembler = QueryAssembler(max_context_tokens=120, tool_result_budget_tokens=40, visible_history_messages=4)
    history = [
        SessionMessage(
            id=f"msg_{idx}",
            role="tool" if idx < 3 else "user",
            blocks=[MessageBlock(type="text", text=("tool-result-" * 60) if idx < 3 else f"user input {idx}")],
            tags=["tool_result"] if idx < 3 else [],
        )
        for idx in range(6)
    ]
    query_view = assembler.build(history, [], compact_summary=None)

    assert query_view.token_estimate <= 120
    assert query_view.stages
    assert any(stage.name == "contextCollapse" for stage in query_view.stages)


def test_interactive_session_handles_set_and_show(tmp_path: Path) -> None:
    session = InteractivePerfSession(output_root=tmp_path, show_progress=False)

    set_output, should_exit = session.handle_input("/set exe /home/tchen/agent/perf_agent/examples/bin/cpu_bound_demo")
    assert should_exit is False
    assert "已设置可执行文件" in set_output

    show_output, should_exit = session.handle_input("/show")
    assert should_exit is False
    assert "cpu_bound_demo" in show_output
    assert "当前会话上下文" in show_output


def test_tool_policy_blocks_dangerous_command() -> None:
    policy = ToolPolicy()
    decision = policy.wrapper_can_use_tool(
        "launch_analysis",
        SessionContext(target_cmd=["rm", "-rf", "/tmp/perf-agent-danger"]),
    )

    assert decision.allowed is False
    assert decision.risk_level == "high"
    assert "destructive_rm_rf" in decision.matched_rules


def test_interactive_session_requires_confirmation_for_sensitive_read(tmp_path: Path) -> None:
    session = InteractivePerfSession(output_root=tmp_path, show_progress=False)

    set_output, should_exit = session.handle_input('/set cmd "cat ~/.bashrc"')
    assert should_exit is False
    assert "已设置目标命令" in set_output

    run_output, should_exit = session.handle_input("/run")
    assert should_exit is False
    assert "检测到中风险目标" in run_output
    assert session.state.pending_approval is not None

    deny_output, should_exit = session.handle_input("/deny")
    assert should_exit is False
    assert "已取消这次执行请求" in deny_output
    assert session.state.pending_approval is None
