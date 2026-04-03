from __future__ import annotations

from pathlib import Path

import yaml

from perf_agent.models.state import AnalysisState
from perf_agent.security.sandbox import SandboxManager


def test_sandbox_manager_wraps_command_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / "safety.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "sandbox_enabled": True,
                "preferred_runtimes": ["demo_template"],
                "fallback_to_none": True,
                "runtimes": {
                    "demo_template": {
                        "enabled": True,
                        "kind": "template",
                        "detection": "always",
                        "template": ["sandbox-demo", "--cwd", "{cwd}", "--"],
                    },
                    "none": {
                        "enabled": True,
                        "kind": "none",
                        "detection": "always",
                    },
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    manager = SandboxManager(str(config_path))
    state = AnalysisState(run_id="run_test", target_cmd=["/bin/echo", "hello"], cwd=str(tmp_path))

    wrapped, resolution = manager.wrap_target_command(state.target_cmd, state)

    assert resolution.applied is True
    assert resolution.runtime_name == "demo_template"
    assert wrapped[:3] == ["sandbox-demo", "--cwd", str(tmp_path)]
    assert wrapped[-2:] == ["/bin/echo", "hello"]


def test_sandbox_manager_falls_back_to_none_when_runtime_unavailable(tmp_path: Path) -> None:
    config_path = tmp_path / "safety.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "sandbox_enabled": True,
                "preferred_runtimes": ["missing_runtime"],
                "fallback_to_none": True,
                "runtimes": {
                    "missing_runtime": {
                        "enabled": True,
                        "kind": "template",
                        "executable": "definitely-missing-sandbox",
                        "detection": "which",
                        "template": ["definitely-missing-sandbox", "--"],
                    },
                    "none": {
                        "enabled": True,
                        "kind": "none",
                        "detection": "always",
                    },
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    manager = SandboxManager(str(config_path))
    state = AnalysisState(run_id="run_test", target_cmd=["/bin/echo", "hello"], cwd=str(tmp_path))

    wrapped, resolution = manager.wrap_target_command(state.target_cmd, state)

    assert resolution.runtime_name == "none"
    assert resolution.applied is False
    assert resolution.fallback_used is True
    assert wrapped == ["/bin/echo", "hello"]
