from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

import yaml

from perf_agent.models.state import AnalysisTask


KEY_ALIASES = {
    "goal": "goal",
    "目标": "goal",
    "symptom": "goal",
    "command": "target_cmd",
    "cmd": "target_cmd",
    "命令": "target_cmd",
    "运行命令": "target_cmd",
    "binary": "executable_path",
    "binary_path": "executable_path",
    "exe": "executable_path",
    "executable": "executable_path",
    "程序": "executable_path",
    "pid": "target_pid",
    "source": "source_dir",
    "source_dir": "source_dir",
    "源码": "source_dir",
    "cwd": "cwd",
    "workdir": "cwd",
    "工作目录": "cwd",
    "label": "workload_label",
    "workload": "workload_label",
    "场景": "workload_label",
    "max_rounds": "max_rounds",
    "max_iterations": "max_rounds",
}


def load_task_note(path: str | Path) -> AnalysisTask:
    """Load a skill-like Markdown/text task note into an AnalysisTask.

    Supported formats:
    - YAML front matter between leading --- markers.
    - Simple `key: value` lines in Markdown or plain text.
    - Shell-style command lines beginning with `$ ` when no command key exists.
    """

    note_path = Path(path)
    text = note_path.read_text(encoding="utf-8")
    payload: dict[str, Any] = {}

    front_matter, body = _split_front_matter(text)
    if front_matter:
        parsed = yaml.safe_load(front_matter) or {}
        if isinstance(parsed, dict):
            payload.update(parsed)

    payload.update(_parse_key_values(body))
    payload = _normalize_payload(payload, body)
    return AnalysisTask.model_validate(payload)


def _split_front_matter(text: str) -> tuple[str | None, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1 :])
    return None, text


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        if line.startswith(("-", "*")):
            line = line[1:].strip()
        if ":" not in line and "：" not in line:
            continue
        delimiter = ":" if ":" in line else "："
        key, value = line.split(delimiter, 1)
        key = key.strip().lower().replace(" ", "_")
        value = value.strip().strip("`")
        if key and value:
            values[key] = value
    return values


def _normalize_payload(raw: dict[str, Any], body: str) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    env: dict[str, str] = {}

    for key, value in raw.items():
        canonical = KEY_ALIASES.get(str(key).strip().lower().replace(" ", "_"), key)
        if canonical == "target_cmd":
            normalized["target_cmd"] = _coerce_command(value)
        elif canonical == "target_pid":
            normalized["target_pid"] = int(value)
        elif canonical == "max_rounds":
            rounds = max(1, int(value))
            normalized["max_verification_rounds"] = max(0, rounds - 1)
        elif canonical == "env":
            env.update(_coerce_env(value))
        else:
            normalized[str(canonical)] = value

    if "target_cmd" not in normalized:
        shell_line = _find_shell_line(body)
        if shell_line:
            normalized["target_cmd"] = shlex.split(shell_line)

    if "goal" not in normalized:
        first_sentence = _first_descriptive_line(body)
        if first_sentence:
            normalized["goal"] = first_sentence

    if env:
        normalized["env"] = env

    return normalized


def _coerce_command(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return shlex.split(str(value))


def _coerce_env(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items()}
    parsed: dict[str, str] = {}
    for chunk in str(value).replace(",", "\n").splitlines():
        if "=" not in chunk:
            continue
        key, item = chunk.split("=", 1)
        parsed[key.strip()] = item.strip()
    return parsed


def _find_shell_line(text: str) -> str | None:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("$ "):
            return line[2:].strip()
    return None


def _first_descriptive_line(text: str) -> str | None:
    for raw_line in text.splitlines():
        line = raw_line.strip().strip("#").strip()
        if not line or line.startswith(("---", "$", "```")):
            continue
        if ":" in line or "：" in line:
            continue
        return line
    return None
