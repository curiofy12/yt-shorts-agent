"""
Finds today's candidate topic.

Strategy (in order of preference):
1. Google Trends realtime trending searches (via pytrends) - free, no key.
2. Fallback to a rotating list of evergreen high-interest topic categories
   if Trends is unavailable or rate-limited.

If CHANNEL_NICHE is set in .env, trending topics are filtered/biased toward
that niche so the channel stays on-brand instead of posting whatever is
trending regardless of fit.
"""
import random
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CHANNEL_NICHE

FALLBACK_TOPICS = [
    "a surprising psychology fact about human memory",
    "an unsolved mystery from history",
    "a mind-bending space fact",
    "a strange law of physics explained simply",
    "an animal ability that sounds fake but is real",
    "a historical event most people misunderstand",
    "a fact about the human body that sounds impossible",
    "a technology prediction from the past that came true",
    "an ocean mystery scientists can't fully explain",
    "a cognitive bias that affects daily decisions",
]


def get_trending_topics(max_results=10):
    """Returns a list of trending search terms, best-effort."""
    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl="en-US", tz=360)
        df = pytrends.trending_searches(pn="united_states")
        topics = df[0].tolist()[:max_results]
        if topics:
            return topics
    except Exception as e:
        print(f"[trends] pytrends unavailable ({e}), using fallback topics.")

    return random.sample(FALLBACK_TOPICS, k=min(max_results, len(FALLBACK_TOPICS)))


def pick_topic(recent_topics=None):
    """
    Picks one topic for today, avoiding repeats from recent_topics
    (a list of strings from posts_log.json).
    """
    recent_topics = recent_topics or []
    candidates = get_trending_topics()

    if CHANNEL_NICHE:
        # Bias: put the niche context alongside the raw trend so the script
        # writer can angle a trending term through the channel's lane.
        candidates = [f"{t} (angle this through: {CHANNEL_NICHE})" for t in candidates]

    for topic in candidates:
        if topic not in recent_topics:
            return topic

    # Everything overlapped with recent history; just take the first one.
    return candidates[0] if candidates else random.choice(FALLBACK_TOPICS)


if __name__ == "__main__":
    print(pick_topic())
