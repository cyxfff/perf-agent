from __future__ import annotations

import json
from pathlib import Path
import shlex

from perf_agent.models.state import AnalysisState, AnalysisTask
from perf_agent.orchestrator.engine import Orchestrator
from perf_agent.utils.ids import new_run_id


def load_task(task_file: str | Path) -> AnalysisTask:
    payload = json.loads(Path(task_file).read_text(encoding="utf-8"))
    if "target" in payload:
        target = payload["target"]
        payload = {
            "goal": payload.get("goal"),
            "executable_path": target.get("executable_path"),
            "target_args": target.get("args", []),
            "target_cmd": target["command"].split() if isinstance(target["command"], str) else target["command"],
            "target_pid": target.get("pid"),
            "workload_label": target.get("label"),
            "source_dir": target.get("source_dir"),
            "build_cmd": target.get("build_cmd", []),
            "max_verification_rounds": payload.get("max_iterations", 2),
            "mock_outputs": target.get("mock_outputs", {}),
            "cwd": target.get("cwd"),
            "env": target.get("env", {}),
        }
    return AnalysisTask.model_validate(payload)


def build_state(task_file: str | Path) -> AnalysisState:
    task = load_task(task_file)
    return AnalysisState.from_task(task, run_id=new_run_id())


def build_state_from_inputs(
    executable_path: str | None = None,
    target_args: list[str] | None = None,
    target_cmd: list[str] | None = None,
    cmd: str | None = None,
    pid: int | None = None,
    source_dir: str | None = None,
    workload_label: str | None = None,
    max_verification_rounds: int = 2,
) -> AnalysisState:
    resolved_cmd = target_cmd or (shlex.split(cmd) if cmd else [])
    if executable_path and not resolved_cmd:
        resolved_cmd = [executable_path, *(target_args or [])]
    task = AnalysisTask(
        executable_path=executable_path,
        target_args=target_args or [],
        target_cmd=resolved_cmd,
        target_pid=pid,
        source_dir=source_dir,
        workload_label=workload_label,
        max_verification_rounds=max_verification_rounds,
    )
    return AnalysisState.from_task(task, run_id=new_run_id())


def run_task(
    task_file: str | Path,
    output_root: str | Path = "runs",
    tool_config_path: str | None = None,
    rule_config_path: str | None = None,
    prompt_config_path: str | None = None,
    event_config_path: str | None = None,
    show_progress: bool = True,
) -> AnalysisState:
    state = build_state(task_file)
    orchestrator = Orchestrator(
        output_root=output_root,
        tool_config_path=tool_config_path,
        rule_config_path=rule_config_path,
        prompt_config_path=prompt_config_path,
        event_config_path=event_config_path,
        show_progress=show_progress,
    )
    return orchestrator.run(state)


def run_state(
    state: AnalysisState,
    output_root: str | Path = "runs",
    tool_config_path: str | None = None,
    rule_config_path: str | None = None,
    prompt_config_path: str | None = None,
    event_config_path: str | None = None,
    show_progress: bool = True,
) -> AnalysisState:
    orchestrator = Orchestrator(
        output_root=output_root,
        tool_config_path=tool_config_path,
        rule_config_path=rule_config_path,
        prompt_config_path=prompt_config_path,
        event_config_path=event_config_path,
        show_progress=show_progress,
    )
    return orchestrator.run(state)
