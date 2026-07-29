"""
Reads the accumulated posts_log.json (topics, titles, hooks, and their
performance stats) and asks Claude to identify patterns and recommend
concrete changes: which topics/hooks/formats are outperforming, what to
try next, what to drop.
"""
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANTHROPIC_API_KEY
import anthropic

SYSTEM_PROMPT = """You are a YouTube Shorts growth analyst. You'll be given a
JSON log of recently posted shorts with their topic, title, hook, and
performance metrics (views, watch time, avg view duration, subs gained).

Write a concise report with these sections:
1. **What's working** — specific topics/hooks/formats correlated with better
   retention or views, citing the actual data points
2. **What's underperforming** — same, for the weak end
3. **3 concrete changes to try next** — specific and actionable (e.g. "shorten
   hook to under 2 seconds", "test topic category X", "post at a different time")
4. **One experiment for next week** — a single testable change

Be honest if the sample size is too small to draw real conclusions — don't
fabricate confidence. Ground every claim in the numbers given; do not invent
statistics not present in the data."""


def generate_insights_report(posts_log: list) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Recent posts and performance:\n{json.dumps(posts_log, indent=2)}",
            }
        ],
    )
    return message.content[0].text
