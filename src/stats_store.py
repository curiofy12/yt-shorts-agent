"""
Reads and writes data/video_stats.json: {video_id: stats dict}.

The weekly report refreshes it; the daily pipeline reads it to decide
which topics are performing best.
"""
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STATS_PATH


def load_stats():
    if os.path.exists(STATS_PATH):
        with open(STATS_PATH) as f:
            return json.load(f)
    return {}


def save_stats(stats):
    os.makedirs(os.path.dirname(STATS_PATH), exist_ok=True)
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=2, sort_keys=True)


def with_stats(log, stats):
    """Copies of the post log entries with their latest stats attached."""
    merged = []
    for entry in log:
        e = dict(entry)
        if entry.get("video_id") in stats:
            e["stats"] = stats[entry["video_id"]]
        merged.append(e)
    return merged
