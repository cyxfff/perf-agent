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


class EventIntentConfig(BaseModel):
    preferred_tools: list[str] = Field(default_factory=list)
    preferred_events: list[str] = Field(default_factory=list)
    fallback_events: list[str] = Field(default_factory=list)
    mode: str = "stat"
    call_graph_modes: list[str] = Field(default_factory=list)


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
