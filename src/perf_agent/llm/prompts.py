from __future__ import annotations

from perf_agent.config import PromptTemplates, load_prompt_templates


def load_prompts(config_path: str | None = None) -> PromptTemplates:
    return load_prompt_templates(config_path)
