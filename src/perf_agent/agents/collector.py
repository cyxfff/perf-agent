from __future__ import annotations

from perf_agent.models.state import AnalysisState
from perf_agent.storage.json_store import JSONArtifactStore
from perf_agent.tools.runner import ToolRunner
from perf_agent.utils.progress import ConsoleProgress


class Collector:
    def __init__(self, runner: ToolRunner, store: JSONArtifactStore, progress: ConsoleProgress | None = None) -> None:
        self.runner = runner
        self.store = store
        self.progress = progress or ConsoleProgress(enabled=False)

    def run(self, state: AnalysisState) -> AnalysisState:
        if not state.pending_actions:
            state.add_audit("collector", "no pending actions to execute")
            return state

        pending = list(state.pending_actions)
        state.pending_actions = []

        for action in pending:
            action.command = self.runner.get_tool(action.tool).build_command(state, action)
            self.progress.action_start(action)
            result = self.runner.run_action(action, state, self.store)
            self.progress.action_end(action, result)
            if result.stdout_path is not None:
                state.artifacts[f"{action.id}.stdout"] = result.stdout_path
            if result.stderr_path is not None:
                state.artifacts[f"{action.id}.stderr"] = result.stderr_path
            for index, path in enumerate(result.artifact_paths):
                state.artifacts[f"{action.id}.artifact.{index}"] = path

            state.actions_taken.append(action)
            state.add_audit(
                "collector",
                "executed action",
                action_id=action.id,
                tool=action.tool,
                intent=action.intent,
                success=result.success,
                exit_code=result.exit_code,
                duration_sec=result.duration_sec,
            )

            if not result.success and not action.retryable:
                state.add_error(
                    f"Non-retryable action {action.id} failed with exit code {result.exit_code}: {result.error_message or ''}".strip()
                )

        return state
