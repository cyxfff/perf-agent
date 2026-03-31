from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import re

from perf_agent.models.observation import Observation
from perf_agent.utils.ids import new_id


HOT_SYMBOL_PATTERN = re.compile(r"^\s*([\d.]+)%\s+[\d.]+%\s+\[.\]\s+(.+?)(?:\s{2,}[-\d].*)?$")
SECTION_PATTERN = re.compile(r"^===\s+([a-z_]+)\s+===$", re.MULTILINE)
SAMPLE_HEADER_PATTERN = re.compile(r"^(?P<comm>\S+)\s+(?P<pid>\d+)/(?P<tid>\d+)\s+(?P<time>[\d.]+):\s*$")
FRAME_PATTERN = re.compile(r"^\s*(?P<ip>[0-9a-f]+)\s+(?P<sym>.+?)\s+\((?P<dso>.+?)\)\s*$")


def parse_text(text: str, source: str, action_id: str | None = None) -> list[Observation]:
    timestamp = datetime.now(timezone.utc)
    report_text, script_text = _split_sections(text)
    observations: list[Observation] = []
    observations.extend(_parse_report(report_text, source, action_id, timestamp))
    observations.extend(_parse_script(script_text, source, action_id, timestamp))
    return observations


def _split_sections(text: str) -> tuple[str, str]:
    report_parts: list[str] = []
    script_parts: list[str] = []
    current: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, current
        if not buffer or current is None:
            buffer = []
            return
        content = "\n".join(buffer).strip()
        if current == "report":
            report_parts.append(content)
        elif current == "script":
            script_parts.append(content)
        buffer = []

    for line in text.splitlines():
        section_match = SECTION_PATTERN.match(line.strip())
        if section_match:
            flush()
            current = section_match.group(1)
            continue
        buffer.append(line)
    flush()
    return ("\n".join(report_parts), "\n".join(script_parts))


def _parse_report(text: str, source: str, action_id: str | None, timestamp: datetime) -> list[Observation]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    observations: list[Observation] = []
    rank = 0
    for line in lines:
        match = HOT_SYMBOL_PATTERN.match(line)
        if not match:
            continue
        rank += 1
        value = float(match.group(1))
        observations.append(
            Observation(
                id=new_id("obs"),
                source=source,
                category="callgraph",
                metric="hot_symbol_pct",
                value=value,
                unit="percent",
                normalized_value=round(value / 100.0, 4),
                scope="function",
                timestamp=timestamp,
                labels={
                    "action_id": action_id or "",
                    "symbol": match.group(2).strip(),
                    "rank": str(rank),
                },
                raw_excerpt=line,
            )
        )
        if rank >= 8:
            break
    return observations


