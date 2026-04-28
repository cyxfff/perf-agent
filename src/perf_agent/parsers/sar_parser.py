from __future__ import annotations

from datetime import datetime, timezone
import re

from perf_agent.models.observation import Observation
from perf_agent.utils.ids import new_id


TIME_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}$")


def parse_text(text: str, source: str, action_id: str | None = None) -> list[Observation]:
    rows: list[dict[str, object]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 8:
            continue
        if parts[0] == "Average:" and parts[1] != "CPU":
            cpu = parts[1]
            values = parts[2:8]
            kind = "average"
        elif TIME_PATTERN.match(parts[0]) and parts[1] != "CPU":
            cpu = parts[1]
            values = parts[2:8]
            kind = "sample"
        else:
            continue
        try:
            user, nice, system, iowait, steal, idle = (float(item) for item in values)
        except ValueError:
            continue
        rows.append(
            {
                "kind": kind,
                "cpu": cpu,
                "user": user,
                "system": system,
                "iowait": iowait,
                "idle": idle,
                "util": round(100.0 - idle, 2),
                "raw": line.strip(),
            }
        )

    if not rows:
        return []

    preferred_rows = [row for row in rows if row["kind"] == "average"] or rows
    all_row = next((row for row in preferred_rows if row["cpu"] == "all"), None)
    per_cpu_rows = [row for row in preferred_rows if row["cpu"] != "all"]
    peak_row = max(per_cpu_rows, key=lambda item: float(item["util"])) if per_cpu_rows else None
    timestamp = datetime.now(timezone.utc)

    observations: list[Observation] = []
    if all_row is not None:
        observations.extend(
            [
                _obs("system_cpu_utilization_pct", float(all_row["util"]), "percent", "cpu", "system", timestamp, action_id, str(all_row["raw"])),
                _obs("system_user_pct", float(all_row["user"]), "percent", "cpu", "system", timestamp, action_id, str(all_row["raw"])),
                _obs("system_system_pct", float(all_row["system"]), "percent", "cpu", "system", timestamp, action_id, str(all_row["raw"])),
                _obs("system_iowait_pct", float(all_row["iowait"]), "percent", "cpu", "system", timestamp, action_id, str(all_row["raw"])),
            ]
        )
    if peak_row is not None:
        observations.append(
            Observation(
                id=new_id("obs"),
                source=source,
                category="cpu",
                metric="system_peak_cpu_utilization_pct",
                value=float(peak_row["util"]),
                unit="percent",
                normalized_value=round(float(peak_row["util"]) / 100.0, 4),
                scope="system",
                timestamp=timestamp,
                labels={"action_id": action_id or "", "cpu": str(peak_row["cpu"])},
                raw_excerpt=str(peak_row["raw"]),
            )
        )
    return observations


def _obs(
    metric: str,
    value: float,
    unit: str,
    category: str,
    scope: str,
    timestamp,
    action_id: str | None,
    raw_excerpt: str,
) -> Observation:
    return Observation(
        id=new_id("obs"),
        source="sar",
        category=category,
        metric=metric,
        value=value,
        unit=unit,
        normalized_value=round(value / 100.0, 4) if unit == "percent" else None,
        scope=scope,
        timestamp=timestamp,
        labels={"action_id": action_id or ""},
        raw_excerpt=raw_excerpt,
    )
