from __future__ import annotations

from pathlib import Path

from perf_agent.tasks import load_task_note


def test_load_task_note_from_front_matter(tmp_path: Path) -> None:
    note = tmp_path / "task.md"
    note.write_text(
        """---
goal: Diagnose low IPC
command: python demo.py --size 10
source_dir: src
max_rounds: 3
---

# demo
""",
        encoding="utf-8",
    )

    task = load_task_note(note)

    assert task.goal == "Diagnose low IPC"
    assert task.target_cmd == ["python", "demo.py", "--size", "10"]
    assert task.source_dir == "src"
    assert task.max_verification_rounds == 2


def test_load_task_note_from_plain_key_values(tmp_path: Path) -> None:
    note = tmp_path / "task.txt"
    note.write_text(
        """目标: Analyze branch misses
命令: ./demo --branchy
工作目录: /tmp/work
""",
        encoding="utf-8",
    )

    task = load_task_note(note)

    assert task.goal == "Analyze branch misses"
    assert task.target_cmd == ["./demo", "--branchy"]
    assert task.cwd == "/tmp/work"
