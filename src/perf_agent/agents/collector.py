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
            if action.request_id:
                request = state.find_request(action.request_id)
                if request is not None and request.status == "tool_selected":
                    request.status = "collecting"
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

            self._refresh_request_status(state, action.request_id)
            if not result.success and not action.retryable:
                state.add_error(
                    f"Non-retryable action {action.id} failed with exit code {result.exit_code}: {result.error_message or ''}".strip()
                )

        return state

    def _refresh_request_status(self, state: AnalysisState, request_id: str | None) -> None:
        if request_id is None:
            return
        request = state.find_request(request_id)
        plan = state.find_execution_plan(request_id)
        if request is None:
            return
        related = [action for action in state.actions_taken if action.request_id == request_id]
        still_pending = any(action.request_id == request_id for action in state.pending_actions)
        if still_pending:
            request.status = "collecting"
            if plan is not None:
                plan.status = "actions_created"
            return
        if related and all(action.status == "done" for action in related):
            request.status = "completed"
            if plan is not None:
                plan.status = "completed"
            return
        if any(action.status == "failed" for action in related):
            request.status = "failed"
            if plan is not None:
                plan.status = "failed"
