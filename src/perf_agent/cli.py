from __future__ import annotations

import argparse
from pathlib import Path
import sys

from perf_agent.interaction.models import SessionContext
from perf_agent.interaction.tool_policy import ToolPolicy
from perf_agent.main import build_state, build_state_from_inputs, run_interactive_session, run_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automated performance analysis scaffold")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze a task JSON file")
    analyze.add_argument("--task", help="Path to the analysis request JSON file")
    analyze.add_argument("--exe", help="Executable file path")
    analyze.add_argument("--cmd", help="Target command as a single shell string")
    analyze.add_argument("--pid", type=int, help="Attach to an existing process id")
    analyze.add_argument("--source-dir", help="Optional source directory for later code-side analysis")
    analyze.add_argument("--label", help="Optional workload label")
    analyze.add_argument("--config", help="Path to tools.yaml")
    analyze.add_argument("--safety-config", help="Path to safety.yaml")
    analyze.add_argument("--events-config", help="Path to events.yaml")
    analyze.add_argument("--rules-config", help="Path to rules.yaml")
    analyze.add_argument("--prompts-config", help="Path to prompts.yaml")
    analyze.add_argument("--output-root", default="runs", help="Directory used for analysis artifacts")
    analyze.add_argument("--quiet", action="store_true", help="Reduce interactive progress output")
    analyze.add_argument("target_cmd", nargs=argparse.REMAINDER, help="Command tokens after --")

    interactive = subparsers.add_parser("interactive", help="Start an interactive session")
    interactive.add_argument("--config", help="Path to tools.yaml")
    interactive.add_argument("--safety-config", help="Path to safety.yaml")
    interactive.add_argument("--events-config", help="Path to events.yaml")
    interactive.add_argument("--rules-config", help="Path to rules.yaml")
    interactive.add_argument("--prompts-config", help="Path to prompts.yaml")
    interactive.add_argument("--output-root", default="runs", help="Directory used for analysis artifacts")
    interactive.add_argument("--quiet", action="store_true", help="Reduce progress output during analysis runs")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "analyze":
        if args.task:
            state = build_state(args.task)
        else:
            remainder = list(args.target_cmd)
            if remainder and remainder[0] == "--":
                remainder = remainder[1:]
            if not remainder and not args.cmd and args.pid is None and not args.exe:
                parser.error("provide --task, --exe, --cmd, --pid, or a command after --")
            state = build_state_from_inputs(
                executable_path=args.exe,
                target_args=remainder if args.exe else None,
                target_cmd=None if args.exe else (remainder or None),
                cmd=args.cmd,
                pid=args.pid,
                source_dir=args.source_dir,
                workload_label=args.label,
            )
        _guard_target_risk(state, parser)
        state = run_state(
            state,
            output_root=Path(args.output_root),
            tool_config_path=args.config,
            safety_config_path=args.safety_config,
            rule_config_path=args.rules_config,
            prompt_config_path=args.prompts_config,
            event_config_path=args.events_config,
            show_progress=not args.quiet,
        )
        print(f"run_id={state.run_id}")
        print(f"status={state.status}")
        print(f"observations={len(state.observations)}")
        print(f"hypotheses={len(state.hypotheses)}")
        if state.source_dir:
            print(f"source_files={len(state.source_files)}")
        if state.final_report is not None:
            print(state.final_report.executive_summary)
        if "report.md" in state.artifacts:
            print(f"report_md={state.artifacts['report.md']}")
        if "report.html" in state.artifacts:
            print(f"report_html={state.artifacts['report.html']}")
    elif args.command == "interactive":
        run_interactive_session(
            output_root=Path(args.output_root),
            tool_config_path=args.config,
            safety_config_path=args.safety_config,
            rule_config_path=args.rules_config,
            prompt_config_path=args.prompts_config,
            event_config_path=args.events_config,
            show_progress=not args.quiet,
        )


def _guard_target_risk(state, parser: argparse.ArgumentParser) -> None:
    policy = ToolPolicy()
    context = SessionContext(
        executable_path=state.executable_path,
        target_cmd=state.target_cmd,
        source_dir=state.source_dir,
        target_pid=state.target_pid,
        workload_label=state.workload_label,
        goal=state.goal,
        cwd=state.cwd,
        env=state.env,
    )
    decision = policy.wrapper_can_use_tool("launch_analysis", context)
    if not decision.allowed:
        parser.error(_format_risk_message(decision))
    if decision.requires_confirmation:
        prompt = _format_risk_message(decision) + "\n继续执行这次分析吗？[y/N] "
        if not sys.stdin.isatty():
            parser.error(prompt.strip() + " 当前不是交互式终端，无法完成确认。")
        answer = input(prompt).strip().lower()
        if answer not in {"y", "yes", "是", "确认", "continue"}:
            raise SystemExit(1)


def _format_risk_message(decision) -> str:
    lines = [f"检测到 {decision.risk_level} 风险目标: {decision.reason}"]
    if decision.command_preview:
        lines.append(f"- 目标命令: {decision.command_preview}")
    if decision.matched_rules:
        lines.append(f"- 风险规则: {', '.join(decision.matched_rules)}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
