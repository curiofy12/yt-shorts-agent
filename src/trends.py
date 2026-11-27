"""
Finds today's candidate topic.

Note: pytrends' realtime trending-search endpoint has been unreliable
(Google has changed/removed it), so this pulls from a large curated
topic pool instead of live trends. This is intentional -- a broken
"live trends" call that silently falls back to a tiny topic list is
worse than a large, deliberately varied static pool.

If CHANNEL_NICHE is set in .env, topics are angled toward that niche so
the channel stays on-brand.
"""
import math
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
    "a lost civilization and what happened to it",
    "an everyday object with a surprising origin story",
    "a scientific discovery that was initially ridiculed",
    "a survival ability humans still have but rarely use",
    "a mathematical pattern that shows up in nature",
    "a famous historical figure's little-known side career",
    "a food that used to be considered poisonous or dangerous",
    "an ancient invention more advanced than expected",
    "a language fact that changes how you think about words",
    "a weather phenomenon that seems impossible but is real",
    "a myth about the human brain that's actually false",
    "an animal migration that defies explanation",
    "a historical coincidence that seems too strange to be true",
    "a psychological experiment with a surprising result",
    "a geographic feature that shouldn't exist but does",
    "a common misconception about space that's actually wrong",
    "an invention that was created completely by accident",
    "a hidden pattern in how cities or societies grow",
    "a sense or ability certain animals have that humans don't",
    "a historical event that almost changed the world but didn't",
    "a fact about sleep that most people don't know",
    "an economic concept explained through a strange real example",
    "a natural phenomenon that inspired a major invention",
    "a decoding of an ancient mystery that took centuries to solve",
    "a fact about the internet or technology's hidden infrastructure",
    "a strange law that's still on the books somewhere",
    "an unexpected connection between two unrelated fields of science",
    "a record-breaking natural event and what caused it",
    "a historical figure who was more radical than people realize",
    "a common phrase or idiom with a surprising true origin",
    "an animal behavior that looks like it shouldn't be possible",
    "a scientific theory that was proven right decades later",
    "a place on Earth that feels like it shouldn't exist",
    "a psychological trick advertisers or media use on you",
    "an ancient technology we still don't fully understand",
    # Added after the first insights reports: space/physics paradoxes and
    # high-stakes history were the channel's strongest performers.
    "a space paradox about speed, time or distance that breaks your intuition",
    "a physics fact about how your own body is moving through space right now",
    "something about black holes that sounds impossible but is true",
    "a fact about the scale of the universe that's hard to believe",
    "what would actually happen to the human body in space",
    "a fact about light or time that breaks common sense",
    "a moment in history when one person's decision saved millions of lives",
    "a near-disaster from history that almost nobody knows about",
    "a Cold War close call that almost ended the world",
    "a small mistake in history that changed the outcome of a war",
    "a single day in history that changed everything",
    "a fact about how old something really is that sounds like time travel",
]

# How many recent posts a topic must sit out before it can be used again.
# Each topic is a broad theme and Claude picks a different specific story
# each time (it's told which titles already exist), so a short cooldown
# is enough to keep things varied.
TOPIC_COOLDOWN_POSTS = 12

# Stats younger than this aren't trusted yet (views are still coming in).
MIN_AGE_DAYS_FOR_SCORING = 3


def base_topic(topic: str) -> str:
    """Strips the niche suffix so the same theme is scored as one topic."""
    return topic.split(" (angle this through:")[0]


def topic_weights(log, stats):
    """
    Gives each topic a weight based on how its past videos did, so topics
    that get more views come up more often. Topics with no data yet get a
    small bonus so new ideas still get tried.

    Uses log(views) so one viral outlier doesn't dominate, and clamps the
    weights so weak topics still appear now and then (things change).
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    per_topic = {}
    for entry in log:
        s = stats.get(entry.get("video_id"))
        if not isinstance(s, dict) or "views" not in s:
            continue
        try:
            posted = datetime.fromisoformat(entry["posted_at"])
        except (KeyError, ValueError):
            continue
        if (now - posted).days < MIN_AGE_DAYS_FOR_SCORING:
            continue
        per_topic.setdefault(base_topic(entry.get("topic", "")), []).append(
            math.log1p(max(s.get("views", 0), 0))
        )

    if not per_topic:
        return {}

    all_scores = [x for xs in per_topic.values() for x in xs]
    overall = sum(all_scores) / len(all_scores)

    weights = {}
    for topic, scores in per_topic.items():
        # Shrink toward the overall average when a topic has few videos
        n = len(scores)
        avg = (sum(scores) + overall * 2) / (n + 2)
        weights[topic] = min(max(math.exp(avg - overall), 0.3), 4.0)
    return weights


def pick_topic(recent_topics=None, log=None, stats=None):
    """
    Picks one topic for the next video: skips topics used in the last few
    posts, then chooses randomly with better-performing topics weighted
    more heavily.
    """
    recent = {base_topic(t) for t in (recent_topics or [])[-TOPIC_COOLDOWN_POSTS:]}
    weights = topic_weights(log or [], stats or {})

    available = [t for t in FALLBACK_TOPICS if t not in recent] or FALLBACK_TOPICS
    w = [weights.get(t, 1.5) for t in available]  # 1.5 = untested bonus
    topic = random.choices(available, weights=w, k=1)[0]

    if weights:
        best = sorted(weights.items(), key=lambda kv: -kv[1])[:3]
        print("[trends] strongest topics so far: " + "; ".join(f"{t} (x{v:.1f})" for t, v in best))

    if CHANNEL_NICHE:
        topic = f"{topic} (angle this through: {CHANNEL_NICHE})"
    return topic


if __name__ == "__main__":
    print(pick_topic())
