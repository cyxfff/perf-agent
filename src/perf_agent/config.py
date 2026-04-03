from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class ToolConfig(BaseModel):
    enabled: bool = True
    timeout_sec: int = 60
    parser: str | None = None


class RuleConfig(BaseModel):
    conditions: list[str] = Field(default_factory=list)
    min_confidence: float = 0.6


class PromptTemplates(BaseModel):
    analyzer_prompt: str
    verifier_prompt: str
    reporter_prompt: str
    interactive_intake_prompt: str = (
        "You are the interactive intake layer for a performance analysis CLI.\n"
        "Read the current session context, normalized user message, attachments, and compacted recent history.\n"
        "Your job is to convert fuzzy user intent into a structured request.\n"
        "Do not invent file paths, commands, or PIDs that are not supported by the input.\n"
        "Prefer asking for clarification when the target program is still ambiguous.\n"
        "If the user clearly wants to launch analysis, set should_run_analysis=true.\n"
        "Return structured JSON only."
    )


class EventIntentConfig(BaseModel):
    preferred_tools: list[str] = Field(default_factory=list)
    preferred_events: list[str] = Field(default_factory=list)
    fallback_events: list[str] = Field(default_factory=list)
    mode: str = "stat"
    call_graph_modes: list[str] = Field(default_factory=list)


class SandboxRuntimeConfig(BaseModel):
    enabled: bool = True
    kind: str = "template"
    executable: str | None = None
    detection: str = "which"
    description: str | None = None
    template: list[str] = Field(default_factory=list)
    extra_args: list[str] = Field(default_factory=list)
    read_only_paths: list[str] = Field(default_factory=list)
    writable_paths: list[str] = Field(default_factory=list)
    workdir: str | None = "{cwd}"
    network_access: bool = True
    variables: dict[str, str] = Field(default_factory=dict)


class SafetyConfig(BaseModel):
    sandbox_enabled: bool = False
    default_runtime: str = "auto"
    preferred_runtimes: list[str] = Field(default_factory=lambda: ["none"])
    fallback_to_none: bool = True
    runtimes: dict[str, SandboxRuntimeConfig] = Field(default_factory=dict)


def load_yaml(path: str | Path) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def load_tool_configs(path: str | Path | None = None) -> dict[str, ToolConfig]:
    config_path = Path(path) if path is not None else project_root() / "configs" / "tools.yaml"
    raw = load_yaml(config_path)
    return {name: ToolConfig.model_validate(payload) for name, payload in raw.items()}


def load_rule_configs(path: str | Path | None = None) -> dict[str, RuleConfig]:
    config_path = Path(path) if path is not None else project_root() / "configs" / "rules.yaml"
    raw = load_yaml(config_path)
    return {name: RuleConfig.model_validate(payload) for name, payload in raw.items()}


def load_prompt_templates(path: str | Path | None = None) -> PromptTemplates:
    config_path = Path(path) if path is not None else project_root() / "configs" / "prompts.yaml"
    raw = load_yaml(config_path)
    return PromptTemplates.model_validate(raw)


def load_event_intent_configs(path: str | Path | None = None) -> dict[str, EventIntentConfig]:
    config_path = Path(path) if path is not None else project_root() / "configs" / "events.yaml"
    raw = load_yaml(config_path)
    return {name: EventIntentConfig.model_validate(payload) for name, payload in raw.items()}


def load_safety_config(path: str | Path | None = None) -> SafetyConfig:
    config_path = Path(path) if path is not None else project_root() / "configs" / "safety.yaml"
    raw = load_yaml(config_path) if config_path.exists() else {}
    return SafetyConfig.model_validate(raw)
