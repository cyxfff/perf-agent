from __future__ import annotations

from datetime import datetime, timezone
import re

from perf_agent.models.observation import Observation
from perf_agent.utils.ids import new_id


AVERAGE_PATTERN = re.compile(
    r"Average:\s+\d+\s+\d+\s+([\d.]+)\s+([\d.]+)\s+[\d.]+\s+([\d.]+)\s+([\d.]+)\s+\d+\s+(.+)"
)


def parse_text(text: str, source: str, action_id: str | None = None) -> list[Observation]:
    match = AVERAGE_PATTERN.search(text)
    if not match:
        return []

    usr, system, wait, cpu, command = match.groups()
    timestamp = datetime.now(timezone.utc)
    rows = [
        ("usr_pct", float(usr), "cpu"),
        ("system_pct", float(system), "cpu"),
        ("wait_pct", float(wait), "io"),
        ("cpu_utilization_pct", float(cpu), "cpu"),
    ]
    return [
        Observation(
            id=new_id("obs"),
            source=source,
            category=category,
            metric=metric,
            value=value,
            unit="percent",
            normalized_value=round(value / 100.0, 4),
            scope="process",
            timestamp=timestamp,
            labels={"action_id": action_id or "", "command": command.strip()},
            raw_excerpt=command.strip(),
        )
        for metric, value, category in rows
    ]
