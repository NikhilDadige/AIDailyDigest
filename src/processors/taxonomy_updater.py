"""Taxonomy updater — applies Claude's proposals to config.yaml via git"""
import yaml
import subprocess
from pathlib import Path
from typing import Dict, List
from src.utils.logger import setup_logger

log = setup_logger("taxonomy")


def update_taxonomy(proposals: List[Dict], config: dict):
    if not proposals:
        return

    config_path = Path("config.yaml")
    if not config_path.exists():
        log.warning("config.yaml not found, skipping taxonomy update")
        return

    with open(config_path) as f:
        raw_config = yaml.safe_load(f)

    changes_made = []

    for proposal in proposals:
        action = proposal.get("action")
        target = proposal.get("target", "")
        parent = proposal.get("parent", "")
        rationale = proposal.get("rationale", "")

        if action == "add" and parent and target:
            taxonomy = raw_config.get("taxonomy", {})
            if parent in taxonomy:
                sub_topics = taxonomy[parent].get("sub_topics", {})
                if target not in sub_topics:
                    sub_topics[target] = {
                        "tool_types": [],
                        "examples": [],
                        "related_to": [],
                    }
                    taxonomy[parent]["sub_topics"] = sub_topics
                    changes_made.append(f"Added sub-topic '{target}' under '{parent}': {rationale}")
                    log.info(f"  Added: {target} -> {parent}")

        elif action == "remove" and target:
            taxonomy = raw_config.get("taxonomy", {})
            for main_id, main_data in taxonomy.items():
                subs = main_data.get("sub_topics", {})
                if target in subs:
                    del subs[target]
                    changes_made.append(f"Removed stale sub-topic '{target}': {rationale}")
                    log.info(f"  Removed: {target}")
                    break

    if changes_made:
        with open(config_path, "w") as f:
            yaml.dump(raw_config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        # Git commit the changes
        try:
            subprocess.run(["git", "add", "config.yaml"], check=True, capture_output=True)
            commit_msg = "taxonomy: auto-update\n\n" + "\n".join(f"- {c}" for c in changes_made)
            subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
            log.info(f"Committed {len(changes_made)} taxonomy changes")
        except subprocess.CalledProcessError as e:
            log.warning(f"Git commit failed: {e}")
