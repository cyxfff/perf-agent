from __future__ import annotations

from typing import Literal


RunStatus = Literal[
    "init",
    "running",
    "profiling_environment",
    "planning",
    "tool_selecting",
    "collecting",
    "parsing",
    "analyzing",
    "verifying",
    "source_analyzing",
    "reporting",
    "done",
    "failed",
]

TERMINAL_STATUSES = {"done", "failed"}
