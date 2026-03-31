from __future__ import annotations

from pathlib import Path

from perf_agent.models.state import AnalysisState
from perf_agent.parsers import generic_parser, perf_record_parser, perf_stat_parser, pidstat_parser, time_parser


class ParserNode:
    def __init__(self) -> None:
        self.registry = {
            "time": time_parser.parse_text,
            "perf_stat": perf_stat_parser.parse_text,
            "perf_record": perf_record_parser.parse_text,
            "pidstat": pidstat_parser.parse_text,
            "mpstat": generic_parser.parse_text,
            "iostat": generic_parser.parse_text,
            "flamegraph": generic_parser.parse_text,
        }

    def run(self, state: AnalysisState) -> AnalysisState:
        for action in state.actions_taken:
            if action.id in state.parsed_action_ids or action.status not in {"done", "failed"}:
                continue

            parser = self.registry.get(action.tool, generic_parser.parse_text)
            payload = self._read_payload(state, action.id, action.tool)
            observations = parser(payload, source=action.tool, action_id=action.id)
            state.observations.extend(observations)
            state.parsed_action_ids.append(action.id)
            state.add_audit(
                "parser",
                "parsed action output",
                action_id=action.id,
                tool=action.tool,
                observation_count=len(observations),
            )
        return state

    def _read_payload(self, state: AnalysisState, action_id: str, tool_name: str) -> str:
        if tool_name == "perf_record":
            return self._read_perf_record_payload(state, action_id)
        stdout_path = state.artifacts.get(f"{action_id}.stdout")
        stderr_path = state.artifacts.get(f"{action_id}.stderr")
        chunks: list[str] = []
        if stdout_path:
            chunks.append(Path(stdout_path).read_text(encoding="utf-8"))
        if stderr_path:
            chunks.append(Path(stderr_path).read_text(encoding="utf-8"))
        payload = "\n".join(part for part in chunks if part)
        return payload.replace("\\n", "\n")

    def _read_perf_record_payload(self, state: AnalysisState, action_id: str) -> str:
        sections: list[str] = []
        stdout_path = state.artifacts.get(f"{action_id}.stdout")
        stderr_path = state.artifacts.get(f"{action_id}.stderr")

        if stdout_path:
            sections.append(f"=== report ===\n{Path(stdout_path).read_text(encoding='utf-8')}")
        for key, path in sorted(state.artifacts.items()):
            if not key.startswith(f"{action_id}.artifact."):
                continue
            artifact_path = Path(path)
            if artifact_path.suffix != ".txt":
                continue
            name = artifact_path.name
            if name.endswith(".script.txt"):
                sections.append(f"=== script ===\n{artifact_path.read_text(encoding='utf-8')}")
            elif name.endswith(".report.stderr.txt"):
                sections.append(f"=== report_stderr ===\n{artifact_path.read_text(encoding='utf-8')}")
            elif name.endswith(".script.stderr.txt"):
                sections.append(f"=== script_stderr ===\n{artifact_path.read_text(encoding='utf-8')}")
        if stderr_path:
            sections.append(f"=== record_stderr ===\n{Path(stderr_path).read_text(encoding='utf-8')}")
        return "\n\n".join(section.replace("\\n", "\n") for section in sections if section)
