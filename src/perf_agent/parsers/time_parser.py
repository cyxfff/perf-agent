from __future__ import annotations

from datetime import datetime, timezone
import re

from perf_agent.models.observation import Observation
from perf_agent.utils.ids import new_id


PATTERNS = [
    ("user_time_sec", "cpu", "seconds", re.compile(r"User time \(seconds\):\s+([\d.]+)")),
    ("system_time_sec", "cpu", "seconds", re.compile(r"System time \(seconds\):\s+([\d.]+)")),
    ("cpu_utilization_pct", "cpu", "percent", re.compile(r"Percent of CPU this job got:\s+(\d+)%")),
    ("max_rss_kb", "memory", "kb", re.compile(r"Maximum resident set size \(kbytes\):\s+(\d+)")),
    ("major_faults", "memory", "count", re.compile(r"Major \(requiring I/O\) page faults:\s+(\d+)")),
    ("voluntary_context_switches", "scheduler", "count", re.compile(r"Voluntary context switches:\s+(\d+)")),
    ("involuntary_context_switches", "scheduler", "count", re.compile(r"Involuntary context switches:\s+(\d+)")),
]


def parse_text(text: str, source: str, action_id: str | None = None) -> list[Observation]:
    timestamp = datetime.now(timezone.utc)
    observations: list[Observation] = []
    for metric, category, unit, pattern in PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        raw = match.group(1)
        value = float(raw) if "." in raw else int(raw)
        observations.append(
            Observation(
                id=new_id("obs"),
                source=source,
                category=category,
                metric=metric,
                value=value,
                unit=unit,
                normalized_value=round(value / 100.0, 4) if unit == "percent" else None,
                scope="process",
                timestamp=timestamp,
                labels={"action_id": action_id or ""},
                raw_excerpt=_find_excerpt(text, pattern),
            )
        )
    elapsed_value = _parse_elapsed_seconds(text)
    if elapsed_value is not None:
        observations.append(
            Observation(
                id=new_id("obs"),
                source=source,
                category="system",
                metric="elapsed_time_sec",
                value=elapsed_value,
                unit="seconds",
                normalized_value=None,
                scope="process",
                timestamp=timestamp,
                labels={"action_id": action_id or ""},
                raw_excerpt=_find_elapsed_excerpt(text),
            )
        )
    return observations


def _find_excerpt(text: str, pattern: re.Pattern[str]) -> str | None:
    for line in text.splitlines():
        if pattern.search(line):
            return line.strip()
    return None


def _parse_elapsed_seconds(text: str) -> float | None:
    pattern = re.compile(r"Elapsed \(wall clock\) time .*:\s+([0-9:.]+)")
    match = pattern.search(text)
    if not match:
        return None
    raw = match.group(1).strip()
    parts = raw.split(":")
    try:
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return round(hours * 3600 + minutes * 60 + seconds, 4)
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return round(minutes * 60 + seconds, 4)
        return round(float(raw), 4)
    except ValueError:
        return None


def _find_elapsed_excerpt(text: str) -> str | None:
    for line in text.splitlines():
        if "Elapsed (wall clock) time" in line:
            return line.strip()
    return None