def _parse_script(text: str, source: str, action_id: str | None, timestamp: datetime) -> list[Observation]:
    blocks = [block for block in re.split(r"\n\s*\n", text) if block.strip()]
    if not blocks:
        return []

    total_samples = 0
    process_counts: Counter[tuple[str, str]] = Counter()
    thread_counts: Counter[tuple[str, str, str]] = Counter()
    frame_counts: Counter[tuple[str, str, str, str, str, str]] = Counter()
    process_order: list[tuple[str, str]] = []
    relation_map: dict[tuple[str, str], str] = {}

    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        header_match = SAMPLE_HEADER_PATTERN.match(lines[0].strip())
        if not header_match:
            continue
        comm = header_match.group("comm")
        pid = header_match.group("pid")
        tid = header_match.group("tid")
        total_samples += 1

        if _is_accountable_comm(comm):
            process_key = (comm, pid)
            if process_key not in process_counts:
                process_order.append(process_key)
            process_counts[process_key] += 1
            thread_counts[(comm, pid, tid)] += 1
            frame = _first_user_frame(lines[1:])
            if frame is not None:
                frame_counts[(frame["ip"], frame["sym"], frame["dso"], comm, pid, tid)] += 1

    observations: list[Observation] = [
        Observation(
            id=new_id("obs"),
            source=source,
            category="callgraph",
            metric="callgraph_samples",
            value=total_samples,
            unit="count",
            scope="callchain",
            timestamp=timestamp,
            labels={"action_id": action_id or ""},
            raw_excerpt=blocks[0].splitlines()[0].strip(),
        )
    ]

    if process_counts:
        primary_by_comm: dict[str, str] = {}
        for comm, pid in process_order:
            primary_by_comm.setdefault(comm, pid)
        for comm, pid in process_order:
            relation_map[(comm, pid)] = "primary" if primary_by_comm.get(comm) == pid else "child_or_peer"

    process_total = sum(process_counts.values())
    for rank, ((comm, pid), count) in enumerate(process_counts.most_common(8), start=1):
        pct = 100.0 * count / process_total if process_total else 0.0
        observations.extend(
            [
                Observation(
                    id=new_id("obs"),
                    source=source,
                    category="callgraph",
                    metric="process_sample_count",
                    value=count,
                    unit="count",
                    scope="process",
                    timestamp=timestamp,
                    labels={
                        "action_id": action_id or "",
                        "comm": comm,
                        "pid": pid,
                        "rank": str(rank),
                        "relation": relation_map.get((comm, pid), "unknown"),
                    },
                    raw_excerpt=f"{comm} pid={pid} samples={count}",
                ),
                Observation(
                    id=new_id("obs"),
                    source=source,
                    category="callgraph",
                    metric="process_sample_pct",
                    value=round(pct, 4),
                    unit="percent",
                    normalized_value=round(pct / 100.0, 4),
                    scope="process",
                    timestamp=timestamp,
                    labels={
                        "action_id": action_id or "",
                        "comm": comm,
                        "pid": pid,
                        "rank": str(rank),
                        "relation": relation_map.get((comm, pid), "unknown"),
                    },
                    raw_excerpt=f"{comm} pid={pid} share={pct:.2f}%",
                ),
            ]
        )

    thread_total = sum(thread_counts.values())
    for rank, ((comm, pid, tid), count) in enumerate(thread_counts.most_common(10), start=1):
        pct = 100.0 * count / thread_total if thread_total else 0.0
        observations.extend(
            [
                Observation(
                    id=new_id("obs"),
                    source=source,
                    category="callgraph",
                    metric="thread_sample_count",
                    value=count,
                    unit="count",
                    scope="thread",
                    timestamp=timestamp,
                    labels={
                        "action_id": action_id or "",
                        "comm": comm,
                        "pid": pid,
                        "tid": tid,
                        "rank": str(rank),
                        "thread_role": "main_thread" if pid == tid else "worker_thread",
                    },
                    raw_excerpt=f"{comm} pid={pid} tid={tid} samples={count}",
                ),
                Observation(
                    id=new_id("obs"),
                    source=source,
                    category="callgraph",
                    metric="thread_sample_pct",
                    value=round(pct, 4),
                    unit="percent",
                    normalized_value=round(pct / 100.0, 4),
                    scope="thread",
                    timestamp=timestamp,
                    labels={
                        "action_id": action_id or "",
                        "comm": comm,
                        "pid": pid,
                        "tid": tid,
                        "rank": str(rank),
                        "thread_role": "main_thread" if pid == tid else "worker_thread",
                    },
                    raw_excerpt=f"{comm} pid={pid} tid={tid} share={pct:.2f}%",
                ),
            ]
        )

    frame_total = sum(frame_counts.values())
    for rank, ((ip, symbol, dso, comm, pid, tid), count) in enumerate(frame_counts.most_common(10), start=1):
        pct = 100.0 * count / frame_total if frame_total else 0.0
        observations.append(
            Observation(
                id=new_id("obs"),
                source=source,
                category="callgraph",
                metric="hot_frame_sample_pct",
                value=round(pct, 4),
                unit="percent",
                normalized_value=round(pct / 100.0, 4),
                scope="function",
                timestamp=timestamp,
                labels={
                    "action_id": action_id or "",
                    "symbol": symbol,
                    "dso": dso,
                    "ip": ip,
                    "comm": comm,
                    "pid": pid,
                    "tid": tid,
                    "rank": str(rank),
                },
                raw_excerpt=f"{ip} {symbol} ({dso})",
            )
        )

    return observations


def _first_user_frame(lines: list[str]) -> dict[str, str] | None:
    for line in lines:
        match = FRAME_PATTERN.match(line)
        if not match:
            continue
        dso = match.group("dso").strip()
        if dso in {"[kernel.kallsyms]", "[unknown]"}:
            continue
        return {
            "ip": match.group("ip").strip(),
            "sym": match.group("sym").strip(),
            "dso": dso,
        }
    return None


def _is_accountable_comm(comm: str) -> bool:
    lowered = comm.lower()
    return lowered not in {"perf-exec", "perf"} and not lowered.startswith("perf-")
