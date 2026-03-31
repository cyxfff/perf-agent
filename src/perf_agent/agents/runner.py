from __future__ import annotations

import os
from pathlib import Path

from perf_agent.models.state import AnalysisState
from perf_agent.storage.json_store import JSONArtifactStore

SOURCE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hpp",
    ".py",
    ".rs",
    ".go",
    ".java",
    ".kt",
    ".js",
    ".ts",
    ".tsx",
}


class Runner:
    def __init__(self, store: JSONArtifactStore) -> None:
        self.store = store

    def run(self, state: AnalysisState) -> AnalysisState:
        state.target_cmd = self._resolve_target_command(state)
        target_metadata = {
            "executable_path": state.executable_path,
            "target_args": state.target_args,
            "target_cmd": state.target_cmd,
            "target_pid": state.target_pid,
            "workload_label": state.workload_label,
            "source_dir": state.source_dir,
            "build_cmd": state.build_cmd,
            "cwd": state.cwd,
        }
        target_path = self.store.save_json("target.json", target_metadata)
        state.artifacts["target.json"] = str(target_path)

        if state.source_dir:
            source_info = self._scan_source_tree(state.source_dir)
            state.source_files = source_info["files"]
            state.source_language_hints = source_info["languages"]
            manifest_path = self.store.save_json("source_manifest.json", source_info)
            state.artifacts["source_manifest.json"] = str(manifest_path)

        state.add_audit(
            "runner",
            "prepared runtime target",
            target_cmd=state.target_cmd,
            source_file_count=len(state.source_files),
        )
        return state

    def _resolve_target_command(self, state: AnalysisState) -> list[str]:
        if state.target_cmd:
            return state.target_cmd
        if state.executable_path:
            return [state.executable_path, *state.target_args]
        if state.target_pid is not None:
            return []
        raise ValueError("AnalysisState must include target_cmd, executable_path, or target_pid.")

    def _scan_source_tree(self, source_dir: str) -> dict[str, list[str] | int]:
        root = Path(source_dir).expanduser().resolve()
        files: list[str] = []
        languages: set[str] = set()
        if not root.exists():
            return {"root": str(root), "files": [], "languages": [], "file_count": 0}

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SOURCE_EXTENSIONS:
                continue
            files.append(str(path))
            hint = self._language_hint(path)
            if hint:
                languages.add(hint)
            if len(files) >= 500:
                break

        return {
            "root": str(root),
            "files": files,
            "languages": sorted(languages),
            "file_count": len(files),
        }

    def _language_hint(self, path: Path) -> str | None:
        mapping = {
            ".c": "c",
            ".cc": "cpp",
            ".cpp": "cpp",
            ".cxx": "cpp",
            ".h": "c-family",
            ".hpp": "cpp",
            ".py": "python",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".kt": "kotlin",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        return mapping.get(path.suffix.lower())
