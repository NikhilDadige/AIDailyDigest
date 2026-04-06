"""Config loader — reads config.yaml and resolves env vars"""
import os
import re
import yaml
from pathlib import Path


def _resolve_env_vars(obj):
    if isinstance(obj, str):
        pattern = r'\$\{(\w+)\}'
        matches = re.findall(pattern, obj)
        for var in matches:
            val = os.environ.get(var, "")
            obj = obj.replace(f"${{{var}}}", val)
        return obj
    elif isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(i) for i in obj]
    return obj


def load_config(path: str = None) -> dict:
    if path is None:
        path = Path(__file__).parent.parent.parent / "config.yaml"
    with open(path) as f:
        config = yaml.safe_load(f)
    return _resolve_env_vars(config)


def get_taxonomy_flat(config: dict) -> dict:
    """Returns a flat dict of sub_topic_id -> {main_topic, tool_types, examples, related_to}"""
    flat = {}
    for main_id, main_data in config["taxonomy"].items():
        for sub_id, sub_data in main_data.get("sub_topics", {}).items():
            flat[sub_id] = {
                "main_topic": main_id,
                "main_description": main_data["description"],
                "tool_types": sub_data.get("tool_types", []),
                "examples": sub_data.get("examples", []),
                "related_to": sub_data.get("related_to", []),
            }
    return flat


def get_taxonomy_summary(config: dict) -> str:
    """Returns a concise text summary of taxonomy for LLM prompts"""
    lines = []
    for main_id, main_data in config["taxonomy"].items():
        lines.append(f"\n## {main_id}: {main_data['description']}")
        for sub_id, sub_data in main_data.get("sub_topics", {}).items():
            types = ", ".join(sub_data.get("tool_types", []))
            lines.append(f"  - {sub_id}: [{types}]")
    return "\n".join(lines)
