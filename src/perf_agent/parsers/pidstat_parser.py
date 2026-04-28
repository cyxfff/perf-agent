from __future__ import annotations

from datetime import datetime, timezone
import re

from perf_agent.models.observation import Observation
from perf_agent.utils.ids import new_id


AVERAGE_PATTERN = re.compile(
    r"Average:\s+\d+\s+\d+\s+([\d.]+)\s+([\d.]+)\s+[\d.]+\s+([\d.]+)\s+([\d.]+)\s+\d+\s+(.+)"
)
WAIT_PATTERN = re.compile(
    r"^(?:Average:\s+)?(?:\d{2}:\d{2}:\d{2}(?:\s+[AP]M)?\s+)?\d+\s+\d+\s+([\d.]+)\s+([\d.]+)\s+(.+)$"
)


def parse_text(text: str, source: str, action_id: str | None = None) -> list[Observation]:
    timestamp = datetime.now(timezone.utc)
    match = AVERAGE_PATTERN.search(text)
    if match:
        usr, system, wait, cpu, command = match.groups()
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

    observations: list[Observation] = []
    for line in text.splitlines():
        stripped = line.strip()
        wait_match = WAIT_PATTERN.match(stripped)
        if not wait_match:
            continue
        cswch, nvcswch, command = wait_match.groups()
        total = float(cswch) + float(nvcswch)
        observations.extend(
            [
                Observation(
                    id=new_id("obs"),
                    source=source,
                    category="scheduler",
                    metric="context_switches_per_sec",
                    value=round(total, 4),
                    unit="per_sec",
                    normalized_value=None,
                    scope="thread",
                    timestamp=timestamp,
                    labels={"action_id": action_id or "", "command": command.strip()},
                    raw_excerpt=stripped,
                ),
                Observation(
                    id=new_id("obs"),
                    source=source,
                    category="scheduler",
                    metric="voluntary_context_switches_per_sec",
                    value=float(cswch),
                    unit="per_sec",
                    normalized_value=None,
                    scope="thread",
                    timestamp=timestamp,
                    labels={"action_id": action_id or "", "command": command.strip()},
                    raw_excerpt=stripped,
                ),
                Observation(
                    id=new_id("obs"),
                    source=source,
                    category="scheduler",
                    metric="involuntary_context_switches_per_sec",
                    value=float(nvcswch),
                    unit="per_sec",
                    normalized_value=None,
                    scope="thread",
                    timestamp=timestamp,
                    labels={"action_id": action_id or "", "command": command.strip()},
                    raw_excerpt=stripped,
                ),
            ]
        )
    return observations
