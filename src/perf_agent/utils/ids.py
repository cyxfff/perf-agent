from __future__ import annotations

from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def new_run_id() -> str:
    return new_id("run")
