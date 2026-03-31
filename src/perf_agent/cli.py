from __future__ import annotations

import argparse
from pathlib import Path

from perf_agent.main import build_state, build_state_from_inputs, run_state


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
    analyze.add_argument("--events-config", help="Path to events.yaml")
    analyze.add_argument("--rules-config", help="Path to rules.yaml")
    analyze.add_argument("--prompts-config", help="Path to prompts.yaml")
    analyze.add_argument("--output-root", default="runs", help="Directory used for analysis artifacts")
    analyze.add_argument("--quiet", action="store_true", help="Reduce interactive progress output")
    analyze.add_argument("target_cmd", nargs=argparse.REMAINDER, help="Command tokens after --")
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
        state = run_state(
            state,
            output_root=Path(args.output_root),
            tool_config_path=args.config,
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


if __name__ == "__main__":
    main()
