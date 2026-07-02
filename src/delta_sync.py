"""
Delta sync: compares each article's updated_at timestamp against a local
sync_state.json to decide added / updated / skipped, so we only re-upload
files that actually changed.
"""

import json
import os

STATE_FILE = "sync_state.json"


def load_state(path: str = STATE_FILE) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict, path: str = STATE_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def compute_delta(articles: list, state: dict):
    """
    Returns (to_process, new_state, counts) where:
    - to_process: list of article dicts that need (re)upload
    - new_state: updated state dict {article_id: updated_at}
    - counts: {"added": int, "updated": int, "skipped": int}
    """
    to_process = []
    new_state = dict(state)
    counts = {"added": 0, "updated": 0, "skipped": 0}

    for art in articles:
        art_id = str(art["id"])
        updated_at = art.get("updated_at", "")
        prev_updated_at = state.get(art_id)

        if prev_updated_at is None:
            counts["added"] += 1
            to_process.append(art)
        elif prev_updated_at != updated_at:
            counts["updated"] += 1
            to_process.append(art)
        else:
            counts["skipped"] += 1

        new_state[art_id] = updated_at

    return to_process, new_state, counts